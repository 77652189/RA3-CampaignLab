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


# DEMO_KILL (strict xfail 2026-11-07, green since sim.Sim.held_up): the opening demo's pair, stopped by the ice 157
# from the player's engineer, counted idle and shot him at 61.7 s; on the bench (`a4 demoeng`) he lives the whole
# demonstration. A plain move stopped short is still on its move now: no fire, no chase till its next order.
@pytest.mark.parametrize('check', ['detour', 'queue', 'melt', 'smoke', 'smash', 'win', 'derrick'])
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
    """order_power: goes, then refused till ReloadTime x 15 = 300 frames on -- the script's cast starts the reload too.
    Bench engine_skill d (by hand): his second click 8 s after the first refused, 21 s after it went."""
    m, s = _skill('a')
    b, power = s.body(m.role('engineer a').name), m.ability('engineer a', 'freeze')
    assert s.order_power(b, power, s.point(m.mark('a1'))) == (True, None)
    s.advance(8 * 15)
    assert s.order_power(b, power, s.point(m.mark('a3'))) == (False, 'reloading')
    s.advance(300 - 8 * 15)
    assert s.order_power(b, power, s.point(m.mark('a3')))[0]      # (a2 lies by an ore node: refused for that)


def test_skill_the_players_click_keeps_off_objects_and_unpathable_ground():
    """Bench engine_skill d (clicked by hand): our own tank 20 / 40 / 60 from the spot blocks nothing; the ore node
    (box 33 x 41) refuses a2, 75 from its centre, not a point 123 from it; the sea (w) and the cliff (c1) refuse."""
    m, s = _skill('d')
    power = m.ability('engineer a', 'freeze')
    got = [s.power_refusal(s.body(m.role(f'engineer b{k}').name), power, *s.point(m.mark(f'b{k}'))) for k in (1, 2, 3)]
    assert got == [None, None, None]
    a, d = s.body(m.role('engineer a').name), s.body(m.role('engineer d').name)
    assert s.power_refusal(a, power, *s.point(m.mark('a2'))) == 'too near an object'
    assert s.power_refusal(d, power, 790.0, 2100.0) is None
    for e, spot in (('engineer w', 'w'), ('engineer c', 'c1')):
        assert s.order_power(s.body(m.role(e).name), power, s.point(m.mark(spot))) == (False, 'not pathable')


# ---- superweapons: a script's cast at a waypoint (sim.SUPERWEAPON_HITS, Sim.blast_due). bench 2026-11-07 engine_super
# p (checks/engine_super.py): health % of base defenses (1000) at 0 / 150 / 240 / 300 from the waypoint, ended
# 44 / 7 / 12 / 100; q: the first loss 56 frames after the cast (+-1)
def test_super_the_proton_collider_ends_as_the_bench():
    rows = _sim_run('engine_super', 'p', 30.0).series[-1][1]
    assert [abs(g - w) <= 2 for g, w in zip(rows, (44, 7, 12, 100))] == [True] * 4, rows


def test_super_the_proton_collider_hits_56_frames_after_the_cast():
    rows = _sim_run('engine_super', 'q', 30.0).series[-1][1]
    assert abs(rows[1] - 56) <= 1, rows        # 满血帧: frames the centre target stayed whole after the cast


def test_super_a_scripts_cast_starts_the_retail_reload():
    """The proton collider's script cast (p) starts its reload: bench engine_super f -- ready again 5550 frames after the
    cast (ReloadTime 360 s = 5400 from the SDK's GlobalData SpecialPowerTemplates.xml + sim.RELOAD_LAG 150; every cast
    restarts it, RA3 1.13 0x7dea80, read): the player's click refused (order_power, INFERRED) until it is over."""
    import build
    import sim
    m, t, _ = build.resolve('engine_super', 'p')
    s = sim.Sim(m, t)
    s.advance(30 * 15)
    b = next(b for b in s.bodies.values() if b.template == 'AlliedSuperWeaponAdvanced')
    power = 'SpecialPowerParticleCannon'
    assert b.ready_at[power] - s.frame_now() > 5400 - 30 * 15 and abs(b.ready_at[power] - 90 - 5550) <= 2 and s.order_power(b, power, (b.x + 500, b.y))[1] == 'reloading'
    s.advance(b.ready_at[power] - s.frame_now())
    assert s.order_power(b, power, (b.x + 500, b.y)) == (True, None)


