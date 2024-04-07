import os
from os.path import join, dirname, splitext, isabs
import re
from typing import Callable, Awaitable, Dict, Any, List, Set, Union, Tuple
from logging import getLogger, Logger
import json
import logging
import glob
import uuid
from queue import Queue
from os.path import exists

from aiohttp import web, WSMsgType
from openai import OpenAI

from agi_green.dispatcher import Protocol, format_call
from agi_green.config import Config

here = dirname(__file__)
logger = logging.getLogger(__name__)
log_level = os.getenv('LOG_LEVEL', 'WARNING').upper()
logging.basicConfig(level=log_level)


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

            return await self.serve_file(file_path)

        else:
            return await self.serve_file(file_path)


    @staticmethod
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
