"""The skirmish AI on the plan simulator (experimental/cnv/simai.py): the engine line's layer-4 model plays the enemy
-- its opening against the bench (checks/engine_aiopen.py f1-f3 and m, frames from the wake), and on a small
skirmish (missions/aiskirm_bench.py) it builds, makes units, teams them up and attacks the player's base. Skipped
where ra3model.ai is not on this computer (labpaths.ENGINE_MODEL), as the simulator's engine model is."""
import collections
import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
# loaded by file: simai.py puts the cnv folders on the path itself (no new sys.path edit here: guard G4's ceiling)
_spec = importlib.util.spec_from_file_location('simai', ROOT / 'experimental' / 'cnv' / 'simai.py')
simai = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(simai)

pytestmark = pytest.mark.skipif(not simai.available(), reason='no ra3model.ai (labpaths.ENGINE_MODEL)')

# checks/engine_aiopen.py f1-f3 (bench 2026-11-06, frames from the wake = the frame 'make base' ran)
BENCH_OWN = [('AlliedBarracks', 152), ('AlliedPowerPlant', 305), ('AlliedRefinery', 607), ('AlliedRefinery', 909),
             ('AlliedPowerPlant', 1062), ('AlliedWarFactory', 1364)]
BENCH_MINER = 667
BENCH_RIPTIDES = [1555, 1716, 1877]
RIPTIDE_SLACK = 7       # simai HOOKS 1: the AI is ticked after a DT tick (7-8 frames), so a unit queued once the last
                        # left the door starts up to a tick late; known difference, not a fit


@pytest.fixture(scope='module')
def lib():
    return simai.model()['xmldata'].Library()


def _from_wake(w):
    (b,) = w.brains.values()
    return b, [(f - b.started, what, t) for f, what, t in b.trace]


def test_opening_frames_match_the_bench(lib):
    b, trace = _from_wake(simai.run('aiopen', until=140, lib=lib, blocks=()))
    own = [(t, f) for f, what, t in trace if what == 'own']
    assert own == BENCH_OWN, own
    miners = [f for f, what, t in trace if t == 'AlliedMiner']
    assert miners[0] == BENCH_MINER, miners
    rip = [f for f, what, t in trace if t == 'AlliedAntiInfantryVehicle_Ground']
    assert len(rip) == 3 and all(abs(m - r) <= RIPTIDE_SLACK for m, r in zip(rip, BENCH_RIPTIDES)), rip


def test_short_of_money_the_opening_stalls_on_the_refinery(lib):
    """aiopenpoor (3000 at the wake), bench m: barracks s19, power s29, money ~0 from s37-38, the refinery never
    finished and nothing after it started."""
    w = simai.run('aiopenpoor', until=120, lib=lib, blocks=())
    b, trace = _from_wake(w)
    own = [(t, f) for f, what, t in trace if what == 'own']
    assert own == BENCH_OWN[:2], own
    assert w.sim.money[b.player] < 30, w.sim.money[b.player]
    (q,) = b.yard_q.values()                            # the orders are in (the yard's queue); its head is stuck
    assert q[0]['template'] == 'AlliedRefinery' and q[0]['full'] is None, q[0]
    # the unit builder runs beside the opening on the 2000 PRODUCTION Deposit (bench m counted no units: model only)
    spent = sum(w.cost(t) for f, what, t in trace if what == 'out')
    assert spent <= 2000, trace


@pytest.fixture(scope='module')
def skirmish(lib):
    return simai.run('aiskirm', until=300, lib=lib)


BARRACKS = ('AlliedScoutInfantry', 'AlliedAntiInfantryInfantry', 'AlliedAntiVehicleInfantry')


def _barracks_out(skirmish):
    (b,) = skirmish.brains.values()
    return [((f - b.started) / simai.FPS, t) for f, what, t in b.trace if what == 'out' and t in BARRACKS]


def test_skirmish_ai_builds_infantry_in_the_opening_until_the_deposit_is_spent(skirmish):
    """bench engine_aiskirm c: the barracks builds from ~15 s after the wake, beside the opening (the unit builder is
    tied to no team, l4_unitbuilder.md 2), 1900 of the opening's PRODUCTION Deposit 2000 by 52 s, then nothing till
    125 s (the opening's budget gives PRODUCTION 0 %)."""
    out = _barracks_out(skirmish)
    assert out and out[0][0] < 30, out                              # during the opening
    spent = sum(skirmish.cost(t) for s, t in out if s < 120)
    assert 1800 <= spent <= 2000, (spent, out)


