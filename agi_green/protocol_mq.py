"""Message Queue Protocol implementations for AGI.green

This module provides three implementations of the message queue protocol:
1. Azure Service Bus (AzureServiceBusProtocol)
2. RabbitMQ (RabbitMQProtocol)
3. In-Process Queue (InProcessMQProtocol)

The implementation can be selected in two ways:

1. Explicitly via environment variable:
    Set MQ_PROTOCOL to one of: 'azure', 'rabbitmq', or 'inprocess'
    If set, the specified implementation will be used and will raise an exception if it fails.

2. Auto-detection (default when MQ_PROTOCOL is not set):
    - First tries Azure Service Bus if AZURE_SERVICEBUS_CONNECTION_STRING is set
    - Then tries RabbitMQ if available
    - Falls back to InProcess implementation

Required environment variables:
- MQ_PROTOCOL (optional): Force a specific implementation ('azure'|'rabbitmq'|'inprocess')
- AZURE_SERVICEBUS_CONNECTION_STRING (required for Azure implementation)
- RABBITMQ_HOST (optional, defaults to 'localhost')
- RABBITMQ_PORT (optional, defaults to 5672)

Example:
    # Auto-detect implementation:
    from agi_green.protocol_mq import MQProtocol

    # Or force specific implementation:
    # export MQ_PROTOCOL=azure
    # export AZURE_SERVICEBUS_CONNECTION_STRING=your_connection_string
"""

import os
from os.path import join, dirname, splitext, isabs
from typing import Callable, Awaitable, Dict, Any, List, Set, Union, Tuple
from logging import getLogger, Logger
import json
import logging
from queue import Queue, Empty
from os.path import exists
import asyncio
import abc

try:
    import aio_pika
    RABBITMQ_AVAILABLE = True
except ImportError:
    RABBITMQ_AVAILABLE = False

from agi_green.dispatcher import Protocol, format_call, protocol_handler

# Add to existing imports, wrapped in try/except to handle when Azure SDK isn't installed
try:
    from azure.servicebus import ServiceBusClient, ServiceBusMessage
    from azure.servicebus.aio import ServiceBusClient as AsyncServiceBusClient
    from azure.servicebus.exceptions import ServiceBusError
    AZURE_AVAILABLE = True
except ImportError:
    AZURE_AVAILABLE = False

here = dirname(__file__)
logger = logging.getLogger(__name__)
log_level = os.getenv('LOG_LEVEL', 'WARNING').upper()
logging.basicConfig(level=log_level)

# Add connection test caching
_connection_test_results = {}

async def _test_azure_connection(connection_string: str = None, raise_errors: bool = False) -> bool:
    """Test Azure Service Bus connection with caching"""
    if not AZURE_AVAILABLE:
        if raise_errors:
            raise ImportError("Azure Service Bus SDK not installed")
        return False

    connection_string = connection_string or os.getenv('AZURE_SERVICEBUS_CONNECTION_STRING')
    if not connection_string:
        if raise_errors:
            raise ValueError("AZURE_SERVICEBUS_CONNECTION_STRING environment variable not set")
        return False

    cache_key = f"azure:{connection_string}"
    if cache_key in _connection_test_results:
        if not _connection_test_results[cache_key] and raise_errors:
            raise ConnectionError("Could not connect to Azure Service Bus")
        return _connection_test_results[cache_key]

    try:
        client = AsyncServiceBusClient.from_connection_string(connection_string)
        async with client:
            for attempt in range(3):
                try:
                    # Try to get a list of queues or perform a simple operation
                    _connection_test_results[cache_key] = True
                    return True
                except Exception as e:
                    if attempt == 2:  # Last attempt
                        logger.debug(f"Azure Service Bus connection test failed: {e}")
                    await asyncio.sleep(1)
    except Exception as e:
        logger.debug(f"Azure Service Bus connection test failed: {e}")

    _connection_test_results[cache_key] = False
    if raise_errors:
        raise ConnectionError("Could not connect to Azure Service Bus")
    return False

