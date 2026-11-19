"""A run's snapshot with the skirmish AI (step S 11b-4, docs/engine/sim-modules.md 9.2): the SimAI's and each Brain's
own fields sorted as simsnap sorts the Sim's, around simsnap's snapshot of the Sim the SimAI plays on.

How a field is kept: simsnap's kinds (STATE, ALIAS, CACHE, WIRE, STATIC) and
  HOST      the Sim the SimAI plays on: simsnap.snapshot / restore
  BRAINS    the brains: each Brain's own fields by BRAIN, made anew on the new SimAI the way attach makes them
  MODEL     an object of the AI plugin's (the engine model's ra3model.ai, private: ADR 0033): taken only through
            the plugin's snapshot port (`snapshot(key)` / `restore(data, obj)`, sim-modules.md 9.2); the host never
            reads its fields. A plugin object without the port: the snapshot is an error naming it, never left out.

A brain's own values as engine/kernel/snap.py keeps them, plus its marks: a Unit it wraps {"$unit": its body's
serial} (one Unit a body: the new brain's wrapper of that body), a random.Random {"$random": its state}, a plugin
object the brain made itself (a HuntGoal of _hunt_goals) {"$model": [module, class, its port's data]}, made anew by
its class and written back through the port. A Team is kept by its snapshot_key() and found again on the restored
plugin by `ai.team(key)` (a wrapper's team, _exp_teams' keys). The plugin's port gets `key(x)` (a Unit or a thing
of the host -> its mark) and on restore `obj(mark)` (the new run's). The Bodies the brain holds out of the world
(_protos, Sim.proto) go to simsnap as roots: kept with the Sim's things, made bare on the new world.
Not yet: a SimAI with record=True (HOOKS 9's runs, held by the plugin's Run objects): an error naming it.

11b-4a: the tables, `unclassified(w)` (guard 4.3), the port refused by name. 11b-4b (this): the brains' public
fields. 11b-4c: the plugin's ports (the engine model's repository)."""
import importlib
import random

import simsnap
from engine.kernel import module as _module
from engine.kernel import snap
from simsnap import ALIAS, CACHE, STATE, STATIC, WIRE

HOST, BRAINS, MODEL = 'host', 'brains', 'model'
VERSION = 2             # 2: the brains (11b-4b)

SIMAI = {
    'sim': HOST, 'world': ALIAS, 'garrison': ALIAS, 'peers': WIRE,
    'mod': STATIC, 'level': STATIC, 'seed': STATIC, 'blocks': STATIC, 'record': STATIC,
    'lib': STATIC, 'data': STATIC,      # the model's library and AI data; the mission's own personalities added once
    '_assigned': STATIC,                # (own_personalities) the same way on the new SimAI; the personalities the
    #                                     sides settle on, in SimAI.__init__
    'brains': BRAINS, 'done_to': STATE, '_own_done': STATE,
    '_data': CACHE, '_cost': CACHE, '_menu': CACHE, '_cs': CACHE, '_kinds': CACHE, '_std': CACHE,
    'pullback': {'world': WIRE, 'peers': WIRE, 'returning': STATE, 'log': STATE, 'armies': STATIC,
                 'filters': CACHE},
}
ALIASES = {('world',): ('sim',), ('garrison',): ('sim', 'garrison')}

