'''
dispatcher
'''

import re
import time
import asyncio
from collections import defaultdict
from typing import Callable, Awaitable, Dict, Any, List, Optional, Union
import json
import websockets
import aio_pika
from aiohttp import web

# RabbitMQ port 5672
# VScode debug port 5678
# Browser port -p option (default=8000)
# WebSocket port is browser port + 1 (default=8001)

class DispatcherMeta(type):
    """Metaclass to handle method registration based on naming convention."""

    registed_methods: Dict[str, Dict[str, Callable[..., Awaitable[None]]]]
    re_on_cmd = re.compile(r'^on_(\w+?)_(\w+)$')
    re_arun = re.compile(r'^arun_(\w+)$')
    re_close = re.compile(r'^close_(\w+)$')

    def __init__(cls, name, bases, attrs):
        super().__init__(name, bases, attrs)

        # Initialize the registry for the class
        cls.registered_methods = defaultdict(dict)
        cls.registered_aruns = []
        cls.registered_closes = []

        # Register methods with the "on_" prefix
        for key in dir(cls):
            method = getattr(cls, key)
            m = DispatcherMeta.re_on_cmd.match(key)
            if m:
                proto, cmd = m.groups()
                cls.registered_methods[proto][cmd] = method
                print (f'DispatcherMeta registered {proto}:{cmd} => {cls.__name__}.{key}(...)')
                continue
            m = DispatcherMeta.re_arun.match(key)
            if m:
                proto = m.groups()[0]
                cls.registered_aruns.append(method)
                print (f'DispatcherMeta registered {proto}:arun => {cls.__name__}.{key}(...)')
                continue
            m = DispatcherMeta.re_close.match(key)
            if m:
                proto = m.groups()[0]
                cls.registered_closes.append(method)
                print (f'DispatcherMeta registered {proto}:close => {cls.__name__}.{key}(...)')
                continue

class Protocol_http_ws:
    '''
    Mixin class to handle http server and websocket connection
    Use port for http server
    Use port+1 for websocket port
    '''

    def __init__(self, port:int=8000, **kwargs):
        super().__init__(**kwargs)
        self.http_port = port
        self.http_app:web.Application = None
        self.http_runner:web.AppRunner = None
        self.http_site:web.TCPSite = None
        self.ws_port = port+1
        self.ws_connected = set()
        self.ws_cmd_handlers = self.registered_methods['ws']

    async def arun_ws(self):
        # Serve static http content from index.html
        self.http_app = web.Application()
        self.http_app.router.add_get('/', self.handle_get_root_request)
        self.http_app.router.add_static('/', path='./static', name='static')
        self.http_runner = web.AppRunner(self.http_app)
        await self.http_runner.setup()
        self.http_site = web.TCPSite(self.http_runner, '0.0.0.0', self.http_port)
        await websockets.serve(self.ws_handle_connection, '0.0.0.0', self.ws_port)
        await self.http_site.start()

    async def close_ws(self):
        # Close all WebSocket connections
        for ws in self.ws_connected:
            await ws.close()
        self.ws_connected.clear()

        # Stop the aiohttp site
        if self.http_site:
            await self.http_site.stop()

        # Shutdown and cleanup the aiohttp app
        if self.http_app:
            await self.http_app.shutdown()
            await self.http_app.cleanup()

        # Finally, cleanup the AppRunner
        if self.http_runner:
            await self.http_runner.cleanup()

    async def handle_get_root_request(self, request):
        substitutions = {
            '__TIMESTAMP__': str(time.time()),
        }

        print(f'GET /')
        with open('./static/index.html', 'r') as file:
            content = file.read()
            for key, value in substitutions.items():
                content = content.replace(key, value)
            return web.Response(text=content, content_type='text/html')

    async def ws_handle_connection(self, websocket, path):
        'Register websocket connection and wait for messages'
        self.ws_connected.add(websocket)
        try:
            await self.ws_cmd_handlers['connect'](self)
            async for mesg in websocket:
                data = json.loads(mesg)
                await self.handle_ws_mesg(**data)
        finally:
            # Unregister websocket connection
            self.ws_connected.remove(websocket)

    async def send_ws(self, cmd:str, **kwargs):
        'send message to browser via websocket'
        kwargs['cmd'] = cmd
        for ws in self.ws_connected:
            await ws.send(json.dumps(kwargs))

    async def handle_ws_mesg(self, cmd:str, **kwargs):
        'receive message from browser via websocket - overload this method'
        print(f"ws received: {cmd} {kwargs}")
        # call registered handler
        if cmd in self.ws_cmd_handlers:
            await self.ws_cmd_handlers[cmd](self, **kwargs)
        else:
            print(f"no handler for ws cmd '{cmd}'")



class Protocol_mq:
    '''
    Mixin class to handle RabbitMQ broadcast protocol
    '''

    registed_methods: Dict[str, Dict[str, Callable[..., Awaitable[None]]]]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.mq_connection: aio_pika.Connection = None
        self.mq_channel: aio_pika.Channel = None
        self.mq_exchange: aio_pika.Exchange = None
        self.mq_queue: aio_pika.Queue = None
        self.mq_cmd_handlers = self.registered_methods['mq']

    async def arun_mq(self):
        try:
            self.mq_connection = await aio_pika.connect_robust("amqp://guest:guest@rabbitmq/")
        except aio_pika.AMQPException as e:
            print(f"RabbitMQ connection failed: {e}")
            return

        self.mq_channel = await self.mq_connection.channel()

        # Declare a fanout exchange
        self.mq_exchange = await self.mq_channel.declare_exchange('chat', aio_pika.ExchangeType.FANOUT)

        # Declare a queue with a random name, exclusive to this connection
        self.mq_queue = await self.mq_channel.declare_queue(exclusive=True)

        # Bind the queue to the exchange, to receive all messages
        await self.mq_queue.bind(self.mq_exchange)
        await self.receive_mq_mesg(),

    async def close_mq(self):
        # Close the RabbitMQ channel and connection
        if self.mq_channel:
            await self.mq_channel.close()
            await self.mq_connection.close()

    async def send_mq(self, cmd:str, **kwargs):
        'broadcast message to RabbitMQ'
        kwargs['cmd'] = cmd
        await self.mq_exchange.publish(
            aio_pika.Message(body=json.dumps(kwargs).encode()),
            routing_key='',  # ignored for fanout exchanges
        )

    async def receive_mq_mesg(self):
        'receive messages from RabbitMQ'
        async with self.mq_queue.iterator() as queue_iter:
            async for message in queue_iter:
                async with message.process():
                    await self.handle_mq_mesg(**json.loads(message.body.decode()))

    async def handle_mq_mesg(self, cmd:str, **kwargs):
        'receive message from RabbitMQ - overload this method'
        print('mq received: {kwargs}')
        # call registered handler
        if cmd in self.mq_cmd_handlers:
            await self.mq_cmd_handlers[cmd](self, **kwargs)
        else:
            print(f"no handler for mq cmd '{cmd}'")



class Dispatcher(metaclass=DispatcherMeta):
    '''
    Manages the connection to RabbitMQ and WebSocket connection to browser.
    '''

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def run(self):
        loop = asyncio.get_event_loop()
        try:
            loop.run_until_complete(self.arun())
        except Exception as e:
            print (e)
            raise
        finally:
            loop.run_until_complete(self.close())
            loop.close()

    async def arun(self):
        # Run all registered async run methods in parallel
        await asyncio.gather(*(m(self) for m in self.registered_aruns))

    async def close(self):
        # Run all registered async close methods in parallel
        await asyncio.gather(*(m(self) for m in self.registered_closes))


