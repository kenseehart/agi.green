'''
implementation of ws, mq and http protocols
'''

import os
from os.path import join, dirname
import time
import shutil
import yaml
from typing import Callable, Awaitable, Dict, Any, List, Set, Union, Tuple
from logging import getLogger, Logger
import json
import asyncio
import aiofiles

import websockets
from websockets.legacy.server import WebSocketServerProtocol
import aio_pika
from aiohttp import web
import openai

from dispatcher import Protocol, format_call, logger
from config import Config

from queue import Queue

here = dirname(__file__)

# RabbitMQ port 5672
# VScode debug port 5678
# Browser port -p option (default=8000)
# WebSocket port is browser port + 1 (default=8001)

class WebSocketProtocol(Protocol):
    '''
    Websocket server
    '''
    protocol_id: str = 'ws'

    def __init__(self, port:int=8000, **kwargs):
        super().__init__(**kwargs)
        self.port = port
        self.connected: Set[WebSocketServerProtocol] = set()

    async def arun(self):
        await websockets.serve(self.handle_connection, '0.0.0.0', self.port)

    async def aclose(self):
        # Close all WebSocket connections
        for ws in self.connected:
            await ws.close()
        self.connected.clear()

    async def handle_connection(self, websocket, path):
        'Register websocket connection and wait for messages'
        self.connected.add(websocket)
        try:
            await self.handle_mesg('connect')
            async for mesg in websocket:
                data = json.loads(mesg)
                await self.handle_mesg(**data)
        finally:
            # Unregister websocket connection
            self.connected.remove(websocket)

    async def do_send(self, cmd:str, **kwargs):
        'send ws message to browser via websocket'
        kwargs['cmd'] = cmd
        for ws in self.connected:
            await ws.send(json.dumps(kwargs))


class HTTPProtocol(Protocol):
    '''
    http server
    Use port for http server
    Use port+1 for websocket port
    '''
    protocol_id: str = 'http'

    def __init__(self, root:str, port:int=8000, nocache=False, **kwargs):
        super().__init__(**kwargs)
        self.root = root
        self.port = port
        self.app:web.Application = None
        self.runner:web.AppRunner = None
        self.site:web.TCPSite = None
        self.md_content = None
        self.substitutions = {}
        self.static = [join(here, 'static')]

        if nocache:
            # force browser to reload static content
            self.substitutions['__TIMESTAMP__'] = str(time.time())

    def add_static(self, path:str):
        'add static directory'
        self.static.append(path)

    @web.middleware
    async def apply_substitutions(self, request:web.Request, handler:Callable[[web.Request], Awaitable[web.Response]]):
        response = await handler(request)

        if self.substitutions and isinstance(response, web.Response) and response.body is not None:
            text = response.text
            for key, value in self.substitutions.items():
                text = text.replace(key, value)
            response = web.Response(text=text, headers=response.headers, status=response.status)
        return response

    def find_static(self, filename:str):
        for static_dir in self.static:
            file_path = os.path.join(static_dir, filename)
            if os.path.isfile(file_path):
                return file_path
        return None

    async def handle_static(self, request:web.Request):
        filename = request.match_info['filename'] or 'index.html'
        file_path = self.find_static(filename)
        if file_path is None:
            return web.Response(status=404)

        if filename.endswith('.md'):
            # Preprocess the .md file
            async with aiofiles.open(file_path, mode='r') as f:
                content = await f.read()
                # Preprocess the content here
            return web.Response(text=content)
        else:
            return web.FileResponse(path=file_path)

    async def arun(self):
        # Serve static http content from index.html
        self.app = web.Application(middlewares=[self.apply_substitutions])
        self.app.router.add_get('/{filename:.*}', self.handle_static)
        self.app.router.add_get('/', self.handle_static, name='index')
        self.app.middlewares.append(self.apply_substitutions)
        self.runner = web.AppRunner(self.app)
        await self.runner.setup()
        self.site = web.TCPSite(self.runner, '0.0.0.0', self.port)
        await self.site.start()

    async def aclose(self):
        # Stop the aiohttp site
        if self.site:
            await self.site.stop()

        # Shutdown and cleanup the aiohttp app
        if self.app:
            await self.app.shutdown()
            await self.app.cleanup()

        # Finally, cleanup the AppRunner
        if self.runner:
            await self.runner.cleanup()

    async def on_ws_request_md_content(self):
        'request markdown content from browser via websocket'
        http = self.get_protocol('http')

        if http.md_content is not None:
            await self.send('ws', 'update_md_content', content=http.md_content, format=http.md_format)


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
        self.queue: aio_pika.Queue = None
        self.offline_queue: Queue = Queue() # queue for messages pending connection
        self.connected = False

    async def arun(self):
        try:
            logger.info(f'Connecting to RabbitMQ on {self.host}:{self.port}')
            self.connection = await aio_pika.connect_robust(host=self.host, port=self.port)
        except aio_pika.AMQPException as e:
            logger.error(f"RabbitMQ connection failed: {e}")
            return

        self.channel = await self.connection.channel()

        # Declare a fanout exchange
        self.exchange = await self.channel.declare_exchange('chat', aio_pika.ExchangeType.FANOUT)

        # Declare a queue with a random name, exclusive to this connection
        self.queue = await self.channel.declare_queue(exclusive=True)

        # Bind the queue to the exchange, to receive all messages
        await self.queue.bind(self.exchange)
        self.connected = True

        logger.info(f'Connected to RabbitMQ on {self.host}:{self.port}')

        # Send any pending messages
        for cmd, kwargs in self.offline_queue.queue:
            await self.do_send(cmd, **kwargs)

        await self.receive_mq_mesg(),

    async def aclose(self):
        # Close the RabbitMQ channel and connection
        if self.channel:
            await self.channel.close()
            await self.connection.close()

    async def do_send(self, cmd:str, **kwargs):
        'broadcast message to RabbitMQ'
        if not self.connected:
            self.offline_queue.put((cmd, kwargs))
            return

        kwargs['cmd'] = cmd

        if not self.exchange:
            self.offline_queue.append(kwargs)
            return

        await self.exchange.publish(
            aio_pika.Message(body=json.dumps(kwargs).encode()),
            routing_key='',  # ignored for fanout exchanges
        )

    async def receive_mq_mesg(self):
        'receive messages from RabbitMQ'
        async with self.queue.iterator() as queue_iter:
            async for message in queue_iter:
                async with message.process():
                    data = json.loads(message.body.decode())
                    await self.handle_mesg(**data)


