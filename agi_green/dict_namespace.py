from typing import Any, Callable
import hashlib
import asyncio
import weakref
import os

def hash_mutable(obj):
    return hashlib.sha256(str(obj).encode('utf-8')).hexdigest()

class DictNamespace(dict):
    '''An optionally asychronous reactive javascript style dict for attribute access to keys
    Attributes starting with _ are stored as actual attributes, not in the dict (unless written as dict keys) so they can be used for internal state
    Pre-existing attributes have priority, such as dict methods (e.g. copy, items, keys, ...)
    But these name may safely be accessed as dict keys, e.g. obj['items']=123, assert obj['items']==123, iter(obj.items())
    Collisions only occur when such attributes are explicitly set, e.g. obj.items=456 => ValueError

    Asynchronous only refers to the ability to bind change handlers to the object. If you don't use this feature, ignore async.

    Content is expected to be json serializable

    _default is the default value for missing attributes.
    Unlike defaultdict, the default value only applies to attribute access, not dict access

    _depth is the number of layers that are DictNamespace by default.
    _default is the default leaf value (or callable to generate it)
    note that unlike defaultdict, you don't need to wrap the default in a lambda

    You can make variable depth simply by assigning a DictNamespace()

    You can attach change handlers to the object with _bind_change_handler(handler).
    '''
    def __init__(self, _depth=0, _default: Any=None, **kwargs):
        super().__init__(**kwargs)

        if _depth > 0:
            self._default = lambda: DictNamespace(_depth=_depth-1, _default=_default)
        else:
            if isinstance(_default, Callable):
                self._default = _default
            else:
                self._default = lambda: _default

        self._dirty_hashes = {}

        if kwargs:
            self._deep_update(kwargs)

    def _deep_update(self, d):
        'update self with d recursively'
        for k, v in d.items():
            v0 = self.get(k, None)

            if isinstance(v, dict) and isinstance(v0, dict):
                if not isinstance(v0, DictNamespace):
                    v0 = DictNamespace(**v)
                    self[k]=v0

                v0._deep_update(v)
            else:
                if isinstance(v, dict) and not isinstance(v, DictNamespace):
                    v = DictNamespace(**v)

                self[k] = v

    def _changed(self, key:str):
        'return True if the object has been changed since the last time this was called with this key'
        h = hash_mutable(self)
        if h != self._dirty_hashes.get(key):
            self._dirty_hashes[key] = h
            return True
        return False

    def _ensure_finalization(self):
        'ensure that the object is _dead when it is garbage collected'
        if not hasattr(self, '_dead'):
            weakref.finalize(self, self._kill)
            self._dead = False

    def _kill(self):
        'kill the object'
        self._dead = True

    async def _bind_change_handler(self, handler:Callable, delay:float=0.1):
        'asyncronously call handler whenever this object changes, within the delay'
        key = id(handler)
        self._ensure_finalization()

        async def change_loop():
            while not self._dead:
                if self._changed(key):
                    await handler()
                await asyncio.sleep(delay)

        asyncio.create_task(change_loop())

    def __getattr__(self, name):
        if name.startswith('_'):
            raise AttributeError(name)

        try:
            return self[name]
        except KeyError:
            self[name] = self._default()
            return self[name]

    def _expandvars(self):
        'replace $VAR with os.environ["VAR"] for all strings, return the modified object'

        def expandvars(x):
            if isinstance(x, str):
                return os.path.expandvars(x)
            elif isinstance(x, dict):
                return DictNamespace(**{k: expandvars(v) for k, v in x.items()})
            elif isinstance(x, list):
                return [expandvars(v) for v in x]
            else:
                return x

        return expandvars(self)

    def __setattr__(self, name: str, value: Any) -> None:
        if name.startswith('_'):
            super().__setattr__(name, value)
        else:
            try:
                super().__getattribute__(name)
                raise AttributeError(f"Cannot set predefined attribute `{name}`. Use obj['{name}'] instead, or use `_{name}` for internal state")
            except AttributeError:
                if isinstance(value, dict):
                    value = DictNamespace(**value)
                self[name] = value

    def __delattr__(self, name: str) -> None:
        if name.startswith('_'):
            super().__delattr__(name)
        else:
            del self[name]




