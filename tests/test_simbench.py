"""A4's bench checks judged in the plan simulator (experimental/cnv/simbench.py, docs/story/sim-vs-bench-a4.md): the ones
the simulator can stand in for pass on the current plan and map, and fail when the player does nothing (so they
are judging something); a reading the simulator has no rule for is listed as SKIP, never as PASS."""
import importlib.util
import math
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
# loaded by file: simbench.py puts the cnv folders on the path itself (no new sys.path edit here: guard G4's ceiling)
_spec = importlib.util.spec_from_file_location('simbench', ROOT / 'experimental' / 'cnv' / 'simbench.py')
simbench = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(simbench)
import engine.loop.frame as simloop  # noqa: E402
import engine.orders.order as simorder  # noqa: E402


# DEMO_KILL (strict xfail 2026-11-07, green since simorder.held_up): the opening demo's pair, stopped by the ice 157
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
    """R4 (sim.Sim.capture_due / engine/modules/deposit.py): bench 2026-11-07 `cnv_check a4 derrick` -- the derrick the player's
    at the first reading after the order (s4) with 500 (the capture bonus), 515 at s7, 800 at s46 (15 every 2 s)."""
    status, lines = simbench.run('derrick')
    got = _series(lines)
    taken = next(s for s, (ours, _) in got if ours == '1')
    money = {s: int(v) for s, (_, v) in got}
    assert abs(taken - 4) <= 1 and money[taken] == 500, got
    at = lambda sec: money[max(s for s in money if s <= sec)]
    assert abs(at(7) - 515) <= 15 and abs(at(46) - 800) <= 15, got


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
    rows, done = [], s.production.due

    def read(frame):
        done(frame)
        rows.append({lab: s.counters.get(c, 0) for c, lab in t.counters})
    s.production.due = read
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
    a banned job stands (Sim.order_build press, Sim.production.due)."""
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
        s.delete(f, 'test')
    assert [o for o in s.offers(s.human) if not o[0].startswith('Upgrade_')] == [] and \
        not s.order_build(s.human, 'AlliedAntiInfantryInfantry')


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
    got = [simorder.power_refusal(s, simorder.Peers(s), s.body(m.role(f'engineer b{k}').name), power, *s.point(m.mark(f'b{k}'))) for k in (1, 2, 3)]
    assert got == [None, None, None]
    a, d = s.body(m.role('engineer a').name), s.body(m.role('engineer d').name)
    assert simorder.power_refusal(s, simorder.Peers(s), a, power, *s.point(m.mark('a2'))) == 'too near an object'
    assert simorder.power_refusal(s, simorder.Peers(s), d, power, 790.0, 2100.0) is None
    for e, spot in (('engineer w', 'w'), ('engineer c', 'c1')):
        assert s.order_power(s.body(m.role(e).name), power, s.point(m.mark(spot))) == (False, 'not pathable')


def test_super_a_scripts_cast_starts_the_retail_reload():
    """The proton collider's script cast (p) starts its reload: bench engine_super f -- ready again 5550 frames after the
    cast (ReloadTime 360 s = 5400 from the SDK's GlobalData SpecialPowerTemplates.xml + sim.RELOAD_LAG 150; every cast
    restarts it, RA3 1.13, read, work/re/l2_ability.md): the player's click refused (order_power, INFERRED) until it is over."""
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
    s.delete(ref, 'test')
    assert not s.order_build(s.human, 'Upgrade_AlliedTech2')


def test_production_mutation_no_order_no_engineer():
    """Mutation: without the order the money stays and no engineer comes -- the readings above are the order's."""
    s, rows, _ = _production_rows('a', order=False)
    assert all(rd['工程师'] == 0 for rd in rows) and s.money[s.human] == 2000


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


def test_power_cut_the_coil_stops():
    """Mutation of on: the plant deleted, the coil is unpowered from then on."""
    s, rows = _powerdef('cut', until=12.0)
    coil = next(b for b in s.living() if b.template == 'SovietBaseDefenseAdvanced')
    assert s.short_of_power(coil.owner) and s.unpowered(coil)
    s2, _ = _powerdef('on', until=12.0)
    assert not s2.unpowered(next(b for b in s2.living() if b.template == 'SovietBaseDefenseAdvanced'))


