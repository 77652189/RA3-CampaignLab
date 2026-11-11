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


def test_r2_unnamed_made_twice_by_one_script_join_the_team_and_are_picked():
    """bench 2026-11-09 `cnv_check ref_d frames` (CampRefDFrames_mcp_1109_061813): one script run twice
    (CREATE_UNNAMED_ON_TEAM_AT_WAYPOINT at M2) -- 造了 2, 坦克 2 from s1; the wall pick took B (the team's middle at M2:
    both on the team; an empty team would take A); the tank type's pick took one of them (坦克 2 -> 1 at the delete)."""
    series = _sim_run('ref_d', 'frames', 16.0).series
    assert series[-1][1][:4] == [2, 1, 1, 0], series[-1]
    assert any(row[1][:2] == [2, 2] for row in series), series[:3]


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


def test_a_scripts_press_of_the_build_button_builds_as_the_click():
    """engine_production e / f (bench 2026-11-08): the check's own script presses barracks 1's
    Command_ConstructAlliedEngineer at 2 s (NAMED_USE_COMMANDBUTTON_ABILITY) -- e paid 1506 at 帧数 148, the engineer at
    帧数 160, as a's click; f (no money) builds nothing in 30 s. The simulator queues it there (Sim.order_build)."""
    s, rows, _ = _production_rows('e', order=False)
    money = {}
    for rd in rows:
        money.setdefault(rd['帧数'], rd['资金'])
    assert money.get(148) == 1506 and money.get(153) == 1500
    assert next(rd['帧数'] for rd in rows if rd['工程师'] >= 1) == 160
    s, rows, _ = _production_rows('f', order=False)
    assert not any(rd['工程师'] for rd in rows) and s.money.get(s.human, 0) == 0 and s.queues


def test_a_ban_holds_the_queue_and_does_not_cancel():
    """engine_production g (bench 2026-11-09, CampProdG_mcp_1109_055742): the engineer banned from the start
    (ALLOW_DISALLOW_ONE_BUILDING 0), the button pressed at 2 s, 8 s, 19 s; let go at 6 s, banned again at 21 s, let go
    at 30 s. Bench: 2000 until the let-go (the 2 s press was queued and waited), the first engineer at 帧数 160 as a;
    the second job stands at 1286 from s20 to s28 (paid kept, nothing refunded, nothing cancelled), goes on at s29,
    the second engineer at s35; the third job pays down to 500 by s45. The simulator: the press queues past the ban,
    a banned job stands (Sim.order_build press, Sim.produce_due)."""
    s, rows, _ = _production_rows('g', order=False)
    assert all(rd['资金'] == 2000 for rd in rows[:90])
    assert next(rd['帧数'] for rd in rows if rd['工程师'] >= 1) == 160
    held = [rd['资金'] for rd in rows[330:440]]          # 22 s .. 29 s: banned halfway through the second
    assert len(set(held)) == 1 and 1240 <= held[0] <= 1300 and all(rd['工程师'] == 1 for rd in rows[330:440])
    assert rows[-1]['工程师'] == 2 and 500 <= rows[-1]['资金'] <= 520


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
    """n: tanks at 0 and 150 from the hive's spot take no fire to the end (497 frames) -- their health goes 100 -> 90 -> 80
    by the bench's two scripted NAMED_DAMAGE hits only (the simulator applies them since engine line C round 5), 250 shot
    down (bench 1 % by 180)."""
    n = _sim_run('engine_super', 'n', 34.0).series[-1][1]
    assert n[-3:-1] == [80, 80] and n[-1] <= 10, n


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
    # the third: 施放数, the cast seen by PLAYER_TRIGGERED_SPECIAL_POWER once (bench i / j: 1; 0 before sim knew it)
    assert by[347] == [100, 100, 1] and by[362][0] < 100 and by[422][0] <= 75, by


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


def test_shot_clock_the_coil_shoots_every_31_s_two_shots_a_tank(monkeypatch):
    """Engine line C round 2: with Sim.shot_clock the coil (SovietBaseDefenseAdvancedTeslaGun: PreAttack 2.5 +
    Firing 0.5 + Reload 0.1 = 3.1 s, Damage 450 against a 480-health tank) loses a tank every 2 x 48 = 96 frames (round 6: the weapon's own frames, engine_clip)
    (the clock works). The bench's is ~125 (~4.15 s a shot): ~1 s a shot the weapon data does not say, not found --
    why the clock stays off by default and the xfail above stands. Frames 100-150 when found."""
    import sim
    monkeypatch.setattr(sim.Sim, 'shot_clock', True)
    s, rows = _powerdef('on')
    lost = [r['帧数'] for i, r in enumerate(rows) if i and r['坦克'] < rows[i - 1]['坦克']]
    assert len(lost) >= 4 and all(90 <= b - a <= 110 for a, b in zip(lost, lost[1:]))     # rows are 15 frames apart
    coil = next(b for b in s.living() if b.template == 'SovietBaseDefenseAdvanced')
    assert coil.weapons[0]['sched'] == [round(38 / 15, 4)] and abs(coil.weapons[0]['cycle'] - 48 / 15) < 1e-9


# ---- crush / slow death (sim.Sim.crush_along, sim.Sim.dying, simunits.crush / slow_death): bench 2026-11-06
# engine_crush (docs/engine/crush.md; one run each): `all` 步兵 170127043 (a Hammer drives over an enemy conscript:
# crushed frame 43, never left its spot, lay dying 127 frames), 坦克 605069701 (a guardian, 20 against 20, lives the
# whole run; an Apocalypse crushes one at frame 69), 建筑 1000 (a plant killed by script: dying the kill frame only);
# `b` the Apocalypse never crushes a Sickle (30 against 30). The simulator has no acceleration: its tanks arrive ~25
# frames sooner and crush a few to ~15 frames earlier -- the frames below are bands, the rest exact.
def _crush(build_name, check):
    import build
    import sim
    m, t, _ = build.resolve(build_name, check)
    s = sim.Sim(m, t)
    s.run(47.7)
    return s, dict(zip([lab for _, lab in t.counters], s.series[-1][1]))


def test_crush_levels_come_from_the_data_and_the_greater_wins():
    import simunits
    conscript, hammer = simunits.crush('SovietAntiInfantryInfantry'), simunits.crush('SovietAntiVehicleVehicleTech1')
    guardian, apoc = simunits.crush('AlliedAntiVehicleVehicleTech1'), simunits.crush('SovietAntiVehicleVehicleTech3')
    sickle = simunits.crush('SovietScoutVehicle')
    assert conscript[1] == 10 and hammer == (20, 20) and guardian[1] == 20 and apoc == (30, 31) and sickle[1] == 30
    assert hammer[0] > conscript[1] and not hammer[0] > guardian[1]             # crush.md: all 1 dies, all 2 lives
    assert apoc[0] > guardian[1] and not apoc[0] > sickle[1] and not apoc[0] > apoc[1]     # all 3 dies, b 1 lives


