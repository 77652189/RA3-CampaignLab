"""A4's bench checks judged in the plan simulator (experimental/cnv/simbench.py, docs/story/sim-vs-bench-a4.md): the ones
the simulator can stand in for pass on the current plan and map, and fail when the player does nothing (so they
are judging something); a reading the simulator has no rule for is listed as SKIP, never as PASS."""
import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
# loaded by file: simbench.py puts the cnv folders on the path itself (no new sys.path edit here: guard G4's ceiling)
_spec = importlib.util.spec_from_file_location('simbench', ROOT / 'experimental' / 'cnv' / 'simbench.py')
simbench = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(simbench)


DEMO_KILL = pytest.mark.xfail(strict=True, reason=(
    'R8 (2026-11-07): with the reach between bounding circles the opening demo\'s Demo Foe 2 (stopped at (2100, 2720), '
    '157 from the player\'s engineer at the clear mark, radii 7 + 7) shoots the engineer at 61.7 s, so no ice later; '
    'the bench\'s engineer lives -- where the demo foe stops against the ice (or whether it turns at once) is not '
    'modelled; holding fire on the move does not save him (tried)'))


@pytest.mark.parametrize('check', [pytest.param('detour', marks=DEMO_KILL), pytest.param('queue', marks=DEMO_KILL),
                                   'melt', 'smoke', pytest.param('smash', marks=DEMO_KILL), 'win',
                                   pytest.param('derrick', marks=DEMO_KILL)])
def test_the_simulators_version_of_the_check_holds(check):
    status, lines = simbench.run(check)
    assert status == 0, '\n'.join(lines)


@pytest.mark.parametrize('check', ['detour', 'queue', 'melt'])
def test_it_fails_when_the_player_builds_no_wall(check):
    """Mutation: the engineer is gone before the check's ice order, so no wall comes of it -- the check must say so."""
    status, lines = simbench.run(check, script=simbench.NO_ENGINEER)
    assert status == 1 and any(x.startswith('FAIL') for x in lines), '\n'.join(lines)


def _sim_run(build_name, check, until):
    import build
    import sim
    m, t, _ = build.resolve(build_name, check)
    return sim.Sim(m, t).run(until)


def test_r1_lifetime_as_the_bench():
    """R1 (sim.Sim.expire): bench 2026-11-07 `cnv_check engine_life frames` -- a 30 s wall made by a script in frame 1
    is seen by 451 frames' scripts, the area count drops with it (墙A 451451); a 5.5 s core lives 83 frames' and its
    wall 450 (墙B 83450)."""
    a, b, _, _ = _sim_run('engine_life', 'frames', 54.0).series[-1][1]
    assert (a, b) == (451451, 83450)


def test_r5_the_ice_engineer_as_the_bench():
    """R5 (sim.Sim.at_site): the same run, the two engineers' orders at 21 s -- bench 冰C 82002 (within range: the
    core one frame after the order, its 82 frames, then the wall), 冰D 82103 (a 272 walk first). The walk is moved a
    0.5 s tick at a time: within a few frames."""
    _, _, c, d = _sim_run('engine_life', 'frames', 54.0).series[-1][1]
    assert c == 82002
    assert d // 1000 == 82 and abs(d % 1000 - 103) <= 4


def test_r7_the_transport_goes_straight_at_the_quay():
    """R7 (sim.Ground: no bridge decks for amphibians; Ground.closest): bench 2026-11-07 `cnv_check engine_land way`
    -- frames from the order to the first time in each box: shore area 89, before the quay 65, the southern way never
    (the run's end). The simulator has no start-up (about 12 frames): within 15."""
    run = _sim_run('engine_land', 'way', 46.0)
    shore, quay, south_water, south_land = run.series[-1][1]
    assert abs(shore - 89) <= 15 and abs(quay - 65) <= 15
    assert south_water == south_land > 600                  # never there: counted every frame since the order


def test_r7_the_ghost_king_lands_as_on_the_bench():
    """smash: the bench (2026-11-07) read the Ghost King ashore at s58; before R7 the simulator had s75."""
    status, lines = simbench.run('smash')
    import re
    row = next(x for x in lines if x.startswith('counters'))
    start = next(int(s) for s, _, king in re.findall(r's(\d+)(?:-s\d+)?: (\S+) (\S+)', row) if king != '0')
    assert abs(start - 58) <= 3, row


