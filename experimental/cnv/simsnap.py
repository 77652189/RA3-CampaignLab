"""A run's snapshot, the host's part (step S, docs/engine/sim-modules.md 9.2): the kernel's (World.snapshot), every
Body's fields and the Sim's own, sorted by how each is kept, and the script executor's (its port). Taken at a tick's
end (Sim.run between steps); written back onto a Sim made anew for the same mission, test, level and script, not yet
run. A transition: it shrinks as blocks move into modules (their STATE is the kernel's) and goes with the old Sim.

How a field is kept (SIM / BODY below; a dict there is a part: an object whose own fields are sorted the same way):
  STATE     taken and written back (a container in place: another name may hold it)
  ALIAS     another field's object under a second name (`ALIASES`): not taken, checked to be the same object
  KERNEL    the world's: World.snapshot (the schedule, the modules' STATE, made, frame, used, gaps)
  EXECUTOR  the script port's Executor.snapshot (an executor that cannot: an error)
  CACHE     read from data that does not change in a run (the new world fills its own)
  WIRE      hooks, views and back-references the constructor makes
  STATIC    the mission's and the run's setup, the same on the new world (tests/tools/test_snapshot.py checks it)

Values as engine/kernel/snap.py keeps them, plus the host's marks: a weapon / armour / weapon slots of the template
data held by identity ({"$weapon": [template, "fight" | "slot", ...]}: written back as the new world's own object of
the same place), one list / dict / set / array held in two places ({"$shared": [n, value]} then {"$ref": n}: one
object again), a numpy array ({"$array": [dtype, shape, base64]}), a player's protocol book ({"$book": fields}), an
order the command port keeps ({"$command": fields}), a script of the map's lists the host holds (a sequential
script's queue: {"$script": the executor's script_key}, the new executor's script of that key).
`unclassified(sim)` (step S's guard 4.3) names every field not sorted here, so a new one cannot be left out."""
import ast
import base64
import hashlib
import importlib
import inspect
import json
import textwrap
from functools import lru_cache

import numpy as np

import simtech
import simunits
from engine.kernel import factory
from engine.kernel import module as _module
from engine.kernel import snap
from engine.kernel.world import World
from engine.ports.command import Command
from engine.script import lists as script_lists
from engine.script.executor import PublicExecutor

STATE, ALIAS, KERNEL, EXECUTOR, CACHE, WIRE, STATIC = 'state', 'alias', 'kernel', 'executor', 'cache', 'wire', 'static'
SEMANTICS = 0           # manual fallback for a format change outside the tables and encoding rules version() reads

