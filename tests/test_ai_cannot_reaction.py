"""Named replay of the CannotAttackTargetReaction bench lifecycle.

Measured samples and ownership gate: work/re/c_cannot_report.md.
These probes do not close the field until the missing consumer is implemented.
"""
import importlib.util
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('simai', ROOT / 'experimental/cnv/simai.py')
simai = importlib.util.module_from_spec(spec)
spec.loader.exec_module(simai)
pytestmark = pytest.mark.skipif(not simai.available(), reason='no private AI model')


@pytest.mark.parametrize('name', [
    'aicantig',
    pytest.param('aicantdi', marks=pytest.mark.xfail(strict=True, raises=AssertionError, reason=(
        'Bench clears a populated team at frame 95 and recruits again at 97; '
        'CannotAttackTargetReaction consumer requires the E-owned tactics module; '
        'see work/re/c_cannot_report.md and handoff-c.md.'))),
    pytest.param('aicantsu', marks=pytest.mark.xfail(strict=True, raises=AssertionError, reason=(
        'Bench switches tactical target at frame 92 and attacks the ground yard at 500; '
        'model keeps the air target. Consumer requires E-owned tactics module; '
        'see work/re/c_cannot_report.md and handoff-c.md.'))),
])
def test_cannot_reaction_replays_observed_lifecycle(name):
    """Assert the observed retention / clearing / new ground target, not inferred timing.

    CNVTeams' clock is relative to carrier creation. Replay checks lifecycle
    order inside the observed window, without treating it as the map clock.
    """
    w = simai.run(name, 'r', until=65, record=True)
    rows = [r for b in w.brains.values() for r in b.rec['frames']
            if r['state_key'] == 'CNVCannot']
    first = next((i for i, r in enumerate(rows)
                  if len(r['members']) == 2 and r['target'] == 'UNIT - CNV Cannot Air'), None)
    assert first is not None, 'the named air target must actually be held by a populated team'
    rows = rows[first:]
    if name == 'aicantig':
        assert all(len(r['members']) == 2 for r in rows)
        assert all(r['target'] == 'UNIT - CNV Cannot Air' and r['state'] == 8 for r in rows)
    elif name == 'aicantdi':
        cleared = next((i for i, r in enumerate(rows) if not r['members']), None)
        assert cleared is not None, 'bench cleared both members after holding the unreachable target'
        assert any(len(r['members']) == 2 for r in rows[cleared+1:]), 'bench recruited again'
    else:
        assert any(r['target'] not in (None, 'UNIT - CNV Cannot Air') and r['state'] == 6 for r in rows), (
            'bench changed to the only enemy ground structure and entered enemy state')
