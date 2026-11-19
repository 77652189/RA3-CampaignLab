"""A run's snapshot with the skirmish AI (step S 11b-4, docs/engine/sim-modules.md 9.2): the SimAI's and each Brain's
own fields sorted as simsnap sorts the Sim's, around simsnap's snapshot of the Sim the SimAI plays on.

How a field is kept: simsnap's kinds (STATE, ALIAS, CACHE, WIRE, STATIC) and
  HOST      the Sim the SimAI plays on: simsnap.snapshot / restore
  BRAINS    the brains: each Brain's own fields by BRAIN, made anew on the new SimAI the way attach makes them
  MODEL     an object of the AI plugin's (the engine model's ra3model.ai, private: ADR 0033): taken only through
            the plugin's snapshot port (its package's `snapshot` module, sim-modules.md 9.2); the host never reads
            its fields. A plugin without the port, a value its port cannot keep: an error naming it, never left out.

The port is one session a brain (an object the plugin holds at two places comes back as one): `Taker(roots, key)`
with the brain's MODEL fields as roots, `ref(x)` for each plugin value the brain itself holds (a HuntGoal of
_hunt_goals, a wrapper's Team, _exp_teams' Teams) -> a mark, `taken()` the data; on restore `Putter(roots, data,
obj, wire)` on the new brain's MODEL fields (written in place) and `get(mark)`. `key(x)`: a Unit or a thing of the
host as its mark; `obj(mark)` the new run's; `wire(x, field)`: a host's closure for a plugin object made anew (a
tactics.Fighter's rate / can_fire, made again by Brain.fighters for its body).
A brain's own values as engine/kernel/snap.py keeps them, plus its marks: a Unit it wraps {"$unit": its body's
serial} (one Unit a body: the new brain's wrapper of that body), a random.Random {"$random": its state}, a plugin
value {"$model": the session's mark}. The Bodies the brain holds out of the world (_protos, Sim.proto) and the things
the plugin's values hold go to simsnap as roots: kept with the Sim's things, made bare on the new world.
HOOKS 9's trail (SimAI(record=True)): rec, _rec_bodies and _rec_runs (the Runs first seen first: plugin values, their
marks) as the brain's own; _rec_mem (run number -> the Run.mem the trail last saw, read only by identity: a micro
update ran when the Run's mem is no longer it) by hand, as whether it is the Run's mem now (true), None, or an older
one (false: a stand-in, never the Run's).

11b-4a: the tables, `unclassified(w)` (guard 4.3), the port refused by name. 11b-4b: the brains' public fields.
11b-4c: the plugin's port, a session a brain (the engine model's ra3model/ai/snapshot.py). 11b-4e: record=True."""
import importlib
import random

import simsnap
from engine.kernel import module as _module
from engine.kernel import snap
from simsnap import ALIAS, CACHE, STATE, STATIC, WIRE

HOST, BRAINS, MODEL = 'host', 'brains', 'model'
VERSION = 6             # 2: the brains (11b-4b); 3: the plugin's objects a session a brain (11b-4c);
#                         4: a brain's ids / hp keyed by serial, not name (same-name sweep S6a);
#                         5: HOOKS 9's runs, a list, and the mems they saw (_rec_mem by hand, 11b-4e);
#                         6: its hunt goals / cells keyed by serial (S6b)

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
    '_build_radii': CACHE, '_node_offsets': CACHE, '_miner_toggles': CACHE, '_micro_units': CACHE,
}
_BY_HAND = ('wrappers', '_exp_teams', '_rec_mem')
_OWN = [f for f, k in BRAIN.items() if k == STATE and f not in _BY_HAND]
_MODEL = [f for f, k in BRAIN.items() if k == MODEL]

UNIT = {'body': STATE, 'peers': WIRE, 'template': STATIC, 'kindof': STATIC, 'surface': STATIC, 'team': MODEL,
        'escort_of': MODEL}     # the team a member escorts (teams.py writes it)
_UNIT_MODEL = [f for f, k in UNIT.items() if k == MODEL]


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


