"""The skirmish AI on the plan simulator against bench probes no other test replays (B round 108): each test names the
probe (checks/engine_X.py) whose docstring holds the readings it asserts -- the bench's, never the simulator's own
expectation. Rules (who goes where, who first, counts at a time point, never / always), not exact seconds, unless the
simulator and the bench already agree. A reading the simulator misses is a strict xfail saying both numbers. Skipped
where ra3model.ai is not on this computer, as test_simai.py is."""
import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location('simai', ROOT / 'experimental' / 'cnv' / 'simai.py')
simai = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(simai)

pytestmark = pytest.mark.skipif(not simai.available(), reason='no ra3model.ai (labpaths.ENGINE_MODEL)')


@pytest.fixture(scope='module')
def lib():
    return simai.model()['xmldata'].Library()


def _probe_run(build, lib, until, check='a'):
    """(world, rows): the probe's counters once a second, row i ~ second i+1, each row {label: value}."""
    w = simai.run(build, check, until, lib=lib)
    labels = [lab for _, lab in w.sim.test.counters]
    return w, [dict(zip(labels, v)) for _, v in w.sim.series]


def _vals(rows):
    """The rows as plain lists, in the probe's counter order (for probes whose labels are long)."""
    return [list(r.values()) for r in rows]


def _first_row(rows, key, pred=lambda v: v >= 1):
    return next((i for i, r in enumerate(rows) if pred(r[key])), None)


# ---- checks/engine_aicrush.py a (bench 2026-11-09, readings in its docstring): Crush kills the guards on contact
@pytest.mark.parametrize('build', ['aicrush0', 'aicrushlo'])
def test_without_crush_the_guards_are_not_run_over(lib, build):
    """aicrush0 / aicrushlo (checks/engine_aicrush.py): the guards are still 8 or more (bench 11-12 through s37)."""
    _, rows = _probe_run(build, lib, 37.0)
    assert all(r['守军数'] >= 8 for r in rows)


@pytest.mark.xfail(strict=True, reason='aicrush1 has 11/9/9/9/8/8 guards at s28-s33, bench has zero with '
                                       '4 tanks alive. First Crush goal now matches the guard spot, but arrival '
                                       'and target selection timing remain unresolved; hypothesis table and '
                                       'current replay: work/re/c_crush_revisit_report.md; work/re/handoff-c.md.')
def test_crush_runs_the_guards_over_at_once(lib):
    """checks/engine_aicrush.py aicrush1: no guards at s28-s33, all four tanks survive."""
    w, rows = _probe_run('aicrush1', lib, 35.0)
    samples = [(t, r) for (t, _), r in zip(w.sim.series, rows) if 28 <= t <= 33]
    # The series includes t=0; use its mission clock, not row i ~ second i+1.
    assert [t for t, _ in samples] == list(range(28, 34))
    window = [r for _, r in samples]
    assert [r['坦克数'] for r in window] == [4] * 6
    assert [r['守军数'] for r in window] == [0] * 6


# ---- checks/engine_aitarget.py a (bench 2026-11-06): which structure an attack team goes for first
@pytest.mark.parametrize('build', ['aitargetsafe', 'aitargetidle5', 'aitargetidle30', 'aitargetstill'])
def test_threat_to_ground_sends_the_team_to_the_far_plant_first(lib, build):
    """checks/engine_aitarget.py: SimpleAttack + SafestToGroundStructure / ThreatToGround (also with MaxTeamIdleTime
    5 / 30 s, MaxTeamIdleTime and MaxUnitIdleTime 600 s): the far undefended plant first (bench 到远厂 3 @ s35 ...
    4 s36-s60), the near one only afterwards (RAMPAGE, s69)."""
    _, rows = _probe_run(build, lib, 76.0)
    far, near = _first_row(rows, '到远厂'), _first_row(rows, '到近厂')
    assert far is not None and (near is None or far < near)


def test_closest_structure_sends_the_team_to_the_near_plant_and_never_the_far_one(lib):
    """checks/engine_aitarget.py aitargetnear (ClosestStructure, Distance): 到近厂 4 from s14, shot down to 0 by
    s35; 到远厂 0 all 76 s."""
    _, rows = _probe_run('aitargetnear', lib, 76.0)
    assert _first_row(rows, '到近厂') is not None and all(r['到远厂'] == 0 for r in rows)
    assert rows[40]['到近厂'] == 0 and rows[-1]['到近厂'] == 0


def test_idle_time_5_leaves_home_before_the_default(lib):
    """checks/engine_aitarget.py aitargetidle5 vs aitargetsafe: the 5 s team leaves earlier (bench 4 -> 3 @ s17 /
    @ s28)."""
    _, safe = _probe_run('aitargetsafe', lib, 40.0)
    _, idle5 = _probe_run('aitargetidle5', lib, 40.0)
    assert _first_row(idle5, '步兵在家', lambda v: v < 4) < _first_row(safe, '步兵在家', lambda v: v < 4)


