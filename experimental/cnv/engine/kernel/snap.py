"""The snapshot's values (docs/engine/sim-modules.md 9.2, step S): what JSON can hold, plus marks for the rest, so the
same snapshot is kept in one process or written out (json.dumps / loads gives it back equal).

  a thing          {"$thing": serial}          (Thing.serial: its number in its world, World.build)
  a module         {"$module": [serial, k]}    (k: its place in the thing's modules)
  a tuple          {"$tuple": [...]}
  a set            {"$set": [...]}             (sorted by the JSON of each member: the same set, the same list)
  a frozenset      {"$frozenset": [...]}
  a dict whose keys are not all plain strings (or one starts with "$"): {"$items": [[key, value], ...]}, in order
  anything else    the caller's `extra(value)` (the host's own marks: a weapon of the template cache ...), else a
                   TypeError naming where it was -- a value is never dropped in silence.

decode(...) is the inverse on a world whose things are given by serial (`things`)."""
import json

from engine.kernel import module as _module

_PLAIN = (str, int, float, type(None))
MARKS = ('$thing', '$module', '$tuple', '$set', '$frozenset', '$items')


def _place(m):
    t = m.thing
    for k, x in enumerate(t.modules):
        if x is m:
            return k
    raise ValueError(f'{type(m).__name__} of {getattr(t, "name", t)!r} is not among its thing\'s modules')


def encode(v, extra=None, at='snapshot'):
    """`v` as the snapshot keeps it; `at`: where it is, for the error."""
    if isinstance(v, bool) or isinstance(v, _PLAIN):
        return v
    if isinstance(v, _module.Thing):
        return {'$thing': v.serial}
    if isinstance(v, _module.Module):
        return {'$module': [v.thing.serial, _place(v)]}
    if isinstance(v, list):
        return [encode(x, extra, f'{at}[{k}]') for k, x in enumerate(v)]
    if isinstance(v, tuple) and type(v) is tuple:
        return {'$tuple': [encode(x, extra, f'{at}[{k}]') for k, x in enumerate(v)]}
    if isinstance(v, (set, frozenset)) and type(v) in (set, frozenset):
        out = sorted((encode(x, extra, f'{at}{{}}') for x in v), key=lambda e: json.dumps(e, sort_keys=True))
        return {'$set' if type(v) is set else '$frozenset': out}
    if type(v) is dict:
        if all(type(k) is str and not k.startswith('$') for k in v):
            return {k: encode(x, extra, f'{at}.{k}') for k, x in v.items()}
        return {'$items': [[encode(k, extra, f'{at} key'), encode(x, extra, f'{at}[{k!r}]')] for k, x in v.items()]}
    if extra is not None:
        out = extra(v)
        if out is not NotImplemented:
            return out
    raise TypeError(f'{at}: a {type(v).__name__} the snapshot cannot keep ({v!r:.80})')


def decode(e, things, extra=None):
    """The value `e` keeps, on the world whose things are `things` (serial -> Thing); `extra(mark, value)` the
    caller's own marks (NotImplemented: not one of its)."""
    if isinstance(e, list):
        return [decode(x, things, extra) for x in e]
    if not isinstance(e, dict):
        return e
    if len(e) == 1:
        (mark, x), = e.items()
        if mark == '$thing':
            return things[x]
        if mark == '$module':
            return things[x[0]].modules[x[1]]
        if mark == '$tuple':
            return tuple(decode(y, things, extra) for y in x)
        if mark == '$set':
            return {decode(y, things, extra) for y in x}
        if mark == '$frozenset':
            return frozenset(decode(y, things, extra) for y in x)
        if mark == '$items':
            return {decode(k, things, extra): decode(y, things, extra) for k, y in x}
        if mark.startswith('$'):
            out = NotImplemented if extra is None else extra(mark, x)
            if out is NotImplemented:
                raise ValueError(f'a snapshot mark this world does not know: {mark}')
            return out
    return {k: decode(x, things, extra) for k, x in e.items()}


def module_state(m, extra=None):
    """A module's STATE as the snapshot keeps it: {field: value}, the fields it has set (one not set yet left out)."""
    d = vars(m)
    name = f'{type(m).__name__} of {getattr(m.thing, "name", m.thing)!r}'
    return {f: encode(d[f], extra, f'{name}.{f}') for f in m.STATE if f in d}


def set_module_state(m, state, things, extra=None):
    """Write a module's STATE back: the fields the snapshot has, and the ones it has not taken off (as it was)."""
    for f in m.STATE:
        if f in state:
            setattr(m, f, decode(state[f], things, extra))
        elif f in vars(m):
            delattr(m, f)
