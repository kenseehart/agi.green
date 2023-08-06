import sys
import argparse
from dispatcher import Dispatcher, Protocol_mq, Protocol_http_ws
import ptvsd

# RabbitMQ port 5672
# VScode debug port 5678
# Browser port -p option (default=8000)
# WebSocket port is browser port + 1 (default=8001)

class ChatNode(Dispatcher, Protocol_mq, Protocol_http_ws):
    '''
    Manages the connection to RabbitMQ and WebSocket connection to browser.
    handler methods are named on_<protocol>_<cmd> where protocol is mq or ws
    mq = RabbitMQ
    ws = WebSocket
    '''

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    async def on_mq_chat(self, author:str, content:str):
        'receive chat message from RabbitMQ'
        print(f'mq chat received: {author}: "{content}"')
        await self.send_ws('append_chat', content=content)

    async def on_ws_chat_input(self, content:str=''):
        'receive chat input from browser via websocket'
        print(f"ws chat input: '{content}'")

        # broadcast to all (including sender, which will echo back to browser)
        await self.send_mq('chat', author=f'{self.http_port}', content=content)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-p", "--port", default=8000, type=int,
                        help="port to serve ui (websocket will be port+1)")
    parser.add_argument("-d", "--debug", action="store_true")
    args = parser.parse_args()

    if args.port %2 != 0:
        print("Port must be even (because websocket will be port+1)", file=sys.stderr)
        return

    if args.debug:
        print("Enabling debug attach...")
        ptvsd.enable_attach(address=('0.0.0.0', '5678'))

        print("Waiting for debugger to attach...")
        ptvsd.wait_for_attach()
        print(".. debugger attached")

    dispatcher = ChatNode(port=args.port)
    dispatcher.run()

if __name__ == "__main__":
    main()