@pytest.mark.parametrize('build', ['aitargetidle30', 'aitargetstill'])
def test_longer_idle_times_change_nothing(lib, build):
    """checks/engine_aitarget.py: MaxTeamIdleTime 30 s (bench: identical to the 15 s default) and MaxTeamIdleTime /
    MaxUnitIdleTime 600 s (aitargetstill: to the frame as 15 s) read the same as aitargetsafe, second for second."""
    _, safe = _probe_run('aitargetsafe', lib, 70.0)
    _, got = _probe_run(build, lib, 70.0)
    assert got == safe


@pytest.mark.xfail(strict=True, reason='simai aitargetflank = aitargetsafe (far plant first at s26); bench flank: '
                                       'far plant 1 @ s58, ~23 s later than the other tactics, near plant 0 all 76 s')
def test_flank_attack_reaches_the_far_plant_much_later(lib):
    """checks/engine_aitarget.py aitargetflank."""
    _, safe = _probe_run('aitargetsafe', lib, 76.0)
    _, flank = _probe_run('aitargetflank', lib, 76.0)
    assert _first_row(flank, '到远厂') - _first_row(safe, '到远厂') >= 15


# ---- checks/engine_aipullback.py a (bench 2026-11-09): PullbackInjured / ReverseMove / UseGatherState
@pytest.mark.parametrize('build', ['aipull1', 'aipull0'])
def test_no_tank_goes_home_once_the_tanks_are_out(lib, build):
    """checks/engine_aipullback.py aipull1 / aipull0 (4 Hammers vs 12 Peacekeepers): no retreat -- 回家 0 from s3 on
    (the simulator's tank near the factory leaves later, s14), all 4 tanks at the far plant."""
    _, rows = _probe_run(build, lib, 40.0)
    assert all(r['回家'] == 0 for r in rows[14:]) and any(r['到远厂'] == 4 for r in rows)


def test_pullback_switch_makes_no_difference_for_the_hammers(lib):
    """checks/engine_aipullback.py: aipull1 and aipull0 read second for second the same (bench)."""
    assert _probe_run('aipull1', lib, 40.0)[1] == _probe_run('aipull0', lib, 40.0)[1]


def test_a_hurt_allied_tank_team_drives_on_instead_of_home(lib):
    """checks/engine_aipullback.py aipulli1 (health 30 %, retail Allied war factory): they drive on, 到远厂 3 or more,
    回家 0 from s3, all dead (bench by s23)."""
    _, rows = _probe_run('aipulli1', lib, 60.0)
    assert all(r['回家'] == 0 for r in rows[14:]) and any(r['到远厂'] >= 3 for r in rows)
    assert rows[-1]['坦克数'] == 0


def test_a_hurt_soviet_tank_team_is_pulled_back_to_the_crane(lib):
    """checks/engine_aipullback.py aipullsov."""
    _, rows = _probe_run('aipullsov', lib, 40.0)
    assert any(r['回家'] >= 1 for r in rows[14:])


@pytest.mark.xfail(strict=True, reason='simai airev1 / airev0: 近厂 (within 150 of the far plant) 0 all along; bench '
                                       'airev1 / airev0: 近厂 1-2 at s18-s37')
@pytest.mark.parametrize('build', ['airev1', 'airev0'])
def test_reverse_move_tanks_close_in_on_the_far_plant(lib, build):
    """checks/engine_aipullback.py airev1 / airev0."""
    _, rows = _probe_run(build, lib, 40.0)
    assert any(r['近厂'] >= 1 for r in rows)


@pytest.mark.parametrize('build', ['airevp1', 'airevp0'])
def test_a_tank_team_beside_a_healed_plant_stays_whatever_the_reverse_move_switch(lib, build):
    """checks/engine_aipullback.py airevp1 / airevp0 (the target healed): 近厂 4 all along, no back-up (bench 85 s)."""
    _, rows = _probe_run(build, lib, 60.0)
    assert all(r['近厂'] == 4 for r in rows)


def test_no_one_moves_when_the_gather_state_is_off_and_a_turret_is_the_target(lib):
    """checks/engine_aipullback.py airevt1 (UseGatherState off -> state 2, an AlliedBaseDefense as target): no tank
    moves -- 近塔 = 中圈 = 坦克数 all along; the turret kills them one by one (bench 0 from s47)."""
    _, rows = _probe_run('airevt1', lib, 60.0)
    assert all(r['近塔'] == r['中圈'] == r['坦克数'] for r in rows) and rows[-1]['坦克数'] == 0