def test_super_the_vacuum_imploder_ends_as_the_bench():
    """v: 满血帧 62, health % at 0 / 150 / 280 end 5 / 1 / 1; w: the one at 350 untouched."""
    v = _sim_run('engine_super', 'v', 30.0).series[-1][1]
    assert abs(v[0] - 62) <= 1 and [abs(g - w) <= 2 for g, w in zip(v[1:], (5, 1, 1))] == [True] * 3, v
    w = _sim_run('engine_super', 'w', 30.0).series[-1][1]
    assert w[-1] == 100, w


def test_super_the_psionic_decimator_kills_within_300_at_61_frames():
    """e: the base defenses (1000) at 0 and 250 whole 61 frames after the cast, then dead; 350 whole to the end (the
    bench's counters freeze at a dead object's last health, so only the 满血 frames compare)."""
    e = dict(zip(('full0', 'full250', 'full350', 'h250'), _sim_run('engine_super', 'e', 34.0).series[-1][1]))
    assert abs(e['full0'] - 61) <= 1 and abs(e['full250'] - 61) <= 1 and e['full350'] > 400, e


def test_super_the_nanoswarm_keeps_200_out_of_fire():
    """n: tanks at 0 and 150 from the hive's spot whole against enemy fire to the end (497 frames; NAMED_DAMAGE goes
    through -- the bench's two 10 % scripted hits are not in the simulator's run), 250 shot down (bench 1 % by 180)."""
    n = _sim_run('engine_super', 'n', 34.0).series[-1][1]
    assert n[-3:-1] == [100, 100] and n[-1] <= 10, n


def test_super_the_iron_curtain_reaches_800():
    """g / a (each tank shot by an enemy of its own): 满血 frames of tanks at 100 / 300 / 500 / 800 bench 353 / 357 /
    351 / 354 (covered), at 850 / 950 / 1050 / 1150 bench 20 / 23 / 23 / 25 (not)."""
    g = _sim_run('engine_super', 'g', 34.0).series[-1][1]
    a = _sim_run('engine_super', 'a', 34.0).series[-1][1]
    assert all(abs(x - 354) <= 6 for x in g) and all(x <= 30 for x in a), (g, a)


def test_super_the_iron_curtain_reaches_the_tanks_edge():
    """o (rerun 2026-11-07 after the vacuum spot moved): tanks 770 / 807 from the cast whole until frame 361, the one
    at 872 shot from frame 32; the first o run had 832 shot from ~28. Centre distance less the tank's radius 23.3 within
    800 (sim.CURTAIN, measured like R8's reach); by centre alone the 807 one is left out."""
    by = {r[0]: r[1:] for _, r in _sim_run('engine_super', 'o', 34.0).series}
    assert by[347][:2] == [100, 100] and by[347][2] < 100, by[347]


def test_super_the_iron_curtain_holds_off_fire_some_23_seconds():
    """j: both tanks (0 and 150 from the waypoint) whole until frame ~354 after the cast, then the enemy's fire takes
    them down (bench 86 / 73 / 60 % at 362 / 391 / 422: a volley, where the simulator's fire is steady, 72 at 422)."""
    by = {r[0]: r[1:] for _, r in _sim_run('engine_super', 'j', 34.0).series}
    assert by[347] == [100, 100, 0] and by[362][0] < 100 and by[422][0] <= 75, by


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


# ---- mining (HOOKS 7): engine_mining's layout -- the refinery 180 from a lone node -- on Niagara's bluff ore (the
# probe map has no ground for the simulator); the loop alone (mine_due), frames from 0
def _mining(miners=1, frames=1200):
    import build
    import sim
    m, _, _ = build.resolve('aiskirm', None)
    s = sim.Sim(m, None)
    node = next(b for b in s.living() if b.template == 'OreNode' and b.x > 3300 and b.y < 1400)
    p = s.human
    s.add('test refinery', 'AlliedRefinery', p, node.x + 180.0, node.y)
    for k in range(miners):
        s.add(f'test miner {k}', 'AlliedMiner', p, node.x + 180.0, node.y)
    s.money[p] = 0
    got = []
    for fr in range(frames):
        s.mine_due(fr)
        got.append(s.money[p])
    return got