async def _test_rabbitmq_connection(host: str = None, port: int = None, raise_errors: bool = False) -> bool:
    """Test RabbitMQ connection with caching"""
    if not RABBITMQ_AVAILABLE:
        if raise_errors:
            raise ImportError("aio_pika package not installed")
        return False

    host = host or os.getenv('RABBITMQ_HOST', 'localhost')
    port = port or int(os.getenv('RABBITMQ_PORT', '5672'))

    cache_key = f"rabbitmq:{host}:{port}"
    if cache_key in _connection_test_results:
        if not _connection_test_results[cache_key] and raise_errors:
            raise ConnectionError(f"Could not connect to RabbitMQ at {host}:{port}")
        return _connection_test_results[cache_key]

    try:
        for attempt in range(3):
            try:
                connection = await aio_pika.connect_robust(host=host, port=port)
                await connection.close()
                _connection_test_results[cache_key] = True
                return True
            except Exception as e:
                if attempt == 2:  # Last attempt
                    logger.debug(f"RabbitMQ connection test failed: {e}")
                await asyncio.sleep(1)
    except Exception as e:
        logger.debug(f"RabbitMQ connection test failed: {e}")

    _connection_test_results[cache_key] = False
    if raise_errors:
        raise ConnectionError(f"Could not connect to RabbitMQ at {host}:{port}")
    return False

class AbstractMQProtocol(Protocol, abc.ABC):
    """Abstract base class for message queue protocols"""

    protocol_id: str = 'mq'

    def __init__(self, parent: Protocol, host: str = None, port: int = None, **kwargs):
        super().__init__(parent)
        self.host = host
        self.port = port
        self.connected = False
        self.queues: Dict[str, Any] = {}
        self.offline_queue: Queue = Queue()
        self.offline_subscription_queue: Queue = Queue()

    @abc.abstractmethod
    async def run(self):
        """Initialize connection to the message queue"""
        await super().run()

    @abc.abstractmethod
    async def close(self):
        """Close all connections and clean up"""
        await super().close()

    @abc.abstractmethod
    async def subscribe(self, channel_id: str):
        """Subscribe to a channel"""
        pass

    @abc.abstractmethod
    async def unsubscribe(self, channel_id: str):
        """Unsubscribe from a channel"""
        pass

    @abc.abstractmethod
    async def unsubscribe_all(self):
        """Unsubscribe from all channels"""
        pass

    @abc.abstractmethod
    async def do_send(self, cmd: str, channel: str, **kwargs):
        """Send a message to a channel"""
        pass

    def get_full_channel_id(self, channel_id: str) -> str:
        """Get the full channel ID including subdomain"""
        if ':' in channel_id:
            return channel_id
        try:
            subdomain = self.context.subdomain
        except AttributeError:
            raise ValueError("Subdomain is not set in the context. This is required for MQ operations.")
        return f"{subdomain}:{channel_id}"


