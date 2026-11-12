"""E-line AI replays: assertions come from named engine probes, never model output.

engine_aiskirm.z, BuildEntry.Heuristic=BEST_UNIT_EXPECTED: the retail
personality faces ten conscripts (aiskvinf) or ten Hammers (aiskvveh).
Only the infantry choice is covered; other heuristic values remain unverified.
Bench 2026-11-11 E78, both PASS on [s150,s160): aiskvinf Peacekeepers
5 then 6, Javelins 0; aiskvveh Javelins 7 then 8 then 9, Peacekeepers 0.
Evidence and limits: work/re/e_aiheur_e78.md.
"""
import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location('simai', ROOT / 'experimental/cnv/simai.py')
simai = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(simai)

pytestmark = pytest.mark.skipif(not simai.available(), reason='no ra3model.ai (labpaths.ENGINE_MODEL)')


@pytest.mark.parametrize('build,chosen,other', [
    ('aiskvinf', '维和总数', '标枪总数'),
    pytest.param('aiskvveh', '标枪总数', '维和总数', marks=pytest.mark.xfail(
        strict=True, reason='E78 engine_aiskirm z: bench has zero Peacekeepers against ten Hammers '
        'on [s150,s160), default simulator has one. B owns the model; '
        'see work/re/handoff-e.md and work/re/e_aiheur_e78.md.')),
])
def test_best_unit_expected_infantry_choice(build, chosen, other):
    """engine_aiskirm z: on [s150,s160) >=4 counter infantry, zero of the other type.

    Use the default model configuration and the probe's displayed counters.
    Do not infer the choice from internal scores or queue intentions.
    """
    w = simai.run(build, 'z', 160, lib=simai.model()['xmldata'].Library())
    labels = [label for _, label in w.sim.test.counters]
    samples = [(t, dict(zip(labels, values))) for t, values in w.sim.series if 150 <= t < 160]
    assert [t for t, _ in samples] == list(range(150, 160))
    assert all(row[chosen] >= 4 for _, row in samples), samples
    assert all(row[other] == 0 for _, row in samples), samples
