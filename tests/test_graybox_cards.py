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


def test_a4_card_a_third_version_grinds_the_escort_in_two_waves():
    """A4 甲 recheck: at 1050 a street a wave, the card's own trick (three groups a horn, in a column) leaves the escort
    ~60 % after one horn and wipes it in the second, before the planned top-up after the third; at 900 it takes a
    top-up every second horn (or one wall a horn); the lump keeps ~90 %, thirds are ground to nothing."""
    w = facts()['a4_waves']
    assert w['waves_three'][1] == 2 and 0.5 < w['waves_three'][0][0] < 0.7
    assert w['waves_two'][1] == 3
    assert w['waves_three_900'][1] == 3 and w['waves_three_900_twice'][1] is None and w['waves_two_900'][1] is None
    assert w['max_scale_three'] < 900 / w['group_cost'] < w['max_scale_two']
    assert w['whole_left'] > 0.8 and w['third_left'] < 0.05


def test_j7_card_a_the_counter_must_be_about_three_times_the_army_under_the_tower():
    """J7 甲 recheck: the best Empire army waiting under the tower eats a counterattack up to ~3x its own cost when the
    three routes come at once, ~4x when the first route comes 15 s ahead; later gaps add nothing (the first route is
    eaten in 15 s), so the card's 15 s a jammer is enough."""
    c = facts()['j7_counter']
    for rname in ('步兵多', '机甲多'):
        same, early, late = (c[(rname, t)]['ratio'] for t in ('同时到', '先一路，另两路晚 15 秒', '先一路，另两路晚 45 秒'))
        assert 2.5 < same < 3.5 and early > 1.2 * same and abs(late - early) < 0.15 * early


def test_the_jammer_costs_seconds_not_multiples_and_v4_outranges_the_empire():
    """J7 甲: an aura of 250 slows a full pass by 10-15 s only; 乙: V4's 500 is far over every Empire gun."""
    j = facts()['j7']
    assert all(5.0 < v['extra'] < 20.0 for v in j['aura_extra'].values())
    assert j['v4_range'] > 2.5 * max(j['ranges'].values())
    assert j['shield_sequential'] / j['shield_together'] > 2.0      # 丙's check (>= 2) holds on paper


def test_s1_card_a_the_sickle_leap_is_as_long_as_the_hook_so_no_band_blocks_it():
    """S1 甲 geometry: the Sickle's leap (its weapon data) is 300, the hook 300; the hook must reach across the band
    (d + w + g <= 300), so w can never exceed the leap: the jump is blocked by being pointless, not by w. A band
    of 180+ also keeps shore infantry from shooting a Guardian at the ice edge; 160 does not."""
    g = facts()['s1_geometry']
    assert g['leap'] == g['hook'] == 300.0 and g['no_w_blocks_leap']
    rows = {r['w']: r for r in g['rows']}
    assert rows[200]['g_max'] == 90.0 and not rows[160]['shore_blocked'] and rows[180]['shore_blocked']
    assert all(r['hook_safe'] for r in g['rows'])                    # d + w > 150 everywhere in the table
    assert rows[160]['window'] > rows[200]['window'] > rows[250]['window'] > rows[280]['window']
    assert 5.0 < rows[200]['window'] < 8.0                           # a few seconds, not a minute


def test_s1_card_a_leaping_in_is_pointless_and_chasing_on_foot_costs_nine_times_the_hook():
    """S1 甲 natural plays: a Guardian shoots a Sickle ~5x harder than it is shot back; infantry walks no faster than
    the convoy; the whole escort needs ~7650 of troops (k* ~1.4 but at 5550 that is a lot early), the Peacekeepers
    that can come ashore ~830 -- the ice cuts the bill about nine times."""
    n, a = facts()['s1_natural'], facts()['s1_ablate']
    assert n['guard_vs_sickle'] > 4 * n['sickle_vs_guard'] and n['infantry_speed'] <= n['convoy_speed']
    assert n['whole_need_cost'] > 5 * n['ashore_need_cost']
    assert a['without_ice_cost'] > 5 * a['with_ice_cost'] and n['best']['lone'] < 0.5
    assert min(n['hook_tank_seconds'].values()) > 5.0                # even six Peacekeepers need > 5 s for a hook tank's body