def test_advance_in_slices_is_run():
    """Sim.advance (simproxy's player plays a slice at a time): 54 one-second slices and a last 7 frames make the same
    run as run(54) -- the same ticks, readings and log."""
    import build
    import sim
    m, t, _ = build.resolve('engine_life', 'frames')
    whole = sim.Sim(m, t).run(54.0)
    m, t, _ = build.resolve('engine_life', 'frames')
    part = sim.Sim(m, t)
    for _ in range(54):
        part.advance(15)
    part.advance(7)
    assert part.t == whole.t and part.series == whole.series and part.log == whole.log


def test_r6_win_is_won_by_the_top_up_not_by_a_fight_left_out():
    """R6 (sim.Sim.deal: the fire dealt frame by frame, after the frame's scripts): win runs with the fight on and is
    won (test_the_simulators_version_of_the_check_holds); the same run without the check's top-up of the trucks must
    be lost -- the fight is real, the top-up is what holds it."""
    import build
    import sim
    m, t, _ = build.resolve(simbench.LEVEL, 'win')
    t.scripts = [s for s in t.scripts if s.name != 'Test - keep the trucks up']
    s = sim.Sim(m, t).run(simbench.UNTIL['win'])
    assert 'combat' in s.used and s.ending_line().startswith('结局：输'), s.ending_line()


def test_a_counter_the_simulator_cannot_read_is_skipped_not_passed():
    """A counter listed blind (a rule the simulator lacks) is taken out of the judged expectations and said as SKIP
    (smash's wall health was, before R2 / R3: a reference nobody set reads 0, and '< 100' took it for a hit)."""
    import build
    _, t, _ = build.resolve(simbench.LEVEL, 'smash')
    keep, skip = simbench.judged(t, {'目标墙血量': 'no rule'})
    assert any(x.startswith('SKIP 目标墙血量') for x in skip)
    assert not any(e[0] == '目标墙血量' for e in keep) and keep


def _series(lines, label_count=2):
    """The counters row of a simbench run as [(second, (values...))] at each change."""
    import re
    row = next(x for x in lines if x.startswith('counters'))
    pat = r's(\d+)(?:-s\d+)?: ' + ' '.join([r'(\S+)'] * label_count)
    return [(int(m[0]), m[1:]) for m in re.findall(pat, row)]


def test_r4_the_engineer_takes_the_derrick_as_on_the_bench():
    """R4 (sim.Sim.capture_due / deposit_due): bench 2026-11-07 `cnv_check a4 derrick` -- the derrick the player's
    at the first reading after the order (s4) with 500 (the capture bonus), 515 at s7, 800 at s46 (15 every 2 s)."""
    status, lines = simbench.run('derrick')
    got = _series(lines)
    taken = next(s for s, (ours, _) in got if ours == '1')
    money = {s: int(v) for s, (_, v) in got}
    assert abs(taken - 4) <= 1 and money[taken] == 500, got
    at = lambda sec: money[max(s for s in money if s <= sec)]
    assert abs(at(7) - 515) <= 15 and abs(at(46) - 800) <= 15, got


@pytest.mark.parametrize('variant, gone', [('ref_a', 2), ('ref_a2', 2), ('ref_b', 1), ('ref_c', 0)])
def test_r2_the_reference_picks_the_wall_the_bench_did(variant, gone):
    """R2 (sim.Sim.nearest_ref): bench 2026-11-07 `cnv_check <variant> frames` (checks/engine_ref.py) -- the wall the
    reference was deleted through: C, nearest the team's middle, whichever member was made first (a, a2); B when C
    has a script name (b); A, nearest the map's corner, for an empty team (c)."""
    series = _sim_run(variant, 'frames', 16.0).series
    walls = series[-1][1][:3]
    assert walls == [0 if k == gone else 1 for k in range(3)], series[-1]


