'''
implementation of ws, mq and http protocols
'''

import os
from os.path import join, dirname, splitext, isabs
import time
import shutil
import re
import yaml
from typing import Callable, Awaitable, Dict, Any, List, Set, Union, Tuple
from logging import getLogger, Logger
import json
import asyncio
import aiofiles
import logging
import glob
import uuid
from queue import Queue
from os.path import exists
import ast

import aio_pika
from aiohttp import web, WSMsgType
from openai import OpenAI

from agi_green.dispatcher import Protocol, format_call
from agi_green.config import Config

here = dirname(__file__)
logger = logging.getLogger(__name__)
log_level = os.getenv('LOG_LEVEL', 'WARNING').upper()
logging.basicConfig(level=log_level)

# RabbitMQ port 5672
# VScode debug port 5678
# Browser port -p option (default=8000)
# WebSocket port is browser port + 1 (default=8001)

text_content_types = {
    '.html': 'text/html',
    '.js': 'application/javascript',
    '.map': 'application/json',
    '.css': 'text/css',
    '.txt': 'text/plain',
    '.md': 'text/markdown',
}

class HTTPServerProtocol(Protocol):
    '''
    http server (or https if ssl_context is provided)

    If ssl_context is provided, use https, and launch a http->https redirect server
    Otherwise, use http

    Either way, our naming convention assumes http (i.e. the class name and protocol_id)
    '''

    protocol_id: str = 'http'

    def __init__(self, session_class, host:str='0.0.0.0', port:int=8000, ssl_context=None, redirect=None, **kwargs):
        super().__init__(**kwargs)
        self.host = host
        self.port = port
        self.redirect = redirect
        self.ssl_context = ssl_context
        self.app:web.Application = None
        self.runner:web.AppRunner = None
        self.site:web.TCPSite = None
        self.session_class = session_class
        self.sessions:Dict[str, Protocol] = {}

    async def http_to_https_redirect(self, request):
        assert self.ssl_context is not None, "SSL context must be set for HTTPS redirect"
        https_location = f'https://{request.host}{request.rel_url}'
        raise web.HTTPMovedPermanently(https_location)

    def get_or_create_session(self, request):
        session_id = request.cookies.get('SESSION_ID')
        new_session_id = None

        if not session_id:
            new_session_id = session_id = str(uuid.uuid4())

        try:
            session = self.sessions[session_id]
        except KeyError:
            session:Protocol = self.session_class(self, session_id=session_id)
            self.sessions[session_id] = session
            self.add_task(session.run())

        return session, new_session_id

    async def handle_http_request(self, request:web.Request):
        session, new_session_id = self.get_or_create_session(request)
        http:HTTPSessionProtocol = session.get_protocol('http')
        response:web.StreamResponse = await http.handle_request(request)

        if new_session_id:
            if response is None:
                logger.error(f'Request failed on new session {new_session_id} on http request:')
                logger.error(f'  {request}')
            response.set_cookie('SESSION_ID', new_session_id)
            logger.info(f'New session: {new_session_id}')

        return response

    async def handle_websocket_request(self, request:web.Request):
        socket = web.WebSocketResponse()
        await socket.prepare(request)
        session, new_session_id = self.get_or_create_session(request)
        session.ws.socket = socket
        await session.ws.handle_mesg('connect')

        async for msg in socket:
            logger.info(f'ws {msg.type}, {msg.data}')
            if msg.type == WSMsgType.TEXT:
                data = json.loads(msg.data)
                # Handle the message
                await session.ws.handle_mesg(**data)
            elif msg.type == WSMsgType.ERROR:
                logger.error('ws connection closed with exception %s' % socket.exception())
            else:
                logger.info('ws {msg.type}')

        if new_session_id:
            logger.error(f'Unexpected new session on ws message: {self} {new_session_id}')

        return socket


    async def run(self):
        self.add_task(super().run())

        self.app = web.Application()
        #handle_websocket_request
        self.app.router.add_get('/ws', self.handle_websocket_request)  # Delegate WebSocket connections
        self.app.router.add_get('/{filename:.*}', self.handle_http_request)
        self.app.router.add_get('/', self.handle_http_request, name='index')

        # Check if SSL context is provided for HTTPS
        if self.ssl_context:
            # HTTPS server setup
            self.runner = web.AppRunner(self.app)
            await self.runner.setup()
            self.site = web.TCPSite(self.runner, self.host, self.port, ssl_context=self.ssl_context)
            logger.info(f'Serving https://{self.host}:{self.port}')
            await self.site.start()

            if self.redirect:
                # Additional HTTP server for redirecting to HTTPS
                redirect_app = web.Application()
                redirect_app.router.add_get('/{tail:.*}', self.http_to_https_redirect)
                redirect_runner = web.AppRunner(redirect_app)
                await redirect_runner.setup()
                redirect_site = web.TCPSite(redirect_runner, self.host, self.redirect)
                logger.info(f'Starting HTTP redirect server on http://{self.host}:{self.redirect}')
                await redirect_site.start()
        else:
            # HTTP server setup
            self.runner = web.AppRunner(self.app)
            await self.runner.setup()
            self.site = web.TCPSite(self.runner, self.host, self.port)
            logger.info(f'Serving http://{self.host}:{self.port}')
            await self.site.start()

    async def close(self):
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

        await super().close()