def test_skirmish_ai_spends_the_deposit_before_70_s(skirmish):
    """bench engine_aiskirm c: nothing from the barracks between 70 and 125 s. Round 45 had seed 1 spend the rest at
    83 s (strict xfail); since round 49 (teams only for slots with a target) seeds 1-6 all spend it by 60 s -- the
    draws moved, the draw path is still not tuned (bench: by 52 s)."""
    out = _barracks_out(skirmish)
    assert not [s for s, t in out if 70 < s < 120], out


def test_skirmish_ai_barracks_mix_matches_the_bench(skirmish):
    """0x8f1490 (read, work/re/l4_unitbuilder.md B): with no UnitBuilderUnitChoiceStrategy -- no SDK personality has
    one -- every idle candidate weighs 1, so the barracks draws uniformly among its standard units. Bench c's one run
    (2 dogs, 3 Javelins, 3 Peacekeepers) is one such draw; the exact counts are chance, so only the set is asserted."""
    made = collections.Counter(t for s, t in _barracks_out(skirmish) if s < 120)
    assert set(made) == {'AlliedScoutInfantry', 'AlliedAntiInfantryInfantry', 'AlliedAntiVehicleInfantry'}, made


def test_skirmish_ai_builds_again_after_the_opening(skirmish):
    """After the opening the unit builder lives on income (CoopBudget PRODUCTION 85 %): the miners' (sim.mine_due,
    HOOKS 7) -- bench c: Peacekeepers again at 125 / 142 / 154 s."""
    assert [s for s, t in _barracks_out(skirmish) if 120 <= s < 160]


def _first_attack(b):
    return next((e for e in b.ai.teams.log if e[1] == 'go'
                 and e[2][0].startswith(('BalancedAttack', 'BalancedCleanup'))), None)


def test_skirmish_ai_builds_makes_units_and_attacks(skirmish):
    """Bench a/c and i-l (B handoff 99): the first team out is BalancedCleanup's (opening done, no enemy within 700,
    income and power advantage -- the player has no refinery: income both 0 / enemy 0), ~123 s after the wake (on
    the miners' income, HOOKS 7); the player's losses come after it left."""
    w = skirmish
    (b,) = w.brains.values()
    made = collections.Counter(t for f, what, t in b.trace if what == 'out')
    assert len(made) >= 3, made                         # a mixed army past the opening's three Riptides
    first = _first_attack(b)
    assert first and first[2][0].startswith('BalancedCleanup'), first
    assert 100 <= (first[0] - b.started) / simai.FPS <= 140, first
    lost = [x for x in w.sim.bodies.values() if x.owner == w.sim.human and not x.alive]
    assert lost, 'the attack destroyed nothing of the player'
    assert min(x.died_at for x in lost) > (first[0] / simai.FPS), 'died before the team left'


def test_skirmish_ai_cleanup_takes_the_defense_team(skirmish):
    """Bench i-m: Cleanup takes the defense team whole (LandDefense 8 -> 0, Cleanup 0 -> 8 in one frame at s131, the
    pool never above 1). read (B handoff 102): every AI tactic team is recruitable (+0x24 = 1, 0x8ef7e0 ->
    0x8b9480(1)), so the general recruit takes LandDefense's men (DEFENSE, RELEASE_TO_PRIORITY) for Cleanup
    (STANDARD) in one commit; the private teams.recruit does that and keep_on is on."""
    (b,) = skirmish.brains.values()
    first = _first_attack(b)
    assert first and len(first[3]) >= 8, first


def test_skirmish_ai_builds_again_as_soon_as_the_opening_is_done(skirmish):
    """Bench c: the 4th Peacekeeper out 125 s after the wake, i.e. the barracks restarts the moment the opening's
    budget ends (~120 s), and then hardly stops (9 infantry + engineer by 177 s). It spends its budget share of the
    bank, not only the miners' income (AIPlayer.available, INFERRED from bench d / f; round 39's sim waited for miner
    trips, 151.5 s). The bound is the seed spread, not a fit: seeds 1-6 gave 126-131.5 s both before and after
    round 43's team / target rules (a uniform draw that lands on a busy candidate skips the round; simai.md
    round 43); bench one run 125 s. Round 49 (teams only for slots with a target, B handoff 47.3) moves the draws:
    seeds 1-6 126-141.5 s (seed 1 141.5); the same workspace without that gate 126-138.5 s (seed 4) -- so the bound
    is the measured spread again (work/logs/gate_seeds2.log), not a fit."""
    again = [s for s, t in _barracks_out(skirmish) if s >= 120]
    assert again and again[0] <= 142, again


@pytest.mark.xfail(strict=True, reason='since keep_on is on (B handoff 102) the second dog is never built by 170 s '
                                       '(no team, not in the pool; off: it goes at 36 s): production side, not read')