BRAIN = {
    'host': WIRE, 'world': WIRE, 'peers': WIRE, 'player': STATIC,
    'made_as': STATIC,      # (side, personality): the snapshot's row, the new brain made with them
    # the plugin's: the AI player and the blocks Brain.attach gives it, the view it is handed, the defence's bases
    'ai': MODEL, 'tactics': MODEL, 'targets': MODEL, 'defense': MODEL, 'micro': MODEL, 'powers': MODEL,
    'view': MODEL, 'base': MODEL, 'bases': MODEL,
    # the brain's own
    'paths': STATE, 'path_rng': STATE, 'tower_rng': STATE, 'place_rng': STATE, 'yard_q': STATE, 'yard_rest': STATE,
    'unit_q': STATE, 'made': STATE, 'wrappers': STATE, 'later': STATE, 'trace': STATE, 'born': STATE, 'frame': STATE,
    'woke': STATE, 'ids': STATE, 'hp': STATE, 'hurt_at': STATE, 'seen_t': STATE, 'fired': STATE, 'home': STATE,
    'rec': STATE, '_rec_runs': STATE, '_rec_mem': STATE, '_rec_bodies': STATE,
    'expansion_anchor': STATE, 'expansion_initial_yards': STATE, '_has_initial_yards': STATE,
    '_switched': STATE, '_prio_seen': STATE, '_hunt_goals': STATE, '_hunt_cells': STATE,
    '_exp_teams': STATE, '_exp_slots': STATE, '_unpack_ordered': STATE,
    # a Body never placed (Sim.proto): built once, it took a serial of the world -- kept, so the serials after it
    # are the same as the run never stopped
    '_protos': STATE,
    # template (or the yards and the structures standing) -> what its data says
    '_team_names': CACHE, '_template_guns': CACHE, '_refinery_spots': CACHE, '_allied_radii': CACHE,
    '_build_radii': CACHE, '_node_offsets': CACHE, '_miner_toggles': CACHE,
}
_OWN = [f for f, k in BRAIN.items() if k == STATE and f not in ('wrappers', '_exp_teams')]   # those two: by hand
_MODEL = [f for f, k in BRAIN.items() if k == MODEL]

UNIT = {'body': STATE, 'peers': WIRE, 'template': STATIC, 'kindof': STATIC, 'surface': STATIC, 'team': MODEL}


def _get(obj, path):
    for f in path:
        obj = getattr(obj, f)
    return obj


def _protos(w):
    return [p for b in w.brains.values() for p in b.__dict__.get('_protos', {}).values()]


def unclassified(w):
    """Step S's guard 4.3 for the SimAI: every field of it, of its parts, of its brains and of the Units they wrap
    that SIMAI / BRAIN / UNIT do not sort, every ALIAS that is not the object it names, and the Sim's own
    (simsnap.unclassified, the brains' Bodies never placed with its things) -- all of them, sorted."""
    out = list(simsnap.unclassified(w.sim, _protos(w)))

    def walk(obj, table, at):
        for f, v in simsnap._fields(obj).items():
            kind = table.get(f)
            if kind is None:
                out.append('.'.join(at + (f,)))
            elif isinstance(kind, dict):
                walk(v, kind, at + (f,))
    walk(w, SIMAI, ('simai',))
    for path, named in ALIASES.items():
        if path[0] in simsnap._fields(w) and _get(w, path) is not _get(w, named):
            out.append('simai.' + '.'.join(path) + ' (not the object it names)')
    for b in w.brains.values():
        walk(b, BRAIN, ('Brain',))
        for u in b.wrappers.values():
            walk(u, UNIT, ('Unit',))
    return sorted(set(out))


def _ported(x):
    return callable(getattr(x, 'snapshot', None)) and callable(getattr(x, 'restore', None))


def _name(x):
    return f'{type(x).__module__}.{type(x).__qualname__}'


def _no_port(w):
    """The first plugin object a brain holds that has not the snapshot port: (where, its class), else None. A held
    Team needs snapshot_key and the AI player `team(key)`; a run with record=True's runs is not kept yet."""
    for player, b in w.brains.items():
        own = simsnap._fields(b)
        for f in _MODEL:
            v = own.get(f)
            for x in (v if isinstance(v, (list, tuple)) else () if v is None else (v,)):
                if not _ported(x):
                    return f'{player}.{f}', _name(x)
        for name, g in own.get('_hunt_goals', {}).items():
            if not _ported(g):
                return f'{player}._hunt_goals[{name!r}]', _name(g)
        teams = [(f'{player}.wrappers[{u.body.name!r}].team', u.team) for u in b.wrappers.values()
                 if u.team is not None]
        teams += [(f'{player}._exp_teams', t) for t, _ in own.get('_exp_teams', [])]
        for at, t in teams:
            if not callable(getattr(t, 'snapshot_key', None)):
                return at, _name(t)
            if not callable(getattr(b.ai, 'team', None)):
                return f'{player}.ai (team(key), for {at})', _name(b.ai)
        if own.get('_rec_runs'):
            return f'{player}._rec_runs (SimAI record=True: the runs HOOKS 9 follows)', _name(next(
                iter(b._rec_runs.values()))[1])
    return None


