"""SKIRMISH_AI_SET_FAVORED_ENEMY on the plan simulator (engine line A round 220): bench engine_aifav a (mission
aipriofav = missions/aiprio_bench.py aipriodef + SET_FAVORED_ENEMY(Soviet_1, Soviet_4) at the wake). The program
(work/re a219_skirmish_transfer.md 2): the enemy table emptied, the one enemy put back at 10. Skipped where
ra3model.ai is not on this computer, as tests/test_simai.py."""
import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location('simai', ROOT / 'experimental' / 'cnv' / 'simai.py')
simai = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(simai)

pytestmark = pytest.mark.skipif(not simai.available(), reason='no ra3model.ai (labpaths.ENGINE_MODEL)')


@pytest.fixture(scope='module')
def run():
    w = simai.run('aipriofav', 'a', 70.0, lib=simai.model()['xmldata'].Library())
    labels = [lab for _, lab in w.sim.test.counters]
    return w, [dict(zip(labels, v)) for _, v in w.sim.series]


def _first(rows, label):
    return next((i for i, r in enumerate(rows) if r[label] >= 1), None)


def test_favored_enemy_queues_a_clear_then_the_enemy_at_ten(run):
    w, _ = run
    assert w.sim.ai_priorities['Soviet_1'] == [(None, 0), ('Soviet_4', 10)]


def test_favored_enemy_alone_in_the_table_goes_for_its_plant(run):
    # bench engine_aifav a (11-14): 到近厂 2 @ s14, 4 s15-s21; 到远厂 0 to s69
    w, rows = run
    (b,) = w.brains.values()
    assert b.ai.enemy_table == {'Soviet_4': 10}
    near = _first(rows, '到近厂')
    assert near is not None and abs(near - 14) <= 2 and _first(rows, '到远厂') is None
