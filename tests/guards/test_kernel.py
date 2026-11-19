"""The kernel's guards (docs/engine/sim-modules.md 8, ADR 0031-0034; step K0 of the module plan): the kernel's own
rules (factory, schedule, Thing.find, sealed data), and

1. a module file imports no other module file, assigns only on itself and finds modules by interface;
2. the centre only shrinks (CENTER: sim.py lines, Sim methods, Body fields, simunits defs, cells not on the schedule);
3. no module-level mutable state and no `global` in the world's files (PROCESS_CACHES, today's exceptions, only
   shrinks);
4. two worlds in one process, advanced in turn, each record as when run alone;
5. every tag the factory registers has a module test by name;
6. the kernel has no dependency on the private model: no name of it in engine/**, imports only engine.* and the
   standard library, and its tests run in full with CNV_ENGINE_MODEL pointing nowhere;
7. a module file runs with no centre file naming it: importing engine.modules loads every file in it, every PHASE is
   a cell of simloop.FRAME, and every cell runs its modules (step K1.5);
8. health and its maximum are written only by Body.set_hp; damage / mend / health go through it (HEALTH_WRITES, K2, B1);
9. every field a module class sets on itself is in its STATE, which holds its RECORDED (STATE_PENDING only shrinks);
10. a thing dies or is deleted only through simbody.Life.kill / Life.delete, which share the one write of alive /
    deleted / died_at (DEATH_WRITES, DEATH_ENTRIES, B4b).
Each guard has a mutation check (a synthetic breach it must catch)."""
import ast
import importlib.util
import inspect
import io
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

from test_plans import small  # noqa: F401,I001  (puts experimental/cnv on the path)
import simrecord  # noqa: E402
import simsmall  # noqa: E402
from engine.kernel import factory, interfaces, module, schedule, world  # noqa: E402
from engine.ports.observe import Observe  # noqa: E402
from maps import probe_block  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent.parent
CNV = ROOT / 'experimental' / 'cnv'
ENGINE = CNV / 'engine'
_spec = importlib.util.spec_from_file_location('test_sim_layers_registry_k', ROOT / 'tests' / 'test_sim_layers.py')
_layers = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_layers)
enginefiles = _layers.enginefiles

APOC = 'SovietAntiVehicleVehicleTech3'
GUARDIAN = 'AlliedAntiVehicleVehicleTech1'


# --- the kernel's own rules ---------------------------------------------------------------------------------------

class Ticker(module.Module, interfaces.Update):
    PHASE = 'autoheal'
    STATE = ('runs',)

    def __init__(self, thing, data, world=None):
        super().__init__(thing, data, world)
        self.runs = []

    def update(self, frame):
        self.runs.append(frame)
        return interfaces.SLEEP if len(self.runs) == 2 else 3


class Mender(module.Module, interfaces.Damage):
    pass


class TickData(module.ModuleData):
    @classmethod
    def parse(cls, head, inner):
        d = cls()
        d.head = head
        return d


Ticker.DATA = TickData


class T(module.Thing):
    def __init__(self, template):
        self.template = template


def test_the_factory_makes_a_module_a_registered_block_and_parses_its_data_once_a_world():
    w = world.World(blocks=lambda template, tag: [('a="1"', '')] * (2 if tag == 'Tick' else 0),
                    tags={'Tick': Ticker, 'Mend': Mender})
    one, two = T('X'), T('X')
    m1, m2 = w.build(one, 0), w.build(two, 0)
    assert [type(m) for m in m1] == [Ticker, Ticker]             # one instance a block
    assert m1[0].data is m2[0].data and m1[0].data.head == 'a="1"'   # shared by the template, parsed once
    try:
        m1[0].data.head = 'b'
        raise AssertionError('module data stayed writable')
    except AttributeError:
        pass
    assert world.World().build(one, 0) == ()                       # nothing registered: nothing made


def test_the_registry_is_read_only_and_a_tag_registers_once():
    assert isinstance(factory.TAGS, type(type.__dict__))
    try:
        factory.TAGS['X'] = Ticker
        raise AssertionError('the registry took a write')
    except TypeError:
        pass


def test_the_schedule_runs_an_awake_module_at_its_cell_and_sleeps_it():
    sch = schedule.Schedule()
    a, b = Ticker(T('X'), None), Ticker(T('X'), None)
    sch.add(a, 5)
    sch.add(b, 6)
    assert sch.run('autoheal', 5) == 1 and a.runs == [5]           # b's wake has not come
    assert sch.run('other', 6) == 0
    sch.run('autoheal', 6)
    assert b.runs == [6]
    sch.run('autoheal', 8)
    sch.run('autoheal', 9)                                          # a: 5 + 3; b: 6 + 3, then both asleep
    assert a.runs == [5, 8] and b.runs == [6, 9] and sch.awake('autoheal') == {}
    sch.run('autoheal', 50)
    assert a.runs == [5, 8]                                         # asleep: not run
    sch.wake(a, 60)
    sch.wake(a, 55)                                                 # the earlier wake wins
    sch.run('autoheal', 55)
    assert a.runs == [5, 8, 55]


def test_the_schedule_never_reuses_an_order_after_a_removal():
    sch = schedule.Schedule()
    a, b, c, d = (Ticker(T('X'), None) for _ in range(4))
    for m in (a, b, c):
        sch.add(m, 5)
    sch.remove(a)
    sch.remove(b)
    sch.add(d, 5)                                                   # by len(seq) it would be 1, before c's 2
    assert sch.seq == {c: 2, d: 3} and sch.added == 4
    sch.run('autoheal', 5)
    assert c.runs == [5] and d.runs == [5]


class Hearer(module.Module, interfaces.Damage):
    def __init__(self, thing, data, world=None):
        super().__init__(thing, data, world)
        self.told = []

    def on_damaged(self, info):
        self.told.append(('damaged', info))

    def on_healed(self, info):
        self.told.append(('healed', info))