SIM = {
    # the setup
    'm': STATIC, 'retail': STATIC, 'mm': STATIC, 'test': STATIC, 'level': STATIC, 'fps': STATIC, 'players': STATIC,
    'human': STATIC, 'foe': STATIC, 'own': STATIC, 'walls': STATIC, 'templates': STATIC, 'script': STATIC,
    'auto_kill': STATIC, 'combat': STATIC, 'high': STATIC, 'unshot': STATIC,
    'areas': {'missing': STATE},    # the map's areas (the dict: the setup); the names looked up the map has not (the
                                    # report's line): retail_s01's first half lost it written back (4.4, 11-19)
    'modifiers': {}, 'assignments': {'world': WIRE},
    # the kernel, the script port, wiring
    'world': KERNEL, 'executor': EXECUTOR, 'eng': WIRE, 'counters': WIRE, 'timers': WIRE, 'team_names': WIRE,
    'order_peers': WIRE,
    'step': WIRE,       # an observer's tick hook (Observe.on_tick wraps the run's step; simrecord's Recorder): the
                        # new run's observer hooks its own (11b-4d: simaisnap's scan met it)
    'used': ALIAS, 'unmodeled': ALIAS, 'money': ALIAS, 'income': ALIAS, 'sharing': ALIAS, 'money_cap': ALIAS,
    # caches (template -> what its data says)
    'declared': CACHE, 'energies': CACHE, '_engineer_rules': CACHE, '_wsets': CACHE, '_xmls': CACHE,
    '_toggles': CACHE, '_invis': CACHE, '_xy': CACHE, '_crushable_pool': CACHE,
    # parts
    'clock': {'frame': STATE},
    'wallet': {'money': STATE, 'income': STATE, 'sharing': STATE, 'money_cap': STATE},
    'mining': {'nodes': STATE, 'mined_to': STATE},
    'ground': {'waterline': STATIC, 'water': STATIC, 'b': STATIC, 'd': STATIC, 'e': STATIC, 'zgrid': STATIC,
               'grids': STATIC, 'fine': STATIC, 'deck': STATIC, 'xy': STATIC,
               'blocked': STATE, 'placed': STATE, 'version': STATE, 'shapes': STATE, 'cache': CACHE},
    'repairs': {'world': WIRE, 'wallet': WIRE, 'ai_switches': ALIAS, 'blocked': STATE, 'players': STATE},
    'heal': {'passive_area_of': CACHE},
    'life': {'lose_of': CACHE, 'blasts_of': CACHE},
    'garrison': {'world': WIRE, 'peers': WIRE, 'boxes': STATE, 'where': STATE, 'going': STATE, 'log': STATE,
                 'ejecting': STATE, 'flying': STATE},
    'infiltrators': {'world': WIRE, 'peers': WIRE, 'wallet': WIRE, 'going': STATE, 'off_until': STATE,
                     'observers': STATE, 'unit_observers': STATE, 'paralyzed_until': STATE, 'attack_until': STATE},
    'lift_timers': {'remaining': STATE},
    'sweeps': {'world': WIRE, 'peers': WIRE, 'lines': STATE},
    'commands': {'_w': WIRE, '_issued': STATE},
    'specials': {'wfires': STATE, 'leaps_due': STATE, 'leap_ground_hits': STATE, 'movement_due': STATE,
                 'self_bits_due': STATE},
    'harm': {'incoming': STATE, 'projectile_hits': STATE, 'knock_drowns': STATE, 'dots': STATE, 'cold_on': STATE,
             'projectile_speeds': CACHE, 'impact_body': CACHE, 'lift_modules': CACHE, 'nugget_powers': CACHE,
             'hit_reaction_of': CACHE},
}
for _f in ('t log box_log panel_log asked up scenes unknown flags objectives markers banned unit_construction_disabled '
           'base_construction_disabled ai_paused buildable banned_ups border reveal_all reveal_all_until revealed_to '
           'reveals peeks reveal_areas seq reshroud camera camera_been personality_of input countdowns ending both '
           'ra3_only last_change ai handed library_ai ai_switches ai_priorities hidden_home audio_end video_end '
           'selected script_disabled kills attacked_by cond_memory made_frame relations team_team_rel '
           'team_player_rel player_team_rel team_targets books tech_to tech_read hunts bodies attachments '
           '_attachment_marked attachment_known_status suppression_fields topples frame_movers refs acting object_lists '
           'base_power powers_off series threat first_threat known known_at guessed due blasts casts power_at '
           'queues produced_to player_ups instances active lost_orders seen firing mid_aims '
           '_field first_death death_blasts events anchored hotspots waypoints volleys chilling _fire_obstacles '
           'impact_flights emp_until knock_hold tech_to '
           'pack_hold').split():     # pack_hold: a yard packing's frames held, by serial (review 1119p #3: unsorted)
    SIM.setdefault(_f, STATE)
# World.snapshot takes its own STATE. This table is for the field guard.
WORLD = {
    'blocks': WIRE, 'tags': STATIC, '_kill': WIRE, '_remove': WIRE, '_pay': WIRE, '_toggled': WIRE,
    '_modify': WIRE, '_suppression_at': WIRE, '_spawn': WIRE, '_vacate': WIRE, '_create': WIRE, '_fire': WIRE,
    'schedule': STATE, 'used': STATE, 'gaps': STATE, 'frame': STATE, 'made': STATE, 'late': STATE,
    'data': CACHE, 'block_lists': CACHE, 'numbered': CACHE, '_living_views': CACHE,
}

# a second name -> the path of the object it names
ALIASES = {('used',): ('world', 'used'), ('unmodeled',): ('world', 'gaps'),
           ('money',): ('wallet', 'money'), ('income',): ('wallet', 'income'), ('sharing',): ('wallet', 'sharing'),
           ('money_cap',): ('wallet', 'money_cap'), ('repairs', 'ai_switches'): ('ai_switches',)}

