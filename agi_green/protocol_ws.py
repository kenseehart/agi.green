import os
from os.path import join, dirname, splitext, isabs
import time
from typing import Callable, Awaitable, Dict, Any, List, Set, Union, Tuple
from logging import getLogger, Logger
import json
import asyncio
import logging
from os.path import exists
import uuid

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
        self.socket_states: Dict[str, Dict] = {}
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

    async def do_send(self, cmd: str, socket_id: str = None, **kwargs):
        'send ws message to specific socket or all connected browsers'
        kwargs['cmd'] = cmd

        if not self.sockets:
            logger.info(f'queuing ws: {format_call(cmd, kwargs)}')
            self.pre_connect_queue.append(kwargs)
            return

        try:
            s = json.dumps(kwargs)
            logger.info(f'Attempting to send WebSocket message: {s}')
        except Exception as e:
            logger.error(f'ws send error: {e})')
            logger.error(f'ws send error: {kwargs}')
            return

        dead_sockets = set()
        target_sockets = [s for s in self.sockets if socket_id is None or getattr(s, 'id', None) == socket_id]

        for socket in target_sockets:
            try:
                logger.info(f'Sending to socket {getattr(socket, "id", "unknown")}: {s}')
                await socket.send_str(s)
                logger.info(f'Successfully sent to socket {getattr(socket, "id", "unknown")}')
            except Exception as e:
                logger.error(f'ws send error: {e} (removing socket)')
                dead_sockets.add(socket)

        self.sockets -= dead_sockets

    @protocol_handler(priority=0)
    async def on_ws_connect(self, socket: web.WebSocketResponse):
        """Handle WebSocket connection"""

        if not socket.id:
            logger.error('No socket.id (should be set by HTTPServerProtocol.handle_websocket_request)')
            raise ValueError('No socket.id')

        self.sockets.add(socket)
        self.add_task(self.ping_loop(socket))

        return {'socket': socket}

    @protocol_handler
    async def on_ws_disconnect(self, socket: web.WebSocketResponse):
        self.sockets.discard(socket)
        # Keep state for potential reconnect
        # Add cleanup after timeout
        self.add_task(self._cleanup_socket_state(socket.id))

    async def _cleanup_socket_state(self, socket_id: str):
        """Remove socket state if no reconnect within timeout"""
        await asyncio.sleep(30)  # Adjust timeout as needed
        if socket_id in self.socket_states:
            state = self.socket_states[socket_id]
            if time.time() - state['last_ping'] > 30:
                del self.socket_states[socket_id]

    async def handle_message(self, socket: web.WebSocketResponse, data: Dict):
        """Handle incoming WebSocket message"""
        # Debug logging
        logger.info(f"Received message with data: {data}")
        await super().handle_message(socket, data)

