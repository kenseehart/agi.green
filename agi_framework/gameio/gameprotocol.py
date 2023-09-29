'''generic game protocol'''

import asyncio
import logging
from dispatcher import Protocol, format_call, logger
from config import Config
from typing import Dict, Any
from os.path import join, dirname, abspath, exists

here = dirname(abspath(__file__))  

class Game:
    '''generic game class
    Override these methods to define a game.

    game state is a dict with any of the following keys:
    legal_moves:
        role: str - role of player making the move

        moves: list - list of legal moves for the role
            a move is either a string|int of a pair of strings|ints
            if a singleton, it is a location, and the role is the piece

    winner:
        role: str - role of winning player
    '''
    def __init__(self, config:Config):
        self.config = config
        self.state = {}


    def play(self, location) -> Dict[str, Any]:
        '''play move
        return game state'''
        raise NotImplementedError



class GameProtocol(Protocol):
    '''
    Turn-based game protocol

    The game object defines the game logic.
    '''
    protocol_id: str = 'game'

    def __init__(self, game:Game, config:Config, **kwargs):
        super().__init__(**kwargs)
        self.config = config
        self.name = 'agi.green'

    async def arun(self):
        'initialize game'
        self.get_protocol('http').add_static(join(here, 'static'))


    async def on_ws_connect(self):
        'websocket connected'
        ...

    async def on_ws_disconnect(self):
        'websocket disconnected'
        ...

    async def on_ws_move(self, location):
        'a move was made in the ui'
        ...


