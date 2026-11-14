"""BuildEntry.MinTime on a TECH entry, by name: the engine model's first_tech_order on each aiskmt build's own
personality (missions/aiskirm_bench.py mintime_xml: 1AlliedBalanced + a ConstantHeuristic state with one
AlliedTechStructure TECH entry) against the bench's 科技帧 (checks/engine_aiskirm.py mt: frames from the wake while
s1 owns no tech building). The simulator's yard builds the opening only, so this asks the model's rule, not a
replay: the order second (+ BuildTime) x 15 = the frame it is owned."""
import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location('simai', ROOT / 'experimental' / 'cnv' / 'simai.py')
simai = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(simai)

pytestmark = pytest.mark.skipif(not simai.available() or not hasattr(simai.model()['player'], 'first_tech_order'),
                                reason='no ra3model.ai first_tech_order (labpaths.ENGINE_MODEL)')

TECH = 'AlliedTechStructure'
EVAL = 15            # one evaluation (the scores' cache is redone once a second)

# bench 2026-11-12 / 11-13 checks/engine_aiskirm.py mt (B handoff 159-164), 科技帧 where it stopped; None = still no
# tech building when the watch ended (that many frames after the wake)
BENCH = {'aiskmt0': 2256, 'aiskmt03': 2256, 'aiskmt20': 2256, 'aiskmt14': 5857, 'aiskmt16': 5857,
         'aiskmt15': 5857, 'aiskmt40': 5857, 'aiskmt99': 5857}
NONE_BY = {'aiskmt2': 4721, 'aiskmt': 365 * 15}     # aiskmt2 watched to s367; aiskmt's second run to s377


def _predict(name, advantage=None):
    import build
    mod = simai.model()
    m, _, _ = build.resolve(name, 'mt')
    data = mod['data'].AIData()
    pid = None
    for a in m.assets:
        if len(a) >= 3 and str(a[2]).startswith('AIPersonalityDefinition:'):
            data.add_text(a[1])
            pid = a[2].split(':', 1)[1]
    assert pid, f'{name} writes no personality of its own'
    states = data.personality_build_states(pid, 'MEDIUM')
    side = 'PlayerTemplate:Allies'
    ends = [max(o.time for o in data.openings[c.target].orders) for c in data.personality(pid).choices
            if c.tag == 'OpeningMove' and 'MEDIUM' in c.difficulty and c.target in data.openings
            and data.openings[c.target].side == side]
    assert ends and len(set(ends)) == 1, ends        # 1AlliedBalanced: AlliedStandard / AlliedIsland both end at 120
    end = ends[0]

    def ctx(t):                  # INFERRED boundary: the opening counts as complete only after its last step
        return {'opening done': t > end, 'enemy nearby': False, 'power advantage': advantage,
                'min power advantage': m.facts.get('power advantage', 1.25)}   # 1.25: BasePersonality.xml
    t = mod['player'].first_tech_order(states, TECH, ctx, yard_free=end, until=1200)
    build_time = float(simai.model()['xmldata'].Library().template(TECH).attrs['BuildTime'])
    return None if t is None else (t + build_time) * simai.FPS


@pytest.mark.parametrize('name', sorted(BENCH))
def test_the_tech_building_is_owned_when_the_bench_owned_it(name):
    """MinTime <= 20 orders when the opening frees the yard (t 120 + 30 s -> f2250); 140 .. 1000 are covered by the
    retail AlliedTechBuildState's own entry (MinTime 360) once the opening completes: the cache is per template and
    that state comes first (D round 100) -> t 360 + 30 -> f5850."""
    got = _predict(name)
    assert got is not None and abs(got - BENCH[name]) <= EVAL, (name, got, BENCH[name])


@pytest.mark.parametrize('name', sorted(NONE_BY))
def test_no_tech_building_where_the_bench_saw_none(name):
    got = _predict(name)
    assert got is None or got > NONE_BY[name], (name, got)


# B round 181, BuildTechMinPowerAdvantage: aiskmtp = aiskmt40 with 1000 written (bench 11-13 aiskmtp__mt.json, PASS):
# no tech building to 科技帧 12159 (s810); aiskmt40 (1.25 inherited) owned one at f5857. The AI's power over the
# player's is not read (the player has 3 buildings, no army): any value in [1.25, 1000) fits both runs.
@pytest.mark.parametrize('advantage', [1.25, 10.0, 999.0])
def test_a_power_advantage_of_1000_keeps_the_tech_building_away(advantage):
    held = _predict('aiskmt40', advantage)
    assert held is not None and abs(held - BENCH['aiskmt40']) <= EVAL, held
    got = _predict('aiskmtp', advantage)
    assert got is None or got > 12159, got
