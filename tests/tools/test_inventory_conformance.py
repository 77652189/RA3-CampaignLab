"""已对拍 from the readings data (ADR 0035 5): inventory.conformance_probes / backing on synthetic folders."""
import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
_spec = importlib.util.spec_from_file_location('inventory', ROOT / 'experimental' / 'cnv' / 'inventory.py')
inventory = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(inventory)

ONE = "CHECKS = {'m1': {'a': a}}\ndef a(): pass\n"
TWO = "CHECKS = {'m1': {'a': a, 'b': b}}\ndef a(): pass\ndef b(): pass\n"


def _reading(rid, build, check, mismatch=None):
    m = f'mismatch = "{mismatch}"\n' if mismatch else ''
    return (f'[[reading]]\nid = "{rid}"\nscene = {{build = "{build}", check = "{check}", until = 3}}\n'
            f'bench = "x"\nproves = "y"\nexpect = "True"\n{m}\n')


def _tree(tmp_path, probes, readings):
    checks = tmp_path / 'checks'
    checks.mkdir()
    for name, text in probes.items():
        (checks / f'{name}.py').write_text(text, encoding='utf-8')
    for name, text in readings.items():
        (checks / f'{name}.readings.toml').write_text(text, encoding='utf-8')
    return checks


def test_a_matching_reading_backs_its_probe_and_a_mismatch_backs_nothing(tmp_path):
    checks = _tree(tmp_path, {'engine_p': ONE, 'engine_q': ONE},
                   {'engine_p': _reading('r1', 'm1', 'a'), 'engine_q': _reading('r2', 'm1', 'a', 'sim 1; bench 2')})
    assert inventory.conformance_probes(str(checks), str(checks)) == {'checks/engine_p.py'}


def test_a_probe_of_several_checks_is_backed_per_check(tmp_path):
    checks = _tree(tmp_path, {'engine_p': TWO}, {'engine_p': _reading('r1', 'm1', 'b')})
    assert inventory.conformance_probes(str(checks), str(checks)) == {'checks/engine_p.py', 'checks/engine_p.py:b'}


def test_readings_beside_no_probe_stop_the_inventory(tmp_path):
    checks = _tree(tmp_path, {}, {'engine_p': _reading('r1', 'm1', 'a')})
    with pytest.raises(SystemExit, match='beside no probe'):
        inventory.conformance_probes(str(checks), str(checks))


def test_an_item_a_reading_backs_says_so(tmp_path):
    checks = _tree(tmp_path, {'engine_p': ONE}, {'engine_p': _reading('r1', 'm1', 'a')})
    tests = tmp_path / 'tests'
    tests.mkdir()
    tested = inventory.backing(str(tests), str(checks), str(checks))
    assert tested == {'checks/engine_p.py': inventory.CONFORMS}
    items = [dict(part=inventory.MODULE, name='Behaviors/FooUpdate', uses=1, state=inventory.GUESSED, why='w')]
    inventory.benched(items, [('checks/engine_p.py', 'FooUpdate 3')], tested)
    assert items[0]['state'] == inventory.BENCHED and inventory.CONFORMS in items[0]['why']
    # the legacy route (a plain set, or a test naming the probe) is told apart
    items[0].update(state=inventory.GUESSED, why='w')
    inventory.benched(items, [('checks/engine_p.py', 'FooUpdate 3')], {'checks/engine_p.py'})
    assert inventory.LEGACY in items[0]['why']


def test_the_real_readings_back_real_probes():
    """Every reading file sits beside a probe, and the data backs at least the AI benches T2 migrated."""
    got = inventory.conformance_probes()
    assert {'checks/engine_aihome.py', 'checks/engine_aitarget.py', 'checks/engine_aidefense.py'} <= got