@DEMO_KILL
def test_r3_the_ghost_king_smashes_the_wall_as_on_the_bench():
    """R2 + R3 (sim.Ground.within: an attacker goes to a spot in range, not round the wall to the cell nearest its
    middle): bench 2026-11-07 `cnv_check a4 smash` -- ashore s58, the wall's health 100 to s67, 76 at s70, 53 s73,
    41 s76, 18 s79, 6 s82, the wall gone at s82 (smashed, before its 30 s were up). Before R3's way the simulator
    took the King round the wall's far side: first damage s78, the wall melted at 40."""
    status, lines = simbench.run('smash')
    got = _series(lines, 3)
    hurt = next(s for s, (_, _, h) in got if h not in ('0', '100'))
    gone = next(s for s, (w, _, _) in got if s > 40 and w == '0')
    assert abs(hurt - 69) <= 2 and abs(gone - 82) <= 3, got


def test_r4_no_engineer_no_derrick():
    """Mutation: the engineer deleted before the order -- the derrick stays neutral and no money comes."""
    status, lines = simbench.run('derrick', script=['0 删除 UNIT - Test Engineer'])
    assert status == 1 and any(x.startswith('FAIL 资金') for x in lines), '\n'.join(lines)


# ---- production: the second hook for simproxy's player (sim.Sim.offers / order_build / produce_due)
# bench 2026-11-05 engine_production (docs/engine/production.md): (帧数, 资金) pairs read on the bench, 帧数 when the
# engineer is first counted -- the same table the engine line's model is held to (RA3-EngineModel BENCH_PRODUCTION)
BENCH_PRODUCTION = {'a': ([(16, 1946), (25, 1916), (31, 1896), (39, 1870), (145, 1516), (153, 1500)], 160),
                    'b': ([(133, 3), (150, 1953), (157, 1929), (210, 1753)], 221),
                    # short of power (sim.Sim.build_frames): c supply 0 / demand 25 -> f 0.3, 495 frames;
                    # d 50 / 75 -> f 0.5 (at most 0.5 while short), 300 frames
                    'c': ([(132, 1866), (488, 1507), (496, 1500)], 505),
                    'd': ([(132, 1780), (299, 1501)], 309)}


def _production_rows(check, order=True):
    """The check run in the simulator with the engineer ordered at frame 30 (the bench clicks the sidebar), the
    counters read after every frame's production."""
    import build
    import sim
    m, t, _ = build.resolve('engine_production', check)
    s = sim.Sim(m, t)
    rows, done = [], s.produce_due

    def read(frame):
        done(frame)
        rows.append({lab: s.counters.get(c, 0) for c, lab in t.counters})
    s.produce_due = read
    s.advance(30)
    offered = [o[0] for o in s.offers(s.human)]
    if order:
        assert s.order_build(s.human, 'AlliedEngineer')
    s.advance(45 * 15 - 30)
    return s, rows, offered


@pytest.mark.parametrize('check', sorted(BENCH_PRODUCTION))
def test_production_pays_as_it_builds_and_comes_out_after_the_door(check):
    """a: 10 s = 150 frames, ceil(500 k / 150) paid by k, full at the 151st (single float), out 10 frames on;
    b: 250 runs out at 3 (owes 251 at k 75), stands until the 2000 come, then goes on."""
    s, rows, offered = _production_rows(check)
    pairs, made = BENCH_PRODUCTION[check]
    money = {}
    for rd in rows:
        money.setdefault(rd['帧数'], rd['资金'])
    assert [(k, money.get(k)) for k, _ in pairs] == pairs
    assert next(rd['帧数'] for rd in rows if rd['工程师'] >= 1) == made
    assert next(rd['出口位'] for rd in rows if rd['出口位']) == 101      # out at UnitCreatePoint, as on the bench
    assert offered[:4] == ['AlliedScoutInfantry', 'AlliedAntiInfantryInfantry', 'AlliedAntiVehicleInfantry',
                           'AlliedEngineer']   # the barracks' tier-1 buttons; the spy needs Upgrade_AlliedTech2