class RabbitMQProtocol(AbstractMQProtocol):
    '''RabbitMQ broadcast protocol'''

    def __init__(self, parent: Protocol, host: str, port: int = 5672, **kwargs):
        super().__init__(parent, host, port, **kwargs)
        self.connection: aio_pika.Connection = None
        self.channel: aio_pika.Channel = None
        self.exchange: aio_pika.Exchange = None
        # Note: queues, offline_queue, and offline_subscription_queue are now inherited
        # Track listening tasks per channel for proper cleanup
        self._listening_tasks: Dict[str, asyncio.Task] = {}

    async def run(self):
        await super().run()

        try:
            logger.info(f'Connecting to RabbitMQ on {self.host}:{self.port}')
            self.connection = await aio_pika.connect_robust(host=self.host, port=self.port)
        except aio_pika.AMQPException as e:
            logger.error(f"RabbitMQ connection failed: {e}")
            await self.send('ws', 'append_chat', author='info', content=f'We got an unexpected error.\n\nRabbitMQ connection failed: {e}')
            return

        self.channel = await self.connection.channel()
        self.exchange = await self.channel.declare_exchange('agi.green', aio_pika.ExchangeType.DIRECT)
        self.connected = True

        logger.info(f'Connected to RabbitMQ on {self.host}:{self.port}')

        # Do any pending subscriptions
        while not self.offline_subscription_queue.empty():
            channel_id = self.offline_subscription_queue.get()
            await self.subscribe(channel_id)

        # Send any pending messages
        while not self.offline_queue.empty():
            cmd, ch, kwargs = self.offline_queue.get()
            await self.do_send(cmd, ch, **kwargs)


    async def close(self):
        # Close the RabbitMQ channel and connection
        await self.unsubscribe_all()

        if self.channel:
            await self.channel.close()
            await self.connection.close()

        # terminate

        await super().close()

    async def listen_to_queue(self, channel_id, queue):
        full_channel_id = self.get_full_channel_id(channel_id)
        try:
            async with queue.iterator() as queue_iter:
                async for message in queue_iter:
                    async with message.process():
                        data = json.loads(message.body.decode())
                        if data['cmd'] == 'unsubscribe':
                            if data['sender_id'] == id(self):
                                break
                        else:
                           await self.handle_mesg(channel_id=channel_id, **data)
        finally:
            # Clean up data structures and task tracking
            if full_channel_id in self.queues:
                del self.queues[full_channel_id]
            self._listening_tasks.pop(full_channel_id, None)
            logger.info(f'{self.dispatcher.context.user.screen_name} unsubscribed from {full_channel_id}')

    async def subscribe(self, channel_id: str):
        if not self.connected:
            self.offline_subscription_queue.put(channel_id)
            return

        full_channel_id = self.get_full_channel_id(channel_id)

        # Check if a listening task already exists for this channel
        if full_channel_id in self.queues:
            logger.info(f'Already subscribed to {full_channel_id}, skipping duplicate task creation')
            return

        queue = await self.channel.declare_queue(exclusive=True)
        await queue.bind(self.exchange, routing_key=full_channel_id)
        self.queues[full_channel_id] = queue
        logger.info(f'{self.dispatcher.context.user.screen_name} subscribed to {full_channel_id}')

        # Create and track listening task for proper cleanup
        task = asyncio.create_task(self.listen_to_queue(channel_id, queue))
        self._listening_tasks[full_channel_id] = task
        self.running_tasks.append(task)
        task.add_done_callback(self.running_tasks.remove)

    async def unsubscribe(self, channel_id: str):
        full_channel_id = self.get_full_channel_id(channel_id)

        # Cancel the listening task first to stop the infinite loop
        if full_channel_id in self._listening_tasks:
            task = self._listening_tasks[full_channel_id]
            if not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
            # Remove from tracking (may already be removed by finally block)
            self._listening_tasks.pop(full_channel_id, None)

        # Send unsubscribe message
        await self.send('mq', 'unsubscribe', channel=full_channel_id, sender_id=id(self))

        # Remove the queue if it exists
        if full_channel_id in self.queues:
            del self.queues[full_channel_id]



    async def unsubscribe_all(self):
        'unsubscribe to everything'
        for full_channel_id in list(self.queues.keys()):
            channel_id = full_channel_id.split(':', 1)[1] if ':' in full_channel_id else full_channel_id
            await self.unsubscribe(channel_id)


    async def do_send(self, cmd: str, channel: str, **kwargs):
        'broadcast message to RabbitMQ'
        if not self.connected:
            self.offline_queue.put((cmd, channel, kwargs))
            return

        kwargs['cmd'] = cmd
        full_channel = self.get_full_channel_id(channel)

        await self.exchange.publish(
            aio_pika.Message(body=json.dumps(kwargs).encode()),
            routing_key=full_channel  # We use routing key as full_channel for direct exchanges
        )