class HTTPSessionProtocol(Protocol):
    '''
    Session http protocol handler
    This is instantiated for each user who connects to the server
    '''

    protocol_id: str = 'http'

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.static = [join(here, 'static'), join(here, 'frontend', 'dist')]
        self.static_handlers:List[Callable] = []

    def add_static(self, path:str):
        'add static directory'
        if not exists(path):
            logger.warn(f'Static directory {path}: does not exist')
        self.static.append(path)

    def add_static_handler(self, handler:Callable):
        'add static handler'
        self.static_handlers.append(handler)

    def find_static(self, filename:str):
        for static_dir in self.static:
            file_path = os.path.join(static_dir, filename)
            if os.path.isfile(file_path):
                return file_path

        return None

    def find_static_glob(self, filename:str):
        files = []
        for static_dir in self.static:
            file_path = os.path.join(static_dir, filename)
            files.extend(glob.glob(file_path))
        return files

    def index_md(self):
        index_file = join(here, 'static', 'docs', 'index.md')
        files = self.find_static_glob('docs/*.md')
        newest_file = max(files, key=os.path.getmtime)

        if newest_file != index_file:
            if index_file in files:
                files.remove(index_file)
            files.sort()

            with open(index_file, 'w') as f:
                f.write(f'<!-- This index is generated by {__file__} - edits will be lost. -->\n\n')
                f.write('| File | Description |\n')
                f.write('| ---- | ----------- |\n')
                for file in files:
                    with open(file, 'r') as f2:
                        s = f2.read()
                        # find first markdown header
                        m = re.search(r'^#+\s+(.*)', s, re.MULTILINE)
                        if m:
                            header = m.group(1)
                            base = os.path.basename(file).replace('.md','')
                            f.write(f'| [**{base}**](/docs/{base}) | *{header}* |\n')


        if not exists(index_file):
            return None
        return index_file

    async def handle_request(self, request:web.Request):
        filename = request.match_info['filename'] or 'index.html'

        if filename == 'index.html':
            # since we are serving index.html, we need to reset the socket in case this is a refresh
            self._root.get_protocol('ws').socket = None

        query = request.query.copy()

        if filename == 'docs':
            file_path_md = self.index_md()
            filename = 'docs/index'
        else:
            # check for filename+'.md' and serve that instead with query: view=render
            file_path_md = self.find_static(filename+'.md')

        if file_path_md is not None:
            query.add('view','render')
            file_path = file_path_md
            filename = filename+'.md'
        else:
            file_path = self.find_static(filename)

        if file_path is None:
            for h in self.static_handlers:
                file_path = h(filename)
                if file_path is not None:
                    break
            else:
                return web.HTTPNotFound()

        ext = os.path.splitext(filename)[1]
        content_type = text_content_types.get(ext, None) # None means binary

        if content_type == 'text/markdown':
            format = query.get('view', 'raw')

            if format == 'raw':
                return web.FileResponse(file_path)

            if not os.path.exists(file_path) or not os.path.isfile(file_path):
                raise web.HTTPNotFound()

            with open(file_path, 'r') as f:
                content = f.read()

            # serve the index.html file. The open_md message will populate the md viewer
            file_path = self.find_static('index.html')

            # since we are serving index.html, we need to reset the socket
            self._root.get_protocol('ws').socket = None

            # queue up the message (will be queued until after the websocket is connected)
            await self.send('ws', 'open_md', name=filename, content=content, viewmode='render')

            return await serve_file(file_path)

        else:
            return await serve_file(file_path)



async def serve_file(file_path):
    response = web.FileResponse(file_path)

    # Manually set Content-Type for .js.map files
    if file_path.endswith('.js.map'):
        response.content_type = 'application/json'
    # Similarly, ensure .js files are served with the correct Content-Type
    elif file_path.endswith('.js'):
        response.content_type = 'application/javascript'

    print(f'{file_path} => {response.content_type}')

    return response


WS_PING_INTERVAL = 20