BODY = {'modules': KERNEL, 'serial': KERNEL, '_find_cache': CACHE}     # the last two: Thing's slots
for _f in ('name template owner x y z speed surface vision kinds immune_until armor acquire radius sight chase '
           'home auto_to resume stood_for spot engaged alive deleted path goal close_since made_by made_at scenery team '
           'instance guessed clear_height angle turn_rate turn_first face rolling carry dest set_off stops_at status '
           'attachment_status lift_status upgrades up_since level_rank script_status auras_on shielded taken '
           'model_conditions dealt level_rate level_vision base died_at mode move_to fired_at leaves building replace '
           'follow frame_move drive_speed jet_motion jet_started hold_fire hold_paused stance ai_acquire unpack_parent '
           'flee ground_fire unpack_here last_by').split():
    BODY.setdefault(_f, STATE)

MODULE_WIRE = ('thing', 'data', 'world')    # Module.__init__'s: the factory makes them again on the new world
_MUTABLE = (list, dict, set)
_NAMED = ('$ref', '$slots', '$weapon', '$armor', '$weapons')    # marks of one object: written back as that object


def digest(*tables):
    """The first 8 hex digits of the sha256 of `tables` written one way: a dict's / set's items sorted, a tuple a
    list. The same tables, in whatever order they were filled, give the same digest in every process."""
    def canon(v):
        if isinstance(v, dict):
            return sorted(([canon(k), canon(x)] for k, x in v.items()), key=json.dumps)
        if isinstance(v, (set, frozenset)):
            return sorted((canon(x) for x in v), key=json.dumps)
        if isinstance(v, (list, tuple)):
            return [canon(x) for x in v]
        return v
    return hashlib.sha256(json.dumps(canon(tables), ensure_ascii=False).encode()).hexdigest()[:8]


def _module_states():
    """[tag, module, class, sorted STATE] of every module class registered from engine.modules (a test's subclass
    left out): the kernel's part of what is kept. The package is imported here, when a version is asked (a fresh
    process reading a snapshot file has made no Sim -- review 1119z P2 #4), not at simsnap's load: a static import
    would make every module file one of this layered tool's imports (tests/test_sim_layers.py)."""
    importlib.import_module('engine.modules')
    return [[tag, cls.__module__, cls.__qualname__, sorted(cls.STATE)] for tag, cls in sorted(factory.TAGS.items())
            if cls.__module__.startswith('engine.modules.')]


@lru_cache(maxsize=64)
def _encoding_rule(code):
    rule = ast.parse(textwrap.dedent(inspect.getsource(code))).body[0]
    body = rule.body[1:] if ast.get_docstring(rule) is not None else rule.body
    return ast.dump(rule.args), [ast.dump(stmt) for stmt in body]


def encoding_rules(*functions):
    """The declared wire rules without comments, docstrings, or file locations, read from the live functions."""
    return [_encoding_rule(f.__code__) for f in functions]


def version():
    """The host snapshot's format depends on its field tables and the rules that encode its values and rows."""
    rules = encoding_rules(snap.encode, snap.decode, snap._place, snap.module_state, snap.set_module_state,
                           _Codec._place_template, _Codec.count, _Codec.extra, _Codec.decode_extra,
                           _Codec._template_object, World.snapshot, World.restore, PublicExecutor.snapshot,
                           PublicExecutor.restore, PublicExecutor._key, PublicExecutor._by_key, snapshot, _setup)
    types = tuple(t.__name__ for t in (*snap._PLAIN, *_MUTABLE))
    wire = digest(SIM, BODY, ALIASES, snap.MARKS, _NAMED, MODULE_WIRE, _module_states(), rules, types)
    return f'{wire}.{SEMANTICS}'


def __getattr__(name):
    if name == 'VERSION':       # simsnap.VERSION, read live (a table changed in a test changes it)
        return version()
    raise AttributeError(f'module {__name__!r} has no attribute {name!r}')


