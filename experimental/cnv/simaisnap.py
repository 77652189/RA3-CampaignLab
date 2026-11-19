"""A run's snapshot with the skirmish AI (step S 11b-4, docs/engine/sim-modules.md 9.2): the SimAI's and each Brain's
own fields sorted as simsnap sorts the Sim's, around simsnap's snapshot of the Sim the SimAI plays on.

How a field is kept: simsnap's kinds (STATE, ALIAS, CACHE, WIRE, STATIC) and
  HOST      the Sim the SimAI plays on: simsnap.snapshot / restore
  BRAINS    the brains: each Brain's own fields by BRAIN, made anew on the new SimAI the way attach makes them
  MODEL     an object of the AI plugin's (the engine model's ra3model.ai, private: ADR 0033): taken only through
            the plugin's snapshot port (`snapshot(key)` / `restore(data, obj)`, sim-modules.md 9.2); the host never
            reads its fields. A plugin object without the port: the snapshot is an error naming it, never left out.

11b-4a (this): the tables, `unclassified(w)` (guard 4.3 over the SimAI, its pullbacks, every Brain and every Unit
the brains wrap), a SimAI without brains taken and written back whole, a brain's plugin without the port refused.
11b-4b: a brain's public fields (Units by their body's serial, the plugin's values through its port)."""
import simsnap
from engine.kernel import snap
from simsnap import ALIAS, CACHE, STATE, STATIC, WIRE

HOST, BRAINS, MODEL = 'host', 'brains', 'model'
VERSION = 1

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

UNIT = {'body': STATE, 'peers': WIRE, 'template': STATIC, 'kindof': STATIC, 'surface': STATIC, 'team': MODEL}


def _get(obj, path):
    for f in path:
        obj = getattr(obj, f)
    return obj


def unclassified(w):
    """Step S's guard 4.3 for the SimAI: every field of it, of its parts, of its brains and of the Units they wrap
    that SIMAI / BRAIN / UNIT do not sort, every ALIAS that is not the object it names, and the Sim's own
    (simsnap.unclassified) -- all of them, sorted."""
    out = list(simsnap.unclassified(w.sim))

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


def _no_port(w):
    """The first plugin object a brain holds that has not the snapshot port: (where, its class), else None."""
    for player, b in w.brains.items():
        for f, kind in BRAIN.items():
            v = simsnap._fields(b).get(f)
            if kind != MODEL or v is None:
                continue
            for x in (v if isinstance(v, (list, tuple)) else (v,)):
                if not (callable(getattr(x, 'snapshot', None)) and callable(getattr(x, 'restore', None))):
                    return f'{player}.{f}', f'{type(x).__module__}.{type(x).__qualname__}'
        for u in b.wrappers.values():
            t = u.team
            if t is not None and not callable(getattr(t, 'snapshot_key', None)):
                return f'{player}.wrappers[{u.body.name!r}].team', f'{type(t).__module__}.{type(t).__qualname__}'
    return None


def snapshot(w):
    """The SimAI's run as it stands (between SimAI.advance's frames): {'version', 'sim' (simsnap's), 'ai' (the
    SimAI's own), 'brains'}. A field not sorted, a brain's plugin without the snapshot port: an error naming it."""
    gaps = unclassified(w)
    if gaps:
        raise ValueError(f'simaisnap.snapshot: fields not sorted (SIMAI / BRAIN / UNIT, simsnap.SIM / BODY): '
                         f'{", ".join(gaps[:8])}')
    miss = _no_port(w)
    if miss is not None:
        raise NotImplementedError(f'simaisnap: {miss[1]} (at {miss[0]}) does not take snapshots -- the AI plugin\'s '
                                  'snapshot port, docs/engine/sim-modules.md 9.2')
    if w.brains:        # 11b-4b: a brain's own fields; no plugin has the port yet, so not reached
        raise NotImplementedError('simaisnap: the brains\' own fields (11b-4b)')
    s = simsnap.snapshot(w.sim)
    ai = [['.'.join(p), snap.encode(_get(w, p), at='simai.' + '.'.join(p))] for p in _paths()
          if all(f in simsnap._fields(_get(w, p[:k])) for k, f in enumerate(p))]
    return {'version': VERSION, 'sim': s, 'ai': ai, 'brains': []}


def _paths(table=SIMAI, at=()):
    for f, kind in table.items():
        if isinstance(kind, dict):
            yield from _paths(kind, at + (f,))
        elif kind == STATE:
            yield at + (f,)


def restore(w, s):
    """Write snapshot `s` onto `w`, a SimAI made anew (on a Sim made anew) for the same mission, level, seed and
    blocks, not yet advanced: the Sim's part (simsnap.restore), then the SimAI's own."""
    if s.get('version') != VERSION or set(s) != {'version', 'sim', 'ai', 'brains'}:
        raise ValueError(f'simaisnap.restore: not a snapshot of this shape ({VERSION})')
    if s['brains']:
        raise NotImplementedError('simaisnap: the brains\' own fields (11b-4b)')
    state = {'.'.join(p) for p in _paths()}
    bad = [r for r in s['ai'] if not (isinstance(r, list) and len(r) == 2 and r[0] in state)]
    if bad:
        raise ValueError(f'simaisnap.restore: not a field the SimAI keeps: {bad[:3]}')
    simsnap.restore(w.sim, s['sim'])
    for path, e in s['ai']:
        p = tuple(path.split('.'))
        setattr(_get(w, p[:-1]), p[-1], snap.decode(e, {}))
