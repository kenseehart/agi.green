'''generic game protocol'''

import asyncio
import logging
from dispatcher import Protocol, format_call, logger
from config import Config, get_data_dir
from typing import Dict, Any, Callable
from os.path import join, dirname, abspath, exists
from os import makedirs
import yaml
import importlib


def AbstractGame():
    'abstract game definition'
    def gameio_init(self)->dict:
        'return initial game state'
        return {}
    def gameio_legal_moves(self, pos: Any, role:str=None):
        'return legal moves for role in pos'
        return []
    def gameio_apply_move(self, pos: Any, move: dict) -> Any:
        'apply move to pos'
        return pos
    def gameio_win(self, pos, role) -> bool:
        'return true if role wins in pos'
        return False
    def gameio_init_pos(self) -> Any:
        'return initial position'
        return None


def get_game_factory(name:str) -> Callable[[], AbstractGame]:
    'get a game factory by name'
    games_dir = join(get_data_dir(), 'games')
    game_registry_file = join(get_data_dir(), 'game_registry.yaml')

    if exists(game_registry_file):
        with open(game_registry_file, 'r') as f:
            registry = yaml.load(f, Loader=yaml.SafeLoader)
    else:
        registry = {}

    if name not in registry['games']:
        logger.error('game not registered: %s', name)
        return None

    module = registry['games'][name]['module']
    factory:Callable[[],AbstractGame] = registry['games'][name]['factory']

    m = importlib.import_module(module)
    f = getattr(m, factory)
    g = f()
    assert hasattr(g, 'gameio_init')
    assert hasattr(g, 'gameio_static_dir')
    assert hasattr(g, 'gameio_legal_moves')
    assert hasattr(g, 'gameio_apply_move')
    assert hasattr(g, 'gameio_win')
    assert hasattr(g, 'gameio_init_pos')
    return f

def register_game(name:str, factory:str):
    'register a new game definition'

    module, factory = factory.split('.')
    # verify that the factory is valid
    try:
        m = importlib.import_module(module)
        f = getattr(m, factory)
    except Exception as e:
        logger.error('failed to register %s', factory, exc_info=True)
        return

    game_registry_file = join(get_data_dir(), 'game_registry.yaml')

    if exists(game_registry_file):
        with open(game_registry_file, 'r') as f:
            registry = yaml.load(f, Loader=yaml.SafeLoader)
    else:
        registry = {}

    if 'games' not in registry:
        registry['games'] = {}

    if name in registry['games']:
        logger.info('updating game: %s', name)
        registry['games'][name]['module'] = module
        registry['games'][name]['factory'] = factory
    else:
        logger.info('registering new game: %s', name)
        registry['games'][name] = {
            'module': module,
            'factory': factory,
            'next_uid': 100000,
        }

    with open(game_registry_file, 'w') as f:
        yaml.dump(registry, f)

def get_game_uid(name:str):
    'generate a unique id for a new game instance'
    game_registry_file = join(get_data_dir(), 'game_registry.yaml')

    with open(game_registry_file, 'r') as f:
        registry = yaml.load(f, Loader=yaml.SafeLoader)

    if name not in registry['games']:
        logger.error('game not registered: %s', name)
        return None

    next = registry['games'][name]['next_uid']
    registry['games'][name]['next_uid'] += 1

    with open(game_registry_file, 'w') as f:
        yaml.dump(registry, f)

    return f'{name}-{next}'

class GameInstance:
    '''A game in progress

    '''

    def __init__(self, uid:str, history=[]):
        self.uid = uid
        name = uid.split('-')[0]
        factory = get_game_factory(name)
        self.gamedef:AbstractGame = factory()
        self.history = history
        self.roles = {role:'' for role in self.gamedef.roles}
        self.position = self.gamedef.gameio_init_pos()
        for move in self.history:
            self.position = self.gamedef.gameio_apply_move(self.position, move)

    def save(self):
        'save the game to disk'
        fname = join(get_data_dir(), 'games', self.uid+'.yaml')
        makedirs(dirname(fname), exist_ok=True)
        with open(fname, 'w') as f:
            yaml.dump({
                'roles': self.roles,
                'history': self.history,
                }, f)

    def __getattr__(self, k: str) -> Any:
        if k.startswith('gameio_'):
            return getattr(self.gamedef, k)

here = dirname(abspath(__file__))

game_cache:Dict[str,GameInstance] = {}

def get_game_instance(name_or_uid:str) -> GameInstance:
    'get a game instance by name or uid'
    if name_or_uid in game_cache:
        return game_cache[name_or_uid]

    if '-' in name_or_uid:
        uid = name_or_uid
        fname = join(get_data_dir(), 'games', uid+'.yaml')

        if exists(fname):
            with open(fname, 'r') as f:
                game_args = yaml.load(f, Loader=yaml.SafeLoader)

            game = GameInstance(uid, **game_args)
        else:
            logger.error('game not found: %s', uid)
            return None
    else:
        uid = get_game_uid(name_or_uid)
        game = GameInstance(uid)

    game_cache[uid] = game
    return game


class GameIOProtocol(Protocol):
    '''
    Turn-based game protocol

    The game object defines the game logic.
    '''
    protocol_id: str = 'gameio'

    def __init__(self, config:Config, **kwargs):
        super().__init__(**kwargs)
        self.config = config
        self.role = ''
        self.game:GameInstance = None

    async def arun(self):
        self.http = self.get_protocol('http')
        self.http.add_static(join(here, 'static'))

    async def on_ws_connect(self):
        'websocket connected'
        ...

    async def on_ws_disconnect(self):
        'websocket disconnected'
        ...

    async def on_cmd_gameio_start(self, game:str, role:str=None) -> str:
        'create a new game instance'
        self.game = get_game_instance(game)
        if role:
            self.role = role
            await self.join(self.game, role)

    async def on_cmd_gameio_join(self, gameid:str, role:str) -> str:
        'join a game instance'

        self.game = get_game_instance(gameid)
        await self.join(self.game, role)

    async def on_ws_gameio_move(self, **move):
            'handle new websocket connection'
            logger.info('move: %s', move)
            self.game.position = self.game.gameio_apply_move(self.game.position, move)
            await self.send('ws', 'gameio_allow', moves=self.game.gameio_legal_moves(self.game.position))

    async def join(self, game:GameInstance, role:str) -> str:
        self.http.add_static(game.gameio_static_dir())
        self.game = game
        await self.send('ws', 'workspace_component', name='gameio')
        await self.send('ws', **self.game.gameio_init())

        pos = self.game.gameio_init_pos()

        for move in self.game.history:
            pos = self.game.gameio_apply_move(pos, move)

        await self.send('ws', 'gameio_allow', moves=self.game.gameio_legal_moves(self.game.position, role))