def test_skirmish_ai_scout_dog_stays_out(skirmish):
    """Bench b: the dogs leave ~44 s after the wake and stay away 120-170 s; the first team (132.8 s) is 2 Riptides +
    3 Peacekeepers out at once, no dog. The AlliedScout team is ReleaseType NEVER_RELEASE, so no team takes its dog
    (teams.releases, read 0x8a9a90); before that rule the scout team ended the frame after it went (BalancedAttack-
    Ground, STANDARD > LOW, took the dog) and was made again every few seconds (simai.md round 39). "No dog at all in
    the first team" is not asserted: the bench's barracks drew 2 dogs, the sim's uniform draw 6 (round 35), and the
    dogs the scout team does not hold are free to join.
    Round 44: AlliedScout is MaxTargets 2 = two slots, two teams (read 0x8d72f0, work/re l4_states.md 7); the bench's
    second dog left ~3 s after the first (s55), the sim's ~20 s after (not asserted: known difference)."""
    (b,) = skirmish.brains.values()
    log = b.ai.teams.log
    until = b.started + 170 * simai.FPS
    scout = [e for e in log if e[2][0] == 'AlliedScout' and e[1] in ('go', 'ended') and e[0] < until]
    assert sorted((e[1], e[2]) for e in scout) == [('go', ('AlliedScout', 'Attack', 0)),
                                                   ('go', ('AlliedScout', 'Attack', 0, 1))], scout


# checks/engine_aistate.py (bench 2026-11-06): the probe's own personality (missions/aistate_bench.py, written into
# the mod as Mission.assets) with two states; frames from the wake (const) / from the state's flag (slash) to the
# first of its four units out of the base area (450 round the east base). Bench clock: aistateconst's wake is s9,
# the units out s14-16 (~5 s; one-second readings, so +-15 frames).
AI_HOME, HOME_R = (3850.0, 3400.0), 450.0
INF, TANK = 'AlliedAntiInfantryInfantry', 'AlliedAntiVehicleVehicleTech1'


def _first_out(build, lib, until=75.0):
    """{template: first frame one of the AI's four is out of the base area}, the run's SimAI."""
    w = simai.run(build, until=1, lib=lib)
    s, first = w.sim, {INF: None, TANK: None}
    while w.frame < until * simai.FPS:
        w.advance(1)
        for tpl in first:
            if first[tpl] is None and any(x.template == tpl and x.owner != s.human and
                                          (x.x - AI_HOME[0]) ** 2 + (x.y - AI_HOME[1]) ** 2 > HOME_R ** 2
                                          for x in s.bodies.values()):
                first[tpl] = w.frame
    return first, w


def test_mission_personality_both_states_go_at_the_wake(lib):
    """aistateconst a: both states always on -- all four of each out s14-16, the wake s9 (~5 s after it)."""
    first, w = _first_out('aistateconst', lib, until=25)
    (b,) = w.brains.values()
    assert b.ai.personality.id == 'CNVStateTest'
    for tpl, f in first.items():
        assert f is not None and abs((f - b.woke) - 5 * simai.FPS) <= 1.5 * simai.FPS, (tpl, f - b.woke)


def test_slash_flags_switch_the_states(lib):
    """aistateslash a: scripts SET_FLAG '/CNVAIInfantry' at 20 s, '/CNVAITanks' at 60 s -- the infantry out 74 frames
    after its flag, the tanks 77 after theirs."""
    first, _ = _first_out('aistateslash', lib)
    inf, tank = first[INF] - 20 * simai.FPS, first[TANK] - 60 * simai.FPS
    assert abs(inf - 74) <= RIPTIDE_SLACK and abs(tank - 77) <= 2 * RIPTIDE_SLACK, (inf, tank)


def test_bare_flags_are_the_script_players_not_the_ais(lib):
    """aistateplain a: bare flag names (the script list's own scope) -- nobody left the base."""
    first, _ = _first_out('aistateplain', lib, until=75)
    assert first == {INF: None, TANK: None}, first


def test_skirmish_ai_talks_about_itself(skirmish):
    th = skirmish.thoughts()
    (me,) = th.values()
    assert me['opening'] == 'AlliedStandard' and me['opening done']
    assert 'targets' in me and any(me['targets'].values())


# ---- the wake's script switches (checks/engine_aiswitch.py, bench 2026-11-08; work/re l4_aiswitches.md)
def _switch_run(build, lib, until=70.0):
    w = simai.run(build, 'a', until, lib=lib)
    labels = [lab for _, lab in w.sim.test.counters]
    return w, [dict(zip(labels, v)) for _, v in w.sim.series]


def test_priorities_zero_send_no_team_to_the_nearest_structure(lib):
    # bench aisw0near: 步兵在家 4 from s1 to s75, nobody at either plant (the control aitargetnear went at s13)
    w, rows = _switch_run('aisw0near', lib)
    (b,) = w.brains.values()
    assert b.ai.enemy_table == []
    assert all(r['步兵在家'] == 4 and r['到近厂'] == 0 and r['到远厂'] == 0 for r in rows)


