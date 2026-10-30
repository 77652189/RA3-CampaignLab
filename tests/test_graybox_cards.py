"""The facts docs/story/graybox-cards.md stands on (experimental/cnv/graybox_cards.py): each is a qualitative claim about a
question card, cheap arithmetic on the unit numbers. If a number moves (a patch to the SDK data, a changed fight model),
the write-up is stale and this says so."""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path[:0] = [os.path.join(ROOT, 'experimental', 'cnv'), os.path.join(ROOT, 'experimental', 'campaign')]
import graybox_cards  # noqa: E402

_cache = []


def facts():
    if not _cache:
        _cache.append(graybox_cards.facts())
    return _cache[0]


def test_one_cheap_type_answers_all_three_streets():
    """A4 甲 says the escort's mix must change street by street; by the numbers Peacekeepers alone are easy on all."""
    assert facts()['a4_types']['one_type_answers_all'] == ['维和步兵']


def test_streets_merged_are_worse_for_the_escort_than_a_column():
    """Lanchester: the same enemy at once beats a force that would take it one group at a time; the card's trick
    (all three into one street) helps only if the street makes them a column."""
    a = facts()['a4_streets']
    assert a['merged'] < a['column'] < a['single']
    assert a['clear_seconds'] < a['truck_seconds']                  # the escort kills a group faster than it kills a truck


def test_one_ice_wall_is_not_enough_for_a_plaza_two_in_relay_are():
    """A4 乙: wall 30 s, cooldown 40 s, a plaza 40 s: one engineer shuts the gate for 75 % (< the card's 80 %), two in
    relay for all of it; the 10 s gap is longer than a truck lasts under one group's fire."""
    p, a = facts()['a4_plaza'], facts()['a4_streets']
    assert p['one_engineer'] < 0.8 and p['two_relay'] == 1.0
    assert 40.0 - 30.0 > a['truck_seconds']


def test_the_hook_outranges_every_gun_on_the_lake_but_not_the_enemys_eyes():
    """S1: hook 300 > the player's longest range 175 > the enemy's 150, yet the convoy sees 500: a sneak needs terrain."""
    s1 = facts()['s1']
    mine = max(s1['ranges'][n] for n in ('防空步兵', '镰刀机甲'))
    theirs = max(s1['ranges'][n] for n in ('守护者坦克', '维和步兵'))
    assert theirs < mine < s1['hook'] < s1['escort_vision']


def test_a_sixty_second_ice_window_is_longer_than_the_lake_unless_the_lake_is_huge():
    s1 = facts()['s1']
    assert s1['window_reach']['镰刀机甲'] > s1['map_width']


def test_the_jammer_costs_seconds_not_multiples_and_v4_outranges_the_empire():
    """J7 甲: an aura of 250 slows a full pass by 10-15 s only; 乙: V4's 500 is far over every Empire gun."""
    j = facts()['j7']
    assert all(5.0 < v['extra'] < 20.0 for v in j['aura_extra'].values())
    assert j['v4_range'] > 2.5 * max(j['ranges'].values())
    assert j['shield_sequential'] / j['shield_together'] > 2.0      # 丙's check (>= 2) holds on paper
