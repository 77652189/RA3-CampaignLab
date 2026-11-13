"""Engineer bench replay and model-only recruitment diagnosis (work/re/e111_engineer.md)."""
import importlib.util
from pathlib import Path

import pytest

_spec = importlib.util.spec_from_file_location(
    'simai', Path(__file__).resolve().parents[1] / 'experimental/cnv/simai.py')
simai = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(simai)
pytestmark = pytest.mark.skipif(not simai.available(), reason='no ra3model.ai')


@pytest.mark.parametrize('build', ['aieng', 'aiengctl'])
def test_engineer_observed_plateau_does_not_establish_dispatch(build):
    """Retail counters agree, but the model never reaches a tactic with members.

    The candidate-pool assertions diagnose the model, not retail recruitment.
    Do not remove its selection filter without a qualified engine observation.
    """
    w = simai.run(build, 'a', until=26, lib=simai.model()['xmldata'].Library(), record=True)
    labels = [label for _, label in w.sim.test.counters]
    rows = [dict(zip(labels, values)) for t, values in w.sim.series if 1 <= t <= 26]
    assert rows
    assert {tuple(row[k] for k in ('目标归属', '到目标量', '工程师量', '目标血量'))
            for row in rows} == {(0, 0, 1, 100)}

    brain, = w.brains.values()
    assert 'CNVStateTF' in brain.ai.states.on
    target = w.sim.m.cnv_named['target']
    slot, = brain.targets.slots['CNVStateTF']
    assert brain.body_of(slot).name == target
    engineer = w.sim.body(w.sim.m.cnv_named['engineer'])
    assert engineer.alive and engineer.owner == brain.player and engineer.speed > 0
    assert {'ENGINEER', 'IGNORES_SELECT_ALL'} <= engineer.kinds
    assert brain.units(brain.ai, brain.frame) == []
    assert any(event[1] == 'expired' for event in brain.ai.teams.log)
    assert not brain.tactics.runs
    assert not brain.rec['orders']