def test_j7_card_a_a_valley_you_clear_is_the_valley_they_take():
    """J7 甲: clearing a valley's last jammer always makes it the cheapest (15 s a jammer outweighs the 15 s steps),
    ties go near, and with two jammers a valley the far valley cannot be made the pick by clearing alone."""
    t = facts()['j7_valley']['pick']
    assert t[(3, 3, 3)]['pull'] == {0: (0, 0, 0), 1: (0, 2, 0), 2: (0, 0, 3)}
    assert t[(2, 2, 2)]['pull'][2] is None and t[(3, 2, 2)]['pull'][2] == (0, 0, 2)
    assert all(r['all_cleared'] == 0 and r['early_by'] == 15.0 * n0[0] for n0, r in t.items())


def test_j7_card_a_the_best_valley_changes_every_wave_but_a_blip_is_enough_to_follow():
    """J7 甲: when the Soviets move a jammer into your valley after each wave, staying put meets only the first wave
    and the picks flip every wave; the minimap blip gives time to follow (the way through a valley is long enough to
    walk between any two mouths less than 1500 apart); with jammers not slowing the Soviets there is nothing to read."""
    v = facts()['j7_valley']
    assert all(r['static_meets'] == 1 and r['changes'] == 5 for r in v['follow'].values())
    assert all(r['static_meets'] == 1 for r in v['pursuit'].values())
    assert v['reach'][0] >= 1500.0 and all(x == [0] for x in v['jam_off'].values())


def test_j7_card_a_the_mouth_with_a_base_behind_it_eats_far_more_than_a_head_on_valley():
    """J7 甲: an Empire army alone in a cleared valley, wave after wave with no top-up, is ground down: it holds a
    wave of 2.9x its cost once, 1.7x three times, 1.3x five times; at the valley mouth with the base topping it up
    and the wave coming out in a column it holds ~3.8x every time. Between them is the card's 'punished' window."""
    h, m = facts()['j7_valley']['head_on'], facts()['j7_valley']['at_mouth']
    assert h[1] > h[3] > h[5] and 2.5 < h[1] < 3.5 and 1.4 < h[3] < 2.0
    assert all(3.0 < x < 4.5 for x in m.values()) and m[3] > 1.8 * h[3]


def test_a4_last_a_mass_of_peacekeepers_eats_a_whole_horn_cheaply():
    """A4 甲 last stretch: three mouths at once plus Ghost Kings is not a wall to a base with a mass of Peacekeepers
    (k* well under 1: the army costs less than the horn); the push stays easy up to 2500 a mouth with two Kings."""
    z = facts()['a4_last']
    assert all(r['k'] < graybox_cards.graybox.EASY for r in z['table'].values())
    assert z['table'][(2500, 2)]['need'] < 6000


def test_a4_last_the_ghost_king_is_a_vehicle_killer_and_infantry_ignores_it():
    """The King (3000 hp, 20/s on infantry, 100+/s on vehicles) is no turning point for infantry: they kill it with a
    small loss; only an army of Guardians is in trouble (k* > 2)."""
    z = facts()['a4_last']
    assert z['king_alone']['维和步兵'] < 1 and z['king_alone']['标枪兵'] < 1 and z['king_alone']['守护者坦克'] > 2
    assert z['killed'][4000][1] < 0.1                                # 4000 cost of infantry loses under a tenth


def test_a4_last_the_wall_in_front_of_the_guns_buys_only_a_few_seconds():
    """A 300 hp wall falls to the King in 3 s: a 4000-cost army gets 22% of its health in free fire; useful, not decisive."""
    z = facts()['a4_last']
    assert abs(z['smash'] - 3.0) < 0.5
    assert z['free'][4000] < 0.3 and z['free'][8000] < 0.5


def test_a4_last_the_horn_size_the_army_can_take_grows_with_its_cost():
    """What a horn must weigh is a matter of the economy (kept for 实机): 4000 cost cannot carry even 900 a mouth for six
    horns with a King each from the third, 16000 carries ~2600."""
    z = facts()['a4_last']['biggest_w']
    assert z[4000][1] < 900 < z[8000][1] < z[16000][1]
    assert z[8000][2] < z[8000][1]
