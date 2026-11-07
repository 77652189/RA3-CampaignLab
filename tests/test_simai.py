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
    assert not [t for f, what, t in trace if what == 'out'], trace


@pytest.fixture(scope='module')
def skirmish(lib):
    return simai.run('aiskirm', until=300, lib=lib)


def test_skirmish_ai_builds_makes_units_and_attacks(skirmish):
    w = skirmish
    (b,) = w.brains.values()
    made = collections.Counter(t for f, what, t in b.trace if what == 'out')
    assert len(made) >= 3, made                         # a mixed army past the opening's three Riptides
    gone = [e for e in b.ai.teams.log if e[1] == 'go' and e[2][0].startswith('BalancedAttack')]
    assert gone and len(gone[0][3]) >= 8, gone          # BalancedAttackGround_MEDIUM: MinUnits 8
    lost = [x for x in w.sim.bodies.values() if x.owner == w.sim.human and not x.alive]
    assert lost, 'the attack destroyed nothing of the player'
    assert min(x.died_at for x in lost) > (gone[0][0] / simai.FPS), 'died before the team left'


def test_skirmish_ai_talks_about_itself(skirmish):
    th = skirmish.thoughts()
    (me,) = th.values()
    assert me['opening'] == 'AlliedStandard' and me['opening done']
    assert 'targets' in me and any(me['targets'].values())
