"""The readers of the simulator's source know the parts by their full names (ADR 0029 step 10-0, refactor line R2):
before step 10 moves sim*.py into experimental/cnv/engine/, the tools that read the source instead of importing it --
cnv/enginefiles.py (module name <-> file), simcoverage.sim_files / sim_code, testbench/affected_tests.py's import graph
-- already follow `import engine.world.base`, `from engine.objects import mend as simmend` and
`from engine.objects.mend import Mend`. A fake tree under tmp_path; nothing here moves a real file."""
import ast
import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CNV = ROOT / 'experimental' / 'cnv'


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


ef = _load('enginefiles', CNV / 'enginefiles.py')
sc = _load('simcoverage', CNV / 'simcoverage.py')
at = sys.modules.get('affected_tests') or _load('affected_tests', ROOT / 'experimental' / 'testbench' / 'affected_tests.py')

SIM = '''from engine.objects import mend as simmend
import engine.world.base as base
import simold


class Sim:
    def patch(self, frame):
        simmend.Mend().patch(self, frame)

    def lazy(self):
        from engine.orders.move import go
        return go()
'''
CNV_FILES = {
    'sim.py': SIM,
    'simproxy.py': 'import sim\n',
    'simshow.py': 'import sim\nSHOWN = "NotAPart"\n',
    'simold.py': 'OLD = "OldStyle"\n',
    'engine/__init__.py': '',
    'engine/objects/__init__.py': '',
    'engine/objects/mend.py': ('import engine.world.base\n\n\nclass Mend:\n    def patch(self, s, f):\n'
                               '        if "GENERIC_TOGGLE_STATE" in s.status:\n            return "MendThing"\n'),
    'engine/world/__init__.py': '',
    'engine/world/base.py': 'W = "WorldThing"\n',
    'engine/orders/__init__.py': '',
    'engine/orders/move.py': 'from engine.objects.mend import Mend\n\n\ndef go():\n    return "MoveThing"\n',
}
TEST_FILES = {
    'tests/test_mend.py': 'from engine.objects import mend\n\n\ndef test_it():\n    mend.Mend()\n',
    'tests/test_facade.py': 'import sim\n\n\ndef test_x():\n    sim.Sim().patch(1)\n\n\ndef test_y():\n    sim.Sim()\n',
}


def fake(tmp_path):
    cnv = tmp_path / 'experimental' / 'cnv'
    for rel, text in {**{f'experimental/cnv/{k}': v for k, v in CNV_FILES.items()}, **TEST_FILES}.items():
        p = tmp_path / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding='utf-8')
    return str(cnv)


def test_names_and_files_go_both_ways(tmp_path):
    cnv = fake(tmp_path)
    mend = ef.file_of('engine.objects.mend', cnv)
    assert Path(mend) == Path(cnv) / 'engine' / 'objects' / 'mend.py'
    assert ef.name_of(mend, cnv) == 'engine.objects.mend'
    assert ef.name_of(ef.file_of('engine.objects', cnv), cnv) == 'engine.objects'       # a package: its __init__
    assert ef.file_of('engine.objects.nothing', cnv) is None and ef.file_of('os', cnv) is None
    names = {ef.name_of(p, cnv) for p in ef.files(cnv)}
    assert {'sim', 'simproxy', 'simshow', 'simold', 'engine', 'engine.objects.mend', 'engine.world.base'} <= names


def test_full_name_imports_resolve_to_the_module_not_the_package(tmp_path):
    cnv = fake(tmp_path)
    tree = ast.parse(SIM)
    assert ef.imports(tree, cnv) == {'engine.objects.mend', 'engine.world.base', 'engine.orders.move', 'simold'}
    assert ef.imports(tree, cnv, packages=True) >= {'engine', 'engine.objects', 'engine.world', 'engine.orders'}
    assert ef.imports(ast.parse('from engine.objects.mend import Mend'), cnv) == {'engine.objects.mend'}
    assert ef.bindings(tree, cnv) == {'simmend': 'engine.objects.mend', 'base': 'engine.world.base',
                                      'simold': 'simold', }                  # `from engine.orders.move import go`: a name


def test_simcoverage_counts_the_parts_under_engine(tmp_path):
    cnv = fake(tmp_path)
    files = set(sc.sim_files(cnv))
    assert {'sim', 'simproxy', 'simold', 'engine.objects.mend', 'engine.world.base', 'engine.orders.move'} <= files
    assert 'simshow' not in files                                            # it imports sim: on top, not a part
    code = sc.sim_code(cnv)
    assert {'MendThing', 'WorldThing', 'MoveThing', 'OldStyle'} <= code and 'NotAPart' not in code


def test_affected_tests_picks_by_full_name_imports(tmp_path):
    fake(tmp_path)
    g = at.ImportGraph(str(tmp_path))
    mend = 'experimental/cnv/engine/objects/mend.py'
    assert mend in g.sim_files() and 'experimental/cnv/engine/orders/move.py' in g.sim_files()
    assert 'experimental/cnv/simshow.py' not in g.sim_files()
    assert g.handles()['engine.objects.mend'] == {'patch'}
    assert g.users(mend) == {'tests/test_mend.py', 'tests/test_facade.py::test_x'}
    src = at.Source(SIM)
    found, left = at.facade_parts(src, {1, 2, 3, 8}, g.part_names(src))     # two import lines, a forwarder
    assert found == {'engine.objects.mend': {'patch'}, 'engine.world.base': set(), 'simold': set()} and not left