# ---- checks/engine_aibasedef.py a (bench 2026-11-09): EnterBaseDefenses / EnterBaseDefensesWhenIdle
def test_with_the_main_switch_off_nobody_goes_into_a_turret_idle_or_not(lib):
    """checks/engine_aibasedef.py aibd0 (both off) / aibdidle (only EnterBaseDefensesWhenIdle on): 进炮塔 0 all
    along, the same readings."""
    _, off = _probe_run('aibd0', lib, 60.0)
    _, idle = _probe_run('aibdidle', lib, 60.0)
    assert all(r['进炮塔'] == 0 for r in off) and idle == off


@pytest.mark.xfail(strict=True, reason='simai: nobody garrisons a turret (进炮塔 0 all along; the gap '
                                       'test_the_team_goes_into_the_house is about too); bench aibd1 进炮塔 1 from s21 '
                                       'to the end, aibdwho too')
@pytest.mark.parametrize('build,key', [('aibd1', '进炮塔'), ('aibdwho', '进炮塔')])
def test_one_peacekeeper_goes_into_the_first_turret(lib, build, key):
    """checks/engine_aibasedef.py aibd1 / aibdwho. Not 旁1 (Peacekeepers near turret 1): since engine A round 146
    (sim.Sim.attack_chase) an attack-moving one turns aside to an enemy in sight and passes turret 1, 旁1 1 without
    going in."""
    _, rows = _probe_run(build, lib, 60.0)
    assert any(r[key] >= 1 for r in rows)


# ---- checks/engine_aiomove.py a (bench 2026-11-09, rounds 83-90): what an OpeningMove line builds
@pytest.mark.parametrize('build,plants,barracks', [
    ('aiowt', 0, 1), ('aiowt2', 1, 0), ('aiodf', 0, 1), ('aiodf2', 1, 0),            # a 0 % line is never drawn
    ('aiom1', 0, 0), ('aiom2', 0, 0), ('aiom4', 0, 0), ('aiom7', 0, 0), ('aiom8', 0, 0), ('aiom16', 0, 0),
    ('aiom5', 1, 0), ('aiom6', 1, 0), ('aiom9', 1, 0), ('aiom10', 0, 1),              # only the last Build of a batch
    ('aiom11', 1, 0), ('aiom12', 1, 0), ('aiom13', 2, 0), ('aiom15', 2, 0),           # a Time of 15 s or more
    ('aiom17', 1, 1), ('aiom18', 1, 0), ('aiom19', 1, 0), ('aiom20', 1, 0)])
def test_opening_move_builds_what_the_bench_built(lib, build, plants, barracks):
    """checks/engine_aiomove.py: power plants / barracks standing at s40: nothing for a lone Build or a short opening,
    only the last Build of a batch, all of them when a Time of 15 s or more follows (aiom13 two plants, aiom17 the
    barracks and the plant)."""
    _, rows = _probe_run(build, lib, 40.0)
    assert (rows[-1]['电厂'], rows[-1]['兵营']) == (plants, barracks), rows[-1]


def test_opening_move_complete_holds_the_tanks_until_the_opening_is_over(lib):
    """checks/engine_aiomove.py aiohc1 (Complete true): the tanks stay home to s42 and are out by s44-s46 (bench 2 @
    s43, 0 from s44); aiohc0 (Complete false): out s14-15 (the simulator ~1 s later)."""
    _, done = _probe_run('aiohc1', lib, 60.0)
    _, not_done = _probe_run('aiohc0', lib, 60.0)
    assert all(r['坦克在家'] == 4 for r in done[:40]) and done[48]['坦克在家'] == 0
    assert not_done[19]['坦克在家'] == 0


@pytest.mark.xfail(strict=True, reason='simai: aiom14 plant stands at s52, aiohc1 plants s22 / s52 / s62; bench '
                                       'aiom14 plant s49 (ordered at s40, the last order), aiohc1 s19 / s49: ~3 s late')
def test_opening_plants_stand_when_the_bench_did(lib):
    """checks/engine_aiomove.py aiom14."""
    _, rows = _probe_run('aiom14', lib, 60.0)
    assert rows[48]['电厂'] == 1


# ---- checks/engine_aidefense.py a / b / c (bench 2026-11-06): StaticDefense, the Distance circle, UpdateTime
@pytest.mark.xfail(strict=True, reason='simai: the 4 Peacekeepers never leave the yard (圈900 4 to s85; aidef450 '
                                       'only partly out); bench aidef250 / aidef450 / aidefupd4 / aidefslack: 圈900 '
                                       '0 from s57, they walked to FAR and stayed')
@pytest.mark.parametrize('build', ['aidef250', 'aidef450', 'aidefupd4', 'aidefslack'])
def test_the_four_walk_out_to_far_and_stay_whatever_the_update_time(lib, build):
    """checks/engine_aidefense.py a (UpdateTime 4 s as 1 s, Distance 250 / 450, CombatLeashSlack 3): all four out of
    the 900 ring, no pull-back."""
    _, rows = _probe_run(build, lib, 85.0)
    assert rows[-1]['圈900'] == 0


