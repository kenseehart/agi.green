
from typing import Any, Callable, Dict, List, Optional, Set, Tuple


class BMapView:
    'bidirection str:str mapping view'
    def __init__(self, bmap: 'BMap', index:int):
        self._bmap = bmap
        self._i = index

    def __repr__(self):
        return f'BMapView: {self.as_dict()}'

    def __getitem__(self, key: str) -> str:
        if self._i == 0:
            return sorted([b for a,b in self._bmap._pairs if a == key])
        else:
            return sorted([a for a,b in self._bmap._pairs if b == key])

    def as_dict(self) -> Dict[str, List[str]]:
        d = {}
        for a,b in sorted(self._bmap._pairs):
            if self._i == 0:
                d.setdefault(a, []).append(b)
            else:
                d.setdefault(b, []).append(a)
        return d

    def from_dict(self, d: Dict[str, List[str]]):
        self._bmap._pairs.clear()
        for a,blist in d.items():
            for b in blist:
                self.add(a,b)

    def add(self, a:str, b:str):
        if self._i == 0:
            self._bmap._pairs.add((a,b))
        else:
            self._bmap._pairs.add((b,a))


class BMap:
    '''bidirection str:str mapping

    implemented as set of pairs
    viewed as two inverse mappings

    Typical usage:
    a,b = BMap()

    `a` and `b` are inverse views of the same mapping.
    '''
    def __init__(self, data: Dict[str, str] = None):
        if data is None:
            self._pairs: Set[Tuple[str, str]] = set()
        else:
            self._pairs = set((a,b) for a,blist in data.items() for b in blist)

        self._views = [BMapView(self, i) for i in (0,1)]

    def __getitem__(self, i:int) -> BMapView:
        return self._views[i]


def test():
    x,y = BMap({'A':['b','c'], 'B':['c','d']})
    x.add('E','f')
    y.add('e','A')
    assert x['A'] == ['b','c','e']
    assert y['c'] == ['A','B']
    assert x['E'] == ['f']
    assert x.as_dict() == {'A':['b','c','e'], 'B':['c','d'], 'E':['f']}
    assert y.as_dict() == {'b':['A'], 'c':['A','B'], 'd':['B'], 'e':['A'], 'f':['E']}

    z,z1 = BMap()
    z.from_dict(x.as_dict())
    assert z.as_dict() == x.as_dict()
    assert z1.as_dict() == y.as_dict()
    print(z)

if __name__ == '__main__':
    test()