def test_priorities_zero_do_not_stop_a_named_target(lib):
    # bench aisw0far: 到远厂 2 @ s15, 4 s17-s33, 0 from s35; then RAMPAGE to the near plant (到近厂 4 s44-s51)
    _, rows = _switch_run('aisw0far', lib)
    far = [i for i, r in enumerate(rows) if r['到远厂'] >= 1]
    near = [i for i, r in enumerate(rows) if r['到近厂'] >= 1]
    assert far and near and far[0] < near[0]


@pytest.mark.parametrize('build', ['aiswrep1', 'aiswrep0'])
def test_the_ais_hurt_plant_is_not_repaired_either_way(lib, build):
    # bench aiswrep1 / aiswrep0: 电厂血量 50 all along (75 s / 107 s), repairs 1 or 0 -- why 1 does not repair is open
    _, rows = _switch_run(build, lib)
    assert all(r['电厂血量'] == 50 for r in rows)


@pytest.mark.parametrize('build', ['aiswreb1', 'aiswreb0'])
def test_a_killed_plant_is_not_rebuilt_either_way(lib, build):
    # bench aiswreb1 / aiswreb0: 电厂数 0 from s14 to s119-s120, 5000 money, rebuild 1 or 0
    w, rows = _switch_run(build, lib, until=100.0)
    kill = int(w.sim.m.facts['kill at'])
    assert rows[kill - 2]['电厂数'] == 1 and all(r['电厂数'] == 0 for r in rows[kill + 2:])


# ---- the team state: retreat and EngagePassiveTargets (checks/engine_airetreat.py, bench 2026-11-08;
# work/re l4_micro_retreat.md, l4_micro_engage.md). The simulator's team leaves ~8 s later than the bench's (s18 / s10):
# compared from the leave.
def _left(rows, key='步兵在家'):
    return next(i for i, r in enumerate(rows) if r[key] == 0)


def test_outgunned_team_walks_home_alive_and_goes_again(lib):
    # bench airet: out s10-s12, 到远厂 2 @ s15, back home 4 @ s26 (步兵数 4 all along), out again s42, home again s54
    _, rows = _switch_run('airet', lib, until=85.0)
    out = _left(rows)
    back = next(i for i in range(out, len(rows)) if rows[i]['步兵在家'] == 4)
    assert any(r['到远厂'] >= 1 for r in rows[out:back])
    assert back - out <= 16 and rows[back]['步兵数'] == 4                   # bench 16 s, nobody lost
    again = next(i for i in range(back, len(rows)) if rows[i]['步兵在家'] == 0)
    assert any(r['到远厂'] >= 1 for r in rows[again:])


@pytest.mark.xfail(strict=True, reason='bench airet: 16 s home before going again and 4 alive to s85; the simulator '
                                       '9 s (members within READY_RADIUS of the base are ready at once, INFERRED) '
                                       'and loses one on the second trip')
def test_outgunned_team_home_stay_and_losses_match_the_bench(lib):
    _, rows = _switch_run('airet', lib, until=85.0)
    out = _left(rows)
    back = next(i for i in range(out, len(rows)) if rows[i]['步兵在家'] == 4)
    again = next(i for i in range(back, len(rows)) if rows[i]['步兵在家'] < 4)
    assert 14 <= again - back <= 18 and all(r['步兵数'] == 4 for r in rows)


def test_no_retreat_at_power_advantage_zero(lib):
    # bench airet0: 到远厂 4 s17-s18, 步兵数 3 @ s19 ... 0 from s25; nobody home again
    _, rows = _switch_run('airet0', lib, until=85.0)
    out = _left(rows)
    assert all(r['步兵在家'] == 0 for r in rows[out:]) and rows[-1]['步兵数'] == 0


def test_engage_passive_on_hits_the_side_plant_first(lib):
    # bench aipas1: 旁厂血量 94 @ s11 (1 s after the wake), 3 @ s25; nobody at the far plant to s85
    _, rows = _switch_run('aipas1', lib, until=60.0)
    hit = next(i for i, r in enumerate(rows) if r['旁厂血量'] < 100)
    assert all(r['到远厂'] == 0 for r in rows[:hit + 10])


def test_engage_passive_off_goes_straight_to_the_far_plant(lib):
    # bench aipas0: 到远厂 2 @ s15, 4 s17-s34; the side plant at 100 until s35, then RAMPAGE hurts it (97 @ s36)
    _, rows = _switch_run('aipas0', lib, until=60.0)
    far = next(i for i, r in enumerate(rows) if r['到远厂'] >= 1)
    hit = next(i for i, r in enumerate(rows) if r['旁厂血量'] < 100)
    assert far < hit


