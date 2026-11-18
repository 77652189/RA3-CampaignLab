"""已对拍 has one way in (ADR 0035 5, docs/engine/testing.md): a reading in the readings data the conformance runner
holds. The legacy ways stay as they were and only shrink: the hand-written registers that make an item 已对拍.

Ceilings are the counts when the readings data became the definition (T4, 11-18); lower one when an entry goes.
Never raise one: write the reading into checks/<bench>.readings.toml instead. And no new test function names a bench
(bench_tests_baseline.txt, below)."""
import ast
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / 'experimental' / 'cnv' / f'{name}.py')
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# register -> ceiling (count of entries that make an item 已对拍)
REGISTER_CEILING = {
    'inventory.BENCHED_TESTS': 121,
    'inventory.NOTES[已对拍]': 36,
    'inventory_ai.BENCHED_REG': 49,
    'inventory_ai.NOTES[已对拍]': 114,
}


def register_counts(inv, ai):
    return {
        'inventory.BENCHED_TESTS': len(inv.BENCHED_TESTS),
        'inventory.NOTES[已对拍]': sum(1 for s, _ in inv.NOTES.values() if s == inv.BENCHED),
        'inventory_ai.BENCHED_REG': len(ai.BENCHED_REG),
        'inventory_ai.NOTES[已对拍]': sum(1 for s, _ in ai.NOTES.values() if s == ai.BENCHED),
    }


def over_ceiling(counts, ceilings=REGISTER_CEILING):
    """[(register, count, ceiling)] that grew."""
    assert set(counts) == set(ceilings), sorted(set(counts) ^ set(ceilings))
    return [(k, counts[k], ceilings[k]) for k in sorted(counts) if counts[k] > ceilings[k]]


def test_the_bench_registers_only_shrink():
    grew = over_ceiling(register_counts(_load('inventory'), _load('inventory_ai')))
    assert not grew, (f'{grew}: a hand-written 已对拍 register grew -- put the reading into '
                      'checks/<bench>.readings.toml (docs/engine/testing.md) instead')


def test_a_register_that_grows_is_caught():
    counts = dict(REGISTER_CEILING)
    assert over_ceiling(counts) == []
    counts['inventory_ai.BENCHED_REG'] += 1
    assert over_ceiling(counts) == [('inventory_ai.BENCHED_REG', 50, 49)]


# ---------------------------------------------------------------- no new test naming a bench
# A new reading goes into checks/<bench>.readings.toml (the conformance runner runs each scene once), not into a new
# test function that replays a bench mission for one or two numbers (ADR 0035 3, docs/engine/testing.md). The test
# functions that name a bench today are BASELINE; the set only shrinks: a new one is red, and a gone one must leave
# the list in the same change (a stale line would let a test of that name come back).

BASELINE = ROOT / 'tests' / 'guards' / 'bench_tests_baseline.txt'
inventory = _load('inventory')


def _affected_tests():
    spec = importlib.util.spec_from_file_location('affected_tests_bt',
                                                  ROOT / 'experimental' / 'testbench' / 'affected_tests.py')
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _test_defs(tree):
    """[(test id within the file, node)]: module-level test_* functions and the test_* methods of Test* classes."""
    fns = (ast.FunctionDef, ast.AsyncFunctionDef)
    out = []
    for n in tree.body:
        if isinstance(n, fns) and n.name.startswith('test'):
            out.append((n.name, n))
        elif isinstance(n, ast.ClassDef) and n.name.startswith('Test'):
            out += [(f'{n.name}::{m.name}', m) for m in n.body if isinstance(m, fns) and m.name.startswith('test')]
    return out