def _fields(obj):
    """An object's own fields: its __dict__ and every slot set along its classes (review 1119i #7: a slot beside a
    __dict__ was left out of the scan)."""
    slots = [f'_{k.__name__.lstrip("_")}{f}' if f.startswith('__') and not f.endswith('__') else f    # a private
             for k in type(obj).__mro__ for f in (lambda s: (s,) if isinstance(s, str) else s)(        # slot under
                 vars(k).get('__slots__', ())) if f not in ('__dict__', '__weakref__')]              # its mangled name
    out = dict(vars(obj)) if hasattr(obj, '__dict__') else {}
    out.update((f, getattr(obj, f)) for f in slots if f not in out and hasattr(obj, f))
    return out


def _get(sim, path):
    obj = sim
    for f in path:
        obj = getattr(obj, f)
    return obj


def _state_paths(sim, table=SIM, at=()):
    """(path, kind) of every field of the table the sim has, parts walked into, in the table's order."""
    for f, kind in table.items():
        obj = _get(sim, at)
        if f not in _fields(obj) and not (isinstance(kind, dict) and hasattr(obj, f)):
            continue
        if isinstance(kind, dict):
            yield from _state_paths(sim, kind, at + (f,))
        else:
            yield at + (f,), kind


def unclassified(sim, roots=()):
    """Step S's guard 4.3: fields left out of SIM / WORLD / BODY or a module's STATE, and broken ALIASes."""
    out = []

    def walk(obj, table, at):
        for f, v in _fields(obj).items():
            kind = table.get(f)
            if kind is None:
                out.append('.'.join(at + (f,)))
            elif isinstance(kind, dict):
                walk(v, kind, at + (f,))
            elif kind == ALIAS and (at[1:] + (f,)) in ALIASES:
                if v is not _get(sim, ALIASES[at[1:] + (f,)]):
                    out.append('.'.join(at + (f,)) + ' (not the object it names)')
    walk(sim, SIM, ('sim',))
    walk(sim.world, WORLD, ('sim', 'world'))
    for b in _things(sim, roots):
        out.extend(f'Body.{f}' for f in _fields(b) if f not in BODY)
        for m in b.modules:     # a module's own: its STATE (the kernel's) and the factory's wiring, nothing set besides
            out.extend(f'{type(m).__name__}.{f}' for f in _fields(m) if f not in MODULE_WIRE and f not in m.STATE)
    return sorted(set(out))


def _things(sim, roots=()):
    """The run's things: the bodies, then the ones held but not in bodies (a map object whose name a later one took:
    Sim.add keeps it in topples, out of bodies and the schedule, still knocked over), found through the fields the
    snapshot takes, in their order, then through `roots` (what a caller holding the sim keeps: the skirmish AI's
    Bodies never placed, simaisnap). A thing not of this world -- not the object World.numbered holds under its
    serial: another run's, of a serial taken here or of one left free here (review 1119e #8, h P3) -- an error."""
    out = list(sim.bodies.values())
    seen = {}
    for b in out:
        if sim.world.numbered.get(getattr(b, 'serial', None)) is not b:
            raise ValueError(f'simsnap: thing {getattr(b, "serial", None)} {b.name!r} is in bodies but this world '
                             'did not number it (not bodies of the run)')
        seen.setdefault(b.serial, b)
    todo = []

    def reach(x):
        if isinstance(x, _module.Module):
            x = x.thing
        if isinstance(x, _module.Thing):
            have = seen.get(getattr(x, 'serial', None))
            if have is x:
                return
            if have is not None or sim.world.numbered.get(getattr(x, 'serial', None)) is not x:   # not this world's
                raise ValueError(f'simsnap: thing {getattr(x, "serial", None)} {getattr(x, "name", "")!r} is held but '
                                 'is not bodies of the run')
            seen[x.serial] = x
            out.append(x)
            todo.append(x)
        elif isinstance(x, dict):
            for k, v in x.items():
                reach(k)
                reach(v)
        elif isinstance(x, (list, tuple, set, frozenset)):
            for v in x:
                reach(v)

    def fields(b):
        for f, kind in BODY.items():
            if kind == STATE and f in vars(b):
                reach(vars(b)[f])
        for m in b.modules:
            for f in m.STATE:
                if f in vars(m):
                    reach(vars(m)[f])

    for p, kind in _state_paths(sim):
        if kind == STATE:
            reach(_get(sim, p))
    for x in roots:
        reach(x)
    todo.extend(out[:len(sim.bodies)])
    while todo:
        fields(todo.pop(0))
    return out


