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
                s = json.dumps(kwargs)
            except Exception as e:
                logger.error(f'ws send error: {e})')
                logger.error(f'ws send error: {kwargs}')
                return
            try:
                await self.socket.send_str(s)
            except Exception as e:
                logger.error(f'ws send error: {e} (queueing message)')
                self.socket = None
                self.pre_connect_queue.append(kwargs)
        else:
            logger.info(f'queuing ws: {format_call(cmd, kwargs)}')
            self.pre_connect_queue.append(kwargs)

    @protocol_handler
    async def on_ws_connect(self):
        'websocket connected'
        if not self.is_server:
            assert self.socket is not None, "socket must be set"

            while self.pre_connect_queue and self.socket is not None:
                kwargs = self.pre_connect_queue.pop(0)
                await self.do_send(**kwargs)

            if self.socket is None:
                logger.error('websocket closed before queue was emptied')
                return

            self.add_task(self.ping_loop())

    @protocol_handler
    async def on_ws_disconnect(self):
        'websocket disconnected'
        self.socket = None

