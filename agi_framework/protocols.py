'''
implementation of ws, mq and http protocols
'''

import os
import time
import shutil
import yaml
from typing import Callable, Awaitable, Dict, Any, List, Set
from logging import getLogger, Logger
import json
import asyncio

import websockets
from websockets.legacy.server import WebSocketServerProtocol
import aio_pika
from aiohttp import web
import openai

from dispatcher import Protocol, format_call, logger
from config import Config

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

        if nocache:
            # force browser to reload static content
            self.substitutions['__TIMESTAMP__'] = str(time.time())

    async def arun(self):
        # Serve static http content from index.html
        self.app = web.Application()
        self.app.router.add_get('/', self.handle_get_root_request)
        self.app.router.add_get('/{path:.*}.md', self.handle_md_request)
        self.app.router.add_static('/', path=os.path.join(self.root, 'static'), name='static')
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

    async def handle_get_root_request(self, request):
        logger.info(f'GET /')
        with open(os.path.join(self.root, 'static/index.html'), 'r') as file:
            content = file.read()
            for key, value in self.substitutions.items():
                content = content.replace(key, value)
            return web.Response(text=content, content_type='text/html')

    async def handle_md_request(self, request):
        path = request.match_info['path']
        file_path = os.path.join(self.root, 'static', f"{path}.md")
        format = request.query.get('format', 'render')

        if os.path.exists(file_path) and os.path.isfile(file_path):
            with open(file_path, 'r') as f:
                self.md_content = f.read()

            self.md_format = format

            if format == 'text':
                return web.Response(text=self.md_content, content_type='text/plain')

            with open('md_template.html', 'r') as template_file:
                template = template_file.read()

            for key, value in self.substitutions.items():
                template = template.replace(key, value)

            return web.Response(text=template, content_type='text/html')

        # If the file doesn't exist, return a 404 Not Found
        raise web.HTTPNotFound()

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
        self.offline_queue: List[Dict[str, Any]] = []

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
        for msg in self.offline_queue:
            await self.do_send(**msg)
        await self.receive_mq_mesg(),

    async def aclose(self):
        # Close the RabbitMQ channel and connection
        if self.channel:
            await self.channel.close()
            await self.connection.close()

    async def do_send(self, cmd:str, **kwargs):
        'broadcast message to RabbitMQ'
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