def test_mining_pays_8_a_frame_and_a_trip_takes_269():
    """bench engine_mining a: 250 in 30 frames (8 a frame, the rest on the last), the next trip's first money 269
    frames after the last's (the trip's drives fitted to it, sim.MINE_DRIVE_EXTRA)."""
    got = _mining()
    starts = [f for f in range(1, len(got)) if got[f] > got[f - 1] and got[f - 1] % 250 == 0]
    first = starts[0]
    assert [got[first + k] - got[first - 1] for k in (0, 1, 8, 28, 29)] == [8, 16, 72, 232, 250]
    assert [b - a for a, b in zip(starts, starts[1:])] == [269] * (len(starts) - 1) and len(starts) >= 3


def test_mining_a_second_miner_on_one_node_adds_nothing():
    """bench engine_mining b / d: two miners on one node earn what one does -- the other waits there for good (the
    retail node has no queue place)."""
    assert _mining(miners=2) == _mining(miners=1)


# ---- air (ADR 0022 item 5): flight over terrain, anti-air reach, air-to-ground (sim.Ground.route 'air', Sim.can_hit,
# Sim.in_range; simunits weapon inheritFrom). bench 2026-11-08 engine_air (readings in checks/engine_air.py, map
# maps/probe_air.py): a Twinblade (Speed 150, radius 19.4) flies 1 200 over flat ground, a sea trench or a cliff;
# hovers before a flak cannon (300, radius 14-21) / a flak trooper (anti-air 300 by inheritFrom) / a Guardian
# (no ANTI_AIRBORNE); attacks a NO_ATTACK Guardian 600 off. A Twinblade placed by the map is an air target from the
# start, as the simulator has it (bench 2026-11-08 land_*: shot by the flak cannon from frame ~18 and by the flak
# trooper with no order, never by a Guardian; it fires where it stands); the 11-07 "placed, it stands on the ground"
# was not reproduced, so the probe's move at Go changes nothing.
def _air_rows(variant, until=25.0):
    import build
    import sim
    m, t, _ = build.resolve(f'air_{variant}', 'frames')
    s = sim.Sim(m, t)
    s.run(until)
    labels = [lab for _, lab in t.counters]
    return [(k, dict(zip(labels, row))) for k, row in s.series if k >= 1]


@pytest.mark.parametrize('variant', ['fly_flat', 'fly_sea', 'fly_cliff'])
def test_air_flies_straight_over_sea_and_cliff_at_its_speed(variant):
    """Bench: 114 frames from Go to the end box, the middle box at s4-s5, whatever lies under the lane. The
    simulator has no acceleration (bench ~0.5 s): 8 frames early is in."""
    rows = _air_rows(variant, 12.0)
    flown = next(r['飞帧'] for _, r in rows if r['到达'] == 1)
    assert abs(flown - 114) <= 10
    mid = [k for k, r in rows if r['中途'] == 1]
    assert mid and abs(mid[0] - 4) <= 1


@pytest.mark.parametrize('variant, hit', [('gun280', True), ('gun320', True), ('gun370', False),
                                          ('flak280', True), ('flak312', True)])
def test_air_anti_air_reaches_edge_to_edge_on_the_flat(variant, hit):
    """Bench: the flak cannon fires at 320 centre to centre (300 + both radii, 2D: with the 130 flight height counted
    it would not) and not at 370; the flak trooper's anti-air weapon (written as inheritFrom: no damage of its own)
    fires in place at 280 and 312. The cannon kills by s5 (bench 4 left at s5), the trooper takes ~4 a second (the
    simulator ~5.5: dead s18 against the bench's 4 at s24)."""
    rows = _air_rows(variant)
    assert all(r['原地'] == 1 for _, r in rows)
    if not hit:
        assert all(r['机血'] == 100 for _, r in rows)
        return
    assert rows[0][1]['机血'] < 100
    gone = next(k for k, r in rows if r['机血'] <= 5)
    assert abs(gone - (5 if variant.startswith('gun') else 22)) <= 4


@pytest.mark.xfail(strict=True, reason='bench engine_air flak354: with both sides revealed the idle trooper walked in '
                   'on a Twinblade 354 off (334 beyond its radius, vision 200) and shot it; idle_chase only goes '
                   'within VisionRange + the target radius (R8, read unrevealed) -- the scan with a reveal not known')
def test_air_flak_trooper_walks_in_from_354_when_revealed():
    rows = _air_rows('flak354')
    assert any(r['原地'] == 0 for _, r in rows) and rows[-1][1]['机血'] < 50


def test_air_a_guardian_does_not_shoot_up():
    rows = _air_rows('noaa', 20.0)
    assert all(r['机血'] == 100 and r['原地'] == 1 for _, r in rows)


