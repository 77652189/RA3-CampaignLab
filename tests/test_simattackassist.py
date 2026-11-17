"""Pending E144 assist-response probe; no successful engine reading yet.

See work/re/e144_attackassist.md. This expected failure is not bench evidence.
"""
import importlib.util
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('assist_simbench', ROOT / 'experimental/cnv/simbench.py')
bootstrap = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bootstrap)


@pytest.mark.xfail(strict=True, reason='E144: both engine starts crashed before readings; notification entry and simulator response remain gaps; see work/re/e144_attackassist.md')
def test_attackassist_named_secondary_response():
    import build
    import sim
    m, t, _ = build.resolve('engine_attackassist', 'a')
    engine = sim.Sim(m, t).run(20)
    verdicts = build.judge(t, engine.series)
    assert verdicts and all(ok for ok, _ in verdicts), verdicts
