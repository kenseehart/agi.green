'''
dispatcher
'''

import re
import asyncio
from collections import defaultdict
from typing import Callable, Awaitable, Dict, Any, Tuple, List
from types import MethodType

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
            return f'[{", ".join([trunc_repr(v, item_max_len) for v in value[:3]])}]'
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

class ProtocolDispatcherMeta(type):
    """Metaclass for protocols and dispatchers."""

    re_on_cmd = re.compile(r'^on_(\w+?)_(\w+)$')

    def __init__(cls, name, bases, attrs):
        super().__init__(name, bases, attrs)

        # Initialize the registry for the class
        cls._registered_methods: Dict[str, Dict[str, Callable[..., Awaitable[None]]]] = defaultdict(dict)

        # Register methods with the "on_" prefix
        for key in dir(cls):
            method = getattr(cls, key)
            m = cls.re_on_cmd.match(key)
            if m:
                proto, cmd = m.groups()
                cls._registered_methods[proto][cmd] = method
                print (f'Registered {proto}:{cmd} => {format_method(method)}')
                continue

class Protocol(metaclass=ProtocolDispatcherMeta):
    _registered_methods: Dict[str, Dict[str, Callable[..., Awaitable[None]]]]

    protocol_id: str = ''

    def __init__(self):
        super().__init__()
        self.parent: 'Protocol' = None
        self.children: List['Protocol'] = []
        self.exception = Exception
        self._registered_methods_cache = None
        self._registered_protocols_cache = None

    def __repr__(self):
        r =  self.__class__.__name__
        if self.protocol_id:
            r += f':{self.protocol_id}'

    @property
    def root(self):
        'Return root protocol (dispatcher)'
        return self.parent.root if self.parent else self

    @property
    def all_children(self) -> List['Protocol']:
        'Return all children of this protocol'
        return self.children + [c for p in self.children for c in p.all_children]

    @property
    def registered_methods(self) -> Dict[str, Dict[str, Callable[..., Awaitable[None]]]]:
        'Return all registered methods for this protocol and its children'
        if self._registered_methods_cache is None:
            self._registered_methods_cache = defaultdict(dict)
            for p in self.children:
                for proto, methods in p.registered_methods.items():
                    self._registered_methods_cache[proto].update(methods)
            for proto, methods in self._registered_methods.items():
                self._registered_methods_cache[proto].update(methods)
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
        self.children.append(protocol)
        self._registered_methods_cache = None
        self._registered_protocols_cache = None

    def get_protocol(self, protocol_id: str) -> "Protocol":
        return self.root.registered_protocols[protocol_id]

    def catch_exception(self, exception: Exception):
        self.exception = exception

    async def arun(self):
        raise NotImplementedError(f'{self.__class__.__name__}.arun() not implemented')

    async def aclose(self):
        pass

    async def handle_mesg(self, cmd:str, **kwargs):
        'receive message from any protocol and dispatch to registered handler'
        print(f'received: {self.protocol_id}:{format_call(cmd, kwargs)}')
        # call registered handler
        cmd_handlers = self.root.registered_methods[self.protocol_id]

        if cmd in cmd_handlers:
            await cmd_handlers[cmd](self, **kwargs)
        else:
            print(f"no handler for {self.protocol_id}:{cmd}")

    async def send(self, protocol_id, cmd:str, **kwargs):
        'send message via specified protocol'
        print(f'sending: {self.protocol_id}:{format_call(cmd, kwargs)}')
        await self.root.get_protocol(protocol_id).do_send(cmd, **kwargs)

    async def do_send(self, cmd:str, **kwargs):
        'override to implement send'
        raise NotImplementedError(f'{self.__class__.__name__}.do_send() not implemented')

class Dispatcher(Protocol):
    '''
    Base class for dispatchers
    Manages connections and messaging via protocols
    '''
    registed_methods: Dict[str, Dict[str, Callable[..., Awaitable[None]]]]

    def __init__(self, *protocols: Tuple[Protocol]):
        super().__init__()
        for p in protocols:
            self.add_protocol(p)

    def run(self):
        loop = asyncio.get_event_loop()
        try:
            loop.run_until_complete(self.arun())
        except Exception as e:
            print (e)
            raise
        finally:
            loop.run_until_complete(self.aclose())
            loop.close()

    async def arun(self):
        # Run all registered async run methods in parallel
        await asyncio.gather(*(p.arun() for p in self.children))

    async def aclose(self):
        # Run all registered async close methods in parallel
        await asyncio.gather(*(p.aclose() for p in self.children))