def _name(x):
    return f'{type(x).__module__}.{type(x).__qualname__}'


def _port(w):
    """The AI plugin's snapshot port: its package's `snapshot` module (Taker / Putter), else None."""
    pkg = (w.mod or {}).get('player')
    if pkg is None:
        return None
    try:
        port = importlib.import_module(pkg.__name__.rsplit('.', 1)[0] + '.snapshot')
    except ImportError:
        return None
    return port if hasattr(port, 'Taker') and hasattr(port, 'Putter') else None


def _no_port(w):
    """What keeps a SimAI with brains from being taken: (where, what), else None -- the plugin without its
    snapshot port."""
    if not w.brains:
        return None
    if _port(w) is None:
        pkg = (w.mod or {}).get('player')
        return 'the AI plugin', (pkg.__name__.rsplit('.', 1)[0] if pkg else 'none') + '.snapshot (Taker / Putter)'
    return None


def _model_modules(w):
    return {m.__name__: m for m in (w.mod or {}).values()}


def _key_of(held, brain):
    """The port's `key(x)`: a Unit or a thing of the host as its mark, or the brain itself ({"$brain": 0}: a method
    of it the plugin holds, e.g. the Opening's structure hook, is the new brain's); each thing given is noted in
    `held` (kept as one of simsnap's roots)."""
    def key(x):
        if x is brain:
            return {'$brain': 0}
        if x is brain.host:
            return {'$simai': 0}        # a method of the SimAI's in the facts (kinds)
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
    own = simsnap._fields(b)
    sess = _port(w).Taker({f: own.get(f) for f in _MODEL}, _key_of(held, b))
    mods = _model_modules(w)

    def extra(v):
        if isinstance(v, random.Random):
            ver, st, gauss = v.getstate()
            return {'$random': [ver, list(st), gauss]}
        if type(v).__name__ == 'Unit' and isinstance(getattr(v, 'body', None), _module.Thing):
            return sess.key(v)
        if type(v).__module__ in mods:
            return {'$model': sess.ref(v, f'Brain {b.player}')}
        return NotImplemented

    fields = {f: snap.encode(own[f], extra, f'Brain {b.player}.{f}') for f in _OWN if f in own}
    held.extend(x for f in _OWN if f in own for x in [own[f]])      # the things in them: simsnap's roots
    fields['wrappers'] = [[name, u.body.serial, {f: sess.ref(vars(u)[f], f'{name}.{f}') for f in _UNIT_MODEL
                                                 if f in vars(u)}] for name, u in b.wrappers.items()]
    held.extend(u.body for u in b.wrappers.values())
    if '_exp_teams' in own:
        fields['_exp_teams'] = [[sess.ref(t, '_exp_teams'), snap.encode(p)] for t, p in b._exp_teams]
    if '_rec_mem' in own:
        runs = own.get('_rec_runs', [])
        fields['_rec_mem'] = [[n, _mem_mark(m, runs[n - 1] if 0 < n <= len(runs) else None)]
                              for n, m in b._rec_mem.items()]
    side, pid = b.made_as
    return [b.player, side, pid, fields, sess.taken()]


def _mem_mark(mem, run):
    """A mem HOOKS 9 last saw: true (the Run's mem now), None, false (an older one)."""
    if run is not None and mem is run.mem:
        return True
    return None if mem is None else False


class _Older:
    """The stand-in for a mem the trail saw before its Run's present one: never the Run's (Brain.snap reads it only
    as `r.mem is not last`)."""


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
    own = set(_OWN) | set(_BY_HAND)
    bad = [r[:3] if isinstance(r, list) else r for r in s['brains']
           if not (isinstance(r, list) and len(r) == 5 and isinstance(r[3], dict) and set(r[3]) <= own
                   and 'wrappers' in r[3] and isinstance(r[4], dict) and set(r[4]) == {'roots', 'objects'}
                   and isinstance(r[4]['roots'], dict) and set(r[4]['roots']) == set(_MODEL))]
    if bad:
        raise ValueError(f'simaisnap.restore: not a brain of this shape: {bad[:3]}')


