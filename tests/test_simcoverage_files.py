"""Guard (ADR 0029, refactor line R2): the inventory tools read the simulator's source -- simcoverage.sim_code (the
module and nugget names inventory.py and the device check look for) and status_modelled (the status bits acted on) --
off simcoverage.sim_files, which must cover every file the simulator is made of. Until 11-17 they read sim.py (and
simunits.py / simproxy.py) by name, and the blocks moved out of sim.py dropped out of the count silently (400 strings,
GENERIC_TOGGLE_STATE and SHROUD_REVEAL_TO_ALL).

The simulator's files here are what the layer guard registers (tests/test_sim_layers.py LAYER_OF: every block moved out
of sim.py goes there) and the three files of the run before the refactor -- a reading independent of sim_files' own
(derived from the imports), so a block the import walk misses turns this red."""
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CNV = ROOT / 'experimental' / 'cnv'


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# loaded by file: simcoverage.py puts the cnv folders on the path itself (no new sys.path edit here: guard G4's ceiling)
sc = _load('simcoverage', CNV / 'simcoverage.py')
LAYER_OF = _load('test_sim_layers_registry', ROOT / 'tests' / 'test_sim_layers.py').LAYER_OF


def simulator_modules():
    return sorted(set(LAYER_OF) | {'sim', 'simunits', 'simproxy'})


def uncounted(code, status):
    """(module, 'status' / 'string', value) for each status test or string constant of a simulator module that the
    given reading (sim_code, status_modelled) does not hold."""
    out = []
    for m in simulator_modules():
        path = Path(sc.enginefiles.file_of(m))          # simX, or engine.<layer>.<part> after step 10
        out += [(m, 'status', s) for s in sorted(set(sc.STATUS_TEST.findall(path.read_text(encoding='utf-8'))) - status)]
        out += [(m, 'string', s) for s in sorted(sc.code_strings(path) - code)]
    return out


def test_the_inventory_counts_every_file_of_the_simulator():
    missed = uncounted(sc.sim_code(), sc.status_modelled())
    assert not missed, 'simcoverage.sim_files misses a file of the simulator:\n' + \
        '\n'.join(f'  {m} {kind} {v!r}' for m, kind, v in missed[:20])


def test_reading_sim_py_by_name_would_be_caught():
    """The pre-11-17 reading (sim.py, simunits.py, simproxy.py by name) misses status bits and module names that moved
    out of sim.py: the guard above sees it."""
    old = ('sim', 'simunits', 'simproxy')
    code = set().union(*(sc.code_strings(sc.enginefiles.file_of(m)) for m in old))
    status = set(sc.STATUS_TEST.findall((CNV / 'sim.py').read_text(encoding='utf-8'))) | {'IN_STASIS'}
    missed = uncounted(code, status)
    assert ('simcond_vision', 'status', 'SHROUD_REVEAL_TO_ALL') in missed
    assert ('simheal', 'status', 'GENERIC_TOGGLE_STATE') in missed
    assert ('simlevel', 'string', 'LevelUpUpgrade') in missed


def test_a_module_that_imports_sim_is_not_a_part_of_it():
    """simshow and simchecks sit on top of the simulator (they import sim): their strings are not its code."""
    files = sc.sim_files()
    assert 'sim' in files and 'simproxy' in files and 'simunits' in files
    assert 'simshow' not in files and 'simchecks' not in files and 'simcoverage' not in files