def test_a_health_move_tells_the_damage_modules_and_a_wake_comes_at_the_running_cells_frame():
    """Step K2: Thing.health_moved is the Damage broadcast; World.wake defaults to World.frame (the frame loop sets
    it before each cell); a module whose thing left the world is not woken back onto the schedule."""
    t = T('X')
    h = Hearer(t, None)
    t.modules = (h, Ticker(t, None))
    t.health_moved(10, 4)
    t.health_moved(4, 9)
    t.health_moved(9, 9)                                            # a moved maximum: not a hurt
    assert h.told == [('damaged', 10), ('healed', 4), ('healed', 9)]
    assert T('Y').health_moved(1, 0) is None                        # no modules: nobody told
    w = world.World(blocks=lambda template, tag: [('', '')] if tag == 'Tick' else [], tags={'Tick': Ticker})
    thing = T('X')
    thing.modules = w.build(thing, 0)
    (a,) = thing.modules
    w.schedule.run('autoheal', 0)
    w.frame = 1
    w.wake(a)
    w.schedule.run('autoheal', 1)                                   # woken for 1 (not 3): run, then asleep
    assert a.runs == [0, 1] and w.schedule.awake('autoheal') == {}
    w.frame = 7
    w.wake(a)
    assert w.schedule.awake('autoheal') == {a: 7}
    w.drop(thing)
    w.wake(a)
    assert w.schedule.awake('autoheal') == {} and a not in w.schedule.seq


def test_find_is_by_interface_and_body_is_one():
    t = T('X')
    t.modules = (Ticker(t, None), Mender(t, None))
    assert [type(m) for m in t.find(interfaces.Update)] == [Ticker]
    assert t.find(interfaces.Damage)[0].thing is t
    assert t.find(interfaces.Body) is None


def test_a_body_is_a_thing_with_no_modules_field_until_its_modules_are_made():
    import sim
    bare = sim.Body('a', 'BaseBridgeGateHouse', 'Player_1', 0.0, 0.0)     # not made by Sim.add: no module
    assert isinstance(bare, module.Thing) and bare.modules == () and 'modules' not in vars(bare)
    assert (bare.hp, bare.max_hp, bare.immortal, bare.prop) == (100.0, 100.0, False, None)    # the forwards' defaults
    s = simsmall.small_world([('a', 'BaseBridgeGateHouse', 'Player_1', 0.0, 0.0)], model=False)
    b = s.bodies['a']
    assert [type(m).__name__ for m in b.modules] == ['ManagedImmortalBody']     # its Body only (step B2b)
    assert s.unmodeled is s.world.gaps and s.used is s.world.used
    s.gap('武器', 'X', 'why')
    s.gap('武器', 'X')
    assert s.world.gaps[('武器', 'X')] == {'n': 2, 't': s.t, 'what': 'why'}


# --- 1. module files ----------------------------------------------------------------------------------------------

MODULE_OK = ('engine.kernel', 'engine.ports.templates')


def _imported(tree):
    """Every module a tree imports by an absolute name (top level or in a function); `from a import b` gives a.b."""
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            yield from (a.name for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and not node.level:
            yield from (f'{node.module}.{a.name}' for a in node.names)


def module_breaks(sources):
    """(file, why) for each breach of rule 1 in {module name: source} of engine/modules files."""
    out = []
    for name, src in sources.items():
        tree = ast.parse(src)
        for n in sorted(_imported(tree)):
            if not any(n == ok or n.startswith(ok + '.') for ok in MODULE_OK) and n.split('.')[0] not in sys.stdlib_module_names:
                out.append((name, 'imports ' + n))
        for node in ast.walk(tree):
            targets = node.targets if isinstance(node, ast.Assign) else \
                [node.target] if isinstance(node, (ast.AugAssign, ast.AnnAssign)) else []
            for t in targets:
                while isinstance(t, ast.Subscript):
                    t = t.value
                if isinstance(t, ast.Attribute) and not (isinstance(t.value, ast.Name) and t.value.id == 'self'):
                    out.append((name, 'assigns ' + ast.unparse(t)))
            if isinstance(node, ast.Attribute) and node.attr == 'modules':
                out.append((name, 'reads ' + ast.unparse(node)))
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in ('isinstance', 'hasattr') \
                    and len(node.args) == 2:
                kind = node.args[1]
                if node.func.id == 'hasattr' or not (isinstance(kind, ast.Attribute) and
                                                      isinstance(kind.value, ast.Name) and kind.value.id == 'interfaces'):
                    out.append((name, ast.unparse(node)))
    return out


def module_sources():
    return {enginefiles.name_of(p): Path(p).read_text(encoding='utf-8') for p in enginefiles.files()
            if Path(p).is_relative_to(ENGINE / 'modules')}


def test_module_files_keep_to_themselves():
    assert not module_breaks(module_sources())


def test_module_guard_bites():
    ok = ('from engine.kernel import interfaces, module\n'
          'class A(module.Module, interfaces.Damage):\n'
          '    def on_damaged(self, info):\n'
          '        self.hurt = info\n'
          '        for m in self.thing.find(interfaces.Update):\n'
          '            m.wake_me()\n')
    assert not module_breaks({'engine.modules.a': ok})
    bad = {'engine.modules.b': 'import engine.modules.a\nimport simunits\n',
           'engine.modules.c': 'def f(self, other):\n    other.hp = 1\n    for m in self.thing.modules:\n        pass\n',
           'engine.modules.d': 'import engine.modules.a as a\ndef f(m):\n    return isinstance(m, a.A) or hasattr(m, "x")\n'}
    got = {(f, why.split()[0]) for f, why in module_breaks(bad)}
    assert ('engine.modules.b', 'imports') in got and len([g for g in module_breaks(bad) if g[0] == 'engine.modules.b']) == 2
    assert {('engine.modules.c', 'assigns'), ('engine.modules.c', 'reads')} <= got
    assert {('engine.modules.d', 'imports'), ('engine.modules.d', 'isinstance(m,'), ('engine.modules.d', 'hasattr(m,')} <= got


# --- 2. the centre only shrinks -----------------------------------------------------------------------------------

CENTER = {'sim.py lines': 3421, 'Sim methods': 194, 'Body fields': 79, 'simunits defs': 139,
          'cells with old code': 31}


def _old_code(fn):
    """Does a frame cell still hold code of its own (beyond a docstring / pass)? Every cell runs its modules
    (simloop._with_modules); a cell that is only its modules has none."""
    body = [n for n in fn.body if not (isinstance(n, ast.Expr) and isinstance(n.value, ast.Constant)) and
            not isinstance(n, ast.Pass)]
    return bool(body)


def center(sim_src=None, units_src=None, loop_src=None):
    sim_src = sim_src if sim_src is not None else (CNV / 'sim.py').read_text(encoding='utf-8')
    units_src = units_src if units_src is not None else (CNV / 'simunits.py').read_text(encoding='utf-8')
    loop_src = loop_src if loop_src is not None else (CNV / 'simloop.py').read_text(encoding='utf-8')
    tree = ast.parse(sim_src)
    cls = {n.name: n for n in tree.body if isinstance(n, ast.ClassDef)}
    loop = ast.parse(loop_src)
    frame = next(ast.literal_eval(n.value) for n in loop.body
                 if isinstance(n, ast.Assign) and any(getattr(t, 'id', '') == 'FRAME' for t in n.targets))
    cells = {n.name: n for n in loop.body if isinstance(n, ast.FunctionDef)}
    return {'sim.py lines': len(sim_src.splitlines()),
            'Sim methods': sum(isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) for n in cls['Sim'].body),
            'Body fields': sum(isinstance(n, ast.AnnAssign) for n in cls['Body'].body),
            'simunits defs': sum(isinstance(n, ast.FunctionDef) for n in ast.parse(units_src).body),
            'cells with old code': sum(c not in cells or _old_code(cells[c]) for c in frame)}


