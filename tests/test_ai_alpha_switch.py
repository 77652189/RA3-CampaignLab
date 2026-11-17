"""AlphaStrikeTargetHealthPct: the switch's on / off effect, bench and model (D round 146).

Bench aialobshi / aialobslo (missions/aialphaclose_bench.py, CNVTeams host on the AI yard; E99 runs, both PASS 5/5)
differ only in the threshold (0.9 / 0.01). Fixtures tests/fixtures/d_alpha/*_states.txt keep the SimpleAttack team's
state samples. Bench: high 8 -> 6 f230 -> 0 (alpha strike) f290 -> 8 f575 (team gone); low 8 -> 6 f230 -> 1 (retreat)
f470 and never 0. The model: high 6 f240 -> 0 f270; low 6 f240 -> 1 f480, never 0. The exact frames and the low side's
later 8 / 6 / 1 loop (bench f650 / f950 / f980) stay INFERRED (the alpha-close outcome xfails in test_simai_bench_c).

AlphaStrikeTargetTimeToKill (B round 219): aialobttk is aialobshi with the kill-time gate 1000 -> 0.01, nothing else.
Predicted from the model before the run (health share x kill time never under 0.01: no alpha strike), bench
CampAlObsHiKA_mcp_1116_070902 PASS: the low side's sequence frame for frame (8 -> 6 f230 -> 1 f470, never 0).
"""
import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location('simai', ROOT / 'experimental/cnv/simai.py')
simai = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(simai)
import teamlog

OBSERVED = ROOT / 'tests/fixtures/d_alpha'
ALPHA, ENEMY, RETREAT = 0, 6, 1


def _sequence(states):
    out = []
    for s in states:
        if not out or out[-1] != s:
            out.append(s)
    return out


@pytest.mark.parametrize('build', ['aialobshi', 'aialobslo', 'aialobttk'])
def test_bench_alpha_state_only_with_the_high_threshold(build):
    rows = teamlog.states(str(OBSERVED / (build + '_states.txt')))['T']
    seq = _sequence([r['mstate'] for r in rows])
    first = {s: min(r['frame'] for r in rows if r['mstate'] == s) for s in set(seq)}
    if build == 'aialobshi':
        assert seq[:3] == [8, ENEMY, ALPHA] and RETREAT not in seq, seq
        assert first[ENEMY] == 230 and first[ALPHA] == 290
    else:
        assert seq[:3] == [8, ENEMY, RETREAT] and ALPHA not in seq, seq
        assert first[ENEMY] == 230 and first[RETREAT] == 470


@pytest.mark.skipif(not simai.available(), reason='no ra3model.ai (labpaths.ENGINE_MODEL)')
@pytest.mark.parametrize('build', ['aialobshi', 'aialobslo', 'aialobttk'])
def test_model_alpha_state_only_with_the_high_threshold(build):
    w = simai.run(build, 'a', until=40, lib=simai.model()['xmldata'].Library(), record=True)
    brain, = w.brains.values()
    seq = _sequence([r['state'] for r in brain.rec['frames']])
    if build == 'aialobshi':
        assert seq[:3] == [8, ENEMY, ALPHA] and RETREAT not in seq, seq
    else:
        assert seq[:3] == [8, ENEMY, RETREAT] and ALPHA not in seq, seq
