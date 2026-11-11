"""Replay the funded / zero-credit AI RepairUpdate probes by name."""
import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location('repair_simai', ROOT / 'experimental/cnv/simai.py')
simai = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(simai)


@pytest.mark.parametrize('name, expected', [('repairai', [50, 50, 5000]), ('repairzero', [50, 50, 0])])
def test_ai_repair_funded_and_zero_credit_final_readings(name, expected):
    import build
    from parts import contract, merged

    w = simai.run(name, 'a', until=81, blocks=())
    e = w.sim
    assert not contract(merged(e.m, e.test))
    assert e.m.player('s1') in w.brains
    assert e.ai_switches[e.m.player('s1')]['SKIRMISH_AI_USE_REPAIRS'] == 1
    rows = [row for sec, row in e.series if 75 <= sec <= 80]
    assert rows
    assert all(row == expected for row in rows), rows
    # A matching inactive probe is evidence of activation failure, not a repair
    # implementation. Preserve the unmet funded prediction and TODO status.
    assert build.report(e.test, e.series)[1] == (1 if name == 'repairai' else 0)


@pytest.mark.xfail(strict=True, reason='E41 repairai:a bench stays 50%/5000 with repair inactive; '
                   'AI dispatch/eligibility needs D observations, repair execution unimplemented; '
                   'work/re/handoff-e.md 待答问题 E41')
def test_ai_repair_funded_activation_and_cost_prediction():
    import build

    w = simai.run('repairai', 'a', until=81, blocks=())
    rows = [row for sec, row in w.sim.series if 75 <= sec <= 80]
    assert rows
    assert all(row == [100, 50, 4900] for row in rows), rows
    assert build.report(w.sim.test, w.sim.series)[1] == 0