openai_key_request = '''
OpenAI API key required for GPT-4 chat mode.

``` form
fields:
  - type: text
    label: OpenAI API key
    key: openai.key
```
'''


class GPTChatProtocol(Protocol):
    '''
    OpenAI GPT Chat protocol

    This is just a POC: simple async wrapper around the OpenAI API in chat mode.
    Next step is to implement HuggingFace transformers and langchain for more control.
    '''
    protocol_id: str = 'gpt'

    def __init__(self, config:Config, **kwargs):
        super().__init__(**kwargs)
        self.config = config
        self.name = 'agi.green'
        self.uid = 'bot'

    async def arun(self):
        # Ensure the OpenAI client is authenticated
        api_key = self.config.get('openai.key', None)
        if api_key is None:
            logger.warn('Missing OpenAI API key in config')
            # request api key
            asyncio.create_task(self.request_key())

        self.messages = [
            {"role": "system", "content": "You are a helpful assistant representing agi.green."},
        ]

        if api_key:
            openai.api_key = api_key
        else:
            logger.warn('Missing OpenAI API key in config')
            # request api key
            asyncio.create_task(self.request_key())

    async def request_key(self):
        'request api key from browser'
        await self.send('mq', 'chat', author=self.name, content=openai_key_request)

    async def on_ws_form_data(self, cmd:str, data:dict):
        key = data.get('key')
        openai.api_key = key
        self.config.set('openai.key', key)
        self.messages.append({"role": "system", "content": "OpenAI API key was just now set by the user."})
        await self.get_completion()

    async def on_mq_chat(self, author:str, content:str):
        'receive chat message from RabbitMQ'
        if author != self.uid:
            self.messages.append({"role": "user", "content": content})
            # Schedule the synchronous OpenAI call to run in a thread executor
            task = asyncio.create_task(self.get_completion())

    async def get_completion(self):
        loop = asyncio.get_event_loop()
        content = await loop.run_in_executor(None, self.sync_completion)
        await self.send('mq', 'chat', author=self.uid, content=content)

    def sync_completion(self):
        try:
            response = openai.ChatCompletion.create(
                model="gpt-4",
                messages=self.messages,
                )
            return response.choices[0]['message']['content']
        except Exception as e:
            msg = f'OpenAI API error: {e}'
            logger.error(msg)
            return f'<span style="color:red">{msg}</span>'