@pytest.mark.parametrize('build', ['aidefctl', 'aidefctl4'])
def test_pushed_out_the_team_is_pulled_back_ring_by_ring(lib, build):
    """checks/engine_aidefense.py b (U = 1 s / 4 s): all four in the 300 ring before the push, every ring 0 after it,
    then back from the outside in (圈900, 650, 450, 300), all 4 at the end (bench to s120)."""
    _, rows = _probe_run(build, lib, 125.0, check='b')
    assert rows[50] == dict.fromkeys(rows[50], 4)
    gone = _first_row(rows, '圈900', lambda v: v == 0)
    assert gone is not None and all(rows[gone][k] == 0 for k in rows[gone])
    back = [next(i for i in range(gone, len(rows)) if rows[i][k] == 4) for k in ('圈900', '圈650', '圈450', '圈300')]
    assert back == sorted(back) and rows[-1] == dict.fromkeys(rows[-1], 4)


@pytest.mark.xfail(strict=True, reason='simai aidefctl4 (UpdateTime 4 s) = aidefctl (1 s) second for second; bench: '
                                       'aidefctl4 is back 1-2 s later per ring (900 s68 vs s66, 300 s82 vs s80)')
def test_a_longer_update_time_pulls_back_a_little_later(lib):
    """checks/engine_aidefense.py b aidefctl4 vs aidefctl."""
    _, fast = _probe_run('aidefctl', lib, 125.0, check='b')
    _, slow = _probe_run('aidefctl4', lib, 125.0, check='b')
    def back(rows):
        gone = _first_row(rows, '圈300', lambda v: v == 0)
        return next(i for i in range(gone, len(rows)) if rows[i]['圈300'] == 4)
    assert back(slow) > back(fast)


def test_a_script_move_order_never_takes_the_team_out_of_the_circle(lib):
    """checks/engine_aidefense.py b aidefmv (MOVE_NAMED_UNIT_TO): no ring ever drops after the s20 walk to the yard
    (bench 4 4 4 4 from s9 to s120)."""
    _, rows = _probe_run('aidefmv', lib, 125.0, check='b')
    assert all(r == dict.fromkeys(r, 4) for r in rows[25:])


@pytest.mark.xfail(strict=True, reason='simai aidefmv c: 圈100 0 at the end, 圈175 / 圈225 emptied by s30 (圈275 stays '
                                       '4); bench: 圈100 4 from s57 to the end, 圈175 / 225 / 275 hold 4 throughout')
def test_a_script_move_is_called_back_before_175(lib):
    """checks/engine_aidefense.py c aidefmv."""
    _, rows = _probe_run('aidefmv', lib, 125.0, check='c')
    assert rows[-1] == dict.fromkeys(rows[-1], 4)


# ---- checks/engine_aitower.py (bench 2026-11-07): where the base defence tower goes, BaseCompactness x ~600
def test_the_openers_tower_goes_up_in_the_build_time_and_in_no_band(lib):
    """checks/engine_aitower.py aitower50 a: the stop frame 451 (the wake is frame 150: 20 s, the build time; the
    simulator ~7 frames later) and every BaseCompactness band 0 -- the turret stands round the yard, elsewhere."""
    _, rows = _probe_run('aitower50', lib, 40.0)
    v = _vals(rows)
    assert v[-1][:3] == [0, 0, 0] and abs(v[-1][3] - 451) <= 7


@pytest.mark.parametrize('build', ['aitowerstate', 'aitowerfoe'])
def test_the_build_state_alone_builds_no_tower(lib, build):
    """checks/engine_aitower.py aitowerstate / aitowerfoe (own budget, only AlliedDefenseBuildState; an enemy army
    nearby): no turret in 70 s (the stop frame keeps counting). No refinery: without income the budget share pays
    nothing (bench aitowerinc / aitoweropen e, 2026-11-11)."""
    _, rows = _probe_run(build, lib, 75.0)
    assert _vals(rows)[-1][3] >= 70 * 15


def test_an_empty_opener_does_not_fund_the_share(lib):
    """checks/engine_aitower.py aitoweropen e (as aitowerstate + an opener of one Time 0s order, own budget kept):
    bench no turret to s143 -- the share is not held back by an unfinished opening."""
    _, rows = _probe_run('aitoweropen', lib, 130.0, check='e')
    assert _vals(rows)[-1][2] == 0


def test_with_a_refinery_and_a_miner_the_share_builds_the_tower(lib):
    """checks/engine_aitower.py aitowerinc e (as aitowerstate + an AI refinery and miner on the east ore): bench the
    first turret at frame 451 (ordered at the wake, its 20 s build), round the yard (350 ring 1)."""
    _, rows = _probe_run('aitowerinc', lib, 40.0, check='e')
    v = _vals(rows)[-1]
    assert v[1] == 1 and abs(v[3] - 451) <= 7


