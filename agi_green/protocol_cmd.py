import os
from os.path import join, dirname, splitext, isabs
import re
from typing import Callable, Awaitable, Dict, Any, List, Set, Union, Tuple
from logging import getLogger, Logger
import logging
from os.path import exists
import ast

from agi_green.dispatcher import Protocol, format_call
from agi_green.config import Config

here = dirname(__file__)
logger = logging.getLogger(__name__)
log_level = os.getenv('LOG_LEVEL', 'WARNING').upper()
logging.basicConfig(level=log_level)

# [cmd:foo(x=5, y='333')]
# warning, this regex can't handle lists of tuples due to )] termination
# may be suplemented with extention to handle that
re_command = re.compile(r'''\[cmd:(\w+(?:[^\n](?!(?:\)\])))*.\))\]''')

def ast_node_to_value(node):
    ''
    if isinstance(node, ast.Constant):
        # Handle atomic literals like numbers, strings, etc.
        return node.value
    elif isinstance(node, ast.List):
        # Handle list literals
        return [ast_node_to_value(element) for element in node.elts]
    elif isinstance(node, ast.Tuple):
        # Handle tuple literals
        return tuple(ast_node_to_value(element) for element in node.elts)
    elif isinstance(node, ast.Dict):
        # Handle dict literals
        return {ast_node_to_value(key): ast_node_to_value(value) for key, value in zip(node.keys, node.values)}
    elif isinstance(node, ast.Set):
        # Handle set literals
        return {ast_node_to_value(element) for element in node.elts}
    # Add more cases here for other compound types if needed
    else:
        raise TypeError("Unsupported AST node type")

class CommandProtocol(Protocol):
    '''
    Command protocol

    Handle custom commands
    '''
    protocol_id: str = 'cmd'

    def __init__(self, config:Config, **kwargs):
        super().__init__(**kwargs)
        self.config = config

    async def run(self):
        self.add_task(super().run())

    async def on_ws_chat_input(self, content:str):
        'receive command syntax on the mq chat channel'

        # [cmd:gameio_start(game='y93', players=['user1', 'user2'])]

        for match in re_command.finditer(content):
            call_str = match.group(1)

            # TODO: Handle unbalanced '[(' due to regex limitations: tack on more '.*\)\]' matches
            # meanwhile lists of tuples will be broken
            # workaround is lists of lists.  This is a limitation of the regex, not the parser
            try:
                result = await self.send('cmd', call_str)
            except Exception as e:
                result = f'error: {e}'

            if result is None:
                result = f'error: {call_str} command not found'

            await self.send('ws', 'append_chat', author='info', content=result)

    async def do_send(self, cmd:str, **kwargs):
        '''cmd can be a function call expression like "foo(x=5, y='333')" or a simple function name like "foo"'''
        # Parse cmd as a function call expression using ast
        result = ''

        try:
            node = ast.parse(cmd, mode='eval').body

            if isinstance(node, ast.Name):
                return await super().do_send(cmd, **kwargs)

            elif isinstance(node, ast.Call):
                func_name = node.func.id
                kwargs |= {kw.arg: ast_node_to_value(kw.value) for kw in node.keywords}
                result = await self.send('cmd', func_name, **kwargs)
            else:
                result = f'error: Invalid command syntax: {cmd}'

        except (SyntaxError, ValueError) as e:
            # This might occur if the matched string isn't a valid Python function call
            result = f'error: {e} `{cmd}`'

        result = result or ''

        if result.startswith('error'):
            logger.error(result)
        else:
            logger.info('%s => "%s"', cmd, result)

        return result