def grown(now, limits=CENTER):
    return {k: (v, limits[k]) for k, v in now.items() if v > limits[k]}


def test_the_centre_only_shrinks():
    """Over the list: red. Smaller: lower the list in the same commit (the commit message gives before and after)."""
    now = center()
    assert not grown(now), f'the centre grew: {grown(now)}'
    assert now == CENTER, f'the centre shrank: lower CENTER to {now}'


def test_centre_guard_bites():
    now = center()
    sim_src = (CNV / 'sim.py').read_text(encoding='utf-8').replace('class Sim:\n', 'class Sim:\n    def extra(self):\n        pass\n', 1)
    assert grown(center(sim_src=sim_src))['Sim methods'] == (now['Sim methods'] + 1, CENTER['Sim methods'])
    loop_src = (CNV / 'simloop.py').read_text(encoding='utf-8')
    emptied = loop_src.replace("def passive_area_heal(s, frame, tick):\n    s.heal.passive_area_heal(s)\n",
                               "def passive_area_heal(s, frame, tick):\n    \"\"\"Its modules only.\"\"\"\n", 1)
    assert emptied != loop_src
    assert center(loop_src=emptied)['cells with old code'] == now['cells with old code'] - 1
    refilled = loop_src.replace('    """Its modules only (engine/modules/autoheal.py, run by step)."""\n',
                                '    """Its modules only."""\n    s.heal.autoheal(s)\n', 1)
    assert refilled != loop_src
    assert grown(center(loop_src=refilled))['cells with old code'] == (CENTER['cells with old code'] + 1,
                                                                       CENTER['cells with old code'])


# Body fields moved into modules that outside code still reads (module_plan 1): read-only forwards, listed in
# Body.FORWARDS (the frame record shows them as the fields they were). Only shrinks: a forward goes when its last
# outside reader asks the module's interface itself.
BODY_FORWARDS = {'hp': 'Body', 'max_hp': 'Body', 'health_floor': 'Body', 'immortal': 'Body', 'prop': 'Body',
                 'last_hit': 'Body', 'last_by': 'Body', 'indestructible': 'Body', 'read_until': 'Body',
                 'life_end': 'LifetimeUpdate', 'topple': 'ToppleUpdate', 'toppled': 'ToppleUpdate',
                 'topple_end': 'ToppleUpdate', 'crusher': 'CrusherInfo', 'crushable': 'CrusherInfo',
                 'deposit': 'AutoDepositUpdate', 'deposit_at': 'AutoDepositUpdate',
                 'toggle_at': 'ToggleStatusSpecialAbilityUpdate', 'armor_up': 'ToggleStatusSpecialAbilityUpdate',
                 'suppression_rule': 'SuppressionUpdate', 'suppression_hits': 'SuppressionUpdate',
                 'suppressed': 'SuppressionUpdate', 'suppressed_until': 'SuppressionUpdate',
                 'suppression_next': 'SuppressionUpdate', 'attachment_rules': 'AttachUpdate',
                 'spawned_children': 'SpawnBehavior', 'spawn_refills': 'SpawnBehavior', 'spawn_parent': 'SlavedUpdate',
                 'spawn_module': 'SlavedUpdate', 'ready_at': 'SpecialPower', 'mine': 'OreMinerBehavior',
                 'unpack_end': 'StructureUnpackUpdate', 'sell_end': 'StructureSellUpdate',
                 'cold': 'SecondaryDamageTracker', 'cold_step': 'SecondaryDamageTracker',
                 'level_modules': 'LevelUpUpgrade'}


def body_forwards(sim_src=None):
    """(Body.FORWARDS, the class-level names bound to kernel_module.forward(...), any of those with a setter)."""
    sim_src = sim_src if sim_src is not None else (CNV / 'sim.py').read_text(encoding='utf-8')
    body = next(n for n in ast.parse(sim_src).body if isinstance(n, ast.ClassDef) and n.name == 'Body')
    listed, bound = (), set()
    for n in body.body:
        if isinstance(n, ast.Assign) and len(n.targets) == 1 and isinstance(n.targets[0], ast.Name):
            if n.targets[0].id == 'FORWARDS':
                listed = tuple(ast.literal_eval(n.value))
            elif isinstance(n.value, ast.Call) and getattr(n.value.func, 'attr', '') == 'forward':
                bound.add(n.targets[0].id)
    setters = {d.value.id for n in body.body if isinstance(n, ast.FunctionDef) for d in n.decorator_list
               if isinstance(d, ast.Attribute) and d.attr == 'setter' and isinstance(d.value, ast.Name)} & bound
    return listed, bound, setters


