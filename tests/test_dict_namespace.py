import pytest
from agi_green.dict_namespace import DictNamespace

def test_initialization():
    obj = DictNamespace(a=1, b=2)
    assert obj['a'] == 1
    assert obj['b'] == 2

def test_attribute_access():
    obj = DictNamespace(_depth=2)
    obj.c = 3
    obj.d.e = 4
    assert obj['c'] == 3
    assert obj['d']['e'] == 4

def test_default_values():
    obj = DictNamespace(_depth=2, _default='default')
    assert obj.x == 'default'
    assert obj.y.z == 'default'

def test_dirty_hash_and_change_detection():
    obj = DictNamespace()
    obj.a = 1
    assert obj._changed
    assert not obj._changed
    obj.a = 2
    assert obj._changed
    assert not obj._changed

def test_deep_update():
    obj = DictNamespace(_depth=2)
    obj._deep_update({'a': {'b': 2}})
    assert obj.a.b == 2

def test_attribute_and_item_deletion():
    obj = DictNamespace(a=1)
    del obj.a
    with pytest.raises(AttributeError):
        _ = obj.a