def test_power_back_after_the_plant_unpacks():
    """A plant made short of power unpacks trunc((2 - 0.3) x 150) = 255 frames before it counts (RA3, work/re/l2_construction.md); the
    coil fires after that: no loss before, the first after (bench: 475, ~325 after the plant)."""
    s, rows = _powerdef('back')
    plant = next(b for b in s.bodies.values() if b.template == 'SovietPowerPlant')
    made = int(round(plant.made_at * 15))
    assert abs(plant.unpack_end - made - 255) <= 1          # made_at is the tick's second, the frame the script's
    first = next(r['帧数'] for r in rows if r['坦克'] < 6)
    assert plant.unpack_end <= first <= 475


def test_shot_clock_the_coil_shoots_every_31_s_one_shot_a_tank(monkeypatch):
    """Engine line C round 2: with Sim.shot_clock the coil (SovietBaseDefenseAdvancedTeslaGun: PreAttack 2.5 +
    Firing 0.5 + Reload 0.1 = 3.1 s, Damage 450 against a 480-health tank) loses a tank every 48 frames (round 6: the weapon's own frames, engine_clip)
    (the clock works): the tanks face north with the coil behind them, 450 x Rear 110 % = 495 (engine line A round
    186, Sim.flank_of) -- one tank a shot, as on the bench (checks/engine_powerdef.py). The bench's interval is ~125
    (~4.15 s a shot): ~1 s a shot the weapon data does not say, not found -- why the clock stays off by default and
    the xfail above stands. Frames 100-150 when found."""
    import sim
    monkeypatch.setattr(sim.Sim, 'shot_clock', True)
    s, rows = _powerdef('on')
    lost = [r['帧数'] for i, r in enumerate(rows) if i and r['坦克'] < rows[i - 1]['坦克']]
    assert all(rows[i - 1]['坦克'] - r['坦克'] == 1 for i, r in enumerate(rows) if i and r['坦克'] < rows[i - 1]['坦克'])
    assert len(lost) >= 4 and all(45 <= b - a <= 60 for a, b in zip(lost, lost[1:]))      # rows are 15 frames apart
    coil = next(b for b in s.living() if b.template == 'SovietBaseDefenseAdvanced')
    assert coil.weapons[0]['sched'] == [round(38 / 15, 4)] and abs(coil.weapons[0]['cycle'] - 48 / 15) < 1e-9


def crush_levels(template, own=None):
    """(crusher, crushable) as the CrusherInfo module reads them (engine/modules/crush.py; no block: (0, None))."""
    import engine.data.units as simunits
    from engine.modules import crush
    d = crush.CrushData.parse(*(simunits.module_blocks(template, 'CrusherInfo', own) or [('', '')])[0])
    return d.crusher, d.crushable


def test_crush_levels_come_from_the_data_and_the_greater_wins():
    conscript, hammer = crush_levels('SovietAntiInfantryInfantry'), crush_levels('SovietAntiVehicleVehicleTech1')
    guardian, apoc = crush_levels('AlliedAntiVehicleVehicleTech1'), crush_levels('SovietAntiVehicleVehicleTech3')
    sickle = crush_levels('SovietScoutVehicle')
    assert conscript[1] == 10 and hammer == (20, 20) and guardian[1] == 20 and apoc == (30, 31) and sickle[1] == 30
    assert hammer[0] > conscript[1] and not hammer[0] > guardian[1]             # crush.md: all 1 dies, all 2 lives
    assert apoc[0] > guardian[1] and not apoc[0] > sickle[1] and not apoc[0] > apoc[1]     # all 3 dies, b 1 lives


