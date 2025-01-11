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
        'send ws message to specific socket or all connected browsers via websocket'
        kwargs['cmd'] = cmd

        try:
            s = json.dumps(kwargs)
            logger.info(f'Attempting to send WebSocket message: {s} to socket_id: {socket_id}')
        except Exception as e:
            logger.error(f'ws send error: {e})')
            logger.error(f'ws send error: {kwargs}')
            return

        if not self.sockets:
            logger.info(f'No active sockets, queueing message: {s}')
            self.pre_connect_queue.append(kwargs)
            return

        dead_sockets = set()
        for socket in self.sockets:
            # Skip if socket_id specified and doesn't match
            if socket_id and getattr(socket, 'id', None) != socket_id:
                continue

            try:
                logger.info(f'Sending to socket {getattr(socket, "id", "unknown")}: {s}')
                await socket.send_str(s)
                logger.info(f'Successfully sent to socket {getattr(socket, "id", "unknown")}')
            except Exception as e:
                logger.error(f'ws send error: {e} (removing socket)')
                dead_sockets.add(socket)

        self.sockets -= dead_sockets
        if not self.sockets and not socket_id:  # Only queue if broadcasting
            logger.info(f'No active sockets, queueing message: {s}')
            self.pre_connect_queue.append(kwargs)

    @protocol_handler(priority=0, update=True)
    async def on_ws_connect(self, socket: web.WebSocketResponse, headers: Dict):
        """
        Handle WebSocket connection with priority 0 to intercept reconnections
        before other handlers see them
        """
        connection_id = headers.get('X-Connection-ID')

        if connection_id and connection_id in self.socket_states:
            logger.info(f'Reconnecting existing socket {connection_id}')
            socket.id = connection_id
            self.sockets.add(socket)
            state = self.socket_states[connection_id]
            state['last_ping'] = time.time()
            self.add_task(self.ping_loop(socket))

            # Prevent other handlers from seeing this as a new connection
            return {'__break__': True}

        # New connection
        socket.id = str(uuid.uuid4())
        logger.info(f'New socket connection {socket.id}')
        self.sockets.add(socket)
        self.socket_states[socket.id] = {
            'created_at': time.time(),
            'last_ping': time.time(),
        }
        self.add_task(self.ping_loop(socket))

        # Process any queued messages
        while self.pre_connect_queue:
            await self.do_send(**self.pre_connect_queue.pop(0))

        socket.headers['X-Connection-ID'] = socket.id
        return {'socket': socket, 'headers': headers}

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