@pytest.mark.parametrize('check, power, factor', [('a', (150, 25), 1.0), ('c', (0, 25), 0.3), ('d', (50, 75), 0.5)])
def test_power_is_the_living_objects_energy(check, power, factor):
    """Supply and demand from EnergyProduction of what still stands (yard +50, plant +100, barracks -25 each), the
    low-power factor from them; PLAYER_EXCESS_POWER_COMPARE_VALUE reads supply - demand."""
    import build
    import sim
    m, t, _ = build.resolve('engine_production', check)
    s = sim.Sim(m, t)
    s.advance(30)
    assert s.power(s.human) == power
    assert sim.power_factor(*power) == pytest.approx(factor)
    assert s.cond('PLAYER_EXCESS_POWER_COMPARE_VALUE', [s.human, 2, power[0] - power[1]])


def test_production_needs_a_factory_and_its_prerequisites():
    """Nothing is offered or queued without a factory of the player's; a unit whose NeededUpgrade the barracks lacks is
    not offered until the yard holds it (NAMED_RECEIVE_UPGRADE; GIVE_PLAYER_UPGRADE gives nothing: engine_tech b); a
    banned one (ALLOW_DISALLOW_ONE_BUILDING 0) is not."""
    import build
    import sim
    m, t, _ = build.resolve('engine_production', 'a')
    s = sim.Sim(m, t)
    s.advance(15)
    names = [o[0] for o in s.offers(s.human)]
    assert 'AlliedEngineer' in names and 'AlliedInfiltrationInfantry' not in names
    s.act('GIVE_PLAYER_UPGRADE', [s.human, 'Upgrade_AlliedTech2'], None)
    assert 'AlliedInfiltrationInfantry' not in [o[0] for o in s.offers(s.human)]
    yard = next(b for b in s.living() if b.owner == s.human and b.template == 'AlliedConstructionYard')
    s.act('NAMED_RECEIVE_UPGRADE', ['Upgrade_AlliedTech2', yard.name], None)
    assert 'AlliedInfiltrationInfantry' in [o[0] for o in s.offers(s.human)]
    s.act('ALLOW_DISALLOW_ONE_BUILDING', [s.human, 'alliedengineer', 0], None)
    assert 'AlliedEngineer' not in [o[0] for o in s.offers(s.human)] and not s.order_build(s.human, 'AlliedEngineer')
    for f in s.factories(s.human):
        s.destroy(f, 'test', delete=True)
    assert [o for o in s.offers(s.human) if not o[0].startswith('Upgrade_')] == [] and \
        not s.order_build(s.human, 'AlliedAntiInfantryInfantry')


# ---- skills: a unit's ground power, its reload and placing rules (sim.Sim.act NAMED_FIRE_SPECIAL_POWER_AT_WAYPOINT,
# order_power). bench 2026-11-07 engine_skill (checks/engine_skill.py): per spot, units = frames from the order to the
# core, thousands = frames it stood. A script's cast heeds neither the 20 s reload, ForbiddenObjectRange 32 nor
# PATHABLE_ONLY. c's 平D (a 400 walk first) is left to R5's test; 走D only counts the walk.
BENCH_SKILL = {'a': (82002, 82003, 82003), 'b': (82002, 82002, 82002), 'c': (82004, 82002, 82103), 'w': (82004,)}


@pytest.mark.parametrize('variant', sorted(BENCH_SKILL))
def test_skill_a_scripted_cast_builds_whatever_the_reload_or_the_spot(variant):
    """Every core comes and stands its 82 frames; the frame it comes within 2 of the bench's (the simulator has every
    in-range core 1 frame after its order; the bench 2-3 frames for a, 4 on the cliff edge and in the sea -- the 2 more
    not explained) and the walked D within 4 (as R5)."""
    rows = _sim_run('engine_skill', variant, 60.0).series[-1][1]
    for got, want in zip(rows, BENCH_SKILL[variant]):
        assert got // 1000 == want // 1000
        assert abs(got % 1000 - want % 1000) <= (4 if want % 1000 > 50 else 2)


def _skill(variant):
    import build
    import sim
    m, t, _ = build.resolve('engine_skill', variant)
    s = sim.Sim(m, t)
    s.advance(15)
    return m, s