@pytest.mark.parametrize('build,first', [('aiopath1', 'AlliedBarracks'), ('aiopathr', 'AlliedBarracks'),
                                         ('aiopathi', 'AlliedPowerPlant')])
def test_the_opening_path_test_picks_what_the_bench_picked(lib, build, first):
    """checks/engine_aiopath.py p (bench 2026-11-09): AlliedPowerPlant as ObjectTypeToUseForTest picks the
    PathExists="true" line (Standard, barracks first) whichever is listed first; aiopathi (one Island line, true):
    the probe's personality takes (a power plant first)."""
    b, trace = _from_wake(simai.run(build, until=40, lib=lib, blocks=()))
    own = [t for f, what, t in trace if what == 'own']
    assert own and own[0] == first, own


# bench 2026-11-09 checks/engine_aipoweradv.py a: (build, the AI's Guardians, home at s30)
@pytest.mark.parametrize('build,n,home', [('aipadv2', 8, 0), ('aipadv1', 4, 4), ('aipadvh', 4, 0),
                                          ('aipadvc', 4, 0)])
def test_power_advantage_gates_the_state_as_on_the_bench(lib, build, n, home):
    """PowerAdvantageHeuristic Value 1 Above true: 8 against 4 out s13-16; 4 against 8 home to s65; the player
    with only an Ore Collector (nothing CAN_ATTACK: FLT_MAX) out s15-16; aipadvc (4 against 8, ConstantHeuristic,
    the control) out s14-15."""
    _, rows = _switch_run(build, lib, until=31.0)
    assert rows[5]['坦克在家'] == n and rows[29]['坦克在家'] == home, [r['坦克在家'] for r in rows]


# bench 2026-11-09 checks/engine_aiteamfilter.py a: (build, tanks home, infantry home) from s15 on
@pytest.mark.parametrize('build,tanks,inf', [('aitfany', 0, 4), ('aitfnone', 0, 4), ('aitfall', 4, 0),
                                             ('aitfki', 4, 0), ('aitfke', 0, 4), ('aitfmax', 5, 0)])
def test_team_filters_take_whom_the_bench_sent(lib, build, tanks, inf):
    """ObjectFilter ANY / NONE + IncludeThing Guardian: only the Guardians; ALL + ExcludeThing Guardian: only the
    Peacekeepers; IncludeKindOf INFANTRY / ExcludeKindOf INFANTRY; MaxUnits 3 of 8 Guardians: 5 stay."""
    _, rows = _switch_run(build, lib, until=41.0)
    assert (rows[39]['坦克在家'], rows[39]['步兵在家']) == (tanks, inf), [(r['坦克在家'], r['步兵在家']) for r in rows]


# bench 2026-11-09 checks/engine_aiteamfilter.py a (B round 81): (build, Guardians home, the other type home) at s40
@pytest.mark.parametrize('build,tanks,other', [('aitfland', 0, 4), ('aitfamph', 4, 0), ('aitfwat', 4, 4),
                                               ('aitfosi', 4, 0), ('aitfosv', 0, 4), ('aitfosc', 0, 0)])
def test_locomotor_types_and_object_sets_take_whom_the_bench_sent(lib, build, tanks, other):
    """AllowedLocomotorTypes LAND: only the Guardians; AMPHIBIOUS: only the Riptide ACVs; WATER: nobody (an
    amphibious unit is not WATER). RegisteredObjectSet INFANTRY: only the Peacekeepers; VEHICLES: only the
    Guardians; SKIRMISH_AI_NORMAL_COMBAT_UNITS: both."""
    _, rows = _switch_run(build, lib, until=41.0)
    got = [tuple(r.values()) for r in rows]
    assert got[39] == (tanks, other), got


# bench 2026-11-09 checks/engine_aidiff.py a: (build, tanks home, infantry home) from s17 on; the bench walks normal
@pytest.mark.parametrize('build,tanks,inf', [('aidiff', 0, 4), ('aidiffx', 4, 0)])
def test_only_the_states_listed_for_the_difficulty_run(lib, build, tanks, inf):
    """Two always-on states, one listed Difficulty MEDIUM, one EASY HARD BRUTAL: at campaign normal only the MEDIUM
    one's team leaves (aidiff: the Guardians; aidiffx, lists swapped: the Peacekeepers)."""
    _, rows = _switch_run(build, lib, until=41.0)
    assert (rows[39]['坦克在家'], rows[39]['步兵在家']) == (tanks, inf), [(r['坦克在家'], r['步兵在家']) for r in rows]