def test_a_crushers_move_onto_a_crushable_enemy_keeps_its_goal_and_allies_still_hold_theirs():
    """Sim.claims (Generals' Pathfinder::checkDestination): a Hammer's spot search holds its allies' spots and a
    standing enemy it cannot crush (the guardian, 20 against 20), not a crushable one (the conscript, 10) -- sent onto
    the conscript, it keeps the conscript's spot as its goal (aicrush1's first Crush move had it moved 31.6 aside,
    work/re/c_crush_path_report.md). An ally sent there is moved off the Hammer's goal."""
    import build
    import sim
    m, t, _ = build.resolve('engine_crush', 'all')
    s = sim.Sim(m, t)
    ground = [b for b in s.living() if b.speed > 0 and b.surface == 'ground']
    hammer = next(b for b in ground if b.template == 'SovietAntiVehicleVehicleTech1' and b.crusher)
    conscript = next(b for b in ground if b.template == 'SovietAntiInfantryInfantry' and s.enemy(hammer.owner, b.owner))
    guardian = next(b for b in ground if b.template == 'AlliedAntiVehicleVehicleTech1' and s.enemy(hammer.owner, b.owner))
    allies = [b for b in ground if b is not hammer and b.owner == hammer.owner]
    held = {(x, y) for x, y, _ in s.claims(hammer)}
    assert (conscript.x, conscript.y) not in held and (guardian.x, guardian.y) in held
    assert allies and all((b.x, b.y) in held for b in allies)
    s.order_move(hammer, (conscript.x, conscript.y), False)
    assert tuple(hammer.dest) == (conscript.x, conscript.y)
    s.order_move(allies[0], (conscript.x, conscript.y), False)
    assert tuple(allies[0].dest) != (conscript.x, conscript.y)


# ---- mining (HOOKS 7): engine_mining's layout -- the refinery 180 from a lone node -- on Niagara's bluff ore (the
# probe map has no ground for the simulator); the loop alone (mine_due), frames from 0
def _mining(miners=1, frames=1200, turn=135.0):
    """turn: the node turned this many degrees off facing the refinery (retail 0; engine_mining a's pad 135)."""
    import build
    import sim
    m, _, _ = build.resolve('aiskirm', None)
    s = sim.Sim(m, None)
    node = next(b for b in s.living() if b.template == 'OreNode' and b.x > 3300 and b.y < 1400)
    node.angle = math.radians(turn)                 # the refinery stands east of it
    p = s.human
    s.add('test refinery', 'AlliedRefinery', p, node.x + 180.0, node.y)
    for k in range(miners):
        s.add(f'test miner {k}', 'AlliedMiner', p, node.x + 180.0, node.y)
    s.money[p] = 0
    got = []
    for fr in range(frames):
        simloop.mine(s, fr, None)
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


def _trips(got):
    starts = [f for f in range(1, len(got)) if got[f] > got[f - 1] and got[f - 1] % 250 == 0]
    return [b - a for a, b in zip(starts, starts[1:])]


# bench 2026-11-12 checks/engine_mining.py mineturn<k> p (work/bench_results/mineturn*__p.json): the node turned k
# degrees off facing its refinery -> the period (二笔 - 首笔 = 三笔 - 二笔)
MINE_TURN_BENCH = {0: (151,), 45: (186,), -45: (187,), 90: (241,), -90: (241,), 180: (323,)}


@pytest.mark.parametrize('turn', sorted(MINE_TURN_BENCH))
def test_mining_a_trip_goes_by_how_far_the_node_is_turned_off_its_refinery(turn):
    """mineturn<k> p: retail's facing (0) trips in 151, the further the node is turned away the longer the drive round
    it, either way alike; 45 within 2 (the bench 186 / 187, niagara's 185)."""
    trips = _trips(_mining(frames=1600, turn=float(turn)))
    want = MINE_TURN_BENCH[turn][0]
    assert len(trips) >= 3 and all(abs(t - want) <= (2 if abs(turn) == 45 else 0) for t in trips), trips


def test_mining_niagara_east_ore_trips_in_185_as_the_ai_s_miner_did():
    """checks/engine_aitower.py aitowerinc5 f (bench 2026-11-11, b138_bench2): the AI's miner on niagara's east pad
    (the node at angle 0, 45 off facing its refinery) pays 250 every 185 frames (the 落塔帧 clock) -- ~20.3 a second,
    not the 14.7 the 269 trip gave."""
    import build
    import sim
    m, _, _ = build.resolve('aitowerinc5', None)
    s = sim.Sim(m, None)
    miner = s.bodies[m.cast['ai miner'].name]
    s.money[miner.owner] = 0
    got = []
    for fr in range(1500):
        simloop.mine(s, fr, None)
        got.append(s.money[miner.owner])
    trips = _trips(got)
    assert len(trips) >= 5 and set(trips) == {185}, trips