class _Codec:
    """The host's marks for snap.encode / decode: the template data's weapons and armours by place, containers held
    twice, arrays, protocol books."""

    def __init__(self, sim, roots=()):
        self.sim = sim
        self.index = {}         # id -> (object, mark): the template data a body holds by identity
        self.counts = {}        # id -> (object, times reached)
        self.ids = {}           # id -> n: a container held twice, given its first time
        self.table = {}         # n -> object (decoding)
        self._open = None
        for t in sorted({b.template for b in _things(sim, roots)}):
            self._place_template(t)

    def _put(self, obj, mark):
        self.index.setdefault(id(obj), (obj, mark))

    def template_data(self, v):
        """Whether `v` is the template data's own object (a weapon, an armour, weapon slots), as placed above."""
        hit = self.index.get(id(v))
        return hit is not None and hit[0] is v

    def _place_template(self, t):
        slots = self.sim.__dict__.get('_wsets', {}).get(t)
        if slots:
            self._put(slots, {'$slots': t})
            for si, s in enumerate(slots):
                for li, e in enumerate(s):
                    if e[3]:
                        self._put(e[3], {'$weapon': [t, 'slot', si, li]})
        if t in self.sim.own:           # read anew at each ask: a body's own copy, kept by value
            return
        f = simunits.fight(t, self.sim.own)
        self._put(f['armor'], {'$armor': t})
        self._put(f['weapons'], {'$weapons': t})
        for k, w in enumerate(f['weapons']):
            self._put(w, {'$weapon': [t, 'fight', k]})

    # ---- taking
    def count(self, v):
        """Reach every container once more (before encoding): one reached twice is kept once."""
        if isinstance(v, (_module.Thing, _module.Module)) or self.template_data(v):
            return
        if isinstance(v, (*_MUTABLE, np.ndarray, simtech.Book)):
            obj, n = self.counts.get(id(v), (v, 0))
            self.counts[id(v)] = (v, n + 1)
            if n:
                return
        if isinstance(v, dict):
            for x in v.values():
                self.count(x)
        elif isinstance(v, (list, tuple, set, frozenset)):
            for x in v:
                self.count(x)
        elif isinstance(v, simtech.Book):
            self.count(vars(v))

    def extra(self, v):
        i = id(v)
        hit = self.index.get(i)
        if hit is not None and hit[0] is v:
            return hit[1]
        if self._open == i:
            self._open = None
        elif self.counts.get(i, (None, 0))[1] > 1:
            if i in self.ids:
                return {'$ref': self.ids[i]}
            self.ids[i] = n = len(self.ids)
            self._open = i
            return {'$shared': [n, snap.encode(v, self.extra, f'shared {n}')]}
        if isinstance(v, np.ndarray):
            return {'$array': [v.dtype.str, list(v.shape), base64.b64encode(np.ascontiguousarray(v).tobytes()).decode()]}
        if isinstance(v, simtech.Book):
            return {'$book': snap.encode(dict(vars(v)), self.extra, 'book')}
        if isinstance(v, np.bool_):
            return {'$npbool': bool(v)}
        if isinstance(v, Command):      # an order the command port keeps (its names and numbers)
            return {'$command': snap.encode({f: getattr(v, f) for f in v.__dataclass_fields__}, self.extra, 'command')}
        if isinstance(v, script_lists.Script):      # one of the map's lists (the executor's): by its key
            return {'$script': snap.encode(self.sim.executor.script_key(v), at='script key')}
        return NotImplemented

    # ---- writing back
    def decode_extra(self, things):
        def extra(mark, x):
            if mark == '$shared':
                n, val = x
                obj = self.table[n] = snap.decode(val, things, extra)
                return obj
            if mark == '$ref':
                if x not in self.table:
                    raise ValueError(f'simsnap: a $ref {x} before its $shared')
                return self.table[x]
            if mark == '$array':
                dtype, shape, data = x
                return np.frombuffer(base64.b64decode(data), dtype=np.dtype(dtype)).reshape(shape).copy()
            if mark == '$book':
                b = object.__new__(simtech.Book)
                b.__dict__.update(snap.decode(x, things, extra))
                return b
            if mark == '$npbool':
                return np.bool_(x)
            if mark == '$command':
                return Command(**snap.decode(x, things, extra))
            if mark == '$script':
                return self.sim.executor.script_by_key(snap.decode(x, things))
            if mark in ('$slots', '$weapon', '$armor', '$weapons'):
                return self._template_object(mark, x)
            return NotImplemented
        return extra

    def _template_object(self, mark, x):
        t = x if isinstance(x, str) else x[0]
        if mark in ('$slots', '$weapon') and (mark == '$slots' or x[1] == 'slot'):
            wsets = self.sim.__dict__.setdefault('_wsets', {})
            if t not in wsets:
                wsets[t] = simunits.weapon_sets(t, self.sim.own)
            slots = wsets[t]
            return slots if mark == '$slots' else slots[x[2]][x[3]][3]
        f = simunits.fight(t, self.sim.own)
        if mark == '$armor':
            return f['armor']
        if mark == '$weapons':
            return f['weapons']
        return f['weapons'][x[2]]


