"""The affected-tests picker by import (ADR 0029 consequence 3, "done" (a)): a change to one of the simulator's files
picks the tests that import it, or that test the Sim facade by a name leading to it -- not every test that once ran
it (the coverage map was recorded before the blocks moved out of sim.py). Fake trees under tmp_path, plus two checks on
the real tree (the simulator's files agree with simcoverage; simheal picks its own rule test)."""
import importlib.util
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location('affected_tests', ROOT / 'experimental' / 'testbench' / 'affected_tests.py')
at = sys.modules['affected_tests'] = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(at)

SIM = '''import simleaf
import simother
from simconst import LAG


class Sim:
    def __init__(self):
        self.heal = simleaf.Heal()

    def autoheal(self, frame):
        """simleaf.Heal.autoheal (L2)."""
        self._leaf().autoheal(self, frame)

    def _leaf(self):
        return simleaf.Heal()

    def step(self, frame):
        a = 1
        b = simother.go(a)
        c = b + 1
        d = c + 1
        return d
'''
FILES = {
    'experimental/cnv/sim.py': SIM,
    'experimental/cnv/simproxy.py': 'import sim\n',
    'experimental/cnv/simleaf.py': 'class Heal:\n    def autoheal(self, w, f):\n        return f\n',
    'experimental/cnv/simother.py': 'import simleaf\n\ndef go(a):\n    return a\n',
    'experimental/cnv/simconst.py': 'LAG = 3\n',
    'experimental/cnv/simsmall.py': 'import sim\n',
    'experimental/cnv/simshow.py': 'import sim\nimport simleaf\n',            # sits on top: imports sim itself
    'tests/test_plans.py': 'import simsmall\n',
    'tests/test_leaf.py': 'import simleaf\n\ndef test_a():\n    pass\n',
    'tests/test_by_file.py': "import importlib.util\nS = importlib.util.spec_from_file_location('o', 'experimental/cnv/simother.py')\n",
    'tests/test_facade.py': ('from test_plans import simsmall\n\n\ndef test_heals(s):\n    s.heal.autoheal(s, 0)\n\n\n'
                             'def test_steps(s):\n    s.step(0)\n\n\nclass TestMore:\n    def test_x(self, s):\n'
                             '        s.autoheal(1)\n'),
    'tests/test_helper_names.py': 'import sim\n\n\ndef helper(s):\n    s.autoheal(0)\n\n\ndef test_b():\n    helper(None)\n',
    'tests/test_replay.py': 'import sim\n\n\ndef test_whole_game():\n    sim.Sim().run()\n',
}


def tree(tmp_path):
    for rel, text in FILES.items():
        p = tmp_path / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding='utf-8')
    return at.ImportGraph(str(tmp_path))


def test_sim_files_are_the_run_ends_and_the_parts_they_import(tmp_path):
    g = tree(tmp_path)
    assert {p.rsplit('/', 1)[1] for p in g.sim_files()} == {
        'sim.py', 'simproxy.py', 'simleaf.py', 'simother.py', 'simconst.py'}     # not simsmall / simshow: they import sim


def test_importers_do_not_walk_through_the_facade(tmp_path):
    g = tree(tmp_path)
    leaf = 'experimental/cnv/simleaf.py'
    assert g.importers(leaf) == {'tests/test_leaf.py', 'tests/test_by_file.py'}  # test_by_file via simother (a .py string)
    assert 'tests/test_replay.py' not in g.importers(leaf)                      # reaches simleaf only through sim
    assert g.facade_tests() == {'tests/test_facade.py', 'tests/test_helper_names.py', 'tests/test_replay.py',
                                'tests/test_plans.py'}


def test_handles_are_forwarders_and_attributes(tmp_path):
    g = tree(tmp_path)
    h = g.handles()
    assert h['simleaf'] == {'heal', 'autoheal', '_leaf'}
    assert 'step' not in h.get('simother', ())                                  # too long to be a forwarder
    assert h['simconst'] == {'LAG'}


def test_users_pick_single_tests_and_whole_files_for_helpers(tmp_path):
    g = tree(tmp_path)
    assert g.users('experimental/cnv/simleaf.py') == {
        'tests/test_leaf.py', 'tests/test_by_file.py',
        'tests/test_facade.py::test_heals', 'tests/test_facade.py::TestMore::test_x',
        'tests/test_helper_names.py'}                                           # named in a helper: the whole file


def test_facade_parts_sorts_forwarders_imports_and_code_left_in_sim():
    src = at.Source(SIM)
    parts = {'simleaf', 'simother', 'simconst'}
    lines = SIM.splitlines()
    fwd = lines.index('        self._leaf().autoheal(self, frame)') + 1
    body = lines.index('        c = b + 1') + 1
    found, left = at.facade_parts(src, {1, 3, fwd, body}, parts)
    assert found == {'simleaf': {'autoheal'}, 'simconst': {'LAG'}}
    assert left == {body}