def test_mining_niagara_at_retail_s_facing_trips_as_mineturn0_did():
    """Round 175: the generator stands every node facing its refinery (resources.node_angle), so A7's niagara (no
    longer the benches' MEASURED copy) has the east pad's miner on mineturn0 p's geometry -- the node 180 straight
    ahead, turned 0 -- and its trip is that bench's 151 (~24.8 a second, not the 185 the benches read)."""
    import build
    import sim
    from maps import niagara
    m, _, _ = build.resolve('aitowerinc5', None)
    assert m.map.NODES == 'measured' and getattr(niagara, 'NODES', 'retail') == 'retail'
    m.map = niagara
    s = sim.Sim(m, None)
    for b in [b for b in s.living() if b.unpack_parent is not None]:    # the refinery's own (round 177): the placed
        s.delete(b, 'test')                                           # one's trip alone, as before
    miner = s.bodies[m.cast['ai miner'].name]
    s.money[miner.owner] = 0
    got = []
    for fr in range(1500):
        simloop.mine(s, fr, None)
        got.append(s.money[miner.owner])
    trips = _trips(got)
    assert len(trips) >= 5 and set(trips) == {MINE_TURN_BENCH[0][0]}, trips


def test_mining_a_second_miner_on_one_node_adds_nothing():
    """bench engine_mining b / d: two miners on one node earn what one does -- the other waits there for good (the
    retail node has no queue place)."""
    assert _mining(miners=2) == _mining(miners=1)


def _sim_resolve(build_name, check):
    import build
    import sim
    m, t, _ = build.resolve(build_name, check)
    return m, t, sim.Sim(m, t)


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


def test_line_of_fire_is_the_weapons_flag():
    """`los` = ATTACK_NEEDS_LINE_OF_SIGHT in the WeaponTemplate's Flags: the peacekeeper's shotgun and the Guardian's
    cannon have it, the Athena's lob (AthenaCannonWeapon) does not."""
    import engine.data.units as simunits
    assert all(w['los'] for w in simunits.fight('AlliedAntiInfantryInfantry')['weapons'])
    assert all(w['los'] for w in simunits.fight('AlliedAntiVehicleVehicleTech1')['weapons'])
    assert not any(w['los'] for w in simunits.fight('AlliedAntiStructureVehicle')['weapons'])


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


def test_a_weapon_doing_nothing_to_the_armour_never_takes_the_target():
    """Tanya's pistol (SNIPER) at a faction building's armour (SNIPER 0 %): Generals estimateWeaponDamage 0 ->
    INVALID_SHOT, ordered or not (the a6 Tanya who stood firing at a building); the peacekeeper's GUN (100 %) can."""
    import sim
    import engine.data.units as simunits
    plant = sim.Body('p', 'AlliedPowerPlant', 's1', 0.0, 0.0)
    plant.armor, plant.kinds = simunits.fight('AlliedPowerPlant')['armor'], frozenset({'STRUCTURE'})
    s = sim.Sim.__new__(sim.Sim)
    assert not any(s.can_hit(w, plant) for w in simunits.fight('AlliedCommandoTech1')['weapons'])
    assert all(s.can_hit(w, plant) for w in simunits.fight('AlliedAntiInfantryInfantry')['weapons'])


def test_idle_acquiring_is_the_units_own_word():
    """AutoAcquireEnemiesWhenIdle: the peacekeeper YES, the MCV NO, the Riptide writes none (Generals' 0: no idle
    acquiring); the one ATTACK_BUILDINGS is a squad's."""
    import engine.data.units as simunits
    assert simunits.acquire('AlliedAntiInfantryInfantry') == ['YES']
    assert simunits.acquire('AlliedMCV') == ['NO']
    assert simunits.acquire('AlliedAntiInfantryVehicle') == []


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