@pytest.mark.xfail(strict=True, reason='simai: one turret only (share x money less what it has paid); bench '
                                       'aitowerinc e: 4 from s89 -- the share also spends an income advance; the '
                                       'tried model (work/re/b139_income_window.patch) reddens aiskirmlow (B handoff 139)')
def test_with_income_the_turrets_keep_coming(lib):
    """checks/engine_aitower.py aitowerinc e: 塔在基地 4 by s121 (bench 2 from s49, 3 from s69, 4 from s89, 5 at s128)."""
    _, rows = _probe_run('aitowerinc', lib, 121.0, check='e')
    assert _vals(rows)[-1][2] >= 4


@pytest.mark.xfail(strict=True, reason='simai: no turret (10 % x 1700 = 170 < 800); bench aitowerinc10 e: one at '
                                       'frame 451, ordered at the wake -- the income advance (B handoff 139)')
def test_a_ten_percent_share_borrows_its_first_turret_at_the_wake(lib):
    """checks/engine_aitower.py aitowerinc10 e (DEFENSE 10 %): 落塔帧 451, 塔在基地 1 from s29 and no second to s466."""
    _, rows = _probe_run('aitowerinc10', lib, 40.0, check='e')
    v = _vals(rows)[-1]
    assert v[2] == 1 and abs(v[3] - 451) <= 7


def test_a_ten_percent_share_of_20000_buys_two_turrets_and_no_third(lib):
    """checks/engine_aitower.py aitowerinc10r f (10 %, 20000 at the wake): 塔在基地 1 from s29, 2 from s49, no third to
    s174 (AI钱 ~21000): 10 % x the bank, less what the share has paid."""
    _, rows = _probe_run('aitowerinc10r', lib, 150.0, check='f')
    assert max(r['塔在基地'] for r in rows) == 2 and rows[60]['塔在基地'] == 2


def test_a_five_percent_share_builds_no_turret_however_the_bank_grows(lib):
    """checks/engine_aitower.py aitowerinc5 f (DEFENSE 5 %): no turret to s454 while AI钱 grows 1700 -> 10700."""
    _, rows = _probe_run('aitowerinc5', lib, 120.0, check='f')
    assert all(r['塔在基地'] == 0 for r in rows)


def test_the_tower_stands_in_the_350_circle_for_half_compactness(lib):
    """checks/engine_aitower.py aitower50 b: the 350 circle >= 1 (bench from s33)."""
    _, rows = _probe_run('aitower50', lib, 40.0, check='b')
    assert _vals(rows)[-1][0] >= 1


@pytest.mark.xfail(strict=True, reason='simai: BaseCompactness 0.75 / 1.0 build the same turret as 0.5 (350 ring 1); '
                                       'bench aitower75 / aitower100 b: 350 ring 0, 560 / 700 ring 1 -- the radius '
                                       'follows BaseCompactness x ~600 (0.5 -> ~296)')
@pytest.mark.parametrize('build', ['aitower75', 'aitower100'])
def test_a_wider_base_compactness_puts_the_tower_outside_the_350_circle(lib, build):
    """checks/engine_aitower.py b."""
    _, rows = _probe_run(build, lib, 40.0, check='b')
    assert _vals(rows)[-1][0] == 0


@pytest.mark.xfail(strict=True, reason='simai aitower100 c: the 560 / 590 rings are 1 already (all four rings 1); '
                                       'bench: 560 / 590 ring 0, 620 / 650 ring 1 -> r in (590, 620]')
def test_compactness_one_radius_is_between_590_and_620(lib):
    """checks/engine_aitower.py aitower100 c."""
    _, rows = _probe_run('aitower100', lib, 40.0, check='c')
    assert _vals(rows)[-1] == [0, 0, 1, 1]


def test_an_opener_that_only_deposits_to_defense_builds_the_tower(lib):
    """checks/engine_aitower.py aitowerdep (bench: stop frame 451, the 350 ring 1 from s29; the simulator since B
    round 117 spends the DEFENSE Deposit on the build state's turret)."""
    _, rows = _probe_run('aitowerdep', lib, 40.0)
    assert abs(_vals(rows)[-1][3] - 451) <= 7


# ---- checks/engine_aistate.py a (bench 2026-11-07): SearchRange is only the tech heuristic's -- distance stops no team
def test_far_structure_does_not_stop_a_team_when_two_are_far(lib):
    """checks/engine_aistate.py aistatefar2 (a second far structure: one target per state): both teams out (bench 4 ->
    0 @ s14 for both; the simulator ~3 s later)."""
    _, rows = _probe_run('aistatefar2', lib, 30.0)
    assert rows[-1]['步兵在家'] == 0 and rows[-1]['坦克在家'] == 0


@pytest.mark.xfail(strict=True, reason='simai aistatefar: the infantry go (步兵在家 0 @ s17) and the tanks stay home '
                                       '(4); bench: the tanks 4 -> 0 @ s14, the infantry 4 all run (one structure '
                                       'only, a target one state holds is not given to another)')