def test_body_forwards_are_read_only_listed_and_only_shrink():
    listed, bound, setters = body_forwards()
    assert set(listed) == bound, f'Body.FORWARDS {listed} and the forward(...) attributes {sorted(bound)} differ'
    assert not setters, f'a forward is written: {setters}'
    assert set(listed) <= set(BODY_FORWARDS), f'a new forward: {set(listed) - set(BODY_FORWARDS)}'
    assert set(listed) == set(BODY_FORWARDS), f'a forward went: take it off BODY_FORWARDS {set(BODY_FORWARDS) - set(listed)}'


def test_forward_guard_bites():
    src = (CNV / 'sim.py').read_text(encoding='utf-8')
    listed = re.search(r'    FORWARDS = [(].*?[)]', src, re.S).group(0)     # as sim.py writes it (lines may wrap)
    more = src.replace(listed, '    FORWARDS = ' + repr(tuple(BODY_FORWARDS) + ('shielded',)), 1)
    assert more != src and set(body_forwards(more)[0]) != body_forwards(more)[1]
    unlisted = src.replace(listed, "    FORWARDS = ()", 1)
    assert body_forwards(unlisted)[1] - set(body_forwards(unlisted)[0]) == set(BODY_FORWARDS)
    written = src.replace('    @health.setter\n', '    @life_end.setter\n', 1)
    assert body_forwards(written)[2] == {'life_end'}


def test_a_forward_reads_the_module_and_cannot_be_written():
    s =simsmall.small_world([('p', 'AlliedPowerPlant', 'Player_1', 0.0, 0.0)])
    p = s.bodies['p']
    assert p.life_end is None and 'life_end' not in vars(p)
    with pytest.raises(AttributeError):
        p.life_end = 3


# --- 3. no module-level mutable state -----------------------------------------------------------------------------

MUTATORS = _layers.MUTATORS | {'popitem', 'appendleft'}
CONTAINERS = {'dict', 'list', 'set', 'defaultdict', 'OrderedDict', 'Counter', 'deque'}
# today's process caches of read-only retail data (and the private model's loaders): only shrinks; a line goes when
# its cache moves into the template data port's instance
PROCESS_CACHES = {
    ('sim', '_MODEL'), ('simai', '_AI'), ('simproxy', '_PROXY'), ('simgarrison', '_memo'), ('simsweep', '_weapon_blocks'),
    ('simunits', '_reads'),     # T9 (11-18, coordinator's order): the SDK text / template reads, read-only data
    *(('simunits', n) for n in (
        '_acquire', '_all_defines', '_command_powers', '_equivalent', '_fight',
        '_flee_memo', '_globals', '_hp_memo', '_index', '_ocl_text', '_ocls', '_own_weapons', '_prop_memo', '_radii',
        '_resolved', '_retail_commands', '_retail_files', '_retail_mods', '_retail_powers', '_slow_memo',
        '_surf_memo', '_table', '_turning_memo', '_upgrades', '_weapon_blocks', '_wreck_memo')),
}
REGISTRARS = {('engine.kernel.factory', '_TAGS'): 'register'}     # filled only by the factory's decorator


def _mutable(v):
    if isinstance(v, (ast.Dict, ast.List, ast.Set, ast.ListComp, ast.DictComp, ast.SetComp)):
        return True
    f = v.func if isinstance(v, ast.Call) else None
    return f is not None and (getattr(f, 'id', None) or getattr(f, 'attr', None)) in CONTAINERS


def state_breaks(name, src):
    """{(module, name)}: a `global`, or a module-level container changed inside a function (registrar exempt)."""
    tree = ast.parse(src)
    held = {t.id for n in tree.body if isinstance(n, (ast.Assign, ast.AnnAssign)) and n.value is not None and _mutable(n.value)
            for t in (n.targets if isinstance(n, ast.Assign) else [n.target]) if isinstance(t, ast.Name)}
    out = set()
    for fn in ast.walk(tree):
        if not isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
            continue
        for x in ast.walk(fn):
            if isinstance(x, ast.Global):
                out |= {(name, g) for g in x.names}
            targets = x.targets if isinstance(x, (ast.Assign, ast.Delete)) else \
                [x.target] if isinstance(x, (ast.AugAssign, ast.AnnAssign)) else []
            for t in targets:
                while isinstance(t, (ast.Subscript, ast.Attribute)):
                    t = t.value
                    if isinstance(t, ast.Name) and t.id in held:
                        out.add((name, t.id))
            if isinstance(x, ast.Call) and isinstance(x.func, ast.Attribute) and x.func.attr in MUTATORS and \
                    isinstance(x.func.value, ast.Name) and x.func.value.id in held:
                out.add((name, x.func.value.id))
    return {b for b in out if REGISTRARS.get(b) is None or not _only_in(tree, b[1], REGISTRARS[b])}


def _only_in(tree, held, fn_name):
    """Is `held` changed only inside the function fn_name?"""
    for fn in ast.walk(tree):
        if isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)) and fn.name != fn_name:
            inner = {id(x) for f in ast.walk(fn) if isinstance(f, ast.FunctionDef) and f.name == fn_name for x in ast.walk(f)}
            for x in ast.walk(fn):
                if id(x) in inner:
                    continue
                if isinstance(x, ast.Subscript) and isinstance(x.value, ast.Name) and x.value.id == held and \
                        isinstance(x.ctx, ast.Store):
                    return False
    return True


def world_files():
    """The files a world runs: the kernel, the layered modules, the facade, the proxy and the AI's side."""
    names = set(_layers.LAYER_OF) | {'sim', 'simproxy'} | _layers.AI_SIDE
    return {enginefiles.name_of(p): Path(p).read_text(encoding='utf-8') for p in enginefiles.files()
            if enginefiles.name_of(p) in names or Path(p).is_relative_to(ENGINE)}


def test_no_module_level_mutable_state():
    found = set().union(*(state_breaks(n, src) for n, src in world_files().items()))
    assert not found - PROCESS_CACHES, f'new module-level state: {sorted(found - PROCESS_CACHES)}'
    assert not PROCESS_CACHES - found, f'gone: take off PROCESS_CACHES {sorted(PROCESS_CACHES - found)}'