def _model_modules(w):
    return {m.__name__: m for m in (w.mod or {}).values()}


def _key_of(held):
    """The port's `key(x)`: a Unit or a thing of the host as its mark; each thing given is noted in `held` (kept as
    one of simsnap's roots)."""
    def key(x):
        if isinstance(x, _module.Thing):
            held.append(x)
            return {'$thing': x.serial}
        body = getattr(x, 'body', None)
        if isinstance(body, _module.Thing) and type(x).__name__ == 'Unit':
            held.append(body)
            return {'$unit': body.serial}
        raise TypeError(f'simaisnap: the AI plugin asked a key for a {type(x).__name__}, not a thing or a Unit')
    return key


def _take_brain(w, b, held):
    key = _key_of(held)
    mods = _model_modules(w)

    def extra(v):
        if isinstance(v, random.Random):
            ver, st, gauss = v.getstate()
            return {'$random': [ver, list(st), gauss]}
        if type(v).__name__ == 'Unit' and isinstance(getattr(v, 'body', None), _module.Thing):
            return key(v)
        if type(v).__module__ in mods:
            return {'$model': [type(v).__module__, type(v).__qualname__, v.snapshot(key)]}
        return NotImplemented

    own = simsnap._fields(b)
    fields = {f: snap.encode(own[f], extra, f'Brain {b.player}.{f}') for f in _OWN if f in own}
    held.extend(x for f in _OWN if f in own for x in [own[f]])      # the things in them: simsnap's roots
    fields['wrappers'] = [[name, u.body.serial, None if u.team is None else snap.encode(u.team.snapshot_key())]
                          for name, u in b.wrappers.items()]
    held.extend(u.body for u in b.wrappers.values())
    if '_exp_teams' in own:
        fields['_exp_teams'] = [[snap.encode(t.snapshot_key()), snap.encode(p)] for t, p in b._exp_teams]
    model = {}
    for f in _MODEL:
        v = own.get(f)
        if f == 'base' and v is not None and any(v is x for x in own.get('bases') or ()):
            model[f] = {'$in': next(k for k, x in enumerate(b.bases) if x is v)}
        elif isinstance(v, (list, tuple)):
            model[f] = [x.snapshot(key) for x in v]
        else:
            model[f] = None if v is None else v.snapshot(key)
    side, pid = b.made_as
    return [b.player, side, pid, fields, model]


def snapshot(w):
    """The SimAI's run as it stands (between SimAI.advance's frames): {'version', 'sim' (simsnap's), 'ai' (the
    SimAI's own), 'brains' ([player, side, personality, own fields, the plugin's])}. A field not sorted, a brain's
    plugin without the snapshot port: an error naming it."""
    gaps = unclassified(w)
    if gaps:
        raise ValueError(f'simaisnap.snapshot: fields not sorted (SIMAI / BRAIN / UNIT, simsnap.SIM / BODY): '
                         f'{", ".join(gaps[:8])}')
    miss = _no_port(w)
    if miss is not None:
        raise NotImplementedError(f'simaisnap: {miss[1]} (at {miss[0]}) does not take snapshots -- the AI plugin\'s '
                                  'snapshot port, docs/engine/sim-modules.md 9.2')
    held = []
    brains = [_take_brain(w, b, held) for b in w.brains.values()]
    s = simsnap.snapshot(w.sim, held)
    ai = [['.'.join(p), snap.encode(_get(w, p), at='simai.' + '.'.join(p))] for p in _paths()
          if all(f in simsnap._fields(_get(w, p[:k])) for k, f in enumerate(p))]
    return {'version': VERSION, 'sim': s, 'ai': ai, 'brains': brains}


def _paths(table=SIMAI, at=()):
    for f, kind in table.items():
        if isinstance(kind, dict):
            yield from _paths(kind, at + (f,))
        elif kind == STATE:
            yield at + (f,)


