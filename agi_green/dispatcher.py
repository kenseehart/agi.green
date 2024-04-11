'''
dispatcher

'''


import sys
import os
import re
import asyncio
from collections import defaultdict
from typing import Callable, Awaitable, Dict, Any, Tuple, List
from types import MethodType, FunctionType
import logging
import inspect
from functools import wraps
import weakref
import time
import gc
from .dict_namespace import DictNamespace
from .config_namespace import ConfigNamespace

if '-D' in sys.argv:
    log_format = '%(name)s - %(levelname)s - %(message)s'
else:
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'

logger = logging.getLogger(__name__)
log_level = os.getenv('LOG_LEVEL', 'WARNING').upper()
logging.basicConfig(level=log_level, format=log_format)

def trunc_repr(value:Any, max_len:int=30) -> str:
    'repr() with truncation approximatly to max_len'
    r = repr(value)
    if len(r) <= max_len:
        return r

    item_max_len = (max_len+8) // 2

    match value:
        case int():
            return repr(value)
        case float():
            return f'{value:1.3f}'
        case str():
            return repr(value[:max_len] + '...')
        case list():
            if len(value) > 3:
                value = value[:3] + [...]
            return f'[{", ".join([trunc_repr(v, item_max_len) for v in value])}]'
        case tuple():
            if len(value) > 3:
                value = value[:3] + (...,)
            return f'({", ".join([trunc_repr(v, item_max_len) for v in value])})'
        case dict():
            items = [f"{trunc_repr(k, item_max_len)}: {trunc_repr(v, item_max_len)}" for k, v in value.items()]
            if len(items) > 2:
                items = items[:2] + ['...']
            return f'{{{", ".join(items)}}}'
        case _:
            return f'{r[:max_len]}...'


def format_call(cmd:str, kwargs:Dict[str, Any]) -> str:
    'format command call for logging and debugging'
    return f"{cmd}({', '.join([f'{k}={trunc_repr(v)}' for k,v in kwargs.items()])})"

def format_method(method: MethodType) -> str:
    'format method for logging, debugging, and docs'
    args = ', '.join(method.__code__.co_varnames[:method.__code__.co_argcount])
    return f"{method.__qualname__}({args})"


def add_kwargs(func):
    '''Wrapper function to discard extra kwargs
    - make usage of any keword argument optional without explicit **kwargs
    - support backwards compatibility for message handlers when new kwargs are added
    '''
    @wraps(func)
    def wrapped(*args, **kwargs):
        # Extract only the valid kwargs based on the original function's signature
        sig = inspect.signature(func)
        valid_kwargs = {k: v for k, v in kwargs.items() if k in sig.parameters}
        # Check for signature match
        try:
            bound_args = sig.bind(*args, **valid_kwargs)
            bound_args.apply_defaults()
        except TypeError as e:
            target_file = func.__code__.co_filename
            target_line = func.__code__.co_firstlineno
            func_signature = str(sig)
            raise TypeError(f'Signature mismatch in call to {func.__qualname__}{func_signature} '
                            f'File "{target_file}", line {target_line}: {e}')

        # Call the function with valid arguments only
        return func(*bound_args.args, **bound_args.kwargs)

    # Modify the wrapper function's signature to include **kwargs
    sig = inspect.signature(func)

    # Check if the function already has a variable keyword argument
    if any(p.kind == inspect.Parameter.VAR_KEYWORD for p in sig.parameters.values()):
        return func

    kwargs_param = inspect.Parameter('__kwargs', inspect.Parameter.VAR_KEYWORD)
    new_sig = sig.replace(parameters=list(sig.parameters.values()) + [kwargs_param])
    wrapped.__signature__ = new_sig

    logger.debug(f'added **kwargs to {format_method(func)}')

    return wrapped

class IgnoreException(Exception):
    pass


_protocol_garbage_tracker = None

def protocol_handler(_func=None, *, priority=2, update=False):
    def decorator(func):
        setattr(func, 'priority', priority)
        setattr(func, 'update', update)
        setattr(func, 'is_protocol_handler', True)
        return func

    if isinstance(_func, FunctionType):
        return decorator(_func)

    return decorator