def test_state_guard_bites():
    src = 'X = {}\nY = []\nZ = {}\nZ["a"] = 1\ndef f():\n    global N\n    X["k"] = 1\n    Y.append(2)\n'
    assert state_breaks('m', src) == {('m', 'N'), ('m', 'X'), ('m', 'Y')}
    reg = '_TAGS = {}\ndef module(*t):\n    def register(c):\n        _TAGS[t] = c\n    return register\n'
    assert state_breaks('engine.kernel.factory', reg) == set()
    assert state_breaks('engine.kernel.factory', reg + 'def sneak():\n    _TAGS["x"] = 1\n') == \
        {('engine.kernel.factory', '_TAGS')}


# --- 4. two worlds in one process ---------------------------------------------------------------------------------

def _world_a():
    return simsmall.small_world([('a', APOC, 'Player_1', 0.0, 0.0), ('g', GUARDIAN, 'Soviet_1', 300.0, 0.0)],
                                model=False)


def _world_b():
    s = simsmall.small_world((), model=False, map=probe_block)
    me, foe = s.human, next(p for p in s.players.values() if p != s.human)
    s.add('i', 'AlliedAntiInfantryInfantry', me, 400.0, 400.0)
    s.add('t', 'SovietAntiVehicleVehicleTech1', foe, 600.0, 400.0)
    return s


def simrecord_dt():
    import simworld
    return simworld.DT


def _record(worlds, ticks):
    """One record a world: its line after each tick, the worlds advanced in turn."""
    outs = [io.StringIO() for _ in worlds]
    recs = [simrecord.Recorder(Observe(s), o) for s, o in zip(worlds, outs)]
    for _ in range(ticks):
        for s, r in zip(worlds, recs):
            s.step()
            s.t = round(s.t + simrecord_dt(), 3)         # the caller moves the time on (Sim.run)
            r.line('tick')
    return [o.getvalue() for o in outs]


def test_two_worlds_in_turn_record_as_each_alone():
    alone = [_record([_world_a()], 16)[0], _record([_world_b()], 16)[0]]
    together = _record([_world_a(), _world_b()], 16)
    assert together == alone
    assert alone[0] != alone[1] and alone[0].splitlines()[0] != alone[0].splitlines()[-1]   # they did something


def test_world_guard_bites():
    """A world that leaned on another's state would show: here the second world shares the first's gap log."""
    a, b = _world_a(), _world_b()
    b.unmodeled = b.world.gaps = a.world.gaps
    a.gap('武器', 'shared')                          # a's gap shows in b's record
    assert _record([b], 1)[0] != _record([_world_b()], 1)[0]


# --- 5. every registered tag has a module test --------------------------------------------------------------------

def registered_tags(sources):
    """{tag: module name} from the @module(...) / @factory.module(...) decorators of module files."""
    out = {}
    for name, src in sources.items():
        for node in ast.walk(ast.parse(src)):
            if isinstance(node, ast.ClassDef):
                for d in node.decorator_list:
                    if isinstance(d, ast.Call) and (getattr(d.func, 'id', None) or getattr(d.func, 'attr', None)) == 'module':
                        out.update({a.value: name for a in d.args if isinstance(a, ast.Constant)})
    return out


def untested_tags(sources, tests):
    """Tags with no tests/modules/test_<file>.py naming them; tests: {file stem: source}."""
    return sorted(t for t, m in registered_tags(sources).items() if t not in tests.get('test_' + m.rsplit('.', 1)[-1], ''))


def test_every_registered_tag_has_a_module_test():
    tests = {p.stem: p.read_text(encoding='utf-8') for p in (ROOT / 'tests' / 'modules').glob('test_*.py')} \
        if (ROOT / 'tests' / 'modules').is_dir() else {}
    assert not untested_tags(module_sources(), tests)


def test_tag_guard_bites():
    src = {'engine.modules.autoheal': '@module("AutoHealBehavior")\nclass A: pass\n'}
    assert untested_tags(src, {}) == ['AutoHealBehavior']
    assert untested_tags(src, {'test_autoheal': 'def test_x():  # AutoHealBehavior\n    pass\n'}) == []


# --- 7. a module file runs without a centre file naming it (step K1.5) -------------------------------------------

def test_every_module_file_is_loaded_with_the_package():
    import engine.modules  # noqa: F401
    files = sorted(p.stem for p in (ENGINE / 'modules').glob('*.py') if p.stem != '__init__')
    assert files and all(f'engine.modules.{f}' in sys.modules for f in files)
    assert enginefiles.folder_loaded('engine.modules') == {f'engine.modules.{f}' for f in files}   # the tools see it
    assert {c.__module__ for c in factory.TAGS.values()} <= {f'engine.modules.{f}' for f in files}


def unwired(classes, frame):
    """The update module classes whose PHASE is no cell of the frame order (they would never run)."""
    return sorted(c.__name__ for c in classes if issubclass(c, interfaces.Update) and c.PHASE not in frame)


def test_every_phase_is_a_frame_cell():
    import simloop
    assert not unwired(set(factory.TAGS.values()), simloop.FRAME)


def test_phase_guard_bites():
    import simloop
    typo = type('Typo', (Ticker,), {'PHASE': 'auto_heal'})
    assert unwired({Ticker, typo, Mender}, simloop.FRAME) == ['Typo']


def _probes(s, phases, log):
    """One probe a phase in s's schedule, logging (frame, phase) each run."""
    class Probe(module.Module, interfaces.Update):
        def update(self, frame):
            log.append((frame, self.PHASE))
            return 1
    for p in phases:
        s.world.schedule.add(type('Probe_' + p, (Probe,), {'PHASE': p})(T('x'), None, s.world), 0)


def test_every_frame_cell_runs_its_modules_in_the_frame_order():
    import simloop
    s = simsmall.small_world((), model=False)
    log = []
    _probes(s, simloop.FRAME, log)
    s.step()
    # the scripts cell moves the frame clock on (simloop: as the engine has it), so the cells after it see the next
    after = set(simloop.FRAME[simloop.FRAME.index('scripts') + 1:])
    frames = sorted({f for f, p in log if p not in after})
    assert len(frames) >= 7
    assert log == [(f + (p in after), p) for f in frames for p in simloop.FRAME]