def test_pick_a_forwarder_change_by_import_and_unmoved_code_by_coverage(tmp_path):
    g = tree(tmp_path)
    src = at.Source(SIM)
    lines = SIM.splitlines()
    fwd = lines.index('        self._leaf().autoheal(self, frame)') + 1
    body = lines.index('        c = b + 1') + 1
    seen = []
    tests, why, fell = at.pick(None, [(at.FACADE, at.FACADE, [(fwd, 1, fwd, 1)], False)], {}, {},
                               lambda p: seen.append(p) or set(), g, (src, src), decided := [])
    assert tests == {'tests/test_leaf.py', 'tests/test_by_file.py', 'tests/test_facade.py::test_heals',
                     'tests/test_facade.py::TestMore::test_x', 'tests/test_helper_names.py'}    # + those naming .autoheal
    assert decided == [] and seen == []
    tests, why, fell = at.pick(None, [(at.FACADE, at.FACADE, [(body, 1, body, 1)], False)], {}, {},
                               lambda p: {'tests/test_replay.py'}, g, (src, src), decided)
    assert tests == {'tests/test_replay.py'} and decided == [at.FACADE]        # code still in sim.py: the old way


def test_pick_a_part_change_and_a_part_nobody_imports(tmp_path):
    g = tree(tmp_path)
    changes = [('experimental/cnv/simleaf.py', 'experimental/cnv/simleaf.py', [(2, 1, 2, 1)], False)]
    tests, why, fell = at.pick(None, changes, {}, {}, lambda p: set(), g, (None, None), decided := [])
    assert 'tests/test_leaf.py' in tests and 'tests/test_replay.py' not in tests and decided == []
    assert why['tests/test_leaf.py'] == ['imports simleaf']
    (tmp_path / 'experimental/cnv/simlone.py').write_text('X = 1\n', encoding='utf-8')
    (tmp_path / 'experimental/cnv/simconst.py').write_text('import simlone\nLAG = 3\n', encoding='utf-8')
    g = at.ImportGraph(str(tmp_path))
    changes = [('experimental/cnv/simlone.py', 'experimental/cnv/simlone.py', None, False)]
    tests, why, fell = at.pick(None, changes, {}, {}, lambda p: {'tests/test_by_name.py'}, g, (None, None), decided)
    assert tests == {'tests/test_by_name.py'} and fell == ['experimental/cnv/simlone.py']   # nobody imports it


def test_tests_in_sub_folders_and_packages_on_the_way(tmp_path):
    """A test under tests/modules/ is a test file like any other; importing a.b.c imports a/ and a/b/ too."""
    for rel, text in {'experimental/cnv/pkg/__init__.py': '', 'experimental/cnv/pkg/sub/__init__.py': '',
                      'experimental/cnv/pkg/sub/leaf.py': 'X = 1\n',
                      'tests/modules/test_leaf.py': 'from pkg.sub import leaf\n',
                      'tests/modules/helper.py': '', 'tests/test_top.py': 'import pkg.sub.leaf\n'}.items():
        (tmp_path / rel).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / rel).write_text(text, encoding='utf-8')
    g = at.ImportGraph(str(tmp_path))
    assert g.test_files() == ['tests/modules/test_leaf.py', 'tests/test_top.py']
    assert g.importers('experimental/cnv/pkg/sub/leaf.py') == {'tests/modules/test_leaf.py', 'tests/test_top.py'}
    assert g.importers('experimental/cnv/pkg/__init__.py') == {'tests/modules/test_leaf.py', 'tests/test_top.py'}
    assert at.all_test_files(str(tmp_path)) == ['tests/modules/test_leaf.py', 'tests/test_top.py']
    assert at.is_test_file('tests/modules/test_leaf.py') and not at.is_test_file('tests/modules/helper.py')


def test_estimate_counts_a_single_test_as_its_share_of_the_file():
    serial, par, unknown = at.estimate(['f.py::t1', 'g.py'], {'f.py': 100.0, 'g.py': 10.0}, 2, lambda f: 4)
    assert serial == 35.0 and unknown == 0


def test_the_real_tree():
    g = at.ImportGraph()
    sc_spec = importlib.util.spec_from_file_location('simcoverage', ROOT / 'experimental' / 'cnv' / 'simcoverage.py')
    sc = importlib.util.module_from_spec(sc_spec)
    sc_spec.loader.exec_module(sc)
    assert {at.module_name(p) for p in g.sim_files()} == set(sc.sim_files())
    users = g.users('experimental/cnv/engine/modules/autoheal.py')   # simheal.Heal.autoheal until step K1
    assert {'tests/test_simheal.py', 'tests/modules/test_autoheal.py'} <= {at.file_of(u) for u in users}
    assert not {u for u in users if os.path.basename(at.file_of(u)).startswith('test_simai_bench')}
    assert g.module_names('experimental/cnv/engine/modules/autoheal.py') == {'autoheal', 'AutoHealBehavior'}