def test_skill_the_players_click_waits_for_the_reload():
    """order_power (INFERRED: the click itself not measured): goes, then refused till ReloadTime x 15 = 300 frames on --
    the script's cast starts the reload too."""
    m, s = _skill('a')
    b, power = s.body(m.role('engineer a').name), m.ability('engineer a', 'freeze')
    assert s.order_power(b, power, s.point(m.mark('a1'))) == (True, None)
    s.advance(8 * 15)
    assert s.order_power(b, power, s.point(m.mark('a2'))) == (False, 'reloading')
    s.advance(300 - 8 * 15)
    assert s.order_power(b, power, s.point(m.mark('a2')))[0]


def test_skill_the_players_click_keeps_off_objects_and_unpathable_ground():
    """INFERRED: within ForbiddenObjectRange 32 of the tank's centre refused (20), clear of it (40, 60) not; a point in
    the sea refused (PATHABLE_ONLY)."""
    m, s = _skill('b')
    power = m.ability('engineer b1', 'freeze')
    got = [s.order_power(s.body(m.role(f'engineer b{k}').name), power, s.point(m.mark(f'b{k}')))[1] for k in (1, 2, 3)]
    assert got == ['too near an object', None, None]
    m, s = _skill('w')
    b = s.body(m.role('engineer w').name)
    assert s.order_power(b, m.ability('engineer w', 'freeze'), s.point(m.mark('w'))) == (False, 'not pathable')


# ---- tech tiers: what lets a factory build a tier-2 unit (sim.Sim.holds_upgrade / can_build / upgrade_sellers)
# bench 2026-11-07 engine_tech (checks/engine_tech.py): the Guardian (NeededUpgrade Upgrade_AlliedTech2, 950) clicked
# at ~s16 -- built only in c (the yard holds Tech2, the factory 300 off); e: the player buys Tech2 on the yard
# (1500, 15 s, paid frame by frame), then the Guardian builds
BENCH_TECH = {'a': False, 'b': False, 'c': True, 'd': False, 'g': False, 'h': False}


def _tech(variant, order_at=16 * 15, until=30 * 15):
    import build
    import sim
    m, t, _ = build.resolve('engine_tech', variant)
    s = sim.Sim(m, t)
    s.advance(order_at)
    ordered = s.order_build(s.human, 'AlliedAntiVehicleVehicleTech1')
    s.advance(until - order_at)
    return s, ordered


@pytest.mark.parametrize('variant', sorted(BENCH_TECH))
def test_tech_the_guardian_builds_only_near_a_yard_holding_tech2(variant):
    s, ordered = _tech(variant)
    made = s.counters.get('CNV_Tech_Made', 0)
    assert ordered == BENCH_TECH[variant] and (made >= 1) == BENCH_TECH[variant]
    assert s.money[s.human] < 4000 if BENCH_TECH[variant] else s.money[s.human] >= 4000


def test_tech_bought_on_the_yard_then_the_guardian():
    """e: Tech2 on the yard's button (needs the refinery), 1500 over 15 s paid as a unit is; the yard's button then
    buys Tech3; the Guardian builds after it."""
    import build
    import sim
    m, t, _ = build.resolve('engine_tech', 'e')
    s = sim.Sim(m, t)
    s.advance(15)
    guard = 'AlliedAntiVehicleVehicleTech1'
    names = [o[0] for o in s.offers(s.human)]
    assert 'Upgrade_AlliedTech2' in names and guard not in names
    assert s.order_build(s.human, 'Upgrade_AlliedTech2') and not s.order_build(s.human, 'Upgrade_AlliedTech2')
    start = s.money[s.human]
    s.advance(8 * 15)
    assert start - 1500 < s.money[s.human] < start          # paid as it goes (the refinery's income aside)
    assert not s.order_build(s.human, guard)
    s.advance(8 * 15)
    names = [o[0] for o in s.offers(s.human)]
    assert guard in names and 'Upgrade_AlliedTech3' in names and 'Upgrade_AlliedTech2' not in names
    assert s.order_build(s.human, guard)
    s.advance(25 * 15)
    assert s.counters.get('CNV_Tech_Made', 0) >= 1


