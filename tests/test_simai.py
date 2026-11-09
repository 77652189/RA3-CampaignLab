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


def test_skirmish_ai_builds_makes_units_and_attacks(skirmish):
    """Bench a/c: the first attack team (8) leaves ~133 s after the wake (on the miners' income, HOOKS 7)."""
    w = skirmish
    (b,) = w.brains.values()
    made = collections.Counter(t for f, what, t in b.trace if what == 'out')
    assert len(made) >= 3, made                         # a mixed army past the opening's three Riptides
    gone = [e for e in b.ai.teams.log if e[1] == 'go' and e[2][0].startswith('BalancedAttack')]
    assert gone and len(gone[0][3]) >= 8, gone          # BalancedAttackGround_MEDIUM: MinUnits 8
    lost = [x for x in w.sim.bodies.values() if x.owner == w.sim.human and not x.alive]
    assert lost, 'the attack destroyed nothing of the player'
    assert min(x.died_at for x in lost) > (gone[0][0] / simai.FPS), 'died before the team left'


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
    assert b.path_to_target('Land', 'AlliedPowerPlant', 'NORMAL') is False      # no locomotor: no way


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