def test_air_a_placed_twinblade_is_an_air_target_from_the_start():
    """Bench land_still (no order): the gun's first hit ~frame 18 (the simulator: frame 1), 66 at s1, 4 from s5;
    land_flak: the trooper fires in place, 91 at s1, 4 at s24 (the simulator ~3 tenths faster, as flak280);
    land_gun: a Guardian 100 off never touches it."""
    rows = _air_rows('land_still', 15.0)
    assert rows[0][1]['机血'] < 100
    assert abs(next(k for k, r in rows if r['机血'] <= 5) - 5) <= 2
    rows = _air_rows('land_flak')
    assert rows[0][1]['机血'] < 100 and all(r['原地'] == 1 for _, r in rows)
    assert abs(next(k for k, r in rows if r['机血'] <= 5) - 22) <= 5
    assert all(r['机血'] == 100 for _, r in _air_rows('land_gun'))


@pytest.mark.parametrize('variant', ['land_idle', 'land_atk'])
def test_air_a_placed_twinblade_fires_where_it_stands(variant):
    """Bench: with no order (land_idle) or an attack order at 2 s (land_atk) it hits the Guardian 120 off from s1
    without leaving its spot; the tank 38 at s16, 1 from s17 (land_atk: 10 at s18, 1 from s19)."""
    rows = _air_rows(variant, 20.0)
    assert rows[0][1]['坦克血'] < 100 and all(r['原地'] == 1 for _, r in rows)
    assert abs(next(k for k, r in rows if r['坦克血'] <= 10) - 17) <= 3


def test_air_the_twinblade_attacks_from_its_reach_not_overhead():
    """Bench: within 300 from s3, 200 from s4, never 100 (it stops at 150 + both radii); the tank's first loss s4, 5
    left from s18. The simulator: one second later, steadier fire (no volleys), within 4 s of the bench."""
    rows = _air_rows('a2g', 40.0)
    near = lambda lab: next(k for k, r in rows if r[lab] == 1)          # noqa: E731
    assert abs(near('近300') - 3) <= 1 and abs(near('近200') - 4) <= 1
    assert all(r['近100'] == 0 for _, r in rows)
    assert abs(next(k for k, r in rows if r['坦克血'] < 100) - 4) <= 2
    assert abs(next(k for k, r in rows if r['坦克血'] <= 8) - 18) <= 4


# ---- buildings in the way (sim.Sim.reblock, Ground.set_blocks): docs/engine/pathing.md 6, know-how.md A4 ice walls
def _block_rows(check):
    _, t, s = _sim_resolve('engine_block', check)
    s.run(30.0)
    labels = [c[1] for c in t.counters]
    return [(sec, dict(zip(labels, v))) for sec, v in s.series]


def _sim_resolve(build_name, check):
    import build
    import sim
    m, t, _ = build.resolve(build_name, check)
    return m, t, sim.Sim(m, t)


def test_block_a_unit_on_the_move_goes_through_a_building_made_since():
    """Bench 2026-11-04 `cnv_check engine_block wall`: the bitmap wall and the map's row of bunkers 11 (round by the
    gap, s7); the row made a second after the order 10, at the goal s4 (straight through it). The simulator s8."""
    rows = _block_rows('wall')
    end = rows[-1][1]
    assert end['位图墙'] == 11 and end['建筑墙'] == 11 and end['后建墙'] == 10, rows[-1]
    assert abs(next(k for k, r in rows if r['后建墙'] == 10) - 4) <= 1
    assert abs(next(k for k, r in rows if r['建筑墙'] == 11) - 7) <= 1


def test_block_the_late_row_stands_by_the_first_second():
    """Bench `made`: all 8 of the late row counted from s1 (the counter caps at 8), the map's row 8 from the start."""
    rows = _block_rows('made')
    assert rows[0][1]['建筑墙座数'] == 8
    assert next(k for k, r in rows if r['后建墙座数'] == 8) <= 1


def test_block_a_new_order_goes_round_a_building_made_before_it_infantry_too():
    """Bench 2026-11-08 `cnv_check engine_block foot`: the late row made at the start, 4 s on the IFV and a
    peacekeeper beside it ordered to the goal -- both 11 (round by the gap), the IFV at the goal s13, the soldier s22.
    So a structure made in the run is in a new order's way for infantry as for a vehicle (know-how.md's A4 ice walls
    letting soldiers out was not that). The simulator s12 / s22."""
    rows = _block_rows('foot')
    end = rows[-1][1]
    assert end['后建墙'] == 11 and end['后建墙步兵'] == 11, rows[-1]
    assert abs(next(k for k, r in rows if r['后建墙'] == 11) - 13) <= 2
    assert abs(next(k for k, r in rows if r['后建墙步兵'] == 11) - 22) <= 2