def test_tech_banned_and_needs_the_refinery():
    """ALLOW_DISALLOW_ONE_UPGRADE 0 takes the yard's button away (retail campaigns ban Tech2/3 so); without a
    refinery it is grey (bench: tooltip 'needs refinery')."""
    import build
    import sim
    m, t, _ = build.resolve('engine_tech', 'e')
    s = sim.Sim(m, t)
    s.advance(15)
    s.act('ALLOW_DISALLOW_ONE_UPGRADE', [s.human, 'upgrade_alliedtech2', 0], None)
    assert not any(o[0] == 'Upgrade_AlliedTech2' for o in s.offers(s.human))
    s.act('ALLOW_DISALLOW_ONE_UPGRADE', [s.human, 'upgrade_alliedtech2', 1], None)
    ref = next(b for b in s.living() if b.owner == s.human and b.template == 'AlliedRefinery')
    s.destroy(ref, 'test', delete=True)
    assert not s.order_build(s.human, 'Upgrade_AlliedTech2')


def test_production_mutation_no_order_no_engineer():
    """Mutation: without the order the money stays and no engineer comes -- the readings above are the order's."""
    s, rows, _ = _production_rows('a', order=False)
    assert all(rd['工程师'] == 0 for rd in rows) and s.money[s.human] == 2000


# ---- R8: how far a unit reaches and goes after an enemy by itself (sim.Sim.in_range / idle_chase)
# bench 2026-11-07 engine_acquire (readings in checks/engine_acquire.py): an enemy Guardian (weapon 150, VisionRange
# 200, radius 23.3 like the player's NO_ATTACK tank) idle with the tank d north of it; guard / attack-move beside it
def _acquire_rows(variant):
    import build
    import sim
    m, t, _ = build.resolve(f'acquire_{variant}', 'frames')
    s = sim.Sim(m, t)
    s.run(26.0)
    labels = [lab for _, lab in t.counters]
    return [dict(zip(labels, row)) for k, row in s.series if k >= 1]


def test_r8_idle_180_fires_where_it_stands():
    """Bench: never out of 15 of its spot, the tank hurt from s2 -- 180 centre to centre is within 150 + the radii."""
    rows = _acquire_rows('idle180')
    assert all(r['原地'] == 1 for r in rows)
    assert rows[1]['坦克血'] < 100


@pytest.mark.parametrize('variant', ['idle200', 'idle220'])
def test_r8_idle_within_sight_walks_up_fires_and_comes_back(variant):
    """Bench: out of its spot from s1 (it walked up), the tank hurt from s2, back within 15 once the tank is done
    (bench s16, the tank left at 3; the simulator kills it at s17 and is back by s18)."""
    rows = _acquire_rows(variant)
    assert rows[1]['原地'] == 0 and rows[1]['坦克血'] < 100
    assert rows[-1]['原地'] == 1 and rows[-1]['坦克血'] <= 3


@pytest.mark.parametrize('variant', ['idle240', 'idle260', 'guard260'])
def test_r8_beyond_sight_nothing(variant):
    """Bench: no move, no shot at 240 / 260 (beyond VisionRange 200 + the tank's radius), nor when guarding at 260."""
    rows = _acquire_rows(variant)
    assert all(r['原地'] == 1 and r['坦克血'] == 100 for r in rows)


@pytest.mark.parametrize('variant', ['am260', 'am400'])
def test_r8_attack_move_past_does_not_turn_aside(variant):
    """Bench: walks straight to E (终点 from s7), the tank 260 / 400 beside the path untouched."""
    rows = _acquire_rows(variant)
    assert rows[-1]['终点'] == 1 and all(r['坦克血'] == 100 for r in rows)


# ---- re-ordering: the same attack order given again every frame (sim.Sim.order_attack ignores it)
# bench 2026-11-07 engine_reorder (readings in checks/engine_reorder.py): straight on, round a wall line (dt*), and
# standing in range but turned 90 degrees away (tu*), King or Guardian, every frame or once: all walk and fire alike,
# the wall hurt from s10 (straight), s16 (dt King), s13 (dt Guardian), s14 (tu King), s13 (tu Guardian). A4's King
# stalling on the bridge under every-frame orders (level line 06282d5) did not show on the island (no bridge there).
def _reorder_rows(variant, until):
    import build
    import sim
    m, t, _ = build.resolve(f'reorder_{variant}', 'frames')
    s = sim.Sim(m, t)
    s.run(until)
    labels = [lab for _, lab in t.counters]
    return [(k, dict(zip(labels, row))) for k, row in s.series if k >= 1]