def test_one_far_structure_goes_to_the_tank_team_alone(lib):
    """checks/engine_aistate.py aistatefar."""
    _, rows = _probe_run('aistatefar', lib, 30.0)
    assert rows[-1]['坦克在家'] == 0 and rows[-1]['步兵在家'] == 4


# ---- checks/engine_aiteamfilter.py a, aiar0-3 (bench 2026-11-09, B round 90): AlwaysRecruit -- does a team that has
# gone out take the tanks the AI builds after it (readings in missions/aiteamfilter_bench.py under aiar3)
def test_without_always_recruit_the_late_tanks_stay_home(lib):
    """checks/engine_aiteamfilter.py aiar0 (AlwaysRecruit false): the two built after the team left stay home (bench
    built s20 / s30, 坦克在家 2 of 6 owned; the simulator builds them s23 / s34)."""
    _, rows = _probe_run('aiar0', lib, 62.0)
    assert rows[-1]['坦克在家'] == 2 and rows[-1]['坦克拥有'] == 6


def test_always_recruit_the_gone_team_takes_the_late_tanks(lib):
    """checks/engine_aiteamfilter.py aiar1 (AlwaysRecruit true): each late tank is home a while, then taken by the team
    out there (bench built s19 -> taken s29, s30 -> taken s56; the simulator s23 -> s30, s34 -> s60)."""
    _, rows = _probe_run('aiar1', lib, 62.0)
    assert max(r['坦克在家'] for r in rows[19:35]) == 1
    assert rows[-1]['坦克在家'] == 0 and rows[-1]['坦克拥有'] == 6


def test_always_recruit_a_full_team_takes_no_more(lib):
    """checks/engine_aiteamfilter.py aiar2 (AlwaysRecruit true, MaxUnits 4 already full): both late tanks stay home."""
    _, rows = _probe_run('aiar2', lib, 62.0)
    assert rows[-1]['坦克在家'] == 2 and rows[-1]['坦克拥有'] == 6


def test_without_always_recruit_the_first_built_forms_a_team_the_second_stays(lib):
    """checks/engine_aiteamfilter.py aiar3 (none placed, AlwaysRecruit false): the first one forms the team and goes
    (bench built s21, out s30; the simulator s23 / s29), the second (bench s32) stays home."""
    _, rows = _probe_run('aiar3', lib, 62.0)
    assert max(r['坦克在家'] for r in rows[19:29]) == 1
    assert rows[-1]['坦克在家'] == 1 and rows[-1]['坦克拥有'] == 2


@pytest.mark.xfail(strict=True, reason='simai aiar0 builds a third Guardian s67 and a fourth s78 (owned 8 at s80); '
                                       'bench aiar0-3 own 6 to the end (late=2: the opener builds two, nothing more)')
def test_the_ai_builds_only_the_openers_two(lib):
    """checks/engine_aiteamfilter.py aiar0."""
    _, rows = _probe_run('aiar0', lib, 80.0)
    assert rows[-1]['坦克拥有'] == 6


# ---- checks/engine_aiskirm.py y (bench 2026-11-11, readings in its docstring): units of ours only when listed
def test_the_stock_ai_builds_no_unit_of_ours_from_its_own_barracks(lib):
    """aisknew: s1 owns a copied barracks that builds CNVNewPK; no build state of 1AlliedBalanced lists it -> 新维和 0
    to s168 (the bench built 6 Peacekeepers and 12 Javelins beside)."""
    _, rows = _probe_run('aisknew', lib, 170, 'y')
    assert max(r['新维和'] for r in rows) == 0
    assert rows[-1]['维和总数'] + rows[-1]['标枪总数'] >= 1


def test_listed_in_a_build_state_our_unit_takes_about_half_the_barracks(lib):
    """aisknew2: CNVNewPK listed FEWEST_UNIT in a ConstantHeuristic build state of the personality -> bench: the first
    at s27, 9 of 19 barracks units by s167. The simulator (RA3-EngineModel AIPlayer.build_units, B round 127): the
    first at s27, 10 of 14 by s167 -- a higher share than the bench's (the unit builder's own Peacekeepers and
    Javelins are fewer than the bench's, as in aisknew: 8 vs 18), so only the rule is asserted."""
    _, rows = _probe_run('aisknew2', lib, 170, 'y')
    r = rows[166]
    assert rows[27]['新维和'] >= 1 and r['新维和'] >= 0.4 * (r['新维和'] + r['维和总数'] + r['标枪总数'])


# ---- checks/engine_aiskirm.py s (bench 2026-11-11, readings in the check's RESULTS): RANDOM_UNIT and Difficulty
def test_a_bare_random_percent_is_a_percent(lib):
    """aiskrand: NEW_PK RANDOM_UNIT "0%".."30%", NEW_JAV RANDOM_UNIT "30".."100" (bare, as retail writes them) ->
    bench: 新维和 4, 新标枪 4 by s168 (the first new Javelin at s27) -- a bare 30 is 30 %; read as 30 the Javelin
    entry would never win a [0, 1) roll."""
    _, rows = _probe_run('aiskrand', lib, 170, 's')
    r = rows[166]
    assert r['新标枪'] >= 1 and r['新维和'] >= 1


