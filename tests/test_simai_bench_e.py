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


@pytest.mark.parametrize('build,active', [
    ('aicapctrl', False), ('aicapmed', True), ('aicaphard', False),
])
@pytest.mark.xfail(strict=True, reason='E80 engine_aicap a/b: engine makes three Peacekeepers and three '
    'Javelins on [s70,s100); model makes one and two. MEDIUM cap two also fails on the engine '
    'after the opening (five to nine Peacekeepers). B owns the model; '
    'see work/re/handoff-e.md and work/re/e_aicap_e80.md.')
def test_specific_unit_cap(build, active):
    """engine_aicap b: replay observed counts, including the violated MEDIUM cap.

    The check keeps its original cap-two prediction and FAIL verdict. These
    assertions describe engine readings; no model threshold is relaxed.
    """
    w = simai.run(build, 'b', 100, lib=simai.model()['xmldata'].Library())
    labels = [label for _, label in w.sim.test.counters]
    samples = [(t, dict(zip(labels, values))) for t, values in w.sim.series if 70 <= t < 100]
    assert [t for t, _ in samples] == list(range(70, 100))
    assert all(row['维和总数'] == 3 and row['标枪总数'] == 3 for _, row in samples), samples
    w.advance(100 * simai.FPS)
    late = [(t, dict(zip(labels, values))) for t, values in w.sim.series if 150 <= t < 200]
    assert [t for t, _ in late] == list(range(150, 200))
    assert max(row['维和总数'] for _, row in late) >= 4, late
    assert max(row['标枪总数'] for _, row in late) >= 4, late
    if active:
        assert all(row['维和总数'] >= 5 for _, row in late), late
        assert max(row['维和总数'] for _, row in late) == 9, late


@pytest.mark.parametrize('build,land,water', [
    ('ailocland', 4, 0),
    ('ailocboth', 4, 0),
    pytest.param('ailocwater', 0, 4, marks=pytest.mark.xfail(
        strict=True, reason='E81 engine_ailocation a: Water has four Twinblades at the water plant '
        'and zero at the land plant at s40; default model has zero at both. '
        'B owns the model; see work/re/handoff-e.md and work/re/e_location_e81.md.')),
])
def test_target_location(build, land, water):
    """Replay engine_ailocation a's displayed arrival counters at s40."""
    w = simai.run(build, 'a', 41, lib=simai.model()['xmldata'].Library())
    labels = [label for _, label in w.sim.test.counters]
    samples = [dict(zip(labels, values)) for t, values in w.sim.series if t == 40]
    assert len(samples) == 1
    assert samples[0]['到陆厂'] == land, samples
    assert samples[0]['到水厂'] == water, samples