# bench 2026-11-09 checks/engine_aiotime.py a: power plant / Time 30s / plant / Time 20s / plant, woken at s10:
# the plants stand from s19, s49, s59 (Time = since the wake; the 20s point has passed, the third goes at once)
AIOTIME_BENCH = (19, 49, 59)


# bench 2026-11-09 checks/engine_aitargetpick.py a, at s40: (build, 到电厂, 到兵营, 到坦克, 在家)
@pytest.mark.parametrize('build,plant,barracks,tank,home', [
    ('aitpnear', 4, 0, 0, 0), ('aitpvk', 0, 4, 0, 0), ('aitpfk', 0, 4, 0, 0), ('aitpunit', 0, 0, 4, 0),
    ('aitpphi', 0, 4, 0, 0), ('aitpplo', 4, 0, 0, 0), ('aitpmt1', 4, 0, 0, 4), ('aitpmt2', 4, 4, 0, 0)])
def test_target_pick_as_on_the_bench(lib, build, plant, barracks, tank, home):
    """VitalKindOf / ForbiddenKindOf / EnemyUnit pick the target, the higher TargetHeuristic Priority is tried first,
    MaxTargets 2 sends a second team at the next unique target. The tank's count may fall as it shoots back."""
    _, rows = _switch_run(build, lib, until=41.0)
    r = rows[39]
    got = (r['到电厂'], r['到兵营'], max(x['到坦克'] for x in rows), r['在家'])
    assert got == (plant, barracks, tank, home), got


def test_team_priority_higher_plant_team_as_on_the_bench(lib):
    """aitpprp (B round 82): the plant's team HIGH over the barracks' STANDARD -> all 4 at the plant."""
    _, rows = _switch_run('aitpprp', lib, until=41.0)
    assert (rows[39]['到电厂'], rows[39]['到兵营'], rows[39]['在家']) == (4, 0, 0)


_TIE = pytest.mark.xfail(strict=True, reason='simai sends the plant\'s team (target first, s13) all 4; the bench gives '
                                             'them to the barracks\' state on a tie -- handoff-b 84')


# aitpprh / aitpprl pass since AI tactic teams are recruitable (+0x24 = 1, B handoff 102): the higher team takes them
@pytest.mark.parametrize('build', [pytest.param('aitpprs', marks=_TIE), 'aitpprh', 'aitpprl'])
def test_team_priority_as_on_the_bench(lib, build):
    _, rows = _switch_run(build, lib, until=41.0)
    assert (rows[39]['到电厂'], rows[39]['到兵营'], rows[39]['在家']) == (0, 4, 0)


# bench 2026-11-09 checks/engine_aitargetpick.py a, the plant killed at s35, at s75: (到电厂, 到兵营, 到坦克, 在家)
def _end_at_75(build, lib):
    _, rows = _switch_run(build, lib, until=76.0)
    r = rows[74]
    return r['到电厂'], r['到兵营'], r['到坦克'], r['在家']


@pytest.mark.parametrize('build', ['aiendd', 'aiendh'])
def test_end_behavior_disband_goes_to_the_next_target_as_on_the_bench(lib, build):
    """DISBAND / RETURN_HOME_AND_DISBAND: the plant gone, the 4 tanks stand at the barracks (handoff-b 87)."""
    assert _end_at_75(build, lib) == (0, 4, 0, 0)


def test_end_behavior_rampage_as_on_the_bench(lib):
    """RAMPAGE: the nearest enemy STRUCTURE (0x8e2980's KindOf filter) -- the barracks, never the nearer tank."""
    assert _end_at_75('aiendr', lib) == (0, 4, 0, 0)


def test_end_behavior_pick_new_target_as_on_the_bench(lib):
    """PICK_NEW_TARGET: 0x8f7aa0 just returns -- the team stands where the plant was (bench to s85)."""
    assert _end_at_75('aiendp', lib) == (4, 0, 0, 0)


@pytest.mark.parametrize('build,n', [('aipadm1', 8), ('aipadm0', 4), ('aipadm5', 8)])
def test_team_min_power_advantage_holds_nobody_back(lib, build, n):
    """bench (B round 82): MinPowerAdvantage 1.0 / 5.0 on the team, 8 v 4 and 4 v 8 -- all leave home by s16."""
    _, rows = _switch_run(build, lib, until=31.0)
    assert rows[5]['坦克在家'] == n and rows[19]['坦克在家'] == 0, [r['坦克在家'] for r in rows]


# bench 2026-11-09 checks/engine_aipoweradv.py a (B round 83): (build, last second all 4 home or None, first second
# all gone or None = home to the end)
@pytest.mark.parametrize('build,home,gone', [('aihtim', 32, 34), ('aihtima', 37, 39), ('aihtimx', 22, 23),
                                             ('aihint', 27, 28), ('aihen1', 13, 15), ('aihen0', None, None),
                                             ('aihenn', 13, 16), ('aihoe0', None, None), ('aihoea', None, None),
                                             ('aihoes', 14, 16)])