def test_cell_guard_bites():
    """A frame loop that skips a cell's modules leaves its probe idle."""
    import simloop
    s = simsmall.small_world((), model=False)
    log = []
    _probes(s, ('autoheal', 'deal'), log)
    plain = tuple(simloop._with_modules(n, simloop.CELLS[n]) if n != 'deal' else simloop.CELLS[n]
                  for n in simloop.FRAME)
    simloop.step(s, plain)
    assert {p for _, p in log} == {'autoheal'}


# --- 6. no dependency on the private model ------------------------------------------------------------------------

PRIVATE_NAMES = ('RA3-EngineModel', 'ra3model', 'labpaths', 'modelpin', 'engine_model', 'ENGINE_MODEL',
                 'inventory_model', 'work/re', 'work\\re')


def private_breaks(sources):
    """(file, what) for a private name in a kernel file, or an import other than engine.* and the standard library."""
    out = []
    for name, src in sources.items():
        out += [(name, p) for p in PRIVATE_NAMES if p in src]
        for node in ast.walk(ast.parse(src)):
            mods = [a.name for a in node.names] if isinstance(node, ast.Import) else \
                [node.module] if isinstance(node, ast.ImportFrom) and node.module and not node.level else []
            out += [(name, m) for m in mods if m.split('.')[0] != 'engine' and m.split('.')[0] not in sys.stdlib_module_names]
            if isinstance(node, ast.Call) and getattr(node.func, 'attr', '') in ('spec_from_file_location', 'import_module') \
                    and not _own_folder_load(node):
                out.append((name, ast.unparse(node.func)))
    return out


def _own_folder_load(call):
    """import_module('.' + name, __name__): a package loading a file of its own folder (engine/modules/__init__)."""
    a = call.args
    return getattr(call.func, 'attr', '') == 'import_module' and len(a) == 2 and not call.keywords and \
        isinstance(a[1], ast.Name) and a[1].id == '__name__' and isinstance(a[0], ast.BinOp) and \
        isinstance(a[0].op, ast.Add) and isinstance(a[0].left, ast.Constant) and a[0].left.value == '.'


def engine_sources():
    return {enginefiles.name_of(p): Path(p).read_text(encoding='utf-8') for p in enginefiles.files()
            if Path(p).is_relative_to(ENGINE)}


def test_the_kernel_knows_nothing_private():
    assert engine_sources() and not private_breaks(engine_sources())


def test_private_guard_bites():
    bad = {'engine.kernel.x': 'import modelpin\nimport simunits\nimport importlib\nP = "../RA3-EngineModel"\n'
                              'm = importlib.import_module("ra3model.scripts")\n'}
    got = {w for _, w in private_breaks(bad)}
    assert {'modelpin', 'simunits', 'RA3-EngineModel', 'ra3model', 'importlib.import_module'} <= got
    assert not private_breaks({'engine.kernel.y': 'import types\nfrom engine.kernel import module\n'})
    own = 'import importlib\nimportlib.import_module("." + n, __name__)\n'
    assert not private_breaks({'engine.modules': own})
    for sneak in ('importlib.import_module(".." + n, __name__)', 'importlib.import_module(n, __name__)',
                  'importlib.import_module("." + n, "ra3model")', 'importlib.import_module("." + n)'):
        assert private_breaks({'engine.modules': 'import importlib\n' + sneak + '\n'}), sneak


# Step P1: a plug-in's adapter (the private model's script core on the script executor port) imports only the ports
# (engine.ports.*) and the standard library -- never the kernel's insides nor the simulator (sim-modules.md 6).
ADAPTERS = ('scriptplugin.py',)


def adapter_breaks(sources):
    """(file, module) for each import of an adapter other than engine.ports.* and the standard library."""
    out = []
    for name, src in sources.items():
        for node in ast.walk(ast.parse(src)):
            mods = [a.name for a in node.names] if isinstance(node, ast.Import) else \
                [node.module] if isinstance(node, ast.ImportFrom) and node.module and not node.level else []
            out += [(name, m) for m in mods if not (m == 'engine.ports' or m.startswith('engine.ports.'))
                    and m.split('.')[0] not in sys.stdlib_module_names]
    return out


def test_adapters_import_only_the_ports():
    assert not adapter_breaks({n: (CNV / n).read_text(encoding='utf-8') for n in ADAPTERS})


def test_adapter_guard_bites():
    src = (CNV / 'scriptplugin.py').read_text(encoding='utf-8')
    assert adapter_breaks({'a': src + '\nimport sim\n'}) == [('a', 'sim')]
    assert adapter_breaks({'a': src + '\nfrom engine.kernel import world\n'}) == [('a', 'engine.kernel')]
    assert not adapter_breaks({'a': 'import math\nfrom engine.ports import scripts\nimport engine.ports.templates\n'})


# Guard 8 (steps K2, B1): a thing's health and its maximum are written only by Body.set_hp, which calls health_moved
# (its Damage modules are told: an asleep AutoHeal wakes on it) unless the body is being made or filled before its
# modules first run, or dies. Body.damage / mend / health and every other write (a script's maximum, an elite's
# multiplier, a death) go through it; a direct `.hp` / `.max_hp` write anywhere else in experimental/cnv/sim*.py or
# engine/ breaks the guard.
HEALTH_WRITES = {('engine/modules/body.py', 'Body.set_health')}     # the Body module's since step B2b


def health_sources():
    """{file: source}: experimental/cnv/sim*.py by name, the engine package by path under experimental/cnv."""
    return {**{p.name: p.read_text(encoding='utf-8') for p in sorted(CNV.glob('sim*.py'))},
            **{p.relative_to(CNV).as_posix(): p.read_text(encoding='utf-8') for p in sorted(ENGINE.rglob('*.py'))}}


def _functions(node, prefix=''):
    """(qualified name, function node) of every function under `node`, classes and outer functions dotted in."""
    for child in ast.iter_child_nodes(node):
        if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
            yield prefix + child.name, child
            yield from _functions(child, prefix + child.name + '.')
        elif isinstance(child, ast.ClassDef):
            yield from _functions(child, prefix + child.name + '.')
        else:
            yield from _functions(child, prefix)


