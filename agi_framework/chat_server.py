import os
from os.path import join, dirname, abspath
import sys
import argparse
import random
import logging
import asyncio

from agi_framework.dispatcher import Dispatcher
from agi_framework.protocols import WebSocketProtocol, HTTPProtocol, RabbitMQProtocol, GPTChatProtocol, CommandProtocol
from agi_framework.config import Config

# RabbitMQ port 5672
# VScode debug port 5678
# Browser port -p option (default=8000)
# WebSocket port is browser port + 1 (default=8001)

here = dirname(__file__)
logger = logging.getLogger(__name__)

def get_uid(digits=12):
    'generate a unique id: random 12 digit hex'
    return '%012x' % random.randrange(16**digits)

def create_ssl_context(cert_file:str, key_file:str):
    'create ssl context for https'
    import ssl
    ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
    ssl_context.load_cert_chain(cert_file, key_file)
    return ssl_context

class ChatServer(Dispatcher):
    '''Main server for chat (spawns ChatNode for each user on ws connect)
    To customize, you can start by replacing ChatNode with your own node class.
    '''

    @property
    def is_server(self) -> bool:
        'True if this protocol is a server (default: False)'
        return True

    def __init__(self, root:str='.', host:str='0.0.0.0', port:int=8000, node_class=None, ssl_context=None, redirect=None):
        super().__init__()
        self.node_class = node_class or ChatNode
        self.root = root
        self.server = self
        self.port = port
        self.config = Config(
            join(here, 'agi_config.yaml'),
            join(here, 'agi_config_default.yaml'),
        )

        self.http = HTTPProtocol(root=root, host=host, port=port, nocache=True, ssl_context=ssl_context, redirect=redirect)
        self.ws = WebSocketProtocol(host=host, port=port+1)

        self.add_protocols(
            self.http,
            self.ws,
        )

        self.nodes = {}

    async def on_ws_connect(self):
        'handle new websocket connection'
        # create a new ChatNode for this user
        node = self.node_class(self, root=self.root, port=self.port, rabbitmq_host=self.config['rabbitmq']['host'])
        self.add_node(node)
        asyncio.create_task(node.arun())
        return node

    def add_node(self, node):
        logger.info(f'{self} adding node {node} - {node.username}')
        self.nodes[node.username] = node

    def remove_node(self, node:'ChatNode'):
        logger.info(f'{self} removing node {node} - {node.username}')
        node.server = None
        del self.nodes[node.username]

class ChatNode(Dispatcher):
    '''
    Manages the connection to RabbitMQ and WebSocket connection to browser.
    handler methods are named on_<protocol>_<cmd> where protocol is mq or ws
    mq = RabbitMQ
    ws = WebSocket
    cmd = Command line interface

    This represents a single connection to a browser for one user.
    To customize, we recommend you start by copying and replacing this class with your own.
    '''

    def __init__(self, server:ChatServer, root:str='.', port:int=8000, rabbitmq_host:str='localhost'):
        super().__init__()
        self.server = server
        self.username = f'guest_{get_uid(8)}'
        self.root = root
        self.port = port
        self.config = Config(
            join(here, 'agi_config.yaml'),
            join(here, 'agi_config_default.yaml'),
        )

        self.ws = WebSocketProtocol(self.username)
        self.mq = RabbitMQProtocol(host=rabbitmq_host)
        self.cmd = CommandProtocol(self.config)

        self.add_protocols(
            self.ws,
            self.mq,
            self.cmd,
        )
        logger.info(f'ChatNode {self.username} created')

    def __del__(self):
        logger.info(f'ChatNode {self.username} deleted')

    async def on_ws_connect(self):
        'post connection node setup'
        logger.info(f'ChatNode {self.username} connected')
        await self.mq.subscribe('broadcast')
        await self.mq.subscribe('chat.public')
        self.active_channel = 'chat.public'

    async def on_ws_disconnect(self):
        'post connection node cleanup'
        logger.info(f'ChatNode {self.username} disconnected')
        self.server.remove_node(self)
        asyncio.create_task(self.aclose())

    async def on_ws_chat_input(self, content:str=''):
        'receive chat input from browser via websocket'
        # broadcast to all (including sender, which will echo back to browser)
        if not content.startswith('!'):
            await self.send('mq', 'chat', channel=self.active_channel, author=self.username, content=content)

    async def on_mq_chat(self, author:str, content:str):
        'receive chat message from RabbitMQ'
        await self.send('ws', 'append_chat', author=author, content=content)

    async def on_cmd_user_info(self, **kwargs):
        'receive user info'

class ChatGPTNode(ChatNode):
    '''ChatNode with GPT-4 joining in.

    '''
    def __init__(self, server:ChatServer, root:str='.', port:int=8000, rabbitmq_host:str='localhost'):
        super().__init__(server, root, port, rabbitmq_host)
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

    node_class=ChatGPTNode if args.gpt else ChatNode

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