def named_bench_tests(text, stems, missions):
    """The test ids of one test file's source that name a bench: an 'engine_X' (or a build variant 'engine_X_v')
    of a bench in `stems`, or a bench mission's name quoted ('aiskirm'), in the test (its decorators too) or in a
    module-level helper, constant or fixture the test uses (followed through helpers that use each other). Code
    only: a comment or docstring citing a bench, or a helper no test uses, names nothing. The inventory tool tests
    are blanked first."""
    text = inventory.without_tool_tests(text)
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return set()

    docs = {id(b[0].value) for n in ast.walk(tree)
            if isinstance(n, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and (b := n.body)
            and isinstance(b[0], ast.Expr) and isinstance(b[0].value, ast.Constant)}

    def code_words(node):
        """The strings and names in the code: no comments, no docstrings (a module test cites the bench its rule
        was read on -- 'engine_toggle d' -- and replays none)."""
        for n in ast.walk(node):
            if isinstance(n, ast.Constant) and isinstance(n.value, str) and id(n) not in docs:
                yield n.value
            elif isinstance(n, ast.Name):
                yield n.id
            elif isinstance(n, (ast.Import, ast.ImportFrom)):     # from checks.engine_x import ...
                yield from [getattr(n, 'module', None) or ''] + [a.name for a in n.names]

    def names_a_bench(node):
        for word in code_words(node):
            if word in missions:
                return True
            for name in inventory.PROBE_NAME.findall(word):
                while name not in stems and '_' in name[len('engine_'):]:
                    name = name.rsplit('_', 1)[0]
                if name in stems:
                    return True
        return False

    def uses(node):
        return ({n.id for n in ast.walk(node) if isinstance(n, ast.Name)}
                | {a.arg for n in ast.walk(node) if isinstance(n, ast.arguments)
                   for a in n.posonlyargs + n.args + n.kwonlyargs})

    tests = _test_defs(tree)
    test_nodes = {id(n) for _, n in tests} | {id(n) for n in tree.body
                                              if isinstance(n, ast.ClassDef) and n.name.startswith('Test')}
    helpers = {}                                    # module-level name -> the statement that binds it
    for n in tree.body:
        if id(n) in test_nodes:
            continue
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            helpers[n.name] = n
        elif isinstance(n, (ast.Assign, ast.AnnAssign)):
            for t in (n.targets if isinstance(n, ast.Assign) else [n.target]):
                for x in ast.walk(t):
                    if isinstance(x, ast.Name):
                        helpers[x.id] = n
    tainted = {k for k, n in helpers.items() if names_a_bench(n)}
    while True:
        more = {k for k, n in helpers.items() if k not in tainted and uses(n) & tainted}
        if not more:
            break
        tainted |= more
    return {tid for tid, n in tests if names_a_bench(n) or uses(n) & tainted}


def bench_names(checks=None):
    """(bench stems {'engine_X'}, bench build names) of checks/engine_*.py. The build names are what the bench's
    CHECKS / MISSION / PAIR_BUILDS declares, read by the inventory's one reader of a bench's syntax tree
    (inventory.probe_checks: a bench is not imported, it builds missions, and most are reached lazily, not through
    the registry)."""
    stems, missions = set(), set()
    for p in sorted(Path(checks or inventory.CHECKS).glob('engine_*.py')):
        stems.add(p.stem)
        missions |= inventory.probe_checks(p.read_text(encoding='utf-8'))[0]
    return stems, missions


def bench_tests(root=ROOT, checks=None):
    """{'tests/.../test_x.py::test_y'} of every test file under tests/ that names a bench."""
    stems, missions = bench_names(checks)
    out = set()
    for f in _affected_tests().all_test_files(str(root)):
        text = (Path(root) / f).read_text(encoding='utf-8')
        out |= {f'{f}::{t}' for t in named_bench_tests(text, stems, missions)}
    return out


def read_baseline(path=BASELINE):
    return {ln.strip() for ln in path.read_text(encoding='utf-8').splitlines()
            if ln.strip() and not ln.startswith('#')}


def test_no_new_test_names_a_bench():
    new = sorted(bench_tests() - read_baseline())
    assert not new, (f'{new}: a new test replays a bench for its readings -- write them into '
                     'checks/<bench>.readings.toml (docs/engine/testing.md); the conformance runner checks them')


def test_the_baseline_has_no_gone_tests():
    gone = sorted(read_baseline() - bench_tests())
    assert not gone, f'{gone}: no longer name a bench (or are gone) -- delete these lines from {BASELINE.name}'


SYNTH = '''"""engine_alpha is named in the module docstring only."""
BENCH = 'engine_alpha'
PLAIN = 3


def _run(c):
    return go(BENCH, c)


def _wrap():
    return _run('a')


@pytest.fixture
def world():
    return start('betamission')


def test_by_helper():
    assert _wrap()


def test_by_fixture(world):
    pass


def test_by_name():
    sim('engine_gamma_move')     # a build variant of engine_gamma


@pytest.mark.parametrize('b', ['engine_alpha'])
def test_by_decorator(b):
    pass


def test_plain():
    assert PLAIN == 3 and 'engine_alphabet'


def test_cites_only():
    """Read on engine_alpha a (a citation, not a replay)."""
    assert PLAIN       # engine_gamma b showed it


def test_by_import():
    from checks.engine_gamma import ORDER
    assert ORDER


class TestK:
    def test_m(self):
        go('engine_gamma')
'''


def test_a_test_naming_a_bench_is_found_however_it_names_it():
    found = named_bench_tests(SYNTH, {'engine_alpha', 'engine_gamma'}, {'betamission'})
    assert found == {'test_by_helper', 'test_by_fixture', 'test_by_name', 'test_by_decorator', 'test_by_import',
                     'TestK::test_m'}


def test_a_new_bench_test_in_a_tree_is_caught(tmp_path):
    (tmp_path / 'checks').mkdir()
    (tmp_path / 'checks' / 'engine_alpha.py').write_text("CHECKS = {'alphamission': {'a': 'f'}}\n")
    (tmp_path / 'tests' / 'content').mkdir(parents=True)
    (tmp_path / 'tests' / 'test_old.py').write_text("def test_old():\n    go('engine_alpha')\n")
    base = bench_tests(tmp_path, tmp_path / 'checks')
    assert base == {'tests/test_old.py::test_old'}
    (tmp_path / 'tests' / 'content' / 'test_new.py').write_text("def test_new():\n    run('alphamission')\n")
    assert bench_tests(tmp_path, tmp_path / 'checks') - base == {'tests/content/test_new.py::test_new'}
