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


@pytest.mark.xfail(strict=True, reason='Crush dispatch is connected, but aicrush1 still has 8 guards at row 32; '
                                       'bench has 0 from s28-s33. First move misses its original target footprint; '
                                       'movement interface investigation: work/re/handoff-c.md (Crush path).')
def test_crush_runs_the_guards_over_at_once(lib):
    """checks/engine_aicrush.py aicrush1."""
    _, rows = _probe_run('aicrush1', lib, 35.0)
    assert rows[32]['守军数'] < 8


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


@pytest.mark.xfail(strict=True, reason='simai (since B round 117 the DEFENSE share x money buys towers): the turret '
                                       'at frame 458 (50 % x 1700 = 850 >= 800 at the wake); bench: none in 70 s. Not '
                                       'told apart yet (handoff-b section 125): the share funds nothing without income '
                                       '(no refinery here) / before an opening is done (no opener here) / under this '
                                       'own ConstantHeuristic budget state')
@pytest.mark.parametrize('build', ['aitowerstate', 'aitowerfoe'])
def test_the_build_state_alone_builds_no_tower(lib, build):
    """checks/engine_aitower.py aitowerstate / aitowerfoe (own budget, only AlliedDefenseBuildState; an enemy army
    nearby): no turret in 70 s (the stop frame keeps counting)."""
    _, rows = _probe_run(build, lib, 75.0)
    assert _vals(rows)[-1][3] >= 70 * 15


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
    The simulator's expected efficiency (0x8bd780, l4_efficiency.md: B/A with the unit over B/A without) ranks the
    same one first. Not yet ordering by it (Brain: host.efficiency off -- the unit builder fills the barracks
    first, B handoff 130 H1), so only the ranking is asserted."""
    w = simai.run(build, 'z', 25, lib=lib)
    b = next(iter(w.brains.values()))
    ex = b.expected(b.ai, 0, [best, other])
    assert ex[best] > ex[other] > 0
