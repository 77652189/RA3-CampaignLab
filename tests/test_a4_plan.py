"""A4's plan after the 2026-10-31 decisions (docs/story/plans/a4.md): one ice engineer to start with and refilled up to
two (no cap on the ice walls), the opening scene runs the horn's demonstration, the convoy crawls at 12."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'experimental' / 'cnv'))
sys.path.insert(0, str(ROOT / 'experimental' / 'campaign'))
import plan  # noqa: E402


def mission():
    return plan.Compiler(plan.load('a4')).compile()


def test_one_engineer_to_start_and_the_rest_given_up_to_two():
    d = plan.load('a4')
    start = [u for u in d['开局']['部队'] if u.get('单位') == '冰幕工兵']
    assert len(start) == 1 and int(start[0]['数量']) == 1
    m = mission()
    refill = [s for s in m.scripts if s.name.startswith('CNV A4 - Rule') and 'again' in s.name
              and any(a[0] == 'CREATE_NAMED_ON_TEAM_AT_WAYPOINT' and 'IceEngineer' in a[2] for a in s.do)]
    assert refill, 'no rule gives engineers'
    # while the player has fewer than two (comparison 0 is <), every so often, after the opening scene
    for s in refill:
        counts = [c for c in s.when if c[0] == 'COUNTER' and 'Troops' in c[1]]
        assert counts and counts[0][2:] == (0, 2), s.when
        assert any(c[0] == 'TIMER_EXPIRED' for c in s.when)


def test_no_cap_on_the_ice_walls_is_left_in_the_plan():
    text = (ROOT / 'docs' / 'story' / 'plans' / 'a4.md').read_text(encoding='utf-8')
    assert '禁造/准造' not in text and '封顶两个这一条还没做' not in text
    d = plan.load('a4')
    assert '冰幕工兵' not in str(d.get('禁造'))                          # nothing bans or caps the engineers


def test_the_opening_scene_ends_with_the_demonstration_taken_away_and_the_convoy_is_slow():
    m = mission()
    steps = [s for s in m.scripts if s.name.startswith('CNV A4 - Phase 1 scene')]
    flags = [a[1] for s in steps for a in s.do if a[0] == 'SET_FLAG']
    assert 'CNV_A4_Demo_On' in flags and 'CNV_A4_Demo_Off' in flags
    assert flags.index('CNV_A4_Demo_On') < flags.index('CNV_A4_Demo_Off')
    truck = next(u for u in m.units if u.id == 'CNV_ConvoyTruck')
    assert truck.params['speed'] == 12.0 and 'Speed="12"' in truck.xml
