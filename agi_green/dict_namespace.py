from typing import Any

import json
import hashlib

def hash_mutable(obj):
    # Serialize the object to a JSON string, sorting keys to ensure consistent order
    obj_str = json.dumps(obj)
    # Use hashlib to create a hash of the serialized string
    return hashlib.sha256(obj_str.encode('utf-8')).hexdigest()

class DictNamespace(dict):
    '''A javascript style object for attribute access to dict keys
    Attributes starting with _ are not stored in the dict (unless written as dict keys) so they can be used for internal state
    Only collisions are explicit access of dict methods (e.g. copy, items, keys, ...) which retain dict behavior
    But these may safely be accessed as dict keys, e.g. obj['items']=123

    Content is expected to be json serializable
    '''
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._dirty_hash = hash_mutable(self)

    def deep_update(self, d):
        'update self with d, recursively updating any dicts in self. Recursion stops one level below DictNamespace nodes.'
        for k, v in d.items():
            if k in self:
                v0 = self[k]
                if isinstance(v, DictNamespace):
                    if isinstance(v0, dict):
                        self.k = v0 = DictNamespace(v0)

                if isinstance(v0, DictNamespace):
                    if isinstance(v, dict):
                        v0.deep_update(v)
                    else:
                        raise ValueError(f"Cannot update DictNamespace with non-dict {v}")
                elif isinstance(v0, dict):
                    if isinstance(v, dict):
                        v0.update(v)
                    else:
                        raise ValueError(f"Cannot update dict with non-dict {v}")
            else:
                self[k] = v

    @property
    def _changed(self):
        'return True if the object has been changed since the last time this was called'
        h = hash_mutable(self)
        if h != self._dirty_hash:
            self._dirty_hash = h
            return True
        return False

    def __getattr__(self, name):
        try:
            return super().__getattribute__(name)
        except AttributeError:
            try:
                return self[name]
            except KeyError as e:
                raise AttributeError(f"Attribute {name} not found") from e

    def __setattr__(self, name: str, value: Any) -> None:
        if name.startswith('_'):
            super().__setattr__(name, value)
        else:
            self[name] = value

    def __delattr__(self, name: str) -> None:
        del self[name]