def test_crush_a_tank_drives_over_a_lower_level_and_leaves_an_equal_one():
    s, r = _crush('engine_crush', 'all')
    frames = r['帧数']
    assert 39 <= r['步兵'] % 1000 <= 55                       # conscript crushed at frame 43 (bench)
    assert r['坦克'] % 1000 == frames                          # lane 2: a guardian, level 20 against 20, never crushed
    assert 45 <= r['坦克'] // 1000 % 1000 <= 80                # lane 3: the Apocalypse crushes one (bench 69)
    assert r['坦克'] // 10 ** 6 > 0                            # ... and the Hammer goes round / on to its goal
    s2, r2 = _crush('engine_crush_b', 'two')
    assert r2['镰刀'] % 1000 == r2['帧数'] and r2['镰刀'] // 1000 % 1000 == 0      # 30 against 30: alive, never dying


def test_slow_death_a_crushed_conscript_lies_127_frames_dying_and_in_its_spot():
    s, r = _crush('engine_crush', 'all')
    assert abs(r['步兵'] // 1000 % 1000 - 127) <= 2            # 8.5 s of its SlowDeath
    assert r['步兵'] // 10 ** 6 == r['步兵'] % 1000 + r['步兵'] // 1000 % 1000      # in its spot all the while, not after


def test_destroy_die_a_building_killed_is_dying_one_frame_and_gone():
    s, r = _crush('engine_crush', 'all')
    assert r['建筑'] == 1000                                   # dying the kill frame only; no collapse object counted
    s2, r2 = _crush('engine_crush_b', 'two')
    assert r2['电厂'] == 1000


# ---- selling (sim.Sim.sell, NAMED_DAMAGE): bench 2026-11-06 engine_sell (docs/engine/sell.md; one run each): money 2000
# -> 2400 for a full 800 plant (a), 2200 hurt to half (b), 2250 for a 500 bunker (d), 2400 once for two orders (f);
# 卖帧 31031 = alive 31 frames and SOLD 31 (deleted 30 frames after the order, counted as power till then); killed at
# frame 5 (e): paid, 5004 (SOLD read 5 frames, alive 4); sold while unpacking (c): nothing, never SOLD.
def _sell(which):
    import build
    import sim
    m, t, _ = build.resolve('engine_sell', which)
    s = sim.Sim(m, t)
    s.run(8.0)
    return dict(zip([lab for _, lab in t.counters], s.series[-1][1]))


def test_sell_pays_half_the_cost_scaled_by_health_once_and_deletes_after_30_frames():
    a, b, d, f = (_sell(w) for w in 'abdf')
    assert (a['资金'], b['资金'], d['资金'], f['资金']) == (2400, 2200, 2250, 2400)
    assert a['卖帧'] == b['卖帧'] == d['卖帧'] == f['卖帧'] == 31031
    assert a['第四行'] % 1000 == 31 and a['第四行'] // 1000 == a['帧数'] - 31      # the plant counts 31 frames, then not


def test_sell_a_killed_building_stays_paid_and_a_building_unpacking_is_not_sold():
    e, c = _sell('e'), _sell('c')
    assert e['资金'] == 2400 and e['卖帧'] == 5004 and e['第四行'] % 1000 == 4
    assert c['资金'] == 2000 and c['卖帧'] == c['帧数']                                # never SOLD, never gone


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


def test_line_of_fire_is_the_weapons_flag():
    """`los` = ATTACK_NEEDS_LINE_OF_SIGHT in the WeaponTemplate's Flags: the peacekeeper's shotgun and the Guardian's
    cannon have it, the Athena's lob (AthenaCannonWeapon) does not."""
    import simunits
    assert all(w['los'] for w in simunits.fight('AlliedAntiInfantryInfantry')['weapons'])
    assert all(w['los'] for w in simunits.fight('AlliedAntiVehicleVehicleTech1')['weapons'])
    assert not any(w['los'] for w in simunits.fight('AlliedAntiStructureVehicle')['weapons'])


@pytest.mark.parametrize('variant', ['idle', 'row'])
def test_seal_structures_in_the_line_block_the_shot(variant):
    """Bench engine_seal idle / row (2026-11-08): the player's own bunkers between an idle peacekeeper and an MCV 210
    off (a ring round it, or a row across with both ends open) -- it neither fires (99-100 % for 61 s) nor moves; over
    impassable ground (`cut`) it fires. The simulator's line of fire (`Sim.shot_blocked`: a weapon with
    ATTACK_NEEDS_LINE_OF_SIGHT does not shoot through a structure's footprint) the same."""
    rows, _ = _seal_rows(variant, 40.0)
    assert rows[-1][1]['敌车血量'] >= 99, rows[-1]


def test_seal_a_target_in_the_air_is_not_behind_the_row():
    """Bench engine_seal aa / aaopen (2026-11-08): an IFV, a hovering Twinblade (NO_ATTACK) 200 east, the player's
    row 100 east or no row -- the same readings both ways (79 s1, 50 s4, 16 s7, 4 from s10): the line of fire does
    not stop a shot at a target in the air (Sim.shot_blocked). Only how alike the two are is asserted; the rate is
    not (the simulator's 85 / 40 / 0)."""
    aa, _ = _seal_rows('aa', 12.0)
    op, _ = _seal_rows('aaopen', 12.0)
    assert [r['敌车血量'] for _, r in aa] == [r['敌车血量'] for _, r in op]
    assert aa[-1][1]['敌车血量'] <= 20, aa[-1]


@pytest.mark.xfail(strict=True, reason='bench engine_seal arty / artyhp / artyo (2026-11-08): an idle V4 (range 500, '
                   'min 200, VisionRange 500, AutoAcquire YES, no LINE_OF_SIGHT flag) never fires at the MCV 350 off, '
                   'with the row or without (artyo), the middle bunker 100 too; the simulator fires (MCV 0 by s61). '
                   'Not split yet: the side does not see it (ShroudClearingRange, STANDARD_SHROUD_CLEAR not found), '
                   'or the V4 takes nothing by itself -- next: the same with the map revealed, and the MCV at 250')
def test_seal_an_idle_v4_leaves_the_mcv_350_off_alone():
    rows, _ = _seal_rows('artyo', 61.0)
    assert rows[-1][1]['敌车血量'] >= 99, rows[-1]


def test_bodies_face_as_the_built_map_puts_them():
    """The simulator places a body at the angle the built map writes (model.facing, package._put_objects): its own,
    else the player's north (+y) and everyone else's south -- it took 0 (east) for 'none' till 2026-11-08. The
    engine_seal artyfe / artyf15 / artyf30 V4s write theirs; artyo's V4 writes none (north), its s1 MCV writes 90."""
    import math
    import model
    _, _, s = _sim_resolve('engine_seal', 'artyfe')
    for lane, deg in (('Artyfe', 0.0), ('Artyf15', 15.0), ('Artyf30', 30.0)):
        assert s.body(f'UNIT - CNV Seal {lane} Foot').angle == pytest.approx(math.radians(deg))
    assert s.body('UNIT - CNV Seal Arty Foot').angle == pytest.approx(1.5708)
    assert model.facing(model.Obj('X', 0, 0, side='s1')) == pytest.approx(-1.5708)


def test_seal_told_to_attack_through_the_row_it_walks_round_the_end():
    """Bench engine_seal attack (2026-11-08): row's set-up, an attack order on the MCV at 4 s -- the peacekeeper
    leaves the start by s4, is north of the row's end from s7 (5 = 1 + 4; never east of it), the MCV 97 at s10 down
    to 85 at s40 (Sim.fire_spot: a clear spot in range, the shortest way). The simulator: north of the row from s10,
    the first hit by s13, 86 at s61."""
    rows, _ = _seal_rows('attack', 61.0)
    foot = dict((k, r['兵']) for k, r in rows)
    hp = dict((k, r['敌车血量']) for k, r in rows)
    assert foot[61] & 1 and foot[61] & 4, rows[-1]
    assert next(k for k, v in hp.items() if v < 100) <= 13, hp
    assert hp[61] <= 90, hp


# ---- what a unit takes by itself (sim.Sim.takes_by_itself / auto_acquires / can_hit): docs/engine/pathing.md 7d
def test_seal_erow_an_idle_soldier_leaves_enemy_bunkers_alone():
    """Bench engine_seal erow (2026-11-08): the enemy's 11 bunkers in a row 105 off, the MCV 210 behind -- the player's
    idle peacekeeper fires at neither (the middle bunker 100, the MCV 99 for 61 s). Generals' building filter on a
    unit's own picks; the simulator had shot the middle bunker to 31 %."""
    rows, _ = _seal_rows('erow', 40.0)
    assert rows[-1][1]['中墙血'] >= 99 and rows[-1][1]['敌车血量'] >= 99, rows[-1]
    assert all(r['兵'] == 0 for _, r in rows)


@pytest.mark.parametrize('variant,secs', [('ebld', 60.0), ('ebldam', 22.0), ('pam', 60.0)])
def test_seal_units_leave_the_enemys_buildings_alone_by_themselves(variant, secs):
    """Bench engine_seal (2026-11-08), a bunker and a power plant in range, the line clear: ebld -- the enemy's (a
    computer player's, no skirmish AI) peacekeeper idle, the player's bunker 120 east and plant 150 west: both 100 for
    61 s; ebldam -- it attack-moves 1000 east past the two (100 / 120 off its line, 500 along): both 100 while it
    passes (at the goal, 11, s19-s22; see the xfail below for after); pam -- the player's soldier attack-moves past the
    enemy's two the same way: both 100 for 61 s, at the goal s22. RA3 drops Generals' 'a computer player's units take
    enemy buildings'; an attack-move takes no building either."""
    rows, _ = _seal_rows(variant, secs)
    assert rows[-1][1]['地堡血'] >= 99 and rows[-1][1]['电厂血'] >= 99, rows[-1]
    if variant != 'ebld':
        assert rows[-1][1]['兵'] == 11, rows[-1]


@pytest.mark.xfail(strict=True, reason='bench engine_seal ebldam, twice: some time after the enemy soldier is at its '
                   'attack-move goal (s19) the player\'s plant 500 back loses 5 % / 3 s (from s25 in one run, s31 in '
                   'the other; the bunker untouched), the soldier never in the strip south of the line round the plant '
                   '(100); who fires is not known (that soldier walking back along the line, or the ebld lane\'s), '
                   'the simulator leaves the plant alone')
def test_seal_after_an_attack_move_the_computers_soldier_goes_back_for_the_plant():
    rows, _ = _seal_rows('ebldam', 61.0)
    assert rows[-1][1]['电厂血'] <= 50, rows[-1]


def test_a_weapon_doing_nothing_to_the_armour_never_takes_the_target():
    """Tanya's pistol (SNIPER) at a faction building's armour (SNIPER 0 %): Generals estimateWeaponDamage 0 ->
    INVALID_SHOT, ordered or not (the a6 Tanya who stood firing at a building); the peacekeeper's GUN (100 %) can."""
    import sim
    import simunits
    plant = sim.Body('p', 'AlliedPowerPlant', 's1', 0.0, 0.0)
    plant.armor, plant.kinds = simunits.fight('AlliedPowerPlant')['armor'], frozenset({'STRUCTURE'})
    s = sim.Sim.__new__(sim.Sim)
    assert not any(s.can_hit(w, plant) for w in simunits.fight('AlliedCommandoTech1')['weapons'])
    assert all(s.can_hit(w, plant) for w in simunits.fight('AlliedAntiInfantryInfantry')['weapons'])


def test_idle_acquiring_is_the_units_own_word():
    """AutoAcquireEnemiesWhenIdle: the peacekeeper YES, the MCV NO, the Riptide writes none (Generals' 0: no idle
    acquiring); the one ATTACK_BUILDINGS is a squad's."""
    import simunits
    assert simunits.acquire('AlliedAntiInfantryInfantry') == ['YES']
    assert simunits.acquire('AlliedMCV') == ['NO']
    assert simunits.acquire('AlliedAntiInfantryVehicle') == []


# ---- inventory batch 1 (work/re/l2_scripts1.md): bench 2026-11-08 `cnv_check engine_scripts1 <variant>`, readings in
# checks/engine_scripts2.py (bench 11-09, CampScr2One / CampScr2All: counters A血 B血 比较数 类型数)
def _scripts2(variant, until):
    return {round(sec): vals for sec, vals in _sim_run('engine_scripts2', variant, until).series}


def test_scripts2_a_relation_is_one_way_and_turns_back():
    """one: Soviet_1 neutral to Player_1 -- its Guardian holds fire (A血 100 to bench s8), shoots again from BACK_AT
    (10 s); a killed tank leaves PLAYER_HAS_OBJECT_COMPARISON's count at once, as the type counter (3 -> 2)."""
    by = _scripts2('one', 24.0)
    assert all(v[0] == 100 for s, v in by.items() if s <= 9), by
    assert by[24][0] < 95, by
    assert all(v[2] == v[3] == 2 for s, v in by.items() if s >= 4), by


def test_scripts2_all_players_in_a_relation_changes_nothing():
    """all: PLAYER_RELATES_PLAYER(Soviet_1, '<All Players>', Neutral) -- the Guardian shoots the player's MCV all along
    (bench A血 98 at s1, 80 at s25)."""
    by = _scripts2('all', 24.0)
    assert by[24][0] < 95 and by[5][0] < 100, by


# checks/engine_scripts3.py (bench 11-09, CampScr3Math / CampScr3Input)
def test_scripts3_counter_math_codes_as_the_bench():
    """math: COUNTER_MATH_COUNTER by 4 -- 0 adds, 1 takes away (no floor: -1), 2 multiplies, 3 divides (13 -> 3)."""
    series = _sim_run('engine_scripts3', 'math', 10.0).series
    assert series[0][1] == [3, 3, 3, 13] and series[-1][1] == [7, -1, 12, 3], series[-1]


def test_scripts3_a_script_moves_the_player_under_disable_input():
    """input: DISABLE_INPUT at 5 s, the tank's MOVE_NAMED_UNIT_TO at 7 done (走到 1, bench s9); DECREMENT 5 from 2
    reads -3; -13 / 4 reads -3 (toward zero)."""
    last = _sim_run('engine_scripts3', 'input', 24.0).series[-1][1]
    assert last[0] == 1 and last[2:] == [-3, -3], last


# checks/engine_scripts4.py (bench 11-09, CampScr4Border / Team / Clock)
def test_scripts4_off_the_border_nobody_fires_or_is_fired_on():
    """border: the west half from the start -- the pair across its edge (X) and the pair outside (Y) hold their fire
    till the whole map opens at 20 s, the pair inside (Z) fights; Y's Guardian lives on in its area (Y在 1)."""
    by = {round(s): v for s, v in _sim_run('engine_scripts4', 'border', 32.0).series}
    assert by[18][:2] == [100, 100] and by[18][3] == 1 and by[9][2] < 100, by[18]
    assert by[30][0] < 100 and by[30][1] < 100, by[30]


def test_scripts4_team_stop_and_team_guard_area_as_the_bench():
    """team: TEAM_STOP 3 s into a 1400 move -- both stay in the middle; TEAM_GUARD_AREA -- both in the zone."""
    last = _sim_run('engine_scripts4', 'team', 30.0).series[-1][1]
    assert last == [0, 2, 0, 2], last


def test_scripts4_a_hidden_countdown_runs_on():
    """clock: the 20 s timer hidden at 8 and shown at 14 expires at 20 all the same (到点 1, bench s19)."""
    by = {round(s): v for s, v in _sim_run('engine_scripts4', 'clock', 26.0).series}
    assert by[18] == [0] and by[24] == [1], by


# checks/engine_vision.py (bench 11-06 reshroud / resh*, 11-09 perm / undo: counters 揭开 帧数 [撤后] at 30 s)
@pytest.mark.parametrize('variant, opened', [('reshroud', 137), ('resh0', 0), ('resh1', 2), ('resh5', 62),
                                             ('resh10', 137)])
def test_vision_a_plain_reveal_holds_15n_minus_13_frames(variant, opened):
    """MAP_REVEAL_AT_WAYPOINT goes back to fog 137 frames after (default), 15 x N - 13 with RESHROUD_TIME N."""
    assert _sim_run('engine_vision', variant, 30.0).series[-1][1][0] == opened


def test_vision_a_permanent_reveal_holds_and_its_undo_shuts_at_once():
    """perm: 揭开 = 帧数 all along; undo at Go + 10 s: 揭开 stays 151, nothing after the undo (撤后 0)."""
    perm = _sim_run('engine_vision', 'perm', 30.0).series[-1][1]
    undo = _sim_run('engine_vision', 'undo', 30.0).series[-1][1]
    assert perm[0] == perm[1] > 400 and undo[0] == 151 and undo[2] == 0, (perm, undo)


# checks/engine_scripts1.py
def _scripts1(variant, until):
    return {round(sec): vals for sec, vals in _sim_run('engine_scripts1', variant, until).series}


def test_scripts1_conditions_as_the_bench():
    """cond: 条件位 9 all run (Player_1 Human 1 + a line never played reads done 8; Soviet_1 not Human, before and after
    its AI is woken; a clip never played not done); 状态 3 -> 1 at the kill -> 0 at the clear."""
    by = _scripts1('cond', 12.0)
    assert all(v[0] == 9 for v in by.values()), by
    assert (by[3][1], by[4][1], by[11][1]) == (3, 1, 0), by


def test_scripts1_a_team_handed_over_drops_its_move():
    """xfer: Soviet_2's from the hand-over, the move it was on dropped (nobody in `far` in 40 s), both off home."""
    last = _scripts1('xfer', 40.0)[40]
    assert last[:3] == [1, 0, 2], last


def test_scripts1_idle_for_seconds_drops_the_move():
    """idle: the tank without the idle order arrives (bench s7, about 9 game s), the one told UNIT_IDLE_FOR_SECONDS 3
    at 3 s never does in 45 s -- the order dropped, not a 3 s pause."""
    by = _scripts1('idle', 45.0)
    arrived = min(s for s, v in by.items() if v[1] == 1)
    assert 7 <= arrived <= 12 and all(v[0] == 0 for v in by.values()), by


def test_scripts1_hunt_without_an_ai_moves_nobody():
    """hunt: TEAM_HUNT / NAMED_HUNT on a computer player's units (AI not woken) and TEAM_HUNT on the player's: 60 s
    where they stood."""
    assert all(v == [0, 0, 0] for v in _scripts1('hunt', 60.0).values())


@pytest.mark.xfail(strict=True, reason='the Peacekeeper toggle (ToggleStatusSpecialAbilityUpdate) is not simulated: '
                                       'the button reaches each member, the shield status is not set')
def test_scripts1_team_button_raises_both_shields():
    """button: TEAM_USE_COMMANDBUTTON_ABILITY(Pk, the riot shield) at 2 s: 举盾 2 from then."""
    assert _scripts1('button', 10.0)[10] == [2]


def test_video_a_radar_clip_is_done_after_its_length_full_screen_never():
    """movie play (bench, docs/story/handoff.md 1g): CNVTEST01 (95 frames at 23.976) in the radar window done 63 game
    frames after its start; the full-screen clip never reads done."""
    last = _sim_run('movie', 'play', 30.0).series[-1][1]
    assert abs(last[0] - 63) <= 3 and last[1] == 1 and last[3] == 0, last


def test_audio_a_dubbed_line_is_done_its_length_after_it_is_heard(tmp_path):
    """HAS_FINISHED_AUDIO: true for a line never played; a 4.34 s recording played at t is done at t + 0.9 + 4.34 (bench
    11-04 engine_dialog at x1: heard 0.9 s after the play, done at 5.3 s)."""
    import types
    import wave
    import build
    import sim
    wav = tmp_path / 'line.wav'
    with wave.open(str(wav), 'wb') as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(1000)
        w.writeframes(b'\0\0' * 4340)
    m, t, _ = build.resolve('engine_scripts1', 'cond')
    m.voice = types.SimpleNamespace(items=[('CNV_Line', str(wav), None, None)])
    s = sim.Sim(m, t)
    assert s.cond('HAS_FINISHED_AUDIO', ['CNV_Line'])
    s.act('PLAY_SOUND_EFFECT', ['CNV_Line'], None)
    start = s.t
    s.t = start + 5.2
    assert not s.cond('HAS_FINISHED_AUDIO', ['CNV_Line'])
    s.t = start + 5.3
    assert s.cond('HAS_FINISHED_AUDIO', ['CNV_Line'])


# ---- protocol points (experimental/cnv/simtech.py): bench 2026-11-08 `cnv_check engine_protocol <variant>`, readings
# in checks/engine_protocol.py
def _protocol(variant, until):
    return {round(sec): vals for sec, vals in _sim_run('engine_protocol', variant, until).series}


def test_protocol_set_points_follows_the_programs_rule():
    """pts: 点数 1 -> 2 (cap 2) -> 2 (SET_POINTS 1: 2 + 1 passes the cap) -> 0 -> 5 (cap 0 does not limit) -> 3 (SET_POINTS
    0 under cap 3 with 5 held) -> 7; Player_1 holds rank 1's and the Allied default (3), Soviet_1 rank 1's and the Soviet
    default (5); Soviet_1's starting point spent at once (0)."""
    by = _protocol('pts', 16.0)
    assert [by[s][0] for s in (3, 5, 7, 9, 11, 13)] == [2, 2, 0, 5, 3, 7], by
    assert all(v[1:] == [3, 0, 5] for s, v in by.items() if s >= 1), by


def test_protocol_a_computer_player_spends_unless_locked():
    """ailock: everything locked for Soviet_1 keeps its point (1), Soviet_2 unlocked spends it (0)."""
    assert all(v == [1, 0] for s, v in _protocol('ailock', 20.0).items() if s >= 1)


def test_protocol_rank_two_at_frame_5400():
    """rank: Player_1's rank experience reaches 360 in frame 5400 (360 s at 1 a second): 2 points, rank 2 for Player_1 and
    Soviet_2 (cap 2) not Soviet_1 (cap 0): 二级 5; Soviet_2's points spent at once."""
    last = _protocol('rank', 380.0)[380]
    assert last == [2, 0, 5, 5400], last


# ---- sim.HOLD_SPOTS: bench 2026-11-09 `cnv_check engine_spots same / late`, readings in checks/engine_spots.py
@pytest.mark.parametrize('variant,until', [('same', 35.0), ('late', 75.0)])
def test_spots_three_trucks_sent_alone_to_one_point_stand_apart(variant, until):
    """Three trucks, each on a team of its own, sent to one point (at once, or 20 s apart): the bench ends 4 2 1 (环k:
    nested squares 10 / 25 / 45 / 80 round the point) -- the first on the point, the other two 10-80 off. The
    simulator (HOLD_SPOTS): 4 2 2 (truck 3 44.7 off, the bench's beyond 45)."""
    ring = _sim_run('engine_spots', variant, until).series[-1][1]
    assert ring[0] == 4 and all(1 <= r <= 3 for r in ring[1:]), ring


# checks/engine_scripts6.py (bench 11-09 switch / timers, both PASS; the script machinery, no units)
def test_scripts6_switches_and_subroutines_as_the_bench():
    """帧 15 a second, held at 151 from the 10 s DISABLE_SCRIPT till the 14 s ENABLE_SCRIPT; 开关 24 -> 26 -> 42 (an
    [off] script, a once-script cut before / after its turn, a fired one re-armed); 自关 11 (actions after a script's
    own DISABLE_SCRIPT run, NO_OP); 子程序 11 -> 21 (a once-sub runs once, a repeating sub per call, an [off] sub never)."""
    by = {round(s): v for s, v in _sim_run('engine_scripts6', 'switch', 20.0).series}
    assert by[11][0] == by[13][0] == 151 and by[15][0] == 166, by
    assert by[1][1:] == [24, 11, 0] and by[3][1:] == [24, 11, 11] and by[5][1:] == [26, 11, 21], by
    assert by[19][1:] == [42, 11, 21], by


def test_scripts6_else_random_and_timers_as_the_bench():
    """否则 1 -> 11 -> 21 (a once-script's ELSE closes it; a called sub's ELSE); 随机 14 (SET_RANDOM_COUNTER 1..3
    inclusive); 计时 1 (SET_TIMER 45 frames) -> 33 (COUNTER_COUNTER) -> 41 (COUNTER_SECONDS <=) -> 43
    (SET_RANDOM_MSEC_TIMER 6..6 s) -> 63 (COUNTER_SECONDS <, the 8..10 s timer)."""
    by = {round(s): v for s, v in _sim_run('engine_scripts6', 'timers', 20.0).series}
    assert [by[k][0] for k in (1, 3, 19)] == [1, 11, 21], by
    assert by[19][1] == 14, by
    assert by[3][2] == 1 and by[5][2] == 41 and by[7][2] == 43 and by[11][2] == 63, by


# ---- self-healing (sim.Sim.autoheal, simunits.autoheal): bench 2026-11-06 engine_heal (docs/engine/heal.md): an
# Apocalypse (3000 health, AutoHealBehavior 2 points every 7 frames, waits 15 frames after a hurt) hurt 600 at Go:
# 低血 = 1 x frames below 81 % + 1000 x frames below 82 % -> 219114 (81 % again after 114 frames, 82 % after 219);
# b: 30 more at frame 40 -> 230 frames below 81 %, below 82 % to the end. (The state / rank-gated heals c, d, e are not
# modelled.)
def test_autoheal_an_apocalypse_mends_two_points_every_7_frames_after_a_15_frame_wait():
    a = _sim_run('engine_heal', 'a', 18.0).series[-1][1]
    assert a[1] == 219114, a
    b = _sim_run('engine_heal', 'b', 18.0).series[-1][1]
    assert b[1] % 1000 == 230 and b[1] // 1000 == b[0], b          # below 82 % every frame to the end


# ---- the freeze (sim.Sim.chill, SecondaryDamageTracker): bench 2026-11-09 engine_cryo (checks/engine_cryo.py; the bench ran
# it on probe_range, the simulator on Niagara's west field -- the copter's flight differs, the tracker does not):
# one cryocopter / two on a Hammer (550), the beam cut by script 34 s after the order. 先冻 / 冻住 / 化冰 = 139 / 705 / 334
# (one), 79 / 765 / 334 (two): frozen until 844 frames after the order either way, melting 334 frames (= (1100 - 550) / 25
# a second, the 200 % cap) once the beam is gone. The simulator's flight to the target is slower (first frozen 189 / 90).
def test_cryo_a_frozen_tank_melts_334_frames_after_the_beam_whatever_the_beam():
    one = _sim_run('engine_cryo', 'one', 90.0).series[-1][1]
    two = _sim_run('engine_cryo', 'two', 90.0).series[-1][1]
    for first, held, melt in (one, two):
        assert abs(first + held - 844) <= 10 and abs(melt - 334) <= 6, (one, two)
    assert two[0] < one[0], (one, two)          # two beams freeze it sooner


def test_scripts7_idle_for_frames_drops_the_order_as_the_bench():
    """Bench 2026-11-09 engine_scripts7 idle: UNIT_IDLE_FOR_FRAMECOUNT 15 and 1 on a moving Guardian -- neither got
    to its goal (25 s), the control did (二到 1 from s14): the order is dropped, as the seconds version's."""
    last = _sim_run('engine_scripts7', 'idle', 25.0).series[-1][1]
    assert last == [0, 1, 0], last


def test_scripts7_objects_made_with_an_angle_as_the_bench():
    """Bench 2026-11-09 engine_scripts7 face: two CREATE_NAMED_..._WITH_ORIENTATION and two CREATE_UNNAMED_..._WITH_
    ORIENTATION made at 1 s, 造出 4 from s1 (the facing not read: the camera did not show the row)."""
    last = _sim_run('engine_scripts7', 'face', 8.0).series[-1][1]
    assert last == [4], last


@pytest.mark.xfail(strict=True, reason='bench 2026-11-09 engine_scripts7 amove: the attack-mover leaves its enemy at '
                   '12 % and arrives at s38; the simulator kills it (0 at 28 s) and has not arrived by 60 s')
def test_scripts7_attack_move_leaves_a_beaten_enemy_as_the_bench():
    by = {round(s): v for s, v in _sim_run('engine_scripts7', 'amove', 60.0).series}
    assert by[59][0] == 1 and by[59][2] > 0, by


def test_scripts7_a_moving_tank_fires_as_it_drives_by_as_the_bench():
    """Bench 2026-11-09 engine_scripts7 amove: MOVE_NAMED_UNIT_TO's tank hurt the enemy beside its lane as it drove
    by (乙敌 100 -> 60) and arrived (乙到 1 from s23). (The hit sizes are engine line C's: not compared.)"""
    by = {round(s): v for s, v in _sim_run('engine_scripts7', 'amove', 60.0).series}
    assert by[59][1] == 1 and 0 < by[59][3] < 100, by


def test_scripts7_indestructible_stops_no_scripted_damage_as_the_bench():
    """Bench 2026-11-09 engine_scripts7 panel: 甲血 乙血 丁血 58 58 58 after NAMED_DAMAGE 200 at 2 s (the UNIT- and the
    TEAM-flagged ones as the control), 16 16 after another 200 at 8 s; 活着 15 -> 11 (NAMED_KILL of a flagged one)."""
    by = {round(s): v for s, v in _sim_run('engine_scripts7', 'panel', 12.0).series}
    assert by[3] == [58, 58, 58, 15] and by[5][3] == 11, by
    h1, h2, h4, alive = by[11]                  # 16 on the bench, 17 here (the percent's rounding)
    assert abs(h1 - 16) <= 1 and h2 == 58 and abs(h4 - 16) <= 1 and alive == 11, by


def test_scripts7_object_lists_and_the_nearest_refs_as_the_bench():
    """Bench 2026-11-09 engine_scripts7 list: 列表 4 (an object list read as a type), 单类 1 (a type added twice
    counts once); 参考 1 (the named nearest, SET_REF_TO_NEREST_TEAM_OF_TYPE_OWNED_BY_PLAYER), 无名参考 2 (the
    UNNAMED one skips it) from s5."""
    by = {round(s): v for s, v in _sim_run('engine_scripts7', 'list', 10.0).series}
    assert by[2][:2] == [4, 1] and by[9][1:] == [1, 1, 2], by


@pytest.mark.xfail(strict=True, reason='bench 2026-11-09 engine_scripts7 list: a type added to an object list at 4 s '
                   'is not counted (列表 stays 4); the simulator adds it (5) -- not found why')
def test_scripts7_a_type_added_to_a_list_later_as_the_bench():
    by = {round(s): v for s, v in _sim_run('engine_scripts7', 'list', 10.0).series}
    assert by[9][0] == 4, by


def test_reinforcement_teams_as_the_bench():
    """CREATE_REINFORCEMENT_TEAM (sim.Sim.reinforce, bench 11-10 engine_reinf): every line's max count, a new instance
    on every call (teamMaxInstances 1 or not), and an order by the team's name to the oldest instance only.
    two (兵A 出生A 到达A 兵B) ends 6 3 3 4; old (兵A 出生A 到达A 远处A): the first instance stands at the goal (3 3 0 0
    -> 3 0 3 0), the second is made at the spawn, the order to far takes the first: 6 3 0 3."""
    assert _sim_run('engine_reinf_two', 'go', 30.0).series[-1][1] == [6, 3, 3, 4]
    by = {s: v for s, v in _sim_run('engine_reinf_old', 'go', 45.0).series}
    assert by[1] == [3, 3, 0, 0] and by[13] == [3, 0, 3, 0] and by[44] == [6, 3, 0, 3], by


def test_mcv_deploys_at_a_far_waypoint_as_the_bench():
    """NAMED_USE_COMMANDBUTTON_ABILITY_AT_WAYPOINT(mcv, Command_UnPackAlliedMCV, 400 east) (bench 11-10 engine_unpack
    mcv): the MCV drives there and is the yard from frame 121 on (sim 128), the yard on the point, the name passed on
    (名字帧 = 帧数)."""
    frames, unit, yard, name = _sim_run('engine_unpack_mcv', 'go', 40.0).series[-1][1]
    assert 115 <= unit % 1000 <= 135 and unit // 1000 > 0, unit
    assert yard % 1000 == frames - unit % 1000 and yard // 1000 == yard % 1000, (frames, unit, yard)
    assert name == frames


def test_nanocore_deploys_at_a_far_waypoint_as_the_bench():
    """The egg variant (bench 11-10 engine_unpack egg: JapanBaseDefenseEgg -> JapanBaseDefense, replaced at frame 112,
    sim 108). The egg is in the unit table through its chain (simunits.resolve: BaseEgg's EditorSorting UNIT, KindOf
    =$BASE_DEFENSE_EGG_KINDOFS defined in BaseEgg.xml, its own LocomotorSet Speed 60 -- round 139). Not held: the
    bench's PLAYER_HAS_OBJECT_COMPARISON(JapanBaseDefense) stayed 0 while the area count held (场帧 522); the sim
    counts it owned."""
    import simunits
    egg = simunits.stats('JapanBaseDefenseEgg')
    assert egg['speed'] == 60.0 and egg['surface'] == 'both' and 'VEHICLE' in egg['kinds'] and not egg['guessed']
    frames, unit, yard, name = _sim_run('engine_unpack_egg', 'go', 40.0).series[-1][1]
    assert 102 <= unit % 1000 <= 122 and unit // 1000 > 0, unit
    assert yard % 1000 == frames - unit % 1000, (frames, unit, yard)
    assert name == frames


def _changes(build_name, check, until):
    """[(second, readings)] at each change of the run's counters."""
    out = []
    for sec, v in _sim_run(build_name, check, until).series:
        if not out or out[-1][1] != v:
            out.append((sec, list(v)))
    return out


def _first(rows, k, test):
    return next((sec for sec, v in rows if test(v[k])), None)


# The bench's seconds run 1-2 s ahead of the mission's timers (checks/engine_scripts8.py): the simulator's readings,
# in mission seconds, are asserted LAG later at most
LAG = 2


def test_scripts8_team_delete_and_kill_take_every_member_as_the_bench():
    """bench 2026-11-09 engine_scripts8 team: TEAM_DELETE Del and TEAM_KILL Kil at 2 s -- 活着 48 to the end (both
    crews gone at once, Liv whole), 甲死帧 1 (the killed one NAMED_DYING a frame). Not held: 乙死帧 (bench 1, the
    deleted one dying a frame too; the simulator 0)."""
    rows = _changes('engine_scripts8', 'team', 9.0)
    assert rows[-1][1][:2] == [48, 1] and _first(rows, 0, lambda v: v == 48) <= 2 + LAG


def test_scripts8_idle_drops_the_move_as_the_bench():
    """bench engine_scripts8 idle: TEAM_IDLE_FOR_SECONDS 3 / _FRAMECOUNT 15 at 3 s drop the 1 s move order -- 到 100
    (the control's) at s12, 200 from s13, never 211 (the idled crews never arrive)."""
    rows = _changes('engine_scripts8', 'idle', 30.0)
    assert [v[0] for _, v in rows] == [0, 100, 200]
    assert 12 <= _first(rows, 0, lambda v: v == 100) <= 12 + LAG and 13 <= _first(rows, 0, lambda v: v == 200) <= 13 + LAG


def test_scripts8_merge_moves_the_members_as_the_bench():
    """bench engine_scripts8 merge: TEAM_MERGE_INTO_TEAM at 1 s -- 合 1 at s11, 12 from s13 (the source's two took the
    target's order); 源 0 (an order to the emptied source moves nobody)."""
    rows = _changes('engine_scripts8', 'merge', 30.0)
    assert rows[-1][1] == [12, 0] and all(v[1] == 0 for _, v in rows)
    assert 11 <= _first(rows, 0, lambda v: v == 1) <= 11 + LAG and 13 <= _first(rows, 0, lambda v: v == 12) <= 13 + LAG


def test_scripts8_spawn_on_team_at_the_object_as_the_bench():
    """bench engine_scripts8 spawn: UNIT_SPAWN_NAMED_OBJECT_ON_TEAM_AT_NAMED_OBJECT_LOCATION at 1 s -- 生 3 from s1."""
    rows = _changes('engine_scripts8', 'spawn', 6.0)
    assert rows[-1][1] == [3] and _first(rows, 0, lambda v: v == 3) <= 1 + LAG


def test_scripts8b_team_status_holds_and_frees_the_fire_as_the_bench():
    """bench engine_scripts8b status: TEAM_CHANGE_OBJECT_STATUS NO_ATTACK holds the crew's fire to 10 s (甲敌 100 to
    s8), then 75 / 50 / 25 at s9 / s11 / s13 (12.5 a second); the control's enemy (乙敌) 87 at s1, down ~6 a second."""
    rows = _changes('engine_scripts8b', 'status', 20.0)
    assert all(v[0] == 100 for sec, v in rows if sec <= 10)
    at75, at25 = _first(rows, 0, lambda v: v <= 75), _first(rows, 0, lambda v: v <= 25)
    assert 10 <= at75 <= 10 + LAG and 3 <= at25 - at75 <= 5
    down = [(sec, v[1]) for sec, v in rows if 0 < v[1] < 100]
    (s0, h0), (s1, h1) = down[0], down[-1]
    assert 5 <= (h0 - h1) / (s1 - s0) <= 8, down


def test_scripts8b_base_power_sets_the_supply_as_the_bench():
    """bench engine_scripts8b power: PLAYER_SET_BASE_POWER (1000) at 2 s, (300) at 6 s -- 电级 4 then 3: it sets the
    supply, it does not add."""
    rows = _changes('engine_scripts8b', 'power', 10.0)
    assert [v[0] for _, v in rows][-2:] == [4, 3]
    assert _first(rows, 0, lambda v: v == 4) <= 2 + LAG and 6 <= _first(rows, 0, lambda v: v == 3) <= 6 + LAG


@pytest.mark.parametrize('variant, seen', [('pfire', 1), ('pdis', 2)])
def test_scripts8b_the_players_cast_as_the_bench(variant, seen):
    """bench engine_scripts8b pfire / pdis: PLAYER_FIRE_SPECIAL_POWER_AT_WAYPOINT casts the player's collider -- target
    0 whole 56 frames after the cast, then 44 %; PLAYER_TRIGGERED_SPECIAL_POWER sees it one frame (施放数 1). pdis:
    with PLAYER_SPECIAL_POWER_AVAILABILITY Disabled the script's cast goes all the same; the named cast ~20 s later is
    seen (施放数 2 from s26) and hurts nobody (血0 stays 44)."""
    rows = _changes('engine_scripts8bs', variant, 40.0 if variant == 'pdis' else 20.0)
    full, health, count = rows[-1][1][-3:]
    assert abs(full - 56) <= 1 and health == 44 and count == seen
    if variant == 'pdis':
        assert 24 <= _first(rows, 2, lambda v: v == 2) <= 26


@pytest.mark.parametrize('build_name', ['engine_invuln', 'engine_invuln_enemy'])
def test_invuln_the_modifier_alone_keeps_nothing_whole_as_the_bench(build_name):
    """bench 2026-11-04 engine_invuln (targets neutral, handed to the enemy at 8 s by NAMED_TRANSFER_OWNERSHIP_PLAYER)
    and _enemy (enemy throughout): every lane hurt from s7 (A 1111, B 11), the kept-dark ones too; high's health falls
    at one pace through dark, lit and dark again -- below 90 / 75 / 60 / 45 % at s15 / s23 / s33 / s43."""
    rows = _changes(build_name, 'invuln', 50.0)
    assert rows[-1][1][:2] == [1111, 11] and _first(rows, 0, lambda v: v == 1111) <= 7 + LAG
    for k, bench in enumerate((15, 23, 33, 43)):
        assert bench <= _first(rows, 2, lambda v, w=10 ** (k + 1) - 1: v >= w // 9) <= bench + LAG


# bench 2026-11-04 engine_invuln_kinds: the box beside the A09 Iron Curtain aura object is never hurt -- it is a PropBody
# (no health to take: engine_propbody a, simunits.prop_body), so no aura is needed to hold it (line E, 11-10)
def test_invuln_kinds_the_aura_box_holds_as_the_bench():
    rows = _changes('engine_invuln_kinds', 'invuln', 50.0)
    assert rows[-1][1][:2] == [1100, 11]


def test_area_counts_whose_units_as_the_bench():
    """bench 2026-10-25 / 11-04 engine_area (E1): in the west field, three of the player's Guardians -- the player's
    kind count 3, the enemy's kind count 3 too (a KindOf count takes every player's), the enemy's template count 0 and
    SKIRMISH_PLAYER_HAS_UNITS_IN_AREA(enemy) false (those take only the named player's); at the north base the
    player's kind count 2 (the enemy's warriors), the template count 0. The bench measured "has units" only where the
    named player has none (the half that matters: it does not take another player's)."""
    assert _changes('engine_area', 'field', 12.0)[-1][1] == [3, 3, 0, 0]
    assert _changes('engine_area', 'camp', 12.0)[-1][1] == [2, 0]


def test_attacked_by_player_holds_while_the_attacker_stands_as_the_bench():
    """bench 2026-11-04 engine_attack gone (E2): NAMED_ATTACKED_BY_PLAYER holds while the last unit that hit the target
    stands (between its shots too) and is false the frame it is deleted (A) or killed (B) at 6 s, the targets alive,
    about a third of their health gone by then."""
    rows = _changes('engine_attack', 'gone', 16.0)
    assert all(v[:2] == [1, 1] for sec, v in rows if 1 <= sec <= 6)
    assert all(v[:2] == [0, 0] for sec, v in rows if sec >= 7) and rows[-1][1][:2] == [0, 0]
    assert all(55 <= h <= 75 for h in rows[-1][1][2:])


# ---- waypoint paths (Sim.order_follow): bench 2026-11-10 engine_waypath (checks/engine_waypath.py 读数). Each
# reading is (counter index, value, bench second); the simulator's first second at that value is LAG later at most.
WAYPATH = {
    'line': [(0, 1, 3), (0, 2, 9), (1, 4, 9), (0, 3, 15)],
    'exact': [(0, 1, 3), (0, 2, 9), (1, 4, 9), (0, 3, 15)],
    'near': [(0, 1, 3), (0, 2, 15), (1, 4, 16), (0, 3, 21)],
    'team': [(0, 1, 3), (0, 2, 10), (0, 3, 17), (1, 1, 5), (1, 2, 10), (1, 3, 14)],
}


@pytest.mark.parametrize('check', sorted(WAYPATH))
def test_waypath_follows_the_links_waypoint_by_waypoint_as_the_bench(check):
    """line / exact walk A -> B (within 10 of it: no corner cut, the two alike) -> C and stay; near joins at B, the
    nearest, A never again; team: each truck to the waypoint plus its offset from the team's middle (both within 100
    of every one), the first there moves the team on -- truck 3, ahead on the last leg, at C 3 s before truck 2."""
    rows = _changes('engine_waypath', check, 45.0 if check == 'team' else 50.0)
    for k, value, bench in WAYPATH[check]:
        got = _first(rows, k, lambda v, value=value: v == value)
        assert got is not None and bench <= got <= bench + LAG, (check, k, value, bench, got)
    assert rows[-1][1][0] == 3 and (check != 'near' or all(v[0] != 1 for sec, v in rows if sec >= 15))


def test_waypath_loop_goes_round_and_round_a_lap_about_20_s():
    """loop: C linked back to A -- bench 段1 back at A at s23 43 63 84 (laps 20-21 s); the simulator 2-3 s later."""
    rows = _changes('engine_waypath', 'loop', 90.0)
    back = [sec for (sec, v), (_, w) in zip(rows[1:], rows) if v[0] == 1 and w[0] == 3]
    assert len(back) >= 4 and all(b <= s <= b + LAG + 1 for b, s in zip((23, 43, 63, 84), back)), back


# bench 2026-11-10 checks/engine_wayatk.py (counters 敌血, 近敌, 段1): a Guardian on the path A -> B -> C, an enemy
# Guardian (NO_ATTACK) 150 beside the A -> B leg
def test_wayatk_a_plain_path_walker_fires_on_the_way_and_does_not_stop():
    """plain (NAMED_FOLLOW_WAYPOINTS): bench 段1 1 s3, 2 s7, 3 s10, two hits on the way (敌血 73 at the end)."""
    rows = _changes('engine_wayatk', 'plain', 50.0)
    for value, bench in ((1, 3), (2, 7), (3, 10)):
        got = _first(rows, 2, lambda v, value=value: v == value)
        assert got is not None and bench <= got <= bench + LAG, (value, bench, got)
    assert 0 < rows[-1][1][0] < 100


@pytest.mark.parametrize('check', ['atk', 'amove'])
def test_wayatk_an_attack_walker_stops_to_fight_and_goes_on_once_it_is_dead(check):
    """atk (NAMED_ATTACK_FOLLOW_WAYPOINTS) = amove (ATTACK_MOVE_TEAM_TO to B), second by second on the bench: first
    hit s4, a shot every 2 s (13.9 %) to 3 at s16 (the counter keeps a dead unit's last value), on to B at s21 --
    14 s after plain's. GAP (the fire model, not the path): the simulator's continuous fire (6.25 %/s from s6) kills
    at s21 and reaches B at s24; asserted: the first hit within LAG, B only after the kill, 10+ s after plain's."""
    rows = _changes('engine_wayatk', check, 50.0)
    hit = _first(rows, 0, lambda v: v < 100)
    dead = _first(rows, 0, lambda v: v == 0)
    at_b = _first(rows, 2, lambda v: v == 2)
    assert 4 <= hit <= 4 + LAG and dead is not None and at_b is not None and at_b > dead
    assert at_b - _first(_changes('engine_wayatk', 'plain', 50.0), 2, lambda v: v == 2) >= 10