def _check(s):
    """The snapshot's shape, whole, before restore writes anything."""
    if s.get('version') != VERSION or set(s) != {'version', 'sim', 'ai', 'brains'}:
        raise ValueError(f'simaisnap.restore: not a snapshot of this shape ({VERSION})')
    state = {'.'.join(p) for p in _paths()}
    bad = [r for r in s['ai'] if not (isinstance(r, list) and len(r) == 2 and r[0] in state)]
    if bad:
        raise ValueError(f'simaisnap.restore: not a field the SimAI keeps: {bad[:3]}')
    own = set(_OWN) | {'wrappers', '_exp_teams'}
    bad = [r[:3] if isinstance(r, list) else r for r in s['brains']
           if not (isinstance(r, list) and len(r) == 5 and isinstance(r[3], dict) and set(r[3]) <= own
                   and 'wrappers' in r[3] and isinstance(r[4], dict) and set(r[4]) == set(_MODEL))]
    if bad:
        raise ValueError(f'simaisnap.restore: not a brain of this shape: {bad[:3]}')


def restore(w, s):
    """Write snapshot `s` onto `w`, a SimAI made anew (on a Sim made anew) for the same mission, level, seed and
    blocks, not yet advanced: the brains made as attach makes them (before the Sim is written: a Brain's making
    multiplies its player's income, the Sim's part then is the snapshot's), the Sim's part (simsnap.restore), the
    SimAI's own, then each brain's -- its Units, its own fields, the plugin's objects through their port, the Teams
    it holds by their keys."""
    _check(s)
    if w.brains:
        raise ValueError('simaisnap.restore: onto a SimAI that has brains already (made anew, not advanced)')
    Brain = importlib.import_module(type(w).__module__).Brain
    for player, side, pid, fields, _ in s['brains']:
        w.own_personalities()
        w.brains[player] = Brain(w, player, side, pid, snap.decode(fields.get('born', 0), {}))
    things = simsnap.restore(w.sim, s['sim'])
    for path, e in s['ai']:
        p = tuple(path.split('.'))
        setattr(_get(w, p[:-1]), p[-1], snap.decode(e, {}))
    for player, _side, _pid, fields, model in s['brains']:
        _write_brain(w, w.brains[player], fields, model, things)


def _write_brain(w, b, fields, model, things):
    Unit = importlib.import_module(type(w).__module__).Unit
    b.wrappers = {}
    units = {}
    for name, serial, _team in fields['wrappers']:
        b.wrappers[name] = units[serial] = Unit(things[serial], b.peers)

    def obj(mark):
        (k, serial), = mark.items()
        return {'$thing': things, '$unit': units}[k][serial]
    mods = _model_modules(w)

    def extra(mark, x):
        if mark == '$random':
            r = random.Random()
            r.setstate((x[0], tuple(x[1]), x[2]))
            return r
        if mark == '$unit':
            return units[x]
        if mark == '$model':
            mod, qual, data = x
            o = getattr(mods[mod], qual)()
            o.restore(data, obj)
            return o
        return NotImplemented
    for f in _OWN:
        if f in fields:
            setattr(b, f, snap.decode(fields[f], things, extra))
        elif f in vars(b):
            delattr(b, f)
    own = simsnap._fields(b)
    for f in _MODEL:
        v, data = own.get(f), model[f]
        if isinstance(data, dict) and set(data) == {'$in'}:
            continue        # one of bases: written back there
        got = [] if v is None else list(v) if isinstance(v, (list, tuple)) else [v]
        want = [] if data is None else data if isinstance(v, (list, tuple)) else [data]
        if len(got) != len(want) or (v is None) != (data is None):
            raise ValueError(f'simaisnap.restore: brain {b.player}.{f} is {_name(v)} x{len(got)} here, '
                             f'x{len(want)} in the snapshot')
        for x, d in zip(got, want):
            x.restore(d, obj)
    team = b.ai.team if any(t is not None for *_, t in fields['wrappers']) or '_exp_teams' in fields else None
    for name, _serial, k in fields['wrappers']:
        b.wrappers[name].team = None if k is None else team(snap.decode(k, {}))
    if '_exp_teams' in fields:
        b._exp_teams = [(team(snap.decode(k, {})), snap.decode(p, {})) for k, p in fields['_exp_teams']]
    elif '_exp_teams' in vars(b):
        del b._exp_teams
