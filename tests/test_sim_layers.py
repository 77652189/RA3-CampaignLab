"""The simulator's layers (ADR 0029, docs/engine/sim-layers.md): guards that hold each block moved out of sim.py.

- Import direction: a layered module imports only layered modules of its own layer or below (rule 1); `sim` itself
  (the old class, on top of everything) is never imported by a layered module.
- World handle: a module that takes the world reaches only simworld.WORLD_API on it, and never names a Sim (rule 2).
- Frame order in one place: the frame loop's two orders name cells of one roster, and only simloop runs the scripts'
  engine step (rule 5).
- Field owners: a field a moved block owns is assigned only in that block's file (rule 3).

LAYER_OF grows by one entry per block moved (work/re/handoff-r.md 进度)."""
import ast
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CNV = ROOT / 'experimental' / 'cnv'

# module -> layer (0 world, 1 data, 2 object modules, 3 combat, 4 player systems, 5 unit orders, 6 scripts,
# 7 frame loop, 8 skirmish AI, 9 report)
LAYER_OF = {
    'simworld': 0,
    'simunits': 1,
    'simtopple': 2, 'simjet': 2, 'simcrush': 2,
    'simtech': 4,
    'simloop': 7,
}

# modules that take the world as an argument (rule 2): they reach it only through WORLD_API
WORLD_TAKERS = set()

# field -> the one file that may assign it (rule 3), for the blocks moved so far
FIELD_OWNER = {}


def _load(name):
    spec = importlib.util.spec_from_file_location(name, CNV / f'{name}.py')
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _tree(name):
    return ast.parse((CNV / f'{name}.py').read_text(encoding='utf-8'))


def _imports(tree):
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            yield from (a.name.split('.')[0] for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and not node.level:
            yield node.module.split('.')[0]


def import_breaks(layer_of=LAYER_OF):
    """(module, imported, why) for each import that breaks rule 1."""
    out = []
    for mod, layer in layer_of.items():
        for name in _imports(_tree(mod)):
            if not (CNV / f'{name}.py').exists() and not (CNV / name / '__init__.py').exists():
                continue                                   # the standard library, numpy, experimental/campaign
            if name not in layer_of:
                out.append((mod, name, 'not layered'))
            elif layer_of[name] > layer:
                out.append((mod, name, f'L{layer} imports L{layer_of[name]}'))
    return out


def world_breaks(takers=WORLD_TAKERS):
    api = _load('simworld').WORLD_API
    out = []
    for mod in takers:
        for node in ast.walk(_tree(mod)):
            if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name) and node.value.id == 'world' \
                    and node.attr not in api:
                out.append((mod, node.attr))
            if isinstance(node, ast.Name) and node.id in ('sim', 'Sim'):
                out.append((mod, node.id))
    return out


def owner_breaks(owners=FIELD_OWNER):
    """(file, field) for each assignment `<x>.field = / += / [k] =` outside the field's owner."""
    out = []
    for path in sorted(CNV.glob('sim*.py')):
        for node in ast.walk(ast.parse(path.read_text(encoding='utf-8'))):
            targets = node.targets if isinstance(node, ast.Assign) else \
                [node.target] if isinstance(node, (ast.AugAssign, ast.AnnAssign)) else []
            for t in targets:
                while isinstance(t, ast.Subscript):
                    t = t.value
                if isinstance(t, ast.Attribute) and t.attr in owners and path.stem != owners[t.attr]:
                    out.append((path.stem, t.attr))
    return out


def test_layered_modules_import_downward_only():
    assert not import_breaks()


def test_import_guard_bites():
    """Mutation check: a layer that imported one above it, or sim, would be caught."""
    assert ('simtech', 'simunits', 'L4 imports L5') in import_breaks({**LAYER_OF, 'simunits': 5})
    assert any(b[0] == 'simjet' and b[1] == 'simtopple' for b in import_breaks({**LAYER_OF, 'simtopple': 3}))


def test_world_takers_reach_only_the_world_api():
    assert not world_breaks()


def test_field_owners():
    assert not owner_breaks()


def test_frame_orders_share_one_roster():
    loop = _load('simloop')
    assert set(loop.FRAME) <= set(loop.CELLS) and set(loop.OLD) <= set(loop.CELLS)
    assert len(set(loop.FRAME)) == len(loop.FRAME) and len(set(loop.OLD)) == len(loop.OLD)
    assert loop.FRAME.index('tech') < loop.FRAME.index('scripts') < loop.FRAME.index('lose_health')
    assert loop.FRAME[-1] == 'deal'                    # damage last, after the frame's scripts (R6)
    for path in sorted(CNV.glob('sim*.py')):
        if path.stem != 'simloop':
            assert 'eng.step()' not in path.read_text(encoding='utf-8'), path.name