def test_a_build_state_hung_at_hard_does_not_build_at_medium(lib):
    """aiskdiff: NEW_PK FEWEST_UNIT in a state Difficulty="HARD", NEW_JAV FEWEST_UNIT in one Difficulty="MEDIUM"
    -> bench (MEDIUM): 新维和 0 to s169, 新标枪 1 at s27, 8 by s167."""
    _, rows = _probe_run('aiskdiff', lib, 170, 's')
    assert max(r['新维和'] for r in rows) == 0
    assert rows[166]['新标枪'] >= 1


def test_a_new_barracks_first_unit_is_the_unit_builders(lib):
    """aiskvveh check t (ten Hammers): bench 2026-11-12 -- 警犬 1 at s23, 标枪 1 at s29 .. 6 at s57, 维和 0 and
    工程师 0 to s143. The barracks' first idle frame goes to the unit builder (the BEST_UNIT_EXPECTED entries score
    0 on a template's first lookup, FIRST_LOOKUP_ZERO), whose uniform draw gave the dog; the build states then
    take it for Javelins until the Deposit's 2000 is spent. Which unit the draw gives is luck (seed 1 = the dog)."""
    _, rows = _probe_run('aiskvveh', lib, 100, 't')
    assert rows[27]['警犬总数'] == 1 and rows[27]['标枪总数'] == 0
    assert max(r['维和总数'] for r in rows) == 0
    assert rows[98]['标枪总数'] == 6 and rows[98]['警犬总数'] == 1


def test_a_level_personality_lists_our_units_in_a_build_state_of_its_own():
    """enemy_ai.personality(new_units=...) writes what aisknew2 benched (a ConstantHeuristic state, FEWEST_UNIT,
    the unit's file included): read by the engine model, the personality's build states list it with its
    CountModifier, and its AI orders it from an idle factory that makes it."""
    spec = importlib.util.spec_from_file_location('enemy_ai', ROOT / 'experimental' / 'cnv' / 'enemy_ai.py')
    enemy_ai = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(enemy_ai)
    m = simai.model()
    xml = enemy_ai.personality('CNVTestNew', '盟军', new_units={'CNVNewPK': 2})
    assert 'DATA:CNVUnits/Data/CNVNewPK.xml' in xml and 'UnitModifier' not in xml
    data = m['data'].AIData()
    data.add_text(xml.split('\n', 1)[1])
    states = {b.id: b for b in data.personality_build_states('CNVTestNew', 'MEDIUM')}
    assert states['CNVTestNewNew'].entries == [('CNVNewPK', 'FEWEST_UNIT')]
    assert states['CNVTestNewNew'].params[0]['CountModifier'] == '2'
    ai = m['player'].AIPlayer(data, 'CNVTestNew')
    made = []
    ai.builder = lambda t: made.append(t) or True
    ai.units = lambda ai, f: []
    ai.offers = lambda ai, f: [m['teams'].Offer('CNVNewPK', state=0, cost=200)]
    ai.accounts['PRODUCTION'] = 1000
    ai.tell(m['player'].Command('make base'))
    ai.tick(0)
    assert 'CNVNewPK' in made
    assert enemy_ai.new_units_state('x', None) == '' and 'BuildState' not in enemy_ai.personality('y', '盟军')


# ---- checks/engine_aiskirm.py z (bench 2026-11-11, readings in z's RESULTS): the barracks builds only the counter
@pytest.mark.parametrize('build, best, other', [('aiskvinf', 'AlliedAntiInfantryInfantry', 'AlliedAntiVehicleInfantry'),
                                                ('aiskvveh', 'AlliedAntiVehicleInfantry', 'AlliedAntiInfantryInfantry')])
def test_the_expected_efficiency_ranks_the_counter_first(lib, build, best, other):
    """aiskvinf (the player owns 10 conscripts): bench Peacekeepers only; aiskvveh (10 Hammers): Javelins only.
    The simulator's expected efficiency (work/re/l4_efficiency.md: B/A with the unit over B/A without) ranks the
    same one first (the orders it gives: the two tests below)."""
    w = simai.run(build, 'z', 25, lib=lib)
    b = next(iter(w.brains.values()))
    # the player's map-placed war factory has its 3 repair drones (sim.py SpawnBehavior, Codex E 7b9bb57) and the
    # AI does not count them (SimAI.living; counted, nothing of the barracks hits them and the ranking flips)
    slaves = [x for x in w.sim.living() if getattr(x, 'spawn_parent', None) is not None]
    assert len(slaves) == 3 and not set(map(id, slaves)) & set(map(id, b.living())), slaves
    ex = b.expected(b.ai, 0, [best, other])
    assert ex[best] > ex[other] > 0