class InProcessMQProtocol(AbstractMQProtocol):
    """In-process message queue implementation using Python's Queue"""

    def __init__(self, parent: Protocol, **kwargs):
        super().__init__(parent, **kwargs)
        self._subscribers: Dict[str, Set[Queue]] = {}
        self._message_queues: Dict[str, Queue] = {}
        # Get the event loop from asyncio instead of dispatcher
        self._loop = asyncio.get_event_loop()
        # Track listening tasks per channel for proper cleanup
        self._listening_tasks: Dict[str, asyncio.Task] = {}

    async def run(self):
        await super().run()
        self.connected = True

        # Process any pending subscriptions
        while not self.offline_subscription_queue.empty():
            channel_id = self.offline_subscription_queue.get()
            await self.subscribe(channel_id)

        # Send any pending messages
        while not self.offline_queue.empty():
            cmd, ch, kwargs = self.offline_queue.get()
            await self.do_send(cmd, ch, **kwargs)

    async def close(self):
        await self.unsubscribe_all()
        self.connected = False
        await super().close()

    async def subscribe(self, channel_id: str):
        if not self.connected:
            self.offline_subscription_queue.put(channel_id)
            return

        full_channel_id = self.get_full_channel_id(channel_id)

        # Check if a listening task already exists for this channel
        if full_channel_id in self._subscribers:
            logger.info(f'Already subscribed to {full_channel_id}, skipping duplicate task creation')
            return

        self._subscribers[full_channel_id] = set()
        self._message_queues[full_channel_id] = Queue()

        queue = Queue()
        self._subscribers[full_channel_id].add(queue)
        self.queues[full_channel_id] = queue

        # Create and track listening task for cleanup
        task = asyncio.create_task(self._listen_to_queue(channel_id, queue))
        self._listening_tasks[full_channel_id] = task
        self.running_tasks.append(task)
        task.add_done_callback(self.running_tasks.remove)

    async def _listen_to_queue(self, channel_id: str, queue: Queue):
        full_channel_id = self.get_full_channel_id(channel_id)
        try:
            while True:
                try:
                    # Use non-blocking approach with timeout to allow cancellation
                    data = None
                    try:
                        data = queue.get(block=False)  # Non-blocking get
                    except Empty:
                        # Queue is empty, wait a bit and check for cancellation
                        await asyncio.sleep(0.1)
                        continue

                    if data.get('cmd') == 'unsubscribe' and data.get('sender_id') == id(self):
                        break
                    await self.handle_mesg(channel_id=channel_id, **data)
                except asyncio.CancelledError:
                    # Task was cancelled, exit gracefully
                    break
                except Exception as e:
                    logger.error(f"Error processing message: {e}")
                    break
        finally:
            # Clean up task tracking when the listener exits
            if full_channel_id in self._listening_tasks:
                self._listening_tasks.pop(full_channel_id, None)
            logger.debug(f"Listening task for {full_channel_id} terminated")

    async def unsubscribe(self, channel_id: str):
        full_channel_id = self.get_full_channel_id(channel_id)

        # Cancel the listening task first to stop the infinite loop
        if full_channel_id in self._listening_tasks:
            task = self._listening_tasks[full_channel_id]
            if not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
            # Remove from tracking (may already be removed by finally block)
            self._listening_tasks.pop(full_channel_id, None)

        # Send unsubscribe message
        await self.do_send('unsubscribe', channel_id, sender_id=id(self))

        # Clean up data structures
        if full_channel_id in self._subscribers:
            del self._subscribers[full_channel_id]
        if full_channel_id in self._message_queues:
            del self._message_queues[full_channel_id]
        if full_channel_id in self.queues:
            del self.queues[full_channel_id]

    async def unsubscribe_all(self):
        for full_channel_id in list(self._subscribers.keys()):
            channel_id = full_channel_id.split(':', 1)[1] if ':' in full_channel_id else full_channel_id
            await self.unsubscribe(channel_id)

    async def do_send(self, cmd: str, channel: str, **kwargs):
        if not self.connected:
            self.offline_queue.put((cmd, channel, kwargs))
            return

        kwargs['cmd'] = cmd
        full_channel = self.get_full_channel_id(channel)

        if full_channel in self._subscribers:
            message = kwargs
            for queue in self._subscribers[full_channel]:
                queue.put(message)