# ---- walled in, no way (sim.Ground.closest, Sim.send): docs/engine/pathing.md 6, A4 horn troopers behind the ice
def _seal_rows(check, secs=30.0):
    _, t, s = _sim_resolve('engine_seal', check)
    s.run(secs)
    labels = [c[1] for c in t.counters]
    return [(sec, dict(zip(labels, v))) for sec, v in s.series], s


def test_seal_a_walled_in_soldier_walks_to_the_wall_nearest_the_goal_and_stands():
    """Bench 2026-11-08 `cnv_check engine_seal move`: a ring of the player's bunkers made at s1, the order at s4 to a
    goal 600 out -- the peacekeeper 7 (left the start, the east wall's inside) and there to s61, never at the goal. The
    simulator walks it to the cell nearest the goal and keeps it there; standing short is not 'stuck'."""
    rows, s = _seal_rows('move')
    assert rows[-1][1]['兵'] == 7, rows[-1]
    assert next(k for k, r in rows if r['兵'] == 7) <= 8
    assert not [x for x in s.log if x[1] == '卡住']


@pytest.mark.xfail(strict=True, reason='bench engine_seal move: the walled-in IFV ends in the ring\'s south part (17), '
                   'not at the east wall; the simulator takes it to the cell nearest the goal (3). Not looked into')
def test_seal_a_walled_in_ifv_ends_in_the_rings_south_part():
    rows, _ = _seal_rows('move')
    assert rows[-1][1]['车'] == 17, rows[-1]


def test_seal_units_made_inside_a_building_come_out_and_go():
    """Bench `engine_seal spawn`: an IFV and a peacekeeper made at a power plant's centre at s1, ordered 600 east at s4
    -- both out by themselves, at the goal (13) the IFV s10, the soldier s13. The simulator s9 / s16."""
    rows, _ = _seal_rows('spawn')
    assert rows[-1][1]['车'] == 13 and rows[-1][1]['兵'] == 13, rows[-1]
    assert abs(next(k for k, r in rows if r['车'] == 13) - 10) <= 2
    assert abs(next(k for k, r in rows if r['兵'] == 13) - 13) <= 3


def test_seal_open_an_idle_soldier_fires_from_where_it_stands_at_210():
    """Bench `engine_seal open` (no ring): the peacekeeper never leaves its start, the MCV 210 off 99 % at s1 .. 88 %
    at s61 (it fires from there: the MCV is big). The simulator the same, 89 % at s40."""
    rows, _ = _seal_rows('open', 40.0)
    assert all(r['兵'] == 0 for _, r in rows)
    assert 85 <= rows[-1][1]['敌车血量'] <= 95, rows[-1]


def test_seal_cut_off_by_ground_it_still_fires():
    """Bench `engine_seal cut`: the MCV 210 off behind a closed box of impassable ground -- the peacekeeper fires as
    in `open` (88 % at s61): no way to the target does not stop an idle unit taking it. The simulator the same."""
    rows, _ = _seal_rows('cut', 40.0)
    assert all(r['兵'] == 0 for _, r in rows)
    assert 85 <= rows[-1][1]['敌车血量'] <= 95, rows[-1]


SHOT_BLOCKED = ('bench engine_seal idle / row (2026-11-08): the player\'s own bunkers between an idle peacekeeper and an '
                'MCV 210 off (a ring round it, or a row across with both ends open) -- it neither fires (99-100 % for '
                '61 s) nor moves; over impassable ground (`cut`) it fires. Structures in the line block the shot; the '
                'simulator has no line of fire. Not yet known: an enemy\'s structures, the ice walls, other weapons '
                '(cannon, artillery, anti-air)')


@pytest.mark.xfail(strict=True, reason=SHOT_BLOCKED)
@pytest.mark.parametrize('variant', ['idle', 'row'])
def test_seal_structures_in_the_line_block_the_shot(variant):
    rows, _ = _seal_rows(variant, 40.0)
    assert rows[-1][1]['敌车血量'] >= 99, rows[-1]