def restore(w, s):
    """Write snapshot `s` onto `w`, a SimAI made anew (on a Sim made anew) for the same mission, level, seed and
    blocks, not yet advanced: the brains made as attach makes them (before the Sim is written: a Brain's making
    multiplies its player's income, the Sim's part then is the snapshot's), the Sim's part (simsnap.restore), the
    SimAI's own, then each brain's -- its Units, its own fields, the plugin's objects through their port, the Teams
    it holds by their keys."""
    _check(s)
    simsnap.check(w.sim, s['sim'])      # review 1119m #1: the Sim's part refused before a brain is made, not after
    if w.brains:
        raise ValueError('simaisnap.restore: onto a SimAI that has brains already (made anew, not advanced)')
    for player, side, pid, fields, _ in s['brains']:
        # review 1119m #3: found only when a brain is to be made, along the SimAI's classes (a subclass declared
        # where no Brain is finds simai's)
        Brain = simsnap.host_class(w, 'Brain', 'make a brain the snapshot has (simaisnap.restore)')
        w.own_personalities()
        w.brains[player] = Brain(w, player, side, pid, snap.decode(fields.get('born', 0), {}))
    things = simsnap.restore(w.sim, s['sim'])
    for path, e in s['ai']:
        p = tuple(path.split('.'))
        setattr(_get(w, p[:-1]), p[-1], snap.decode(e, things))      # review k #1: a returner's facility
    for name, (g, dest, owner, path) in list(getattr(getattr(w, 'pullback', None), 'returning', {}).items()):
        u = w.sim.bodies.get(name)          # busy asks for the very path the unit walks (by identity): the unit's
        if u is not None and path is not None and u.path == path:
            w.pullback.returning[name] = (g, dest, owner, u.path)
    for player, _side, _pid, fields, model in s['brains']:
        _write_brain(w, w.brains[player], fields, model, things)


def _write_brain(w, b, fields, model, things):
    Unit = simsnap.host_class(w, 'Unit', 'wrap a brain\'s unit (simaisnap.restore)')
    b.wrappers = {}
    units = {}
    for name, serial, _team in fields['wrappers']:
        b.wrappers[name] = units[serial] = Unit(things[serial], b.peers)

    def obj(mark):
        (k, serial), = mark.items()
        if k in ('$brain', '$simai'):
            return b if k == '$brain' else w
        return {'$thing': things, '$unit': units}[k][serial]

    def wire(x, f):
        # a tactics.Fighter made anew: its rate / can_fire, closures of the host's, as fight makes them for its body
        # (Brain.fighters; the ids it may give are written over with the brain's own fields below)
        if type(x).__name__ == 'Fighter' and f in ('rate', 'can_fire') and isinstance(vars(x).get('body'),
                                                                                       _module.Thing):
            return getattr(b.fighters([x.body])[0], f)
        return None
    own = simsnap._fields(b)
    sess = _port(w).Putter({f: own.get(f) for f in _MODEL}, model, obj, wire)

    def extra(mark, x):
        if mark == '$random':
            r = random.Random()
            r.setstate((x[0], tuple(x[1]), x[2]))
            return r
        if mark == '$unit':
            return units[x]
        if mark == '$model':
            return sess.get(x)
        return NotImplemented
    for f in _OWN:
        if f in fields:
            setattr(b, f, snap.decode(fields[f], things, extra))
        elif f in vars(b):
            delattr(b, f)
    for name, _serial, model_fields in fields['wrappers']:
        for f, k in model_fields.items():
            setattr(b.wrappers[name], f, sess.get(k))
    if '_exp_teams' in fields:
        b._exp_teams = [(sess.get(k), snap.decode(p, {})) for k, p in fields['_exp_teams']]
    elif '_exp_teams' in vars(b):
        del b._exp_teams
    if '_rec_mem' in fields:
        runs = b._rec_runs      # written above with the brain's own: the new Runs, in the trail's order
        b._rec_mem = {n: runs[n - 1].mem if v is True else None if v is None else _Older()
                      for n, v in fields['_rec_mem']}
