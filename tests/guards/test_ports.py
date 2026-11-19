"""Readers read the world through the observation port (engine/ports/observe.py; module_plan P "适配器只导入
engine.ports"; R3 12b). First reader: simrecord, the frame record every pure move is judged by.

- simrecord imports from the simulator only engine.ports.*, except in run_task, the harness that makes the run
  (build / sim / retail / simai);
- outside run_task it holds no raw world: no name or argument `s`, `sim_`, `bodies`, no attribute of those or `eng`
  (the recorders get an Observe and read it).
A planted break (a raw import, a recorder reading self.s.bodies) turns each check red. (test_kernel's ADAPTERS is the
whole-file form, for a plug-in adapter; simrecord cannot join it: run_task makes the run.)

The other readers (READERS, READER_PARTS) are held to the same, outside their harness; and every file in experimental/
outside the simulator that uses a world maker is a reader or a row of EXEMPT, the explicit exemption table (file,
function or the whole file, why) -- R3 12c, the observation port's close.

Givers give orders through the command port (engine/ports/command.py; R3 13b): a giver moved onto it (GIVERS) calls no
order of the world's, touches no script event queue and writes no field an order sets, outside its harness."""
import ast
import importlib.util
import textwrap
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
CNV = ROOT / 'experimental' / 'cnv'
HARNESS = {'run_task'}                  # the functions that may make a run
RAW = {'s', 'sim_', 'bodies'}          # what holding the world itself looks like: names and arguments ...
RAW_ATTRS = RAW | {'eng', '_w'}         # ... and attributes (`eng` is also the script port's World argument name:
                                        # PortTap's methods take it, engine/ports/scripts.py; `_w` the world the
                                        # Observe holds: a reader going round the port through it)


def simulator_modules():
    """Top-level module names that are the simulator's (every .py and package in experimental/cnv)."""
    return {p.stem for p in CNV.glob('*.py')} | {p.name for p in CNV.iterdir() if (p / '__init__.py').exists()}


def _functions(tree):
    """node -> its qualified function name (None at module level or in a class body)."""
    where = {}

    def walk(node, prefix='', fn=None):
        for child in ast.iter_child_nodes(node):
            scope, name = prefix, fn
            if isinstance(child, ast.ClassDef):
                scope, name = prefix + child.name + '.', None
            elif isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                name = prefix + child.name
                scope = name + '.'
            where[child] = name
            walk(child, scope, name)
    walk(tree)
    return where


def import_breaks(src, sim=None, harness=HARNESS):
    """(line, module) for each simulator import outside HARNESS that is not engine.ports.*."""
    sim = simulator_modules() if sim is None else sim
    tree = ast.parse(src)
    where = _functions(tree)
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names = [a.name for a in node.names]
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            names = [node.module]
        else:
            continue
        for n in names:
            if n.split('.')[0] in sim and not (n == 'engine.ports' or n.startswith('engine.ports.')) \
                    and where.get(node) not in harness:
                out.append((node.lineno, n))
    return out


def raw_breaks(src, harness=HARNESS, *, data_s=()):
    """(line, name) for each raw-world name or attribute outside HARNESS."""
    tree = ast.parse(src)
    where = _functions(tree)
    out = []
    for node in ast.walk(tree):
        if where.get(node) in harness:
            continue
        if isinstance(node, ast.Name) and node.id in RAW and not (node.id == 's' and where.get(node) in data_s):
            out.append((node.lineno, node.id))
        elif isinstance(node, ast.Attribute) and node.attr in RAW_ATTRS:
            out.append((node.lineno, node.attr))
        elif isinstance(node, ast.arg) and node.arg in RAW:
            out.append((node.lineno, node.arg))
    return out


def _src():
    return (CNV / 'simrecord.py').read_text(encoding='utf-8')


EXP = ROOT / 'experimental'
AUTOPLAY = EXP / 'autoplay'
GAME = EXP / 'simui' / 'game.py'
PLAYCHECK = CNV / 'playcheck.py'
MAPPAGE = EXP / 'mappage' / 'mappage.py'