def snapshot(sim, roots=()):
    """The run as it stands (at a tick's end): {'version', 'mission', 'setup' (_setup), 'kernel', 'bodies', 'others' (the things held
    but not in bodies, _things; `roots` as there), 'parts', 'host', 'executor'}, in
    values json.dumps keeps. A value it cannot keep, a thing held that is not a body of the run, an executor without
    snapshots: an error naming it, never a part left out."""
    things = _things(sim, roots)
    held = {b.serial for b in things}
    c = _Codec(sim, roots)
    w = sim.world
    for v in (w.used, w.gaps):
        c.count(v)
    for b in things:
        for m in b.modules:
            for f in m.STATE:
                if f in vars(m):
                    c.count(vars(m)[f])
    for b in things:
        for f, kind in BODY.items():
            if kind == STATE and f in vars(b):
                c.count(vars(b)[f])
    paths = [p for p, kind in _state_paths(sim) if kind == STATE]
    for p in paths:
        c.count(_get(sim, p))
    kernel = w.snapshot(things, c.extra)
    def own(b):
        return {f: snap.encode(x, c.extra, f'{b.name}.{f}') for f, x in vars(b).items() if BODY.get(f) == STATE}

    bodies = [[key, b.serial, b.name, b.template, own(b)] for key, b in sim.bodies.items()]
    others = [[b.serial, b.name, b.template, own(b)] for b in things[len(sim.bodies):]]
    host = [['.'.join(p), snap.encode(_get(sim, p), c.extra, 'sim.' + '.'.join(p))] for p in paths]
    parts = [[f, type(v).__module__, type(v).__qualname__] for f, v in _fields(sim).items() if isinstance(SIM.get(f), dict)]
    out = {'version': version(), 'mission': getattr(sim.m, 'name', None), 'setup': _setup(sim), 'kernel': kernel,
           'bodies': bodies, 'others': others, 'parts': parts, 'host': host, 'executor': sim.executor.snapshot()}
    found = _serials(out)
    stray = sorted(set(found) - held)
    if stray:
        raise ValueError(f'simsnap.snapshot: things {stray[:10]} are held but are not bodies of the run '
                         f'(the first at {", ".join(found[k] for k in stray[:3])})')
    return out


def _serials(e, out=None, at='snapshot', unit_refs=None):
    """Thing serial -> first reference path. When supplied, collect a brain's Unit references separately."""
    out = {} if out is None else out
    if isinstance(e, list):
        for k, x in enumerate(e):
            _serials(x, out, f'{at}[{k}]', unit_refs)
    elif isinstance(e, dict):
        if len(e) == 1 and '$thing' in e:
            out.setdefault(e['$thing'], at)
        elif len(e) == 1 and '$module' in e:
            out.setdefault(e['$module'][0], at)
        elif len(e) == 1 and '$unit' in e and unit_refs is not None:
            unit_refs.setdefault(e['$unit'], at)
        else:
            for k, x in e.items():
                _serials(x, out, f'{at}.{k}', unit_refs)
    return out


