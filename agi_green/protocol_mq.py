import os
from os.path import join, dirname, splitext, isabs
from typing import Callable, Awaitable, Dict, Any, List, Set, Union, Tuple
from logging import getLogger, Logger
import json
import logging
from queue import Queue
from os.path import exists

import aio_pika

from agi_green.dispatcher import Protocol, format_call, protocol_handler

here = dirname(__file__)
logger = logging.getLogger(__name__)
log_level = os.getenv('LOG_LEVEL', 'WARNING').upper()
logging.basicConfig(level=log_level)


class RabbitMQProtocol(Protocol):
    '''
    RabbitMQ broadcast protocol
    '''

    protocol_id: str = 'mq'

    def __init__(self, host:str, port:int=5672, **kwargs):
        super().__init__(**kwargs)
        self.host = host
        self.port = port
        self.connection: aio_pika.Connection = None
        self.channel: aio_pika.Channel = None
        self.exchange: aio_pika.Exchange = None
        self.queues: Dict[str, aio_pika.Queue] = {}  # Store queues per channel
        self.offline_queue: Queue = Queue() # queue for messages pending connection
        self.offline_subscription_queue: Queue = Queue() # queue for subscriptions pending connection
        self.connected = False

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
        async with queue.iterator() as queue_iter:
            async for message in queue_iter:
                async with message.process():
                    data = json.loads(message.body.decode())
                    if data['cmd'] == 'unsubscribe':
                        if data['sender_id'] == id(self):
                            break
                    else:
                       await self.handle_mesg(channel_id=channel_id, **data)

        del self.queues[channel_id]
        logger.info(f'{self._root.username} unsubscribed from {channel_id}')

    async def subscribe(self, channel_id: str):
        if not self.connected:
            self.offline_subscription_queue.put(channel_id)
            return

        if channel_id not in self.queues:
            queue = await self.channel.declare_queue(exclusive=True)
            await queue.bind(self.exchange, routing_key=channel_id)
            self.queues[channel_id] = queue
            logger.info(f'{self._root.username} subscribed to {channel_id}')

            self.add_task(self.listen_to_queue(channel_id, queue))

    async def unsubscribe(self, channel_id: str):
        await self.send('mq', 'unsubscribe', channel=channel_id, sender_id=id(self))

    async def unsubscribe_all(self):
        'unsubscribe to everything'
        for channel_id in list(self.queues.keys()):
            await self.unsubscribe(channel_id)


    async def do_send(self, cmd: str, channel: str, **kwargs):
        'broadcast message to RabbitMQ'
        if not self.connected:
            self.offline_queue.put((cmd, channel, kwargs))
            return

        kwargs['cmd'] = cmd

        await self.exchange.publish(
            aio_pika.Message(body=json.dumps(kwargs).encode()),
            routing_key=channel  # We use routing key as channel_id for direct exchanges
        )