# The exemption table (R3 12c, the observation port's close): everything in experimental/ that may still touch the
# simulator's world outside the port, one row each -- (file, the function, or None: the whole file -- for a
# READER_PARTS file, the rest of it --, why). The readers' harness sets below are these rows; a file outside the
# simulator that uses a world maker (WORLD_MAKERS) and is neither a reader nor here turns test_every_world_user_is_listed
# red. So "the readers that go round the port" = the None rows of this table.
EXEMPT = [
    (CNV / 'simrecord.py', 'run_task', '造一局（build / sim / retail / simai）；记录器只拿 Observe'),
    (CNV / 'simshow.py', 'attach', '把 Show 挂上一局（注入 CIV、通报动作、mmss：端口不许导入模拟器）'),
    (CNV / 'simshow.py', 'play', '造局并跑'),
    (CNV / 'simshow.py', 'run', '造局并跑'),
    (CNV / 'simshow.py', 'main', '命令行：造局'),
    (AUTOPLAY / 'autoplay.py', 'load', '造局'),
    (AUTOPLAY / 'autoplay.py', 'attach', '唯一拿世界的：View / Orders 从这里拿 Observe / Commands'),
    (AUTOPLAY / 'autoplay.py', 'tick', '驱动一局'),
    (AUTOPLAY / 'autoplay.py', 'play', '造局并驱动'),
    (AUTOPLAY / 'autoplay.py', 'replay', '造局并驱动'),
    (AUTOPLAY / 'autoplay.py', 'main', '命令行：造局'),
    (CNV / 'offline.py', 'walk', '造走查那局并驱动，返回 Observe'),
    (CNV / 'offline.py', 'spelt', '把 sim.mmss / sim.HIGH_STEP 交给报告'),
    (CNV / 'offline.py', 'main', '命令行：造局'),
    (CNV / 'graybox.py', 'main', '命令行：造局'),
    (CNV / 'graybox_cards.py', 'world', '造 A4 那局'),
    (CNV / 'graybox_cards.py', 'main', '命令行：造局'),
    (CNV / 'simbench.py', 'play', '造局、摆路点（derrick 的 Derrick k），返回 Observe'),
    (CNV / 'simchecks.py', 'play', '造局，返回 Observe'),
    (GAME, None, 'Session 跑 tick、跳阶段（驱动；下令经命令端口，GIVER_PARTS 守）；replay 给新的一局喂回放记录；'
                 '读者是 Play / Picture / phase_flags / key_times'),
    (PLAYCHECK, 'read', '造局，返回 Observe'),
    (PLAYCHECK, 'Compiler.play', '只用 sim.parse_script 解析打法的写法'),
    (MAPPAGE, 'simulate', '造局，返回 Observe'),
    (CNV / 'simbench_peak.py', None, '测速：自己驱动整局、下令，等命令端口'),
    (CNV / 'simcoverage.py', None, '"模拟器不认识什么"是模拟器的内部报告，不归观测端口'),
    (CNV / 'simai.py', None, '归 AI 端口'),
    (CNV / 'simproxy.py', None, '归命令端口'),
    (CNV / 'retail.py', None, '造原版关的局（同 build，造局的一边）'),
    (CNV / 'simsmall.py', None, '规则测试的小世界：造局'),
    (CNV / 'simstatic.py', None, '静态半边：只用 sim.CMP 比较表和 sim.Ground 地面，不读跑着的世界'),
    (AUTOPLAY / 'levels.py', None, '只读 simproxy 的常量 LEADS / ESCORT（任务数据）'),
]


def harness(path):
    return {fn for p, fn, _ in EXEMPT if p == path and fn}


# The other readers, one a step (R3, sim_split/obs_port.md): file -> the mission-data modules it may import beside
# engine.ports (its harness is its EXEMPT rows). simshow's: ctx (the contract's timings), model (the camera's picture
# sizes), strip (reads the Show's own records) -- none holds a world. players may import simunits (template data);
# offline's glossary (names) and simunits are data; graybox / graybox_cards read what walk returns through offline's
# numbers. simbench / simchecks report a run's outcome (log, series, unknown, ending, ending_line) off its Observe;
# simbench's build is the check's mission data.
READERS = {
    CNV / 'simrecord.py': set(),
    CNV / 'simshow.py': {'ctx', 'model', 'strip'},
    AUTOPLAY / 'autoplay.py': set(),
    AUTOPLAY / 'players.py': {'simunits'},
    CNV / 'offline.py': {'glossary', 'simunits'},
    CNV / 'graybox.py': {'offline', 'simunits'},
    CNV / 'graybox_cards.py': {'glossary', 'graybox', 'offline', 'simunits'},
    CNV / 'simbench.py': {'build'},
    CNV / 'simchecks.py': {'build'},
    PLAYCHECK: {'build', 'model', 'parts', 'simunits'},
    MAPPAGE: {'contract', 'parts', 'resources'},
}