def _write(obj, f, e, decode, codec):
    """Field `f` of `obj` from its snapshot `e`: a container the field already holds of the same type is filled in
    place (another name may hold it), and stands for the $shared it was taken as -- unless the snapshot names an
    object ($ref: another place's; the template data's, as a body made bare got a default container of its own) or
    the field holds the template data's (all its template's bodies hold it: written over, never filled)."""
    old = _fields(obj).get(f)
    n = None
    if isinstance(e, dict) and len(e) == 1 and '$shared' in e:
        n, e = e['$shared']
    new = decode(e)
    again = isinstance(e, dict) and len(e) == 1 and next(iter(e)) in _NAMED
    if not again and not codec.template_data(old) and type(old) is type(new) and isinstance(old, _MUTABLE) \
            and old is not new:
        if isinstance(old, list):
            old[:] = new
        else:
            old.clear()
            old.update(new)
        new = old
    else:
        setattr(obj, f, new)
    if n is not None:
        codec.table[n] = new


def host_class(host, name, why):
    """The host's class `name` (this layer does not import the host's module): from the module of the first class
    along the host's MRO whose module has one -- a subclass declared where none is (a script's
    `class Derived(sim.Sim)`, `class Derived(simai.SimAI)`) finds its base's. Asked only when one must be built
    (review 1119j #4, 1119m #3); `why` names it in the error."""
    for k in type(host).__mro__:
        cls = getattr(importlib.import_module(k.__module__), name, None)
        if cls is not None:
            return cls
    raise ValueError(f'no {name} class along {type(host).__name__}\'s classes to {why}')


def _host_body(sim):
    return host_class(sim, 'Body', 'build a thing made in the run (simsnap.restore)')


def restore(sim, s):
    """Write snapshot `s` onto `sim`, made anew for the same mission, test, level and script and not yet run: the
    world's part, each body's fields (the bodies held in the snapshot's order; the things held out of bodies found
    on the new world by serial, as _things finds them), the Sim's own (containers in place), the executor's. A body
    the snapshot has and the new world has not (one made in the run) is built bare: a Body of the snapshot's fields,
    its modules made by World.restore (World.remake: no on_create, not scheduled -- the schedule is the snapshot's);
    a module attached in the run (World.attach) is made again the same way. A thing of the new run the snapshot has
    not: an error. Returns the things, serial -> Thing (a thing made bare that nothing of the Sim's holds is held
    only by this: a caller's root, simaisnap)."""
    check(sim, s)
    have = {b.serial: b for b in _things(sim)}
    things = {}
    every = [(serial, name, template, fields) for _key, serial, name, template, fields in s['bodies']] + s['others']
    lost = sorted(set(have) - {serial for serial, *_ in every})
    if lost:
        raise ValueError(f'simsnap.restore: things {lost[:10]} of the new run are not in the snapshot '
                         f'({", ".join(repr(have[k].name) for k in lost[:3])})')
    for serial, name, template, _ in every:
        b = have.get(serial)
        if b is None:       # made in the run: bare -- every field is the snapshot's, its modules World.restore's
            things[serial] = _host_body(sim)(name, template, '', 0.0, 0.0)
            continue
        if (b.name, b.template) != (name, template):
            raise ValueError(f'simsnap.restore: body {serial} is {b.name!r} ({b.template}) here, '
                             f'{name!r} ({template}) in the snapshot')
        things[serial] = b
    c = _Codec(sim)
    extra = c.decode_extra(things)
    sim.executor.restore(s['executor'])     # first: it checks its own part whole before it writes (1119i #6)
    sim.world.restore(s['kernel'], things, extra)
    for serial, name, template, fields in every:
        b = things[serial]
        for f in [f for f in vars(b) if BODY.get(f) == STATE and f not in fields]:
            delattr(b, f)
        for f, e in fields.items():
            _write(b, f, e, lambda x: snap.decode(x, things, extra), c)
    sim.bodies.clear()
    sim.bodies.update((key, things[serial]) for key, serial, *_ in s['bodies'])
    for f, mod, name in s['parts']:     # a part the run made on first use (Sim.harm, Sim.specials ...): made anew
        if f not in _fields(sim):
            setattr(sim, f, getattr(importlib.import_module(mod), name)())
    taken = {path for path, _ in s['host']}
    for p, kind in list(_state_paths(sim)):
        if kind == STATE and '.'.join(p) not in taken:
            delattr(_get(sim, p[:-1]), p[-1])
    for path, e in s['host']:
        p = tuple(path.split('.'))
        _write(_get(sim, p[:-1]), p[-1], e, lambda x: snap.decode(x, things, extra), c)
    sim.ground.cache.clear()
    return things


