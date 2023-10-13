import os
from os.path import join, dirname, abspath
import sys
import argparse
import random
import logging

from dispatcher import Dispatcher
from protocols import WebSocketProtocol, HTTPProtocol, RabbitMQProtocol, GPTChatProtocol, CommandProtocol
from config import Config

# RabbitMQ port 5672
# VScode debug port 5678
# Browser port -p option (default=8000)
# WebSocket port is browser port + 1 (default=8001)

here = dirname(__file__)
logger = logging.getLogger(__name__)

def get_uid():
    'generate a unique id: random 12 digit hex'
    return '%012x' % random.randrange(16**12)

class ChatServer(Dispatcher):
    '''Main server for chat (spawns ChatNode for each user on ws connect)
    To customize, you can start by replacing ChatNode with your own node class.
    '''

    @property
    def is_server(self) -> bool:
        'True if this protocol is a server (default: False)'
        return True

    def __init__(self, root:str='.', port:int=8000, node_class=None):
        super().__init__()
        self.node_class = node_class or ChatNode
        self.root = root
        self.port = port
        self.config = Config(
            join(here, 'agi_config.yaml'),
            join(here, 'agi_config_default.yaml'),
        )

        self.http = HTTPProtocol(root=root, port=port, nocache=True)
        self.ws = WebSocketProtocol(port=port+1)

        self.add_protocols(
            self.http,
            self.ws,
        )

        self.nodes = {}

    async def on_ws_connect(self):
        'handle new websocket connection'
        # create a new ChatNode for this user
        node = self.node_class(self, root=self.root, port=self.port, rabbitmq_host=self.config['rabbitmq']['host'])
        self.nodes[node.uid] = node
        self.create_task(node.arun())
        return node


class ChatNode(Dispatcher):
    '''
    Manages the connection to RabbitMQ and WebSocket connection to browser.
    handler methods are named on_<protocol>_<cmd> where protocol is mq or ws
    mq = RabbitMQ
    ws = WebSocket
    gpt = OpenAI Rest API
    cmd = Command line interface

    This represents a single connection to a browser for one user.
    To customize, we recommend you start by copying and replacing this class with your own.
    '''

    def __init__(self, server:ChatServer, root:str='.', port:int=8000, rabbitmq_host:str='localhost'):
        super().__init__()
        self.server = server
        self.uid = get_uid()
        self.root = root
        self.port = port
        self.config = Config(
            join(here, 'agi_config.yaml'),
            join(here, 'agi_config_default.yaml'),
        )

        self.ws = WebSocketProtocol(self.uid)
        self.mq = RabbitMQProtocol(host=rabbitmq_host)
        self.gpt = GPTChatProtocol(self.config)
        self.cmd = CommandProtocol(self.config)

        self.add_protocols(
            self.ws,
            self.mq,
            self.gpt,
            self.cmd,
        )
        logger.info(f'ChatNode {self.uid} created')

    async def on_ws_connect(self):
        'post connection node setup'
        ...

    async def on_ws_chat_input(self, content:str=''):
        'receive chat input from browser via websocket'
        # broadcast to all (including sender, which will echo back to browser)
        await self.send('mq', 'chat', author=f'K12345', content=content)

    async def on_mq_chat(self, author:str, content:str):
        'receive chat message from RabbitMQ'
        await self.send('ws', 'append_chat', author=author, content=content)

    async def on_cmd_user_info(self, **kwargs):
        'receive user info'



def main():
    default_rabbitmq_host = os.environ.get('RABBITMQ_HOST', 'localhost')
    parser = argparse.ArgumentParser()
    parser.add_argument("-p", "--port", default=8000, type=int,
                        help="port to serve ui (websocket will be port+1)")
    parser.add_argument("-d", "--debug", action="store_true", help="enable vscode debug attach")
    parser.add_argument("-D", "--docker", action="store_true", help="run in docker mode")
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

    dispatcher = ChatServer(root=dirname(abspath(__file__)), port=args.port)
    dispatcher.run()

if __name__ == "__main__":
    main()