# These functions use the local name `s` for mission scripts, map sites, or preview steps.
DATA_S = {
    PLAYCHECK: {'phase_flags', 'Compiler.who', 'Compiler.actions'},
    MAPPAGE: {'locate', 'guides', 'export', 'nearest', '_terrain_line', 'pull', 'apply_preview'},
}


def spec(path):
    """(its harness, the modules it may import) for a whole-file reader."""
    return harness(path), READERS[path]


# Readers that are one class or function of a bigger file (the rest of the file is a None row of EXEMPT): (file, name,
# the mission-data modules it may import). simui's game.py: what the page draws is the Picture's, the voices and the
# replay record the Play's, and the stage flags / the key moments are read off the compiled mission / a run's Observe.
READER_PARTS = [(GAME, 'Play', set()), (GAME, 'Picture', {'simunits'}), (GAME, 'phase_flags', set()),
                (GAME, 'key_times', set())]

# What makes or hands out a world (a sim.Sim): a file outside the simulator that imports one of these, or loads one by
# file (`_load('sim', ...)`), touches the world and must be a reader or in EXEMPT.
WORLD_MAKERS = {'sim', 'simai', 'simproxy', 'retail', 'simsmall'}
_spec = importlib.util.spec_from_file_location('test_sim_layers_registry_p', ROOT / 'tests' / 'test_sim_layers.py')
_layers = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_layers)
SIMULATOR = set(_layers.LAYER_OF) | {'sim'}     # the simulator's own files (they hold the world by design)


LOADERS = {'_load', 'load', 'import_module', 'spec_from_file_location', '__import__'}


def _called(call):
    f = call.func
    return f.id if isinstance(f, ast.Name) else f.attr if isinstance(f, ast.Attribute) else None


def uses_world(src):
    """True when the source imports a world maker or loads one by name or file (a loader call whose first argument
    is its module name)."""
    for node in ast.walk(ast.parse(src)):
        if isinstance(node, ast.Import):
            names = [a.name for a in node.names]
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            names = [node.module]
        elif isinstance(node, ast.Call) and _called(node) in LOADERS and node.args \
                and isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, str):
            names = [node.args[0].value]
        else:
            continue
        if any(n.split('.')[0] in WORLD_MAKERS for n in names):
            return True
    return False


def outside_files():
    """experimental/'s .py files that are not the simulator's own."""
    out = []
    for p in sorted(EXP.rglob('*.py')):
        if 'archive' in p.relative_to(EXP).parts or (CNV / 'engine') in p.parents:
            continue
        if p.parent == CNV and p.stem in SIMULATOR:
            continue
        out.append(p)
    return out


def unlisted(sources):
    """The files of {path: source} that use a world maker and are neither a reader nor in EXEMPT."""
    listed = set(READERS) | {p for p, _, _ in READER_PARTS} | {p for p, _, _ in EXEMPT}
    return sorted(p.relative_to(ROOT).as_posix() for p, src in sources.items() if p not in listed and uses_world(src))


def sim_breaks(src, harness):
    """(line, 'sim') for each use of the simulator module inside a function outside HARNESS (a file that loads it at
    module level, as autoplay.py does for its harness, may; its readers may not reach into it)."""
    tree = ast.parse(src)
    where = _functions(tree)
    return [(n.lineno, 'sim') for n in ast.walk(tree)
            if isinstance(n, ast.Name) and n.id == 'sim' and where.get(n) is not None and where.get(n) not in harness]


def reader_breaks(src, harness, allowed, *, data_s=()):
    sim = simulator_modules() - set(allowed)
    return import_breaks(src, sim, harness) + raw_breaks(src, harness, data_s=data_s) + sim_breaks(src, harness)


def part_src(path, name):
    """The source of a top-level class or function of a file, or of a class's method ('Class.method'), dedented."""
    src = path.read_text(encoding='utf-8')
    body = ast.parse(src).body
    for part in name.split('.'):
        node = next(n for n in body if isinstance(n, (ast.ClassDef, ast.FunctionDef)) and n.name == part)
        body = node.body
    return textwrap.dedent(ast.get_source_segment(src, node, padded=True))


