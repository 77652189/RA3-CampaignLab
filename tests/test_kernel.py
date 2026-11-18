"""The kernel's guards (docs/engine/sim-modules.md 8, ADR 0031-0034; step K0 of the module plan): the kernel's own
rules (factory, schedule, Thing.find, sealed data), and

1. a module file imports no other module file, assigns only on itself and finds modules by interface;
2. the centre only shrinks (CENTER: sim.py lines, Sim methods, Body fields, simunits defs, cells not on the schedule);
3. no module-level mutable state and no `global` in the world's files (PROCESS_CACHES, today's exceptions, only
   shrinks);
4. two worlds in one process, advanced in turn, each record as when run alone;
5. every tag the factory registers has a module test by name;
6. the kernel has no dependency on the private model: no name of it in engine/**, imports only engine.* and the
   standard library, and its tests run in full with CNV_ENGINE_MODEL pointing nowhere.
Each guard has a mutation check (a synthetic breach it must catch)."""
import ast
import importlib.util
import io
import os
import subprocess
import sys
from pathlib import Path

from test_plans import small  # noqa: F401,I001  (puts experimental/cnv on the path)
import simrecord  # noqa: E402
import simsmall  # noqa: E402
from engine.kernel import factory, interfaces, module, schedule, world  # noqa: E402
from maps import probe_block  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
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

    def __init__(self, thing, data):
        super().__init__(thing, data)
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


def test_find_is_by_interface_and_body_is_one():
    t = T('X')
    t.modules = (Ticker(t, None), Mender(t, None))
    assert [type(m) for m in t.find(interfaces.Update)] == [Ticker]
    assert t.find(interfaces.Damage)[0].thing is t
    assert t.find(interfaces.Body) is None


def test_a_body_is_a_thing_with_no_modules_field_while_none_is_registered():
    s = simsmall.small_world([('a', APOC, 'Player_1', 0.0, 0.0)], model=False)
    b = s.bodies['a']
    assert isinstance(b, module.Thing) and b.modules == () and 'modules' not in vars(b)
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

CENTER = {'sim.py lines': 3640, 'Sim methods': 207, 'Body fields': 115, 'simunits defs': 154,
          'cells not on the schedule': 37}


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
    on = {c for c in frame if c in cells and any(isinstance(x, ast.Attribute) and x.attr == 'schedule'
                                                 for x in ast.walk(cells[c]))}
    return {'sim.py lines': len(sim_src.splitlines()),
            'Sim methods': sum(isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) for n in cls['Sim'].body),
            'Body fields': sum(isinstance(n, ast.AnnAssign) for n in cls['Body'].body),
            'simunits defs': sum(isinstance(n, ast.FunctionDef) for n in ast.parse(units_src).body),
            'cells not on the schedule': len(frame) - len(on)}


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
    loop_src = (CNV / 'simloop.py').read_text(encoding='utf-8').replace(
        "def autoheal(s, frame, tick):\n", "def autoheal(s, frame, tick):\n    s.world.schedule.run('autoheal', frame)\n", 1)
    assert center(loop_src=loop_src)['cells not on the schedule'] == now['cells not on the schedule'] - 1


# --- 3. no module-level mutable state -----------------------------------------------------------------------------

MUTATORS = _layers.MUTATORS | {'popitem', 'appendleft'}
CONTAINERS = {'dict', 'list', 'set', 'defaultdict', 'OrderedDict', 'Counter', 'deque'}
# today's process caches of read-only retail data (and the private model's loaders): only shrinks; a line goes when
# its cache moves into the template data port's instance
PROCESS_CACHES = {
    ('sim', '_MODEL'), ('simai', '_AI'), ('simproxy', '_PROXY'), ('simgarrison', '_memo'), ('simsweep', '_weapon_blocks'),
    *(('simunits', n) for n in (
        '_acquire', '_all_defines', '_command_powers', '_crush_memo', '_deposits', '_equivalent', '_fight',
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
    recs = [simrecord.Recorder(s, o) for s, o in zip(worlds, outs)]
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
            if isinstance(node, ast.Call) and getattr(node.func, 'attr', '') in ('spec_from_file_location', 'import_module'):
                out.append((name, ast.unparse(node.func)))
    return out


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


def test_the_kernel_tests_run_in_full_without_the_model(tmp_path):
    if os.environ.get('CNV_KERNEL_INNER'):
        return
    env = {**os.environ, 'CNV_ENGINE_MODEL': str(tmp_path / 'nonexistent'), 'CNV_KERNEL_INNER': '1'}
    r = subprocess.run([sys.executable, '-X', 'utf8', '-m', 'pytest', '-q', '-p', 'no:cacheprovider', '-n', '0',
                        '-rs', str(Path(__file__))], cwd=ROOT, env=env, capture_output=True, text=True, timeout=600)
    tail = r.stdout[-2000:]
    assert r.returncode == 0, tail
    assert 'skipped' not in tail and 'passed' in tail, tail
