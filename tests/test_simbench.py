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
                    'b': ([(133, 3), (150, 1953), (157, 1929), (210, 1753)], 221)}


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


def test_production_needs_a_factory_and_its_prerequisites():
    """Nothing is offered or queued without a factory of the player's; a unit whose NeededUpgrade the player lacks is
    not offered until GIVE_PLAYER_UPGRADE gives it; a banned one (ALLOW_DISALLOW_ONE_BUILDING 0) is not."""
    import build
    import sim
    m, t, _ = build.resolve('engine_production', 'a')
    s = sim.Sim(m, t)
    s.advance(15)
    names = [o[0] for o in s.offers(s.human)]
    assert 'AlliedEngineer' in names and 'AlliedInfiltrationInfantry' not in names
    s.act('GIVE_PLAYER_UPGRADE', [s.human, 'Upgrade_AlliedTech2'], None)
    assert 'AlliedInfiltrationInfantry' in [o[0] for o in s.offers(s.human)]
    s.act('ALLOW_DISALLOW_ONE_BUILDING', [s.human, 'alliedengineer', 0], None)
    assert 'AlliedEngineer' not in [o[0] for o in s.offers(s.human)] and not s.order_build(s.human, 'AlliedEngineer')
    for f in s.factories(s.human):
        s.destroy(f, 'test', delete=True)
    assert s.offers(s.human) == [] and not s.order_build(s.human, 'AlliedAntiInfantryInfantry')


def test_production_mutation_no_order_no_engineer():
    """Mutation: without the order the money stays and no engineer comes -- the readings above are the order's."""
    s, rows, _ = _production_rows('a', order=False)
    assert all(rd['工程师'] == 0 for rd in rows) and s.money[s.human] == 2000