def test_the_other_readers_read_only_the_port():
    for f, allowed in READERS.items():
        breaks = reader_breaks(f.read_text(encoding='utf-8'), harness(f), allowed, data_s=DATA_S.get(f, ()))
        assert breaks == [], (f.name, breaks)
    for path, name, allowed in READER_PARTS:
        assert reader_breaks(part_src(path, name), set(), allowed) == [], (path.name, name)


def test_every_world_user_is_listed():
    """Outside the exemption table nothing in experimental/ touches the world but through the port."""
    assert unlisted({p: p.read_text(encoding='utf-8') for p in outside_files()}) == []


def test_the_exemption_table_is_whole():
    """Every row names a file that is there and a function that is in it, with a reason; a whole-file reader has no
    None row (the whole file would be exempt), a READER_PARTS file has one (its rest)."""
    parts = {p for p, _, _ in READER_PARTS}
    for p, fn, why in EXEMPT:
        assert p.exists() and why, (p, fn)
        if fn:
            assert fn in set(_functions(ast.parse(p.read_text(encoding='utf-8'))).values()), (p.name, fn)
        else:
            assert p not in READERS, p.name
    assert all(any(p == q and fn is None for q, fn, _ in EXEMPT) for p in parts)


def test_a_world_user_outside_the_table_is_found():
    planted = CNV / 'planted_reader.py'
    assert unlisted({planted: 'def f():\n    import sim\n    return sim.Sim(None).bodies\n'})
    assert unlisted({planted: "x = _load('sim', 'sim.py')\n"})
    assert unlisted({planted: 'from simproxy import LEADS\n'})
    assert not unlisted({planted: 'import build\n'})
    assert unlisted({planted: "import importlib\nm = importlib.import_module('simai')\n"})
    assert not unlisted({planted: "SIM = 'sim.py'\n"})
    assert not unlisted({planted: "ok = rel.startswith('sim')\n"})
    peak = CNV / 'simbench_peak.py'
    saved = list(EXEMPT)
    try:
        EXEMPT[:] = [r for r in EXEMPT if r[0] != peak]
        assert unlisted({peak: peak.read_text(encoding='utf-8')}) == ['experimental/cnv/simbench_peak.py']
    finally:
        EXEMPT[:] = saved
    assert unlisted({peak: peak.read_text(encoding='utf-8')}) == []


