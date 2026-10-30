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
    assert set(judged) == {'会场', '北营', '最后一程'}
    for n, (best, mix) in judged.items():
        assert best is not None and best <= graybox.EASY, f'{n}: k*={best} for {mix}'


def test_one_unit_type_cannot_answer_a_stage_with_air_in_it():
    """Rocket angels fly: a Peacekeeper army never kills them, so the last stage cannot be pushed with Peacekeepers
    alone -- the gauge says 'cannot', not 'easy'."""
    s, rows = stages()
    last = next(r for r in rows if r[0] == '最后一程')
    assert last[2][glossary.template('维和步兵', '盟军')] == math.inf
    assert last[4] is not None and len(last[4]) == 2                # the winning army has a second type in it


def test_a_mirror_match_needs_more_than_an_equal_army():
    """Lanchester: k* of a mirror match is sqrt(4/3), about 1.15, under the half-left rule (an equal army kills and
    dies together); eight times the enemy's numbers of a cheap unit is not what a stage asks."""
    s, rows = stages()
    body = graybox.Bodies(s)
    knight = glossary.template('维和步兵', '盟军')
    assert 1.0 < graybox.kstar(body, knight, {knight: 1}) < 1.3