def health_writes(sources=None):
    """{(file, qualified function): calls health_moved} for every function that assigns a `.hp` / `.max_hp`
    attribute itself (not in a function nested in it; simai's own `self.hp` table is not a body's health: left out)."""
    if sources is None:
        sources = health_sources()
    found = {}
    for name, src in sources.items():
        for qual, fn in _functions(ast.parse(src)):
            inner = {id(x) for f in ast.walk(fn) if f is not fn and isinstance(f, (ast.FunctionDef, ast.AsyncFunctionDef))
                     for x in ast.walk(f)}
            writes = [t for st in ast.walk(fn) if id(st) not in inner and isinstance(st, (ast.Assign, ast.AugAssign))
                      for t in (st.targets if isinstance(st, ast.Assign) else [st.target]) for x in ast.walk(t)
                      if isinstance(x, ast.Attribute) and x.attr in ('hp', 'max_hp') and isinstance(x.ctx, ast.Store)
                      and not (name == 'simai.py' and isinstance(x.value, ast.Name) and x.value.id == 'self')]
            if writes:
                found[(name, qual)] = any(isinstance(c, ast.Call) and isinstance(c.func, ast.Attribute) and
                                          c.func.attr == 'health_moved' for c in ast.walk(fn))
    return found


def health_breaks(found):
    """A write outside the Body's HEALTH_WRITES, or one of those that does not call health_moved."""
    return sorted(k for k, tells in found.items() if k not in HEALTH_WRITES or not tells)


def test_health_is_written_only_inside_the_body():
    found = health_writes()
    assert not health_breaks(found), health_breaks(found)
    assert set(found) == HEALTH_WRITES, f'a Body write is gone: lower HEALTH_WRITES {HEALTH_WRITES - set(found)}'


def test_health_guard_bites():
    sources = health_sources()
    raw = dict(sources, **{'simrepair.py': sources['simrepair.py'].replace('b.mend(heal)', 'b.hp = min(b.max_hp, b.hp + heal)', 1)})
    assert raw['simrepair.py'] != sources['simrepair.py'] and health_breaks(health_writes(raw)) == [('simrepair.py', 'Repairs.due')]
    # a write outside the Body that tells is still outside it (as simlevel's elite multiplier was before step B1)
    told = dict(sources, **{'simlevel.py': sources['simlevel.py'].replace(
        'b.set_hp(b.hp * multiplier, b.max_hp * multiplier)', 'b.max_hp *= multiplier; b.health_moved(0, 0)', 1)})
    assert told['simlevel.py'] != sources['simlevel.py'] and health_breaks(health_writes(told)) == [('simlevel.py', 'receive')]
    # a module writing its thing's health
    mod = 'engine/modules/autoheal.py'
    assert mod in sources
    hurt = dict(sources, **{mod: sources[mod] + '\n\ndef hurt(thing):\n    thing.hp = 0.0\n'})
    assert health_breaks(health_writes(hurt)) == [(mod, 'hurt')]
    # a sim.py function named as a Body method but outside the class
    stray = dict(sources, **{'sim.py': sources['sim.py'] + '\n\ndef damage(b):\n    b.hp = 0.0\n    b.health_moved(1, 0)\n'})
    assert health_breaks(health_writes(stray)) == [('sim.py', 'damage')]
    # the Body's own damage writing past set_hp
    bm = 'engine/modules/body.py'
    past = dict(sources, **{bm: sources[bm].replace(
        '            self.set_health(max(self.health_floor if self.immortal else 0.0, self.hp - amount))',
        '            self.hp -= amount', 1)})
    assert past[bm] != sources[bm] and health_breaks(health_writes(past)) == [(bm, 'Body.attempt_damage')]
    # set_health telling no one
    body = dict(sources, **{bm: sources[bm].replace('            self.thing.health_moved(was, hp)\n', '            pass\n', 1)})
    assert body[bm] != sources[bm] and health_breaks(health_writes(body)) == [(bm, 'Body.set_health')]
    assert not health_breaks(health_writes(dict(sources, **{'simai.py': 'class A:\n    def f(self):\n        self.hp = {}\n'})))


# --- 9. a module's state is all in its STATE (step S, the snapshot; work/re sim_split/snapshot.md 4.3) -------------
# The snapshot takes a module's STATE and nothing else of it (a restore makes the things again, without on_create), so
# every field a module class sets on itself must be in its STATE; RECORDED (what the frame record shows) is part of it.
# STATE_PENDING: the fields not yet in, by the class that sets them -- only shrinks (empty since step B4c's
# first part: Body / Spawn / Slaved / Garrison name theirs, RECORDED kept as it was).
STATE_PENDING = set()
KERNEL_SET = {'thing', 'data', 'world'}          # Module.__init__'s wiring, made again by the factory


def _self_sets(cls):
    """The fields a class's own source assigns (or changes in place) on `self`."""
    import inspect
    import textwrap
    tree = ast.parse(textwrap.dedent(inspect.getsource(cls)))
    out = set()
    for n in ast.walk(tree):
        targets = n.targets if isinstance(n, ast.Assign) else \
            [n.target] if isinstance(n, (ast.AugAssign, ast.AnnAssign)) else []
        for t in targets:
            for e in ast.walk(t):
                if isinstance(e, ast.Attribute) and isinstance(e.value, ast.Name) and e.value.id == 'self':
                    out.add(e.attr)
    return out


def module_state_gaps(classes):
    """{(the class that sets it, field)} a module class sets on itself outside its STATE, and {(class, field)} of a
    RECORDED field outside STATE; `classes` the concrete ones (their bases outside module.Module's own are read too)."""
    gaps, recorded = set(), set()
    for cls in classes:
        state = set(cls.STATE)
        for owner in cls.__mro__:
            if owner is module.Module or not (isinstance(owner, type) and issubclass(owner, module.Module)):
                continue
            gaps |= {(owner.__name__, f) for f in _self_sets(owner) - KERNEL_SET - state}
        recorded |= {(cls.__name__, f) for f in set(cls.RECORDED) - state}
    return gaps, recorded