def _table_state(table=SIM, at=()):
    for f, kind in table.items():
        if isinstance(kind, dict):
            yield from _table_state(kind, at + (f,))
        elif kind == STATE:
            yield '.'.join(at + (f,))


def check(sim, s):
    """What restore asks of `s` before it writes anything onto `sim` (a wrapper writing its own part first, simaisnap,
    asks it first: review 1119m #1, an older version refused whole, not half restored): its version, its mission,
    its shape, its setup (level, script: review 1119v P2 #1)."""
    v = version()
    if s.get('version') != v:
        raise ValueError(f'simsnap.restore: a snapshot of version {s.get("version")}, this is {v}')
    if s['mission'] != getattr(sim.m, 'name', None):
        raise ValueError(f'simsnap.restore: a snapshot of {s["mission"]!r} onto {getattr(sim.m, "name", None)!r}')
    _check(s)
    here = _setup(sim)
    differ = [f'{f} {s["setup"][f]!r} onto {v!r}' for f, v in here.items() if s['setup'][f] != v]
    if differ:
        raise ValueError(f'simsnap.restore: a snapshot of another setup: {", ".join(differ)}')


def _setup(sim):
    """What the run was made with besides its mission (Sim(mission, test, level, script)): a snapshot goes back only
    onto a run made at the same level with the same script -- the level decides which of the mission's scripts run
    (review 1119v P2 #1: a normal run's snapshot came back onto a hard host and the hard-only scripts ran). The test
    (a Test, parts of the mission, no name of its own) is not asked: another one's things differ by name or template
    (restore's per-body check)."""
    return {'level': sim.level, 'script': snap.encode(sim.script)}


def _check(s):
    """The snapshot's shape, whole, before restore writes anything (review 1119i #6: a snapshot of an older shape
    passed the version and failed half written): its parts, the rows of bodies and others, the host's fields each
    one SIM sorts STATE, the parts SIM names."""
    want = {'version', 'mission', 'setup', 'kernel', 'bodies', 'others', 'parts', 'host', 'executor'}
    bad = []
    if set(s) != want:
        bad.append(f'parts {sorted(set(s) ^ want)}')
    elif not isinstance(s['setup'], dict) or set(s['setup']) != {'level', 'script'}:
        bad.append('setup')
    else:
        bad += [f'body row {r[:3]}' for r in s['bodies'] if not (isinstance(r, list) and len(r) == 5)]
        bad += [f'other row {r[:2]}' for r in s['others'] if not (isinstance(r, list) and len(r) == 4)]
        state = set(_table_state())
        bad += [f'host field {r[0] if isinstance(r, list) and r else r!r}' for r in s['host']
                if not (isinstance(r, list) and len(r) == 2 and r[0] in state)]
        bad += [f'part {r!r}' for r in s['parts']
                if not (isinstance(r, list) and len(r) == 3 and isinstance(SIM.get(r[0]), dict))]
        kernel = {'made', 'frame', 'used', 'gaps', 'schedule', 'things', 'late'}     # World.snapshot's (review k
        k = s['kernel']                                                             # #3: one missing failed after
        if not isinstance(k, dict) or set(k) != kernel:                             # the executor was written)
            bad.append(f'kernel {sorted(set(k) ^ kernel) if isinstance(k, dict) else type(k).__name__}')
    if bad:
        raise ValueError(f'simsnap.restore: the snapshot is not of this shape ({version()}): {", ".join(bad[:5])}')

