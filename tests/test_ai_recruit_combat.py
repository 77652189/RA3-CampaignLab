"""TeamTemplate.AllowRecruitUnitsInCombat on the plan simulator against bench aicombat0 / aicombat1
(experimental/cnv/checks/engine_aicombat.py, readings in its docstring): capacity one, the first candidate shooting at
a player tank in range until s30, the second idle. Bench 11-16 (both PASS): off -- the idle one leaves f184, the
fighter stays to s55; on -- the fighter is taken and leaves f462 (once its foe is deleted at s30), the idle one stays.
Skipped where ra3model.ai is not on this computer."""
import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location('simai', ROOT / 'experimental' / 'cnv' / 'simai.py')
simai = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(simai)

pytestmark = pytest.mark.skipif(not simai.available(), reason='no ra3model.ai (labpaths.ENGINE_MODEL)')
KEYS = ('战者在原位', '闲者在原位', '首离身份')


def _rows(build):
    w = simai.run(build, 'a', until=52, lib=simai.model()['xmldata'].Library())
    labels = [label for _, label in w.sim.test.counters]
    return [(t, dict(zip(labels, values))) for t, values in w.sim.series]


def _at(rows, s):
    return next(row for t, row in rows if s <= t < s + 1)


@pytest.mark.parametrize('build, first, at50', [('aicombat0', 2, (1, 0)), ('aicombat1', 1, (0, 1))])
def test_allow_recruit_units_in_combat_picks_who_is_taken(build, first, at50):
    rows = _rows(build)
    row = _at(rows, 50)
    assert (row['首离身份'], row['战者在原位'], row['闲者在原位']) == (first, *at50), row


def test_off_takes_the_idle_one_while_the_fighter_shoots():
    row = _at(_rows('aicombat0'), 25)
    assert tuple(row[k] for k in KEYS) == (1, 0, 2), row


@pytest.mark.xfail(strict=True, raises=AssertionError, reason=(
    'bench aicombat1: the recruited fighter keeps shooting where it stands until its foe goes (s30, leaves f462); '
    'the simulator sends it off with the team at f175'))
def test_on_the_taken_fighter_fights_on_before_it_leaves():
    row = _at(_rows('aicombat1'), 25)
    assert tuple(row[k] for k in KEYS) == (1, 1, 0), row