class Protocol:
    _registered_methods: Dict[str, Dict[str, Callable[..., Awaitable[None]]]]
    dispatcher: 'Dispatcher'
    protocol_id: str = ''

    @property
    def is_server(self) -> bool:
        'True if this protocol instance is a server'
        if self is self.dispatcher:
            return False
        return self.dispatcher.is_server

    def __init__(self, parent: 'Protocol' = None):
        parent.add_protocol(self) if parent else None
        self.children: List['Protocol'] = []
        self.exception = Exception
        self._registered_methods_cache = None
        self._registered_protocols_cache = None
        self.running_tasks = []
        self._closed = False
        logger.info(f'created: {type(self)}')

    def __repr__(self):
        r =  self.__class__.__name__
        if self.protocol_id:
            r += f':{self.protocol_id}'
        return r

    def _register_methods(self):
        'Register methods for a protocol'
        registry = self.dispatcher._registered_methods_cache
        re_on_cmd = re.compile(r'^on_(\w+?)_(\w+)$')

        # Register methods for children
        for ch in self.children:
            ch._register_methods()

        # Register methods with the "on_" prefix
        for key in dir(self):
            m = re_on_cmd.match(key)
            method = getattr(self, key)
            if not isinstance(method, FunctionType|MethodType):
                continue
            if m:
                if not hasattr(method, 'is_protocol_handler'):
                    logger.warning(f'protocol handler {key} not decorated => {format_method(method)}')
                    continue
                if isinstance(method, MethodType):
                    proto, cmd = m.groups()
                    if method not in registry[proto][cmd]:
                        setattr(self.__class__, key, add_kwargs(getattr(self.__class__, key)))
                        method = getattr(self, key)
                        registry[proto][cmd].append(method)
                        logger.debug(f'Registered {proto}:{cmd} => {format_method(method)}')
            else:
                if hasattr(method, 'is_protocol_handler'):
                    logger.error(f'protocol handler name syntax error: {format_method(method)}')

    @property
    def all_children(self) -> List['Protocol']:
        'Return all children of this protocol'
        return self.children + [c for p in self.children for c in p.all_children]

    @property
    def registered_methods(self) -> Dict[str, Dict[str, Callable[..., Awaitable[None]]]]:
        'Return all registered methods for this protocol and its children'
        if self._registered_methods_cache is None:
            self._registered_methods_cache = defaultdict(lambda: defaultdict(list))
            self._register_methods()
            # sort by priority
            for proto, cmds in self._registered_methods_cache.items():
                for cmd, handlers in cmds.items():
                    self._registered_methods_cache[proto][cmd] = sorted(handlers, key=lambda x: x.priority)
        return self._registered_methods_cache

    @property
    def registered_protocols(self) -> Dict[str, 'Protocol']:
        'Return all registered protocols for this protocol and its children'
        if self._registered_protocols_cache is None:
            self._registered_protocols_cache = {}
            for p in self.children:
                self._registered_protocols_cache[p.protocol_id] = p
                self._registered_protocols_cache.update(p.registered_protocols)
        return self._registered_protocols_cache

    def add_protocol(self, protocol: "Protocol"):
        protocol.parent = self
        protocol.dispatcher = self.dispatcher
        protocol.context = self.context
        self.children.append(protocol)
        self._registered_methods_cache = None
        self._registered_protocols_cache = None

    def get_protocol(self, protocol_id: str) -> "Protocol":
        try:
            return self.registered_protocols[protocol_id]
        except KeyError as e:
            raise ValueError(f'protocol {protocol_id} not found in {self}') from e

    def catch_exception(self, exception: Exception):
        self.exception = exception

    def add_task(self, coro):
        """Starts a task and adds it to running_tasks."""
        if self._closed:
            raise Exception("Protocol is closed. Cannot add new tasks.")
        task = asyncio.create_task(coro)
        self.running_tasks.append(task)
        task.add_done_callback(self.running_tasks.remove)

    async def run(self):
        pass

    async def close(self):
        self._closed = True

        logger.info(f'closing: {self}')

        for task in self.running_tasks:
            task.cancel()

        await asyncio.gather(*self.running_tasks, return_exceptions=True)

        self.running_tasks.clear()

        await asyncio.gather(*[p.close() for p in self.children])

        if self.parent:
            self.parent.children.remove(self)
            self.parent = None

        self._registered_methods_cache = None
        self._registered_protocols_cache = None

        obj_id = id(self)
        _protocol_garbage_tracker[obj_id] = [weakref.ref(self, self._create_finalize_callback(obj_id)), time.time()]

    @staticmethod
    def _create_finalize_callback(obj_id):
        def _finalize(ref):
            del _protocol_garbage_tracker[obj_id]
            logger.debug(f'finalizing: {obj_id}')
        return _finalize

    @staticmethod
    def reveal_orphan(ref, indent='    '):
        'Reveal orphaned protocols'
        if isinstance(ref, weakref.ref):
            orphan = ref()
        else:
            orphan = ref

        if orphan is not None:
            refs = gc.get_referrers(orphan)
            for orphan_r in refs:
                if isinstance(orphan_r, dict):
                    for k, v in orphan_r.items():
                        if v is orphan and not k.startswith('orphan'):
                            logger.debug(f'{indent}ref: {orphan} dict key {k}')
                            break
                else:
                    logger.debug(f'{indent}ref: {orphan} referrer {orphan_r}')

    @staticmethod
    async def scan_orphans():
        'Scan for orphaned protocols'
        while True:
            await asyncio.sleep(1)
            for k, v in _protocol_garbage_tracker.items():
                if v[1] < time.time() - 2:
                    logger.warn(f'orphaned protocol: {v[0]()}')
                    Protocol.reveal_orphan(v[0])
                    v[1] = time.time() + 30 # prevent repeated warnings for this orphan for 30 seconds

    async def handle_mesg(self, cmd:str, **kwargs):
        'receive message from any protocol and dispatch to registered handlers, return last non-None response'
        logger.info(f'received: {self.protocol_id}:{format_call(cmd, kwargs)}')

        # call registered handler
        cmd_handlers = self.dispatcher.registered_methods[self.protocol_id][cmd]

        if cmd_handlers:
            for handler in cmd_handlers:
                response = None
                try:
                    r = await handler(**kwargs)

                    if handler.update:
                        if isinstance(r, dict):
                            kwargs.update(r)
                            r = kwargs # update mode returns the updated kwargs
                        else:
                            logger.error(f'{format_method(handler)} must return a dict (update mode)')

                    if r is not None:
                        response = r
                except self.exception as e:
                    logger.error(e, exc_info=True)
            return response
        else:
            logger.warn(f"no handler for {self.protocol_id}:{cmd}")

    async def send(self, protocol_id, cmd:str, **kwargs):
        'send message via specified protocol'
        logger.info(f'sending: {protocol_id}:{format_call(cmd, kwargs)}')
        return await self.dispatcher.get_protocol(protocol_id).do_send(cmd, **kwargs)

    async def do_send(self, cmd: str, **kwargs):
        'default: send request to self - override to implement a protocol specific send'
        return await self.handle_mesg(cmd, **kwargs)