# the build states order by the expected efficiency (SimAI.efficiency, on by default since B round 131; set here so
# these two keep asserting it if the default is ever turned off): the barracks' counter
def test_against_tanks_the_barracks_builds_javelins(lib, monkeypatch):
    """aiskvveh (the player owns 10 Hammers): bench 标枪 14 by s185, 维和 0. The simulator (B round 129, the Land
    build state on once ObjectOfTypeExists Rule=ALL reads any enemy object): 标枪 12, 维和 1 (the unit builder's, s68,
    while the states order nothing) by s170."""
    monkeypatch.setattr(simai.SimAI, 'efficiency', True)
    _, rows = _probe_run('aiskvveh', lib, 170, 'z')
    assert rows[-1]['标枪总数'] >= 10 and rows[-1]['标枪总数'] >= 5 * rows[-1]['维和总数']


def test_against_conscripts_the_barracks_builds_no_javelin(lib, monkeypatch):
    """aiskvinf (the player owns 10 conscripts): bench 维和 7 by s164, 标枪 0 to s169. B round 129's strict xfail
    (sim 5 / 9, the Javelin ranked first) was the player's war factory drones in the AI's count (aircraft: only the
    Javelin hits them); without them (SimAI.living) the simulator builds no Javelin."""
    monkeypatch.setattr(simai.SimAI, 'efficiency', True)
    w, rows = _probe_run('aiskvinf', lib, 170, 'z')
    assert rows[-1]['维和总数'] >= 4
    # the bench's 标枪 0 split by source (B round 140): none from the build states; a Javelin the unit builder's
    # uniform draw gives (the model's s136 draw, seed 1) is luck -- the bench's draws here were dogs / an engineer
    log = [(k, t) for b in w.brains.values() for f, k, t in b.ai.log]
    assert ('state build', 'AlliedAntiVehicleInfantry') not in log
    assert rows[-1]['标枪总数'] == log.count(('produce', 'AlliedAntiVehicleInfantry'))


# the war factory (B round 132): an empty IFV held its passenger guns (slots 3-7 of its WeaponSetUpdate, one
# <Weapon Upgrade="Uprade_IFV_*"> line each: a 750-dps pistol, a 484-dps rifle ...), so the AI's expected efficiency
# put it at 7.6 vs conscripts (a Riptide 1.37) and the war factory built IFVs only, no Riptide. simunits.weapon_sets
# now reads Upgrade as a need (pick_weapons' upgrades; passengers granting it are not modelled)
def test_an_empty_ifv_holds_only_its_missiles():
    simunits = simai.simunits
    ws = simunits.weapon_sets('AlliedAntiAirVehicleTech1')
    held = [w.get('weapon_key') for w in simunits.pick_weapons(ws, set())]
    assert held == ['AlliedAntiAirVehicleTech1MissileGroundLauncher', 'AlliedAntiAirVehicleTech1MissileLauncher']
    shot = [w.get('weapon_key') for w in simunits.pick_weapons(ws, {'CONTAINER_OCCUPIED'}, {'Uprade_IFV_Shotgun'})]
    assert shot == ['AAAVT1_ShotgunWeapon']


def test_against_conscripts_the_war_factory_builds_riptides(lib, monkeypatch):
    """aiskvinf (z, bench 2026-11-11): 激流 1 s111 .. 6 s165. Three Riptides are a team's order (s101 in the
    simulator, the same in both builds); the other three are the amphibious build state's -- with the IFV fix its
    Riptide (1.16) outranks the IFV (1.04): 3 more by s169 (before: none, 4 IFVs). The war factory makes the land
    form AlliedAntiInfantryVehicle_Ground, which the probe's counter (AlliedAntiInfantryVehicle) does not count in
    the simulator: both forms are counted here."""
    monkeypatch.setattr(simai.SimAI, 'efficiency', True)
    w = simai.run('aiskvinf', 'z', 175, lib=lib)
    assert _riptides(w) >= 5


def _riptides(w):
    b = next(iter(w.brains.values()))
    return sum(1 for x in b.living() if x.owner == b.player
               and x.template in ('AlliedAntiInfantryVehicle', 'AlliedAntiInfantryVehicle_Ground'))


def test_against_tanks_only_the_teams_riptides(lib, monkeypatch):
    """aiskvveh (z, bench 2026-11-11): 激流 1 s112 .. 3 s133 against 10 Hammers, no more to s185 -- the team's three
    only; the build state's war factory pick is not a Riptide (simulator: the IFV 1.041 over the Riptide 1.019; the
    bench's z does not count IFVs)."""
    monkeypatch.setattr(simai.SimAI, 'efficiency', True)
    w = simai.run('aiskvveh', 'z', 175, lib=lib)
    assert _riptides(w) == 3