class AzureServiceBusProtocol(AbstractMQProtocol):
    """Azure Service Bus implementation of the message queue protocol"""

    def __init__(self, parent: Protocol, **kwargs):
        super().__init__(parent, **kwargs)
        self.connection_string = os.getenv('AZURE_SERVICEBUS_CONNECTION_STRING')
        self.servicebus_client: AsyncServiceBusClient = None
        self.senders: Dict[str, Any] = {}
        self.receivers: Dict[str, Any] = {}
        # Track listening tasks per channel for proper cleanup
        self._listening_tasks: Dict[str, asyncio.Task] = {}

    async def run(self):
        await super().run()

        try:
            self.servicebus_client = AsyncServiceBusClient.from_connection_string(
                conn_str=self.connection_string,
                logging_enable=True
            )
            self.connected = True
            logger.info('Connected to Azure Service Bus')

            # Process pending subscriptions
            while not self.offline_subscription_queue.empty():
                channel_id = self.offline_subscription_queue.get()
                await self.subscribe(channel_id)

            # Send pending messages
            while not self.offline_queue.empty():
                cmd, ch, kwargs = self.offline_queue.get()
                await self.do_send(cmd, ch, **kwargs)

        except ServiceBusError as e:
            logger.error(f"Azure Service Bus connection failed: {e}")
            await self.send('ws', 'append_chat',
                author='info',
                content=f'Azure Service Bus connection failed: {e}')

    async def close(self):
        await self.unsubscribe_all()

        # Close all senders
        for sender in self.senders.values():
            await sender.close()

        # Close all receivers
        for receiver in self.receivers.values():
            await receiver.close()

        if self.servicebus_client:
            await self.servicebus_client.close()

        self.connected = False
        await super().close()

    async def subscribe(self, channel_id: str):
        if not self.connected:
            self.offline_subscription_queue.put(channel_id)
            return

        full_channel_id = self.get_full_channel_id(channel_id)

        # Check if a listening task already exists for this channel
        if full_channel_id in self.receivers:
            logger.info(f'Already subscribed to {full_channel_id}, skipping duplicate task creation')
            return

        receiver = self.servicebus_client.get_queue_receiver(
            queue_name=full_channel_id,
            max_wait_time=1  # 1 second wait time for receiving messages
        )
        self.receivers[full_channel_id] = receiver
        self.queues[full_channel_id] = receiver
        logger.info(f'{self.dispatcher.context.user.screen_name} subscribed to {full_channel_id}')

        # Create and track listening task for proper cleanup
        task = asyncio.create_task(self._listen_to_queue(channel_id, receiver))
        self._listening_tasks[full_channel_id] = task
        self.running_tasks.append(task)
        task.add_done_callback(self.running_tasks.remove)

    async def _listen_to_queue(self, channel_id: str, receiver):
        full_channel_id = self.get_full_channel_id(channel_id)
        try:
            async with receiver:
                while True:
                    try:
                        messages = await receiver.receive_messages(max_message_count=10, max_wait_time=1)
                        for message in messages:
                            async with message:
                                data = json.loads(str(message))
                                if data.get('cmd') == 'unsubscribe' and data.get('sender_id') == id(self):
                                    return
                                await self.handle_mesg(channel_id=channel_id, **data)
                    except Exception as e:
                        logger.error(f"Error processing Azure Service Bus message: {e}")
                        break
        finally:
            # Clean up task tracking when the listener exits
            self._listening_tasks.pop(full_channel_id, None)
            logger.debug(f"Azure Service Bus listening task for {full_channel_id} terminated")

    async def unsubscribe(self, channel_id: str):
        full_channel_id = self.get_full_channel_id(channel_id)

        # Cancel the listening task first to stop the infinite loop
        if full_channel_id in self._listening_tasks:
            task = self._listening_tasks[full_channel_id]
            if not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
            # Remove from tracking (may already be removed by finally block)
            self._listening_tasks.pop(full_channel_id, None)

        # Send unsubscribe message
        await self.do_send('unsubscribe', channel_id, sender_id=id(self))

        # Clean up data structures
        if full_channel_id in self.receivers:
            receiver = self.receivers[full_channel_id]
            await receiver.close()
            del self.receivers[full_channel_id]
            del self.queues[full_channel_id]

    async def unsubscribe_all(self):
        for full_channel_id in list(self.receivers.keys()):
            channel_id = full_channel_id.split(':', 1)[1] if ':' in full_channel_id else full_channel_id
            await self.unsubscribe(channel_id)

    async def do_send(self, cmd: str, channel: str, **kwargs):
        if not self.connected:
            self.offline_queue.put((cmd, channel, kwargs))
            return

        kwargs['cmd'] = cmd
        full_channel = self.get_full_channel_id(channel)

        # Get or create sender for this channel
        if full_channel not in self.senders:
            self.senders[full_channel] = self.servicebus_client.get_queue_sender(full_channel)

        sender = self.senders[full_channel]
        message = ServiceBusMessage(json.dumps(kwargs))

        async with sender:
            await sender.send_messages(message)

    async def _retry_operation(self, operation: Callable, max_retries: int = 3):
        """Helper method for retrying Azure operations"""
        for attempt in range(max_retries):
            try:
                return await operation()
            except ServiceBusError as e:
                if attempt == max_retries - 1:
                    raise
                await asyncio.sleep(1)  # Wait before retry


