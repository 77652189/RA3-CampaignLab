"""E107 named EngageHostileTargets pair on the repaired observer clock.

Exact observations and unresolved acquisition boundary: work/re/e107_engage_clock.md.
No scripted special-power press is present in either named check.
"""
import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location('simai', ROOT / 'experimental/cnv/simai.py')
simai = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(simai)
pytestmark = pytest.mark.skipif(not simai.available(), reason='no ra3model.ai')


@pytest.fixture(scope='module', params=['aiegon', 'aiegoff'])
def engage_record(request):
    world = simai.run(request.param, 'a', until=45,
                      lib=simai.model()['xmldata'].Library(), record=True)
    brain, = world.brains.values()
    first = next(row for row in brain.rec['frames'] if row['members'])
    cohort = {member['name'] for member in first['members']}
    return request.param, brain, cohort


def test_engage_clock_recruits_initial_pair(engage_record):
    """Keep the recruited, live first-cohort prerequisite outside xfail."""
    build, brain, cohort = engage_record
    assert len(cohort) == 2, (build, cohort)
    first = next(row for row in brain.rec['frames'] if row['members'])
    assert all(member['alive'] for member in first['members']), (build, first)


@pytest.mark.xfail(strict=True, raises=AssertionError, reason=(
    'E107 first-cohort movement diverges before power selection; original '
    'recruitment/formation and targetless marching remain unresolved. '
    'See work/re/e107_engage_clock.md and work/re/handoff-e.md.'))
def test_engage_clock_replays_first_cohort_movement(engage_record):
    """Compare actual bench movement emission; formation offsets stay a gap."""
    build, brain, cohort = engage_record
    expected = {'aiegon': 352}
    orders = [order for order in brain.rec['orders']
              if order['member'] in cohort and order['kind'] in ('move', 'attack-move')]
    if build == 'aiegoff':
        # No player-issued move/formation orders after recruitment in the bench log.
        assert orders == [], orders
        return
    frame = expected[build]
    first = orders[0]
    assert first['frame'] == frame, (build, first)
