import os
from os.path import join, dirname, splitext, isabs
import time
from typing import Callable, Awaitable, Dict, Any, List, Set, Union, Tuple
from logging import getLogger, Logger
import json
import asyncio
import logging
from os.path import exists

from aiohttp import web

from agi_green.dispatcher import Protocol, format_call, protocol_handler

here = dirname(__file__)
logger = logging.getLogger(__name__)
log_level = os.getenv('LOG_LEVEL', 'WARNING').upper()
logging.basicConfig(level=log_level)


WS_PING_INTERVAL = 20

class WebSocketProtocol(Protocol):
    '''
    Websocket session
    '''
    protocol_id: str = 'ws'

    def __init__(self, parent:Protocol):
        super().__init__(parent)
        self.sockets: Set[web.WebSocketResponse] = set()
        self.pre_connect_queue = []

    async def ping_loop(self, socket: web.WebSocketResponse):
        'ping the websocket to keep it alive'
        last_pong_time = time.time()

        while socket in self.sockets:
            try:
                await socket.ping()
            except ConnectionResetError as e:
                logger.error(f'ws connection reset (closing) {e} {self.dispatcher.session_id}')
                self.sockets.discard(socket)
                break
            await asyncio.sleep(WS_PING_INTERVAL)

    async def do_send(self, cmd: str, **kwargs):
        'send ws message to all connected browsers via websocket'
        kwargs['cmd'] = cmd
        if self.sockets:
            try:
                s = json.dumps(kwargs)
            except Exception as e:
                logger.error(f'ws send error: {e})')
                logger.error(f'ws send error: {kwargs}')
                return

            dead_sockets = set()
            for socket in self.sockets:
                try:
                    await socket.send_str(s)
                except Exception as e:
                    logger.error(f'ws send error: {e} (removing socket)')
                    dead_sockets.add(socket)

            self.sockets -= dead_sockets
            if not self.sockets:
                self.pre_connect_queue.append(kwargs)
        else:
            logger.info(f'queuing ws: {format_call(cmd, kwargs)}')
            self.pre_connect_queue.append(kwargs)

    @protocol_handler
    async def on_ws_connect(self, socket: web.WebSocketResponse):
        'websocket connected'
        if not self.is_server:
            self.sockets.add(socket)

            while self.pre_connect_queue and self.sockets:
                kwargs = self.pre_connect_queue.pop(0)
                await self.do_send(**kwargs)

            if not self.sockets:
                logger.error('all websockets closed before queue was emptied')
                return

            self.add_task(self.ping_loop(socket))

    @protocol_handler
    async def on_ws_disconnect(self, socket: web.WebSocketResponse):
        'websocket disconnected'
        self.sockets.discard(socket)