def test_planted_breaks_in_the_other_readers_are_found():
    harness, allowed = spec(CNV / 'simshow.py')
    src = (CNV / 'simshow.py').read_text(encoding='utf-8')
    assert reader_breaks(src + '\nimport sim\n', harness, allowed)
    assert reader_breaks(src.replace('for b in obs.living()', 'for b in self.obs._w.bodies.values()'), harness, allowed)
    assert not reader_breaks(src + '\ndef run():\n    import sim\n', harness, allowed)
    harness, allowed = spec(AUTOPLAY / 'autoplay.py')
    src = (AUTOPLAY / 'autoplay.py').read_text(encoding='utf-8')
    assert reader_breaks(src.replace('obs = self.obs', 's = self.obs'), harness, allowed)
    assert reader_breaks(src.replace('obs.fresh_sight()', 'sim.CIV'), harness, allowed)
    harness, allowed = spec(AUTOPLAY / 'players.py')
    src = (AUTOPLAY / 'players.py').read_text(encoding='utf-8')
    assert reader_breaks(src + '\nimport sim\n', harness, allowed)
    assert reader_breaks(src.replace('obs.can_hit(w, f.body)', 'view.s.can_hit(w, f.body)'), harness, allowed)
    harness, allowed = spec(CNV / 'offline.py')
    src = (CNV / 'offline.py').read_text(encoding='utf-8')
    assert reader_breaks(src + '\nimport sim\n', harness, allowed)
    assert reader_breaks(src.replace('obs.ground_z(vx, vy)', 's.ground.z(vx, vy)'), harness, allowed)
    assert reader_breaks(src.replace("'段：' + '，'.join(f'{n} {mmss(t)}'", "'段：' + '，'.join(f'{n} {sim.mmss(t)}'"),
                         harness, allowed)
    harness, allowed = spec(CNV / 'graybox_cards.py')
    src = (CNV / 'graybox_cards.py').read_text(encoding='utf-8')
    assert reader_breaks(src.replace("wall = obs.specimen(", "wall = obs._w.bodies.get("), harness, allowed)
    assert reader_breaks(src + '\nimport plan\n', harness, allowed)
    play = part_src(GAME, 'Play')
    assert raw_breaks(play.replace('obs = self.obs', 's = self.obs'))
    picture = part_src(GAME, 'Picture')
    assert reader_breaks(picture.replace('clock=mmss(t)', 'clock=sim.mmss(t)'), set(), {'simunits'})
    assert reader_breaks(picture.replace('shape = obs.blocks(b)', 'shape = obs._w.blocks(b)'), set(), {'simunits'})
    assert reader_breaks(picture.replace('import simunits', 'import simunits\n        import sim'), set(), {'simunits'})
    assert reader_breaks(picture.replace('readings = ex.readings()', 'readings = self.s.executor.readings()'),
                         set(), {'simunits'})
    assert reader_breaks(part_src(GAME, 'key_times').replace('ending = obs.ending()', 's = obs; ending = s.ending'),
                         set(), set())
    # the outcome readers (12c): a raw read, the simulator reached in a reader function, a run made outside play
    harness, allowed = spec(CNV / 'simbench.py')
    src = (CNV / 'simbench.py').read_text(encoding='utf-8')
    for planted in (src.replace('in obs.series() if', 'in obs._w.series if'),
                    src.replace("b = obs.thing(m.role('engineer').name)", "b = obs._w.bodies[m.role('engineer').name]"),
                    src.replace('    import build\n    if check', '    import build\n    import sim\n    if check')):
        assert planted != src and reader_breaks(planted, harness, allowed)
    harness, allowed = spec(CNV / 'simchecks.py')
    src = (CNV / 'simchecks.py').read_text(encoding='utf-8')
    planted = src.replace('ending = obs.ending()', 's = obs; ending = s.ending')
    assert planted != src and reader_breaks(planted, harness, allowed)
    readings = part_src(PLAYCHECK, 'readings')
    assert reader_breaks(readings.replace('for sec, v in obs.series()', 'for sec, v in obs._w.series'), set(), set())
    timeline = part_src(MAPPAGE, 'timeline')
    planted = timeline.replace('obs = simulate(name, script)',
                               "sim = _load('sim', CNV)\n    obs = sim.simulate(name, '', script)")
    assert planted != timeline and reader_breaks(planted, set(), set())


def test_simrecord_imports_only_the_ports():
    assert import_breaks(_src()) == []


def test_simrecord_holds_no_raw_world():
    assert raw_breaks(_src()) == []


def test_planted_breaks_are_found():
    src = _src()
    assert import_breaks(src + '\nimport sim\n')
    assert import_breaks(src + '\ndef f():\n    from engine.kernel import module\n')
    assert not import_breaks(src + '\ndef run_task():\n    import sim\n')
    planted = src.replace("parts = [f'{where} t={o.t!r}']", "parts = [f'{where} t={o.t!r}'] + list(self.s.bodies)")
    assert planted != src and raw_breaks(planted)
    assert raw_breaks(src + '\ndef g(s):\n    return 1\n')
    assert raw_breaks(src + '\ndef h(x):\n    return x.eng.frame\n')


# The givers moved onto the command port (R3 13b: autoplay's Orders and the players; simui, the plays, the script
# actions, simproxy and simai follow, cmd_port.md). What giving an order round the port looks like: a call of the
# world's order methods, the script event queue, or a write of a field an order sets.
ORDER_CALLS = {'order_move', 'order_group', 'order_attack', 'order_capture', 'order_build', 'order_guard',
               'order_power', 'order_transform', 'order_stop', 'order_follow', 'order_unpack', 'sell', 'stand', 'send',
               'happen', 'parse_script', 'flee_start', 'hunt_due', 'drop_goal', 'set_goal'}
ORDER_QUEUES = {'events', 'anchored'}
ORDER_FIELDS = {'goal', 'path', 'dest', 'move_to', 'mode', 'stance', 'hold_fire', 'hold_paused', 'ground_fire', 'face',
                'ai_acquire', 'follow', 'engaged'}
GIVERS = [AUTOPLAY / 'autoplay.py', AUTOPLAY / 'players.py']


