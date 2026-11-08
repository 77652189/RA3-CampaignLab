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
    trips, 151.5 s)."""
    again = [s for s, t in _barracks_out(skirmish) if s >= 120]
    assert again and again[0] <= 130, again


@pytest.mark.xfail(strict=True, reason='work/re/simai.md round 39: the AlliedScout team ends the frame after it '
                   'goes (a higher-priority team recruits its dog away: teams.recruit takes from gone teams), so the '
                   "dogs are home and fill BalancedAttackGround's MaxTypesOfUnits 2 with Javelins; tried: no "
                   'recruiting from gone teams (dogs still home, team 169.5 s) -- ADR 0019 two tries')
def test_skirmish_ai_first_attack_team_takes_no_dogs(skirmish):
    """Bench b: the dogs leave ~44 s after the wake and stay away 120-170 s; the first team (132.8 s) is 2 Riptides +
    3 Peacekeepers out at once, no dog."""
    (b,) = skirmish.brains.values()
    gone = [e for e in b.ai.teams.log if e[1] == 'go' and e[2][0].startswith('BalancedAttack')]
    assert gone and 'AlliedScoutInfantry' not in gone[0][3], gone[:1]


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