@pytest.mark.parametrize('once, every, until, bench', [('once', 'every', 25.0, 10), ('dt1', 'dtev', 45.0, 16),
                                                       ('tu1', 'tuev', 35.0, 14)])
def test_reorder_every_frame_is_the_order_once(once, every, until, bench):
    """The every-frame variant runs row for row as the once one, and the wall is hurt within 3 s of the bench (the
    simulator starts ~1-2 s late: no acceleration)."""
    a, b = _reorder_rows(once, until), _reorder_rows(every, until)
    assert a == b
    hp = next(k for k in a[0][1] if '血' in k)
    first = next(k for k, r in a if r[hp] < 100)
    assert abs(first - bench) <= 3


@pytest.mark.parametrize('variant, until, bench', [('dtevg', 50.0, 13), ('tuevg', 35.0, 13)])
def test_reorder_every_frame_guardian(variant, until, bench):
    rows = _reorder_rows(variant, until)
    hp = next(k for k in rows[0][1] if '血' in k)
    assert abs(next(k for k, r in rows if r[hp] < 100) - bench) <= 3


# ---- power: a POWERED structure of a player short of power holds its fire (sim.Sim.unpowered)
# bench 2026-11-07 engine_powerdef (readings in checks/engine_powerdef.py): s1's Tesla coil (-75) beside six NO_ATTACK
# Guardians; on (a plant +100): first loss at 111, then one per ~125 frames; off (no plant): none in 728; cut (the
# plant deleted ~150): none after; back (a plant made by script ~150): first loss at 475
def _powerdef(variant, until=50.0):
    import build
    import sim
    m, t, _ = build.resolve(f'powerdef_{variant}', 'frames')
    s = sim.Sim(m, t)
    s.run(until)
    labels = [lab for _, lab in t.counters]
    return s, [dict(zip(labels, row)) for k, row in s.series if k >= 1]


def test_power_off_the_coil_never_fires():
    s, rows = _powerdef('off')
    assert rows[-1]['帧数'] >= 728 and all(r['坦克'] == 6 for r in rows)


def test_power_cut_the_coil_stops():
    """Mutation of on: the plant deleted, the coil is unpowered from then on."""
    s, rows = _powerdef('cut', until=12.0)
    coil = next(b for b in s.living() if b.template == 'SovietBaseDefenseAdvanced')
    assert s.short_of_power(coil.owner) and s.unpowered(coil)
    s2, _ = _powerdef('on', until=12.0)
    assert not s2.unpowered(next(b for b in s2.living() if b.template == 'SovietBaseDefenseAdvanced'))


def test_power_back_after_the_plant_unpacks():
    """A plant made short of power unpacks trunc((2 - 0.3) x 150) = 255 frames before it counts (RA3 0x720100); the
    coil fires after that: no loss before, the first after (bench: 475, ~325 after the plant)."""
    s, rows = _powerdef('back')
    plant = next(b for b in s.bodies.values() if b.template == 'SovietPowerPlant')
    made = int(round(plant.made_at * 15))
    assert abs(plant.unpack_end - made - 255) <= 1          # made_at is the tick's second, the frame the script's
    first = next(r['帧数'] for r in rows if r['坦克'] < 6)
    assert plant.unpack_end <= first <= 475


@pytest.mark.xfail(strict=True, reason='the coil kills a tank a second in the simulator (damage per second over a '
                   'continuous cycle), one per ~125 frames on the bench: the fight model does not shoot by the clip '
                   '(round 77 "战斗按弹夹的节奏")')
def test_power_on_the_coil_kills_one_tank_per_125_frames():
    s, rows = _powerdef('on')
    lost = [r['帧数'] for i, r in enumerate(rows) if i and r['坦克'] < rows[i - 1]['坦克']]
    assert 100 <= lost[1] - lost[0] <= 150
