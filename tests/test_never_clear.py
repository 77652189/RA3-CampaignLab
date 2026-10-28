"""plancheck: '敌人清空 <site>' with an enemy building placed in that site never holds (buildings count too; bench
2026-10-27, A5's control room) -- caught without the bench."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'experimental' / 'cnv'))
import plan  # noqa: E402
import plancheck  # noqa: E402


def test_a_building_in_the_cleared_site_is_a_problem():
    d = plan.load('a5')
    assert not plancheck.never_clear(d)
    d['段'][1]['结束'] = '敌人清空 control yard'
    got = plancheck.never_clear(d)
    assert len(got) == 1 and '科技中心' in got[0] and ('问题', got[0]) in plancheck.design_check(d)


def test_every_plan_is_clear_of_it():
    plans = [p.stem for p in (ROOT / 'docs' / 'story' / 'plans').glob('*.md') if p.stem != 'README']
    assert plans
    for lv in plans:
        assert not plancheck.never_clear(plan.load(lv)), lv