def test_a_modules_state_is_all_in_its_state():
    import engine.modules  # noqa: F401
    gaps, recorded = module_state_gaps(set(factory.TAGS.values()))
    assert not recorded, f'RECORDED outside STATE: {sorted(recorded)}'
    assert not gaps - STATE_PENDING, f'set on the module but not in its STATE: {sorted(gaps - STATE_PENDING)}'
    assert not STATE_PENDING - gaps, f'now in STATE: take them out of STATE_PENDING {sorted(STATE_PENDING - gaps)}'


class Stateful(module.Module, interfaces.Create):
    STATE = ('kept',)

    def on_create(self, frame):
        self.kept, self.lost = frame, frame


class StatefulTwo(Stateful):
    RECORDED = ('kept', 'shown')

    def bump(self):
        self.more += 1


def test_module_state_guard_bites():
    gaps, recorded = module_state_gaps({Stateful, StatefulTwo})
    assert gaps == {('Stateful', 'lost'), ('StatefulTwo', 'more')}
    assert recorded == {('StatefulTwo', 'shown')}
    # RECORDED follows a class's own STATE unless named; a class naming neither keeps its base's
    assert Stateful.RECORDED == ('kept',) and type('Plain', (Stateful,), {}).RECORDED == ('kept',)
    assert type('Hidden', (Stateful,), {'STATE': ('kept', 'x'), 'RECORDED': ()}).RECORDED == ()


# Guard 10 (step B4b): a thing's end has two entries, Sim.destroy -> simbody.Life.kill (a death: lethal damage to an
# immortal, a prop's fall, death weapons, an air crash) and Sim.delete -> Life.delete (no death); both go through
# Life._out, the one function that writes a body's alive / deleted / died_at. A write anywhere else in
# experimental/cnv/sim*.py or engine/, or a third caller of _out, breaks the guard (step B4c hangs the Die
# modules' broadcast on the death entry alone).
DEATH_WRITES = {('simbody.py', 'Life._out')}
DEATH_ENTRIES = {('simbody.py', 'Life.kill'), ('simbody.py', 'Life.delete')}      # the callers of Life._out
DEATH_EXEMPT = {('engine/ports/observe.py', 'Observe.specimen'),   # a specimen made dead, never in the fight
                ('simai.py', 'Brain.attach')}                      # the AI's teams.alive hook, not a body's field


def death_writes(sources=None):
    """{(file, qualified function)}: every function that assigns an `.alive` / `.deleted` / `.died_at` attribute
    itself (not in a function nested in it), and {(file, qualified function)} of those that call `._out(`."""
    if sources is None:
        sources = health_sources()
    writes, entries = set(), set()
    for name, src in sources.items():
        for qual, fn in _functions(ast.parse(src)):
            inner = {id(x) for f in ast.walk(fn) if f is not fn and isinstance(f, (ast.FunctionDef, ast.AsyncFunctionDef))
                     for x in ast.walk(f)}
            mine = [st for st in ast.walk(fn) if id(st) not in inner]
            if any(isinstance(x, ast.Attribute) and x.attr in ('alive', 'deleted', 'died_at') and isinstance(x.ctx, ast.Store)
                   for st in mine if isinstance(st, (ast.Assign, ast.AugAssign, ast.AnnAssign))
                   for t in (st.targets if isinstance(st, ast.Assign) else [st.target]) for x in ast.walk(t)):
                writes.add((name, qual))
            if any(isinstance(c, ast.Call) and isinstance(c.func, ast.Attribute) and c.func.attr == '_out'
                   for c in mine) and name == 'simbody.py':
                entries.add((name, qual))
    return writes - DEATH_EXEMPT, entries


def death_breaks(found):
    """A write outside DEATH_WRITES, or a caller of Life._out outside DEATH_ENTRIES."""
    writes, entries = found
    return sorted((writes - DEATH_WRITES) | (entries - DEATH_ENTRIES))


def test_a_thing_ends_only_through_the_two_entries():
    found = death_writes()
    assert not death_breaks(found), death_breaks(found)
    assert found == (DEATH_WRITES, DEATH_ENTRIES), f'an end entry is gone: lower DEATH_WRITES / DEATH_ENTRIES {found}'
    import sim
    import simbody
    assert 'delete' not in inspect.signature(sim.Sim.destroy).parameters      # one entry each, no flag between them
    assert {'kill', 'delete'} <= set(vars(simbody.Life)) and 'destroy' not in vars(simbody.Life)


def test_death_guard_bites():
    sources = health_sources()
    # a script action marking its thing dead itself
    act = dict(sources, **{'simact_object.py': sources['simact_object.py'] + '\n\ndef gone(b):\n    b.alive = False\n'})
    assert death_breaks(death_writes(act)) == [('simact_object.py', 'gone')]
    # a module deleting its thing past the host
    mod = 'engine/modules/sell.py'
    assert mod in sources
    sold = dict(sources, **{mod: sources[mod] + '\n\ndef gone(thing, t):\n    thing.deleted, thing.died_at = True, t\n'})
    assert death_breaks(death_writes(sold)) == [(mod, 'gone')]
    # a third entry into the shared part
    third = dict(sources, **{'simbody.py': sources['simbody.py'] + '\n\ndef sneak(life, w, b, g):\n    life._out(w, b, True, g)\n'})
    assert death_breaks(death_writes(third)) == [('simbody.py', 'sneak')]
    # the kill writing its own alive past _out
    bm = 'simbody.py'
    past = dict(sources, **{bm: sources[bm].replace('        self._out(world, b, False, garrison)\n',
                                                    '        b.alive = False\n', 1)})
    assert past[bm] != sources[bm] and death_breaks(death_writes(past)) == [(bm, 'Life.kill')]


def test_the_kernel_tests_run_in_full_without_the_model(tmp_path):
    if os.environ.get('CNV_KERNEL_INNER'):
        return
    env = {**os.environ, 'CNV_ENGINE_MODEL': str(tmp_path / 'nonexistent'), 'CNV_KERNEL_INNER': '1'}
    r = subprocess.run([sys.executable, '-X', 'utf8', '-m', 'pytest', '-q', '-p', 'no:cacheprovider', '-n', '0',
                        '-rs', str(Path(__file__))], cwd=ROOT, env=env, capture_output=True, text=True, timeout=600)
    tail = r.stdout[-2000:]
    assert r.returncode == 0, tail
    assert 'skipped' not in tail and 'passed' in tail, tail
