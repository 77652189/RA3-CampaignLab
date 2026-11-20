"""Read-only views a port hands its readers in place of the world's own containers (review 1119z P2 #2 + y P3 #5:
`systems.queues.clear()` emptied the production queues past the command port; `firing()` / `volleys()` /
`attachments()` and the other readers of the observation port were the same class).

`view(v)` is live, not a copy: a reader that keeps one sees the world change under it, as it saw the container
itself (the record reads every frame, so nothing is copied). A view has the read half of its container's protocol
(Mapping / Sequence / Set: get, items, len, in, iteration, indexing, slicing, ==) and none of the write half
(`[k] = v`, del, append, add, clear, pop ... raise AttributeError or TypeError). A value read through a view is a
view too, to any depth (the queue's job dicts, the switches' inner dicts, a series row's readings). A tuple holding
a container comes back a new tuple of views (a namedtuple keeps its type); one holding none comes back itself.
Anything not a container -- numbers, strings, a thing, a template's data -- passes through as it is.

Not json / pickle: a reader that writes one out turns it into a dict / list first (`dict(v)`, `list(v)`), as a
reader of the world's own would have had to for a set."""
import collections
import collections.abc as abc

_LEAF = frozenset((str, bytes, int, float, bool, type(None), complex))
_CONTAINER = (list, dict, set, tuple, collections.deque, abc.Mapping, abc.Set, abc.Sequence)


def view(v):
    """v read only (see the module): a view of a container, a tuple of views, or v itself."""
    t = type(v)
    if t in _LEAF or isinstance(v, (MapView, SeqView, SetView)):
        return v
    if isinstance(v, tuple):
        if not any(type(x) not in _LEAF and isinstance(x, _CONTAINER) for x in v):
            return v
        items = [view(x) for x in v]
        return v._make(items) if hasattr(v, '_make') else tuple(items)
    if isinstance(v, abc.Mapping):
        return MapView(v)
    if isinstance(v, (abc.Set, set, frozenset)):
        return v if isinstance(v, frozenset) else SetView(v)
    if isinstance(v, (list, collections.deque, abc.Sequence)) and not isinstance(v, (str, bytes, bytearray)):
        return SeqView(v)
    return v


class MapView(abc.Mapping):
    """A mapping read only and live; its values read as views."""
    __slots__ = ('_m',)

    def __init__(self, m):
        self._m = m

    def __getitem__(self, k):
        return view(self._m[k])

    def __iter__(self):
        return iter(self._m)

    def __len__(self):
        return len(self._m)

    def __contains__(self, k):
        return k in self._m

    def __eq__(self, other):
        if isinstance(other, abc.Mapping):
            return len(self) == len(other) and all(k in other and self[k] == other[k] for k in self)
        return NotImplemented

    __hash__ = None

    def __repr__(self):
        return f'MapView({self._m!r})'


class SeqView(abc.Sequence):
    """A list read only and live; its items read as views (a slice reads as a tuple of them)."""
    __slots__ = ('_s',)

    def __init__(self, s):
        self._s = s

    def __getitem__(self, i):
        if isinstance(i, slice):
            return tuple(view(x) for x in self._s[i])
        return view(self._s[i])

    def __iter__(self):
        return map(view, self._s)

    def __len__(self):
        return len(self._s)

    def __contains__(self, x):
        return x in self._s

    def __eq__(self, other):
        if isinstance(other, (list, tuple, SeqView)):
            return len(self) == len(other) and all(a == b for a, b in zip(self, other))
        return NotImplemented

    __hash__ = None

    def __add__(self, other):
        if isinstance(other, (list, tuple, SeqView)):
            return tuple(self) + tuple(other)
        return NotImplemented

    def __radd__(self, other):
        if isinstance(other, (list, tuple)):
            return tuple(other) + tuple(self)
        return NotImplemented

    def __repr__(self):
        return f'SeqView({self._s!r})'


class SetView(abc.Set):
    """A set read only and live (its members are hashable, so not containers to wrap)."""
    __slots__ = ('_s',)

    def __init__(self, s):
        self._s = s

    def __contains__(self, x):
        return x in self._s

    def __iter__(self):
        return iter(self._s)

    def __len__(self):
        return len(self._s)

    @classmethod
    def _from_iterable(cls, it):
        return frozenset(it)               # `a | b`, `a - b` ... make a new (frozen) set, not a view

    def __repr__(self):
        return f'SetView({self._s!r})'
