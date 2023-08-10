# agi.green
A user interface platform for python AI applications using docker and a browser chat interface featuring markdown content. 

A high level python package controls all of the business logic, including a unified message model and asynchronous interaction with the chat ui.

**Please note:** *This is in very early development (August 2003). The framework should be considered completely unstable for a few weeks, with no backward compatibility or versioning.* By September, we should be stable enough to support derivative works, and there will be a Github Template to facilitate deploying `agi.green` as a git submodule.

## Components:

- `docker`: Peers are deployed as a docker containers
- `websockets`: Communicate with browser ui
- `aio_pika`: Communicate via `AMQP` with other docker containers
- `markdown`: Messages are rendered as markdown (and plugins such as mermaid and mathjax)

## Example chat room:

This implements a peer to peer chat node. It runs inside a docker container, and broadcasts to all peers on the same docker network.

It doesn't get simpler than this. `Dispatcher` hides all the details.

A similar Dispatcher could implement an interface to OpenAI or other model, or various agents and API command handlers.

``` python
class ChatNode(Dispatcher):
    '''
    Manages the connection to RabbitMQ and WebSocket connection to browser.
    handler methods are named on_<protocol>_<cmd> where protocol is mq or ws
    mq = RabbitMQ
    ws = WebSocket
    '''

    async def on_mq_chat(self, author:str, content:str):
        'receive chat message from RabbitMQ - append to chat dialog in browser ui'
        await self.send_ws('append_chat', content=content)

    async def on_ws_chat_input(self, content:str=''):
        'receive chat input from browser via websocket - broadcast to peers (including self)'
        await self.send_mq('chat', author=f'{self.name}', content=content)
```

Note that `on_mq_chat` and `on_ws_chat_input` are not predefined overloaded methods. You can add any methods that are prefixed with `on_{protocol}_{command}` with arbitrary named arguments, and these handler methods will autoregister. Send messages with `send_{protocol}(command, **kwargs)` with corresponding arguments. The function signature defines the message schema. Predefined protocols are `ws` (socket connection to browser ui) and `mq` (amqp broadcast to peers, including echo to self). Protocol `gpt` coming soon. The framework provides for the definition of new protocols.

## Intended applications for this framework:

- fish: fantastic imap sorting hat (conversational email sorting)
- yara: yet another research assistant (interactively build an up to date expert on any topic)
- various experiments in layered language models
  