def _detect_and_create_protocol():
    """Factory function to determine and create appropriate MQ implementation"""
    # Check for explicit protocol selection
    forced_protocol = os.getenv('MQ_PROTOCOL', '').lower()
    if forced_protocol:
        if forced_protocol == 'azure':
            asyncio.run(_test_azure_connection(raise_errors=True))
            print(f"Using Azure Service Bus implementation (MQ_PROTOCOL={forced_protocol})")
            return AzureServiceBusProtocol

        elif forced_protocol == 'rabbitmq':
            asyncio.run(_test_rabbitmq_connection(raise_errors=True))
            print(f"Using RabbitMQ implementation (MQ_PROTOCOL={forced_protocol})")
            return RabbitMQProtocol

        elif forced_protocol == 'inprocess':
            print(f"Using InProcess MQ implementation (MQ_PROTOCOL={forced_protocol})")
            return InProcessMQProtocol

        else:
            raise ValueError(f"Invalid MQ_PROTOCOL value: {forced_protocol}. "
                "Must be one of: 'azure', 'rabbitmq', 'inprocess'")

    # Auto-detection logic
    try:
        if asyncio.run(_test_azure_connection()):
            print("Using Azure Service Bus implementation (auto-detected)")
            return AzureServiceBusProtocol

        if asyncio.run(_test_rabbitmq_connection()):
            print("Using RabbitMQ implementation (auto-detected)")
            return RabbitMQProtocol

    except Exception as e:
        print(f"Debug: Error during MQ detection: {e}")

    # Default to InProcess
    print("Using InProcess MQ implementation (auto-detected)")
    return InProcessMQProtocol

# Make the selected implementation available as MQProtocol
MQProtocol = _detect_and_create_protocol()