def test_scripts7_objects_made_with_an_angle_as_the_bench():
    """Bench 2026-11-09 engine_scripts7 face: two CREATE_NAMED_..._WITH_ORIENTATION and two CREATE_UNNAMED_..._WITH_
    ORIENTATION made at 1 s, 造出 4 from s1. Bench 2026-11-10 (CampScr7Face_mcp_1110_232041 frame 11, s30): the hulls
    face east, north, west, south-west for 0, pi/2, pi, -3pi/4 -- radians, 0 east, pi/2 north (the map's own)."""
    s = _sim_run('engine_scripts7', 'face', 8.0)
    assert s.series[-1][1] == [4], s.series[-1]
    from checks import engine_scripts7 as p
    made = {round(x) for x, _, _ in p.FACE}                # the panel row stands on the same line, further west
    row = {round(b.x): b.angle for b in s.living() if abs(b.y - p.FACE_Y) < 1 and round(b.x) in made}
    assert row == {round(x): pytest.approx(a) for x, a, _ in p.FACE}, row


def test_nanocore_deploys_at_a_far_waypoint_as_the_bench():
    """The egg variant (bench 11-10 engine_unpack egg: JapanBaseDefenseEgg -> JapanBaseDefense, replaced at frame 112,
    sim 108). The egg is in the unit table through its chain (simunits.resolve: BaseEgg's EditorSorting UNIT, KindOf
    =$BASE_DEFENSE_EGG_KINDOFS defined in BaseEgg.xml, its own LocomotorSet Speed 60 -- round 139). Not held: the
    bench's PLAYER_HAS_OBJECT_COMPARISON(JapanBaseDefense) stayed 0 while the area count held (场帧 522); the sim
    counts it owned."""
    import engine.data.units as simunits
    egg = simunits.stats('JapanBaseDefenseEgg')
    assert egg['speed'] == 60.0 and egg['surface'] == 'both' and 'VEHICLE' in egg['kinds'] and not egg['guessed']
    frames, unit, yard, name = _sim_run('engine_unpack_egg', 'go', 40.0).series[-1][1]
    assert 102 <= unit % 1000 <= 122 and unit // 1000 > 0, unit
    assert yard % 1000 == frames - unit % 1000, (frames, unit, yard)
    assert name == frames


# checks/engine_rewind.py (engine line D round 45, A8's Liberty rewind)
def test_rewind_carrier_wears_the_time_belt():
    """The carrier the A8 rewind bench flies: ImmortalBody (HighlanderBody let NAMED_DAMAGE kill it below full
    health, bench CampRwStill_mcp_1111_161912) and Tanya's two belt modules, 3 s back."""
    import build
    m, _, _ = build.resolve('rewind_imm', 'auto')
    x = m.units[0].xml
    assert '<ImmortalBody' in x and 'TimeStepsBack="3s"' in x and '<StoreCurrentStateUpdate' in x


def test_mark_objective_as_the_bench():
    """engine_markobj goals (bench 11-16 CampMarkGoals_mcp_1116_124443, the menu at s16.5): MARK_MISSION_OBJECTIVE_
    COMPLETED is status 2 from any status (shown, failed, hidden -> ticked), ..._NOT_COMPLETED status 1 (shown, done,
    bonus -> an empty box, never the failed mark). Before, the engine model's core kept them and Sim.objectives (the
    timeline's) never saw them."""
    _, _, s = _sim_resolve('engine_markobj', 'goals')
    s.run(12.0)
    got = {k.split()[-1]: v for k, v in s.objectives.items()}
    assert got == {'M1': 2, 'M2': 2, 'M3': 1, 'M4': 1, 'M5': 2, 'M6': 1}, got


def test_objective_status_and_links_as_the_bench():
    """engine_scripts5 goals (bench 11-09 CampScr5Goals_mcp_1109_095326, the menu at s14): O1 1 -> 2 done, O2 1 -> 3
    failed, O3 1 -> 0 hidden again, O4 2 listed done, O5 1 -> 7 still shown (7 ignored), O6 bonus shown; markers: O1
    left on the tank, O2 unlinked, O6 on the east waypoint. (Until round 267 no test replayed this probe -- only
    test_inventory's fixture string named it.)"""
    _, _, s = _sim_resolve('engine_scripts5', 'goals')
    s.run(12.0)
    got = {k.split()[-1]: v for k, v in s.objectives.items()}
    assert got == {'O1': 2, 'O2': 3, 'O3': 0, 'O4': 2, 'O5': 1, 'O6': 1}, got
    marks = {k.split()[-1]: sorted(v) for k, v in s.markers.items() if v}
    assert marks == {'O1': ['UNIT - CNV S5 Tank'], 'O6': ['CNV S5 East']}, marks
