"""The simulator's graybox (ADR 0011, experimental/cnv/graybox.py): k* must call the old A4 a push, and must still
refuse a stage no single unit type answers (a gauge that passes everything says nothing)."""
import math
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path[:0] = [os.path.join(ROOT, 'experimental', 'cnv'), os.path.join(ROOT, 'experimental', 'campaign')]
import glossary  # noqa: E402
import graybox  # noqa: E402

_cache = []


def stages():
    """The walkthrough is the slow part (~9 s): once for the file."""
    if not _cache:
        _cache.append(graybox.stages('a4'))
    return _cache[0]


def test_old_a4_can_be_pushed_through_every_stage():
    """The user (2026-10-28): A4 is basically a push. The graybox's own verdict must say the same, stage by stage;
    the gate of ADR 0011 -- a simulator that cannot tell this stops the graybox."""
    s, rows = stages()
    judged = {n: (best, mix) for n, e, ks, best, mix in rows if e}
    # 港口生变 is not judged: the scene starts when the last truck is at the halt and the sides cease fire for its
    # length (user 2026-11-02: the fight went on under the scene and the mission was lost in it)
    assert set(judged) == {'会场', '北营', '最后一程'}
    for n, (best, mix) in judged.items():
        assert best is not None and best <= graybox.EASY, f'{n}: k*={best} for {mix}'


def test_one_unit_type_cannot_answer_a_stage_with_air_in_it():
    """Rocket angels fly: a Peacekeeper army never kills them, so a stage with them in it cannot be pushed with
    Peacekeepers alone -- the gauge says 'cannot', not 'easy' (the A4 rework has no air of its own: the stage is
    made up of what the old A4's last stretch had)."""
    s, rows = stages()
    body = graybox.Bodies(s)
    peacekeeper, javelin, ifv = (glossary.template(n, '盟军') for n in ('维和步兵', '标枪兵', '多功能步兵车'))
    stage = {glossary.template(n, '帝国'): k for n, k in (('火箭天使', 3), ('帝国武士', 6), ('坦克杀手', 6))}
    assert graybox.kstar(body, peacekeeper, stage) == math.inf
    best, mix = graybox.best_mix(body, [peacekeeper, javelin, ifv], stage)
    assert best is not None and len(mix) == 2                       # the winning army has a second type in it


def test_a_mirror_match_needs_more_than_an_equal_army():
    """Lanchester: k* of a mirror match is sqrt(4/3), about 1.15, under the half-left rule (an equal army kills and
    dies together); eight times the enemy's numbers of a cheap unit is not what a stage asks."""
    s, rows = stages()
    body = graybox.Bodies(s)
    knight = glossary.template('维和步兵', '盟军')
    assert 1.0 < graybox.kstar(body, knight, {knight: 1}) < 1.3


def test_a_walkthrough_time_hangs_on_the_plans_events_not_the_clock():
    """ADR 0015 (I4 follow-up): the A4 walkthrough's seconds after the opening scene are `段 <phase>+n` / `过场 <phase>
    结束+n`, turned into the plan's flags, so a longer opening (the 演示 added 7.5 s) moves the walkthrough with it."""
    import plan
    import pytest
    import sim
    import offline
    c = plan.Compiler(plan.load('a4'))
    c.compile()
    ph = next(p for p in c.phases if p.name == '北营')
    text = offline.anchored('段北营+4 摧毁 north command; 过场会场结束+2:00 派 guardian 去 halt; 40 造 x 在 y', c)
    assert text.startswith(f'{ph.flag}+4 摧毁') and f'{c.scene_flag(c.phases[0])}+2:00 派' in text and '; 40 造' in text
    ev = sim.parse_script(text)
    assert ev[0][0] == ('@', ph.flag, 4.0) and ev[1][0][2] == 120.0 and ev[2][0] == 40.0
    with pytest.raises(ValueError, match='no phase'):
        offline.anchored('段没有+1 摧毁 x', c)
    after_opening = [e for e in sim.parse_script(offline.anchored(offline.WALK['a4'], c)) if e[0] is not None]
    assert all(isinstance(e[0], tuple) or e[0] <= 40.0 for e in after_opening)    # nothing later is on the bare clock