def test_condition_heuristics_gate_the_state_as_on_the_bench(lib, build, home, gone):
    """Timer (MAP_START / AI_START, EndTime a length), Interval (off first), EnemyNearby, ObjectOfTypeExists ALLIES
    with one's own: within 3 s of the bench (the simulator's teams leave a second or two apart from it)."""
    _, rows = _switch_run(build, lib, until=61.0)
    seq = [r['坦克在家'] for r in rows]
    if home is None:
        assert all(v == 4 for v in seq), seq
        return
    last = next(k for k, v in enumerate(seq) if v < 4)          # rows[k] is second k + 1: the last all-home second
    assert abs(last - home) <= 3 and seq[gone + 2] == 0, (last, seq)


@pytest.mark.parametrize('build,out', [('aihoe1', True), ('aihoef', False)])
def test_object_of_type_exists_counts_the_relationship_as_on_the_bench(lib, build, out):
    _, rows = _switch_run(build, lib, until=41.0)
    assert (rows[39]['坦克在家'] == 0) == out


def _aiotime_firsts(lib):
    w = simai.run('aiotime', 'a', 70.0, lib=lib, blocks=())
    seen = [v[0] for _, v in w.sim.series]
    return [next(k + 1 for k, v in enumerate(seen) if v >= n) for n in (1, 2, 3)]


def test_opening_time_counts_from_the_wake_as_on_the_bench(lib):
    """The gaps: 30 s to the second plant, 10 s (one build) to the third -- not 20 s (since the previous Time)."""
    a, b, c = _aiotime_firsts(lib)
    assert (b - a, c - b) == (AIOTIME_BENCH[1] - AIOTIME_BENCH[0], AIOTIME_BENCH[2] - AIOTIME_BENCH[1]), (a, b, c)


@pytest.mark.xfail(strict=True, reason='simai 22 / 52 / 62: the first plant 3 s late (an opening that starts with a '
                                       'power plant, no barracks: aiopen is on time) -- not found, handoff-b 81')
def test_opening_time_plants_stand_when_on_the_bench(lib):
    assert all(abs(f - b) <= 1 for f, b in zip(_aiotime_firsts(lib), AIOTIME_BENCH))


def test_path_to_target_is_asked_on_the_simulators_grid(lib):
    """PathToTargetHeuristic (work/re l4_states.md 3): the opening and the states ask the brain; the skirmish map is
    one piece of land, so infantry has a way and a ship finds no water spot (= no way). At 300 s the player's base
    is gone: no enemy with a base object, so it cannot judge (None, counted as a way)."""
    w = simai.run('aiskirm', until=30, lib=lib)
    (b,) = w.brains.values()
    assert any(k[0] == 'Land' and v[1] is True for k, v in b.paths.items())   # the opening / states asked
    b.paths.clear()
    assert b.path_to_target('Land', 'AlliedAntiInfantryInfantry', 'NORMAL') is True
    assert b.path_to_target('Water', 'AlliedAntiNavalScout', 'NORMAL') is False
    assert b.path_to_target('Land', 'AlliedPowerPlant', 'NORMAL') is True       # no locomotor: a way (aiopath1)


def test_path_to_target_cannot_judge_without_an_enemy_base(skirmish):
    (b,) = skirmish.brains.values()
    s = b.sim
    if any(x.owner != b.player and 'STRUCTURE' in x.kinds and s.enemy(b.player, x.owner) for x in s.living()):
        pytest.skip('an enemy structure still stands at 300 s')
    b.paths.clear()
    assert b.path_to_target('Land', 'AlliedAntiInfantryInfantry', 'NORMAL') is None


