"""Readers read the world through the observation port (engine/ports/observe.py; module_plan P "适配器只导入
engine.ports"; R3 12b). First reader: simrecord, the frame record every pure move is judged by.

- simrecord imports from the simulator only engine.ports.*, except in run_task, the harness that makes the run
  (build / sim / retail / simai);
- outside run_task it holds no raw world: no name or argument `s`, `sim_`, `bodies`, no attribute of those or `eng`
  (the recorders get an Observe and read it).
A planted break (a raw import, a recorder reading self.s.bodies) turns each check red. (test_kernel's ADAPTERS is the
whole-file form, for a plug-in adapter; simrecord cannot join it: run_task makes the run.)"""
import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
CNV = ROOT / 'experimental' / 'cnv'
HARNESS = {'run_task'}                  # the functions that may make a run
RAW = {'s', 'sim_', 'bodies'}          # what holding the world itself looks like: names and arguments ...
RAW_ATTRS = RAW | {'eng'}               # ... and attributes (`eng` is also the script port's World argument name:
                                        # PortTap's methods take it, engine/ports/scripts.py)


def simulator_modules():
    """Top-level module names that are the simulator's (every .py and package in experimental/cnv)."""
    return {p.stem for p in CNV.glob('*.py')} | {p.name for p in CNV.iterdir() if (p / '__init__.py').exists()}


def _functions(tree):
    """node -> the name of the top-level function / method it sits in (None at module level or in a class body)."""
    where = {}

    def walk(node, fn):
        for child in ast.iter_child_nodes(node):
            name = child.name if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)) else fn
            where[child] = name
            walk(child, name)
    walk(tree, None)
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


def raw_breaks(src, harness=HARNESS):
    """(line, name) for each raw-world name or attribute outside HARNESS."""
    tree = ast.parse(src)
    where = _functions(tree)
    out = []
    for node in ast.walk(tree):
        if where.get(node) in harness:
            continue
        if isinstance(node, ast.Name) and node.id in RAW:
            out.append((node.lineno, node.id))
        elif isinstance(node, ast.Attribute) and node.attr in RAW_ATTRS:
            out.append((node.lineno, node.attr))
        elif isinstance(node, ast.arg) and node.arg in RAW:
            out.append((node.lineno, node.arg))
    return out


def _src():
    return (CNV / 'simrecord.py').read_text(encoding='utf-8')


# The other readers, one a step (R3, sim_split/obs_port.md): file -> (its harness: the functions that make the run or
# hang the reader on it, the mission-data modules it may import beside engine.ports). simshow's: ctx (the contract's
# timings), model (the camera's picture sizes), strip (reads the Show's own records) -- none holds a world.
AUTOPLAY = ROOT / 'experimental' / 'autoplay'
READERS = {
    CNV / 'simshow.py': ({'attach', 'play', 'run', 'main'}, {'ctx', 'model', 'strip'}),
    # the auto player: attach / tick / play / replay make and drive the run (Orders' lines go out through attach's
    # post, a function inside attach); the View, Orders, finish and the players read Observe. players may import
    # simunits (template data).
    AUTOPLAY / 'autoplay.py': ({'load', 'attach', 'post', 'tick', 'play', 'replay', 'main'}, set()),
    AUTOPLAY / 'players.py': (set(), {'simunits'}),
}
# Readers that are one class of a bigger file (the rest of the file drives the run): (file, class).
READER_CLASSES = [(ROOT / 'experimental' / 'simui' / 'game.py', 'Play')]


def sim_breaks(src, harness):
    """(line, 'sim') for each use of the simulator module inside a function outside HARNESS (a file that loads it at
    module level, as autoplay.py does for its harness, may; its readers may not reach into it)."""
    tree = ast.parse(src)
    where = _functions(tree)
    return [(n.lineno, 'sim') for n in ast.walk(tree)
            if isinstance(n, ast.Name) and n.id == 'sim' and where.get(n) is not None and where.get(n) not in harness]


def reader_breaks(src, harness, allowed):
    sim = simulator_modules() - set(allowed)
    return import_breaks(src, sim, harness) + raw_breaks(src, harness) + sim_breaks(src, harness)


def class_src(path, name):
    src = path.read_text(encoding='utf-8')
    node = next(n for n in ast.parse(src).body if isinstance(n, ast.ClassDef) and n.name == name)
    return ast.get_source_segment(src, node)


def test_the_other_readers_read_only_the_port():
    for f, (harness, allowed) in READERS.items():
        assert reader_breaks(f.read_text(encoding='utf-8'), harness, allowed) == [], f.name
    for path, name in READER_CLASSES:
        src = class_src(path, name)
        assert import_breaks(src) == [] and raw_breaks(src) == [], (path.name, name)


def test_planted_breaks_in_the_other_readers_are_found():
    harness, allowed = READERS[CNV / 'simshow.py']
    src = (CNV / 'simshow.py').read_text(encoding='utf-8')
    assert reader_breaks(src + '\nimport sim\n', harness, allowed)
    assert reader_breaks(src.replace('for b in obs.living()', 'for b in self.obs._w.bodies.values()'), harness, allowed)
    assert not reader_breaks(src + '\ndef run():\n    import sim\n', harness, allowed)
    harness, allowed = READERS[AUTOPLAY / 'autoplay.py']
    src = (AUTOPLAY / 'autoplay.py').read_text(encoding='utf-8')
    assert reader_breaks(src.replace('obs = self.obs', 's = self.obs'), harness, allowed)
    assert reader_breaks(src.replace('obs.fresh_sight()', 'sim.CIV'), harness, allowed)
    harness, allowed = READERS[AUTOPLAY / 'players.py']
    src = (AUTOPLAY / 'players.py').read_text(encoding='utf-8')
    assert reader_breaks(src + '\nimport sim\n', harness, allowed)
    assert reader_breaks(src.replace('obs.can_hit(w, f.body)', 'view.s.can_hit(w, f.body)'), harness, allowed)
    play = class_src(*READER_CLASSES[0])
    assert raw_breaks(play.replace('obs = self.obs', 's = self.obs'))


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
