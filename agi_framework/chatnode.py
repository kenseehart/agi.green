import os
import sys
import argparse
from dispatcher import Dispatcher, logger
from protocols import WebSocketProtocol, HTTPProtocol, RabbitMQProtocol, GPTChatProtocol
from config import Config

# RabbitMQ port 5672
# VScode debug port 5678
# Browser port -p option (default=8000)
# WebSocket port is browser port + 1 (default=8001)

class ChatNode(Dispatcher):
    '''
    Manages the connection to RabbitMQ and WebSocket connection to browser.
    handler methods are named on_<protocol>_<cmd> where protocol is mq or ws
    mq = RabbitMQ
    ws = WebSocket
    gtp = OpenAI Rest API
    '''

    def __init__(self, port:int=8000, rabbitmq_host:str='localhost'):
        super().__init__()
        self.port = port
        self.config = Config('agi_config.yaml', 'agi_config_default.yaml')

        self.http = HTTPProtocol(port=port, nocache=True)
        self.ws = WebSocketProtocol(port=port+1)
        self.mq = RabbitMQProtocol(host=rabbitmq_host)
        self.gpt = GPTChatProtocol(self.config)

        self.add_protocols(
            self.http,
            self.ws,
            self.mq,
            self.gpt,
        )

    async def on_mq_chat(self, author:str, content:str):
        'receive chat message from RabbitMQ'
        await self.send('ws', 'append_chat', author=author, content=content)

    async def on_ws_connect(self):
        'handle new websocket connection'
        await self.send('ws', 'set_user_data', name='Ken Seehart', uid='K12345', icon='avatars/K12345.jpg')
        await self.send('ws', 'set_user_data', name='agi.green', uid='bot', icon='avatars/bot.png')

    async def on_ws_chat_input(self, content:str=''):
        'receive chat input from browser via websocket'
        # broadcast to all (including sender, which will echo back to browser)
        await self.send('mq', 'chat', author=f'K12345', content=content)




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

    dispatcher = ChatNode(port=args.port, rabbitmq_host=default_rabbitmq_host)
    dispatcher.run()

if __name__ == "__main__":
    main()