class WebSocketProtocol(Protocol):
    '''
    Websocket session
    '''
    protocol_id: str = 'ws'

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.socket:web.WebSocketResponse = None
        self.pre_connect_queue = []

    async def ping_loop(self):
        'ping the websocket to keep it alive'
        self.last_pong_time = time.time()

        while self.socket is not None:
            try:
                await self.socket.ping()
            except ConnectionResetError as e:
                logger.error(f'ws connection reset (closing)')
                self.socket = None
                break
            await asyncio.sleep(WS_PING_INTERVAL)


    async def do_send(self, cmd:str, **kwargs):
        'send ws message to browser via websocket'
        kwargs['cmd'] = cmd
        if self.socket is not None:
            try:
                await self.socket.send_str(json.dumps(kwargs))
            except Exception as e:
                logger.error(f'ws send error: {e} (queueing message)')
                self.socket = None
                self.pre_connect_queue.append(kwargs)
        else:
            logger.info(f'queuing ws: {format_call(cmd, kwargs)}')
            self.pre_connect_queue.append(kwargs)

    async def on_ws_connect(self):
        'websocket connected'
        if not self.is_server:
            assert self.socket is not None, "socket must be set"

            while self.pre_connect_queue:
                kwargs = self.pre_connect_queue.pop(0)
                await self.do_send(**kwargs)

            self.add_task(self.ping_loop())

    async def on_ws_disconnect(self):
        'websocket disconnected'
        self.socket = None


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

    _openai_client: OpenAI = None

    def __init__(self, config:Config, **kwargs):
        super().__init__(**kwargs)
        self.config = config
        self.name = 'agi.green'
        self.uid = 'bot'

    @property
    def openai_client(self):
        if GPTChatProtocol._openai_client is None:
            api_key = os.environ.get("OPENAI_API_KEY", None)

            if api_key is None:
                raise Exception("OPENAI_API_KEY environment variable must be set")

            GPTChatProtocol._openai_client = OpenAI(api_key=api_key)

        return GPTChatProtocol._openai_client

    async def run(self):
        self.add_task(super().run())

        self.messages = [
            {"role": "system", "content": "You are a helpful assistant."},
        ]

    async def on_ws_form_data(self, cmd:str, data:dict):
        key = data.get('key')
        self.config.set('openai.key', key)
        self.messages.append({"role": "system", "content": "OpenAI API key was just now set by the user."})
        await self.get_completion()

    async def on_ws_connect(self):
        await self.send('ws', 'set_user_data', uid='bot', name='GPT-4', icon='/avatars/agibot.png')
        await self.send('ws', 'set_user_data', uid='info', name='InfoBot', icon='/avatars/infobot.png')

    async def on_mq_chat(self, channel_id:str, author:str, content:str):
        'receive chat message from RabbitMQ'
        if author != self.uid:
            self.messages.append({"role": "user", "content": content})
            task = asyncio.create_task(self.get_completion())

    async def get_completion(self):
        logger.info('skipping GPT4 completion')
        #loop = asyncio.get_event_loop()
        #content = await loop.run_in_executor(None, self.sync_completion)
        #await self.send('mq', 'chat', channel='chat.public', author=self.uid, content=content)

    def sync_completion(self):
        try:
            response = self.openai_client.chat.completions.create(model="gpt-4",
            messages=self.messages)
            return response.choices[0].message.content
        except Exception as e:
            msg = f'OpenAI API error: {e}'
            logger.error(msg)
            return f'<span style="color:red">{msg}</span>'


re_command = re.compile(r'''^!(\w+\(([^)]*)\))''')

def ast_node_to_value(node):
    if isinstance(node, ast.Constant):
        # Handle atomic literals like numbers, strings, etc.
        return node.value
    elif isinstance(node, ast.List):
        # Handle list literals
        return [ast_node_to_value(element) for element in node.elts]
    elif isinstance(node, ast.Tuple):
        # Handle tuple literals
        return tuple(ast_node_to_value(element) for element in node.elts)
    elif isinstance(node, ast.Dict):
        # Handle dict literals
        return {ast_node_to_value(key): ast_node_to_value(value) for key, value in zip(node.keys, node.values)}
    elif isinstance(node, ast.Set):
        # Handle set literals
        return {ast_node_to_value(element) for element in node.elts}
    # Add more cases here for other compound types if needed
    else:
        raise TypeError("Unsupported AST node type")

class CommandProtocol(Protocol):
    '''
    Command protocol

    Handle custom commands
    '''
    protocol_id: str = 'cmd'

    def __init__(self, config:Config, **kwargs):
        super().__init__(**kwargs)
        self.config = config

    async def run(self):
        self.add_task(super().run())

    async def on_ws_chat_input(self, content:str):
        'receive command syntax on the mq chat channel'

        # !gameio_start(game='y93', players=['user1', 'user2'])

        for match in re_command.finditer(content):
            call_str = match.group(1)

            result = await self.send('cmd', call_str)

            if result:
                await self.send('ws', 'append_chat', author='info', content=result)

    async def do_send(self, cmd:str, **kwargs):
        # Parse cmd as a function call expression using ast
        result = ''

        try:
            node = ast.parse(cmd, mode='eval').body

            if isinstance(node, ast.Name):
                return await super().do_send(cmd, **kwargs)

            elif isinstance(node, ast.Call):
                func_name = node.func.id
                kwargs |= {kw.arg: ast_node_to_value(kw.value) for kw in node.keywords}
                result = await self.send('cmd', func_name, **kwargs)
            else:
                result = f'error: Invalid command syntax: {cmd}'

        except (SyntaxError, ValueError) as e:
            # This might occur if the matched string isn't a valid Python function call
            result = f'error: {e} `{cmd}`'

        result = result or ''

        if result.startswith('error'):
            logger.error(result)
        else:
            logger.info('%s => "%s"', cmd, result)

        return result