class Dispatcher(Protocol):
    @property
    def is_server(self) -> bool:
        'True if this protocol is a server'
        return False

    def __init__(self, session_id:str=None):
        super().__init__()
        self.dispatcher = self
        self.session_id = session_id
        self.stop_event = asyncio.Event()
        self.context = DictNamespace(1)

        if not hasattr(Protocol, 'config'):
            # Set the config for all protocols globally
            Protocol.config = ConfigNamespace(
                '$WORKSPACE/chat.agi.green/agi_config.yaml',
                '$WORKSPACE/chat.agi.green/agi_config_default.yaml',
                depth=2)

    async def run(self):
        'run the dispatcher in additive async mode (concurrent dispatchers use run()).'
        global _protocol_garbage_tracker
        self.running = True

        self.add_task(super().run())

        # Start all registered async run methods concurrently
        for p in self.children:
            #logger.info(f'task launched for {self}:{id(self)}->{p}')
            self.add_task(p.run())

        if _protocol_garbage_tracker is None:
            _protocol_garbage_tracker = {}
            self.add_task(self.scan_orphans())

        # Wait for the stop signal
        await self.stop_event.wait()
        logger.info(f'{self}.run() stopped')

    async def close(self):
        'close all subtasks concurrently'
        await super().close()
        close_tasks = [asyncio.create_task(p.close()) for p in self.children]
        await asyncio.gather(*close_tasks)
        self.stop()

    def stop(self):
        'signal to stop the Dispatcher'
        self.stop_event.set()


