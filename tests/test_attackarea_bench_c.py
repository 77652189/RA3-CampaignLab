"""Named native counters; a quiet result does not establish area-attack semantics.

Both native area windows have no damage (b reveals the map); subsequent named
attacks hit. Full replay is a strict gap, never an inventory promotion.
Evidence and target-kind/autoacquire hypotheses: work/re/c_attackarea_report.md.
Raw post-death getter accumulation/OCR tail remains in the fixture but is not
used as a position measurement; replay below stops before that tail.
"""
import importlib.util
import json
from functools import lru_cache
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location('attackarea_simbench', ROOT / 'experimental/cnv/simbench.py')
_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_module)


@lru_cache(None)
def replay(variant):
    import build
    import sim
    rows = json.loads((ROOT / 'tests/fixtures/c_attackarea.json').read_text(encoding='utf-8'))[variant]
    expected = {row[-1]: row for row in rows if row[-1] <= 450}
    m, t, _ = build.resolve('engine_attackarea', variant)
    e = sim.Sim(m, t, script='不打')
    got = {}
    tick = e.produce_due

    def observe(frame):
        tick(frame)
        if frame in expected:
            got[frame] = [e.counters.get(k, 0) for k, _ in t.counters]

    e.produce_due = observe
    e.advance(max(expected)+8)
    return expected, got, e.unknown.get('NAMED_ATTACK_AREA', 0)


@pytest.mark.parametrize('variant', ['a', 'b'])
def test_attackarea_native_quiet_window_and_stationary_control(variant):
    expected, got, _ = replay(variant)
    frames = [f for f in expected if 75 <= f < 270]
    assert len(frames) >= 20
    assert {tuple(expected[f][:3]) for f in frames} == {(100, 100, 3100)}
    assert {f: got[f] for f in frames} == {f: expected[f] for f in frames}


@pytest.mark.parametrize('variant', ['a', 'b'])
@pytest.mark.xfail(strict=True, reason='NAMED_ATTACK_AREA unsupported; two native area windows have no hits despite named-attack positives. Selection/autoacquire/target-kind unresolved; full missile timing also differs. See work/re/c_attackarea_report.md')
def test_attackarea_full_native_readings_and_action_recognition(variant):
    expected, got, unknown = replay(variant)
    assert got == expected
    assert unknown == 0
