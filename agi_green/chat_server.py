import os
from os.path import join, dirname, abspath
import sys
import argparse
import random
import logging
import asyncio

from agi_green.dispatcher import Dispatcher
from agi_green.protocols import WebSocketProtocol, HTTPServerProtocol, HTTPSessionProtocol, RabbitMQProtocol, GPTChatProtocol, CommandProtocol
from agi_green.config import Config

# RabbitMQ port 5672
# VScode debug port 5678
# Browser port -p option (default=8000)
# WebSocket port is browser port + 1 (default=8001)

here = dirname(__file__)
logger = logging.getLogger(__name__)

def get_uid(digits=12):
    'generate a unique id: random 12 digit hex'
    return f'%0{digits}x' % random.randrange(16**digits)

def create_ssl_context(cert_file:str, key_file:str):
    'create ssl context for https'
    import ssl
    ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
    ssl_context.load_cert_chain(cert_file, key_file)
    return ssl_context

class ChatServer(Dispatcher):
    '''Main server for chat (spawns ChatSession for each user on ws connect)
    To customize, you can start by replacing ChatSession with your own session class.
    '''

    @property
    def is_server(self) -> bool:
        'True if this protocol is a server (default: False)'
        return True

    def __init__(self, root:str='.', host:str='0.0.0.0', port:int=8000, session_class=None, ssl_context=None, redirect=None):
        super().__init__()
        self.session_class = session_class or ChatSession
        self.root = root
        self.server = self
        self.port = port
        self.config = Config(
            join(here, 'agi_config.yaml'),
            join(here, 'agi_config_default.yaml'),
        )

        self.http = HTTPServerProtocol(self.session_class, host=host, port=port, ssl_context=ssl_context, redirect=redirect)

        self.add_protocols(
            self.http,
        )

        self.nodes = {}

class ChatSession(Dispatcher):
    '''
    Manages the connection to RabbitMQ and WebSocket connection to browser.
    handler methods are named on_<protocol>_<cmd> where protocol is mq or ws
    mq = RabbitMQ
    ws = WebSocket
    cmd = Command line interface

    This represents a single connection to a browser for one user.
    To customize, we recommend you start by copying and replacing this class with your own.
    '''

    def __init__(self, server:ChatServer, session_id, **kwargs):
        super().__init__(**kwargs)
        self.server = server
        self.username = f'guest_{get_uid(8)}'
        self.session_id = session_id
        self.config = Config(
            join(here, 'agi_config.yaml'),
            join(here, 'agi_config_default.yaml'),
        )

        rabbitmq_host = os.environ.get('RABBITMQ_HOST', 'localhost')

        self.http = HTTPSessionProtocol()
        self.ws = WebSocketProtocol()
        self.mq = RabbitMQProtocol(host=rabbitmq_host)
        self.cmd = CommandProtocol(self.config)

        self.add_protocols(
            self.http,
            self.ws,
            self.mq,
            self.cmd,
        )
        logger.info(f'{type(self).__name__} {self.username} created: rabbitmq={rabbitmq_host}')

    def __repr__(self):
        return f'{super().__repr__()} {self.username}'

    def __del__(self):
        logger.info(f'{self} deleted')

    async def on_ws_connect(self):
        'post connection node setup'
        logger.info(f'{self} connected')
        await self.mq.subscribe('broadcast')
        await self.mq.subscribe('chat.public')
        self.active_channel = 'chat.public'

    async def on_ws_disconnect(self):
        'post connection node cleanup'
        logger.info(f'{self} disconnected')
        self.server.remove_node(self)
        self.add_task(self.close())

    async def on_ws_chat_input(self, content:str=''):
        'receive chat input from browser via websocket'
        # broadcast to all (including sender, which will echo back to browser)
        if not content.startswith('!'):
            await self.send('mq', 'chat', channel=self.active_channel, author=self.username, content=content)

    async def on_mq_chat(self, channel_id:str, author:str, content:str):
        'receive chat message from RabbitMQ'
        await self.send('ws', 'append_chat', author=author, content=content)

    async def on_cmd_user_info(self, **kwargs):
        'receive user info'

class ChatGPTSession(ChatSession):
    '''ChatNode with GPT-4 joining in.

    '''
    def __init__(self, server:ChatServer, port:int=8000, rabbitmq_host:str='localhost'):
        super().__init__(server, port, rabbitmq_host)
        self.gpt = GPTChatProtocol(self.config)
        self.add_protocol(self.gpt)


def main():
    default_rabbitmq_host = os.environ.get('RABBITMQ_HOST', 'localhost')
    parser = argparse.ArgumentParser()
    parser.add_argument("-H", "--host", default='0.0.0.0', type=str,
                        help="host to serve website")
    parser.add_argument("-p", "--port", default=8000, type=int,
                        help="port to serve ui (websocket will be port+1)")
    parser.add_argument("-d", "--debug", action="store_true", help="enable vscode debug attach")
    parser.add_argument("-D", "--docker", action="store_true", help="run in docker mode")
    parser.add_argument("-g", "--gpt", action="store_true", help="enable gpt4 chat")
    parser.add_argument("--http", action="store_true", help="use http (default is https)")
    args = parser.parse_args()

    if args.port %2 != 0:
        logger.info("Port must be even (because websocket will be port+1)", file=sys.stderr)
        return

    if args.debug:
        import ptvsd

        logger.info("Enabling debug attach...")
        ptvsd.enable_attach(address=('0.0.0.0', '5678'))

        logger.info("Waiting for debugger to attach...")
        ptvsd.wait_for_attach()
        logger.info(".. debugger attached")

    node_class=ChatGPTSession if args.gpt else ChatSession

    if args.http:
        ssl_context = None
    else:
        cert_file = os.environ.get('SSL_CERT', None)
        key_file = os.environ.get('SSL_KEY', None)
        if not cert_file or not key_file:
            logger.info("SSL_CERT and SSL_KEY environment variables must be set for https mode", file=sys.stderr)
            return 1

        ssl_context = create_ssl_context(cert_file, key_file)

    dispatcher = ChatServer(root=dirname(abspath(__file__)), port=args.port, node_class=node_class)
    dispatcher.run()
    return 0

if __name__ == "__main__":
    r = main()
    sys.exit(r)