def giver_breaks(src, harness):
    """(line, name) for each order given round the port outside HARNESS."""
    tree = ast.parse(src)
    where = _functions(tree)
    out = []
    for node in ast.walk(tree):
        if where.get(node) in harness:
            continue
        if isinstance(node, ast.Call) and _called(node) in ORDER_CALLS:
            out.append((node.lineno, _called(node)))
        elif isinstance(node, ast.Attribute) and node.attr in ORDER_QUEUES:
            out.append((node.lineno, node.attr))
        elif isinstance(node, ast.Attribute) and node.attr in ORDER_FIELDS and isinstance(node.ctx, (ast.Store, ast.Del)):
            out.append((node.lineno, node.attr))
    return out


# Givers that are one class of a bigger file (R3 13c): simui's Session -- the page's clicks and typed lines are posted
# through the port, a stage jump's hand-over drops the queue through it (game.replay, the harness, feeds a fresh run);
# Sim.happen -- a script line's player order (派 走 攻击 放 占领 X 进 Y 生产 买) is the port's do; what it still does
# itself is the god's hand (摧毁 删除 血量 打 one-name 占领 旗标 造), no order.
GIVER_PARTS = [(GAME, 'Session'), (CNV / 'sim.py', 'Sim.happen')]
# Script action files whose orders go through the port (R3 13d), with the functions that are no order: a teleport and
# the AI hand-over drop the unit's order (stand) as the god's hand.
SCRIPT_GIVERS = {CNV / 'simact_order.py': {'unit_teleport_to_waypoint', 'unit_ai_transfer'}}


def test_the_givers_give_through_the_command_port():
    for f in GIVERS:
        assert giver_breaks(f.read_text(encoding='utf-8'), harness(f)) == [], f.name
    for path, name in GIVER_PARTS:
        assert giver_breaks(part_src(path, name), set()) == [], (path.name, name)
    for path, gods_hand in SCRIPT_GIVERS.items():
        assert giver_breaks(path.read_text(encoding='utf-8'), gods_hand) == [], path.name


def test_planted_orders_in_a_script_action_are_found():
    f = CNV / 'simact_order.py'
    src = f.read_text(encoding='utf-8')
    for old, new in (("    _order(sim, 'stop', [a[0]])\n", "    sim.order_stop(sim.body(a[0]))\n"),
                     ("        _order(sim, 'stance', [a[0]], ('stance', int(a[1])))\n",
                      "        b.stance = int(a[1])\n"),
                     ("        _order(sim, 'face', [a[0]], place=a[1])\n", "        b.face = 0.0\n")):
        planted = src.replace(old, new)
        assert planted != src and giver_breaks(planted, SCRIPT_GIVERS[f]), new


def test_planted_orders_in_a_giver_part_are_found():
    src = part_src(GAME, 'Session')
    for old, new in (('self.commands.drop_pending()', 's.events.clear()'),
                     ('got = self.commands.post_line(text)', 'got = sim.parse_script(text)'),
                     ('self.commands.post(cmd, s.t)', 'self.s.order_move(cmd, cmd.place, True)')):
        planted = src.replace(old, new)
        assert planted != src and giver_breaks(planted, set())
    src = part_src(CNV / 'sim.py', 'Sim.happen')
    for old, new in (('        self.commands.do(cmd)\n', '        self.order_move(rest[0], rest[1], True)\n'),
                     ("    elif verb == '旗标':\n", "    elif verb == '停':\n        b.goal = None\n"
                                                   "    elif verb == '旗标':\n")):
        planted = src.replace(old, new)
        assert planted != src and giver_breaks(planted, set())


def test_planted_orders_round_the_port_are_found():
    f = AUTOPLAY / 'autoplay.py'
    src = f.read_text(encoding='utf-8')
    for planted in (src.replace('        self.commands.post_line(line)\n',
                                '        self.commands.post_line(line)\n        self.view.obs.world.events.append(1)\n'),
                    src.replace("        time = num(self.view.obs.t)\n",
                                "        time = num(self.view.obs.t)\n        self.view.w.order_move(b, p, True)\n"),
                    src.replace("        self.memo[b.name] = key\n",
                                "        self.memo[b.name] = key\n        b.goal = None\n")):
        assert planted != src and giver_breaks(planted, harness(f))
    assert not giver_breaks(src + '\ndef tick(s):\n    s.events.sort()\n', harness(f))