def test_strategic_facts_the_brain_gives(lib):
    """The cheap strategic-state facts (work/re l4_states.md 10, states.strategic): harvesters, money, the first
    enemy's money, no beacons, and PowerAdvantage asked lazily with tactics' rule; the rest stay unmodelled."""
    w = simai.run('aiskirm', until=30, lib=lib)
    (b,) = w.brains.values()
    f = b.facts()
    st = b.host.mod['states']
    assert f['harvesters'] == sum('HARVESTER' in x.kinds for x in b.sim.living() if x.owner == b.player)
    assert f['money'](0) == b.sim.money.get(b.player, 0)
    assert f['beacons'] == set()
    assert st.value('BeaconExistsHeuristic', {'Type': 'Assault', 'Exists': 'false'}, f) == 1.0
    assert st.value('MoneyHeuristic', {'Money': '0', 'Above': 'true'}, f) == float(f['money'](0) > 0)
    theirs, ours = b.power_advantage('CAN_ATTACK', 'CAN_ATTACK', True, True)
    assert theirs >= 0.0 and ours >= 0.0
    want = 1.0 if theirs > 9999 else 0.0 if ours > 9999 else float(ours <= 0 or theirs / ours > -1)
    assert st.value('PowerAdvantageHeuristic', {'Value': '-1'}, f) == want                # 0x8c4910's caps
    assert st.value('RedAlertHeuristic', {}, f) is None
    # 'energy': ours by SAME_PLAYER, else the first enemy's; 'attacked': a structure / harvester of ours hurt lately
    sup, dem = b.sim.power(b.player)
    assert f['energy']('SAME_PLAYER') == sup - dem
    assert st.value('EnergyHeuristic', {'Relationship': 'SAME_PLAYER', 'ExcessEnergy': str(sup - dem - 1),
                                        'Above': 'true'}, f) == 1.0
    assert st.value('StructureOrHarvesterUnderAttackHeuristic', {}, f) == float(f['attacked'](4))
    yard = next(t for t in b.view.things if t.owner == b.player and 'STRUCTURE' in t.kindof)
    b.hurt_at[yard.id] = b.frame - 3 * 15
    assert f['attacked'](4) and not f['attacked'](2)                                     # hurt 3 s ago


# ---- EnterBaseDefenses / EnterGarrisons (checks/engine_aibasedef.py, engine_aigarrison.py, bench 11-09; public
# docs/engine/aiteamstate.md sections 3 / 4). The simulator has no garrisons: simai.Garrisons carries the model's
# 'enter' orders out; sim.py does not count ENCLOSED, so these read Garrisons.log, not the check's counters.
def _garrison_run(build, lib, until=60.0):
    w = simai.run(build, 'a', until, lib=lib)
    return w, [e for e in w.garrison.log if not e[3]]          # the AI's own entries (not the script's sitter)


def _ai_hooks(build, lib):
    """The brain just after the wake: an AI Peacekeeper's defenses / houses lists (building names, the list's order)."""
    w = simai.run(build, 'a', 12.0, lib=lib)
    (b,) = w.brains.values()
    u = simai.Unit(next(x for x in w.sim.living() if x.owner == b.player and 'INFANTRY' in x.kinds
                        and not w.garrison.busy(x)))
    names = lambda got: [b.body_of(i).name for i, _ in got                    # noqa: E731
                         if not b.body_of(i).scenery]      # the map's own houses are on the list too (real ones)
    return w, names(b.garrisons(u, True)), names(b.garrisons(u, False))


def test_the_ais_turrets_are_its_base_defenses_in_their_order_not_houses(lib):
    _, defenses, houses = _ai_hooks('aibd1', lib)
    assert defenses == [f'UNIT - CNV AI Turret {k}' for k in (1, 2, 3, 4)] and houses == []


def test_a_full_turret_stays_first_on_the_list(lib):
    # bench aibdpre: turret 1 full from s0, nobody went into turret 2 / 3 -- the pass does not skip a full one
    w, defenses, _ = _ai_hooks('aibdpre', lib)
    assert w.garrison.inside['UNIT - CNV AI Turret 1'][0].name == 'UNIT - CNV AI Sitter'
    assert defenses[0] == 'UNIT - CNV AI Turret 1'


def test_a_neutral_house_is_a_house_not_a_defense(lib):
    _, defenses, houses = _ai_hooks('aigar1', lib)
    assert defenses == [] and houses == ['UNIT - CNV AI House']


@pytest.mark.parametrize('build', ['aibd0', 'aibdidle', 'aigar0', 'aigarfar', 'aibdpre'])
def test_nobody_goes_in_where_the_bench_had_nobody(lib, build):
    # bench: aibd0 / aibdidle / aigar0 / aigarfar nobody in; aibdpre nobody besides the sitter
    _, got = _garrison_run(build, lib)
    assert got == []


@pytest.mark.xfail(strict=True, reason="bench aibd1: one Peacekeeper in turret 1 from s21; the simulator's fight kills "
                                       "all four turrets by s25, before the team (~8 s late) gets there")
def test_one_goes_into_the_first_turret(lib):
    _, got = _garrison_run('aibd1', lib)
    assert [e[2] for e in got] == ['UNIT - CNV AI Turret 1']


# bench aigar1: the house the AI's at s18, three alive inside to s75. Passes since the topple props (188 lamp posts on
# this map) stopped being walls: the men no longer walk round them under fire (codex/topple, 2026-11-09).
def test_the_team_goes_into_the_house(lib):
    _, got = _garrison_run('aigar1', lib, until=75.0)
    assert len(got) == 3
