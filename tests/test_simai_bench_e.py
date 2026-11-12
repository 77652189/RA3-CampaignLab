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


@pytest.mark.parametrize('build', ['aiopwater', 'aiopair'])
def test_path_locomotor_condition(build):
    """E84 engine_aiopathcond a: both conditions gave barracks=1, power=0.

    The water check retains its failed Island prediction. Equal observations
    cannot verify condition selection; see work/re/e_pathcond_e84.md.
    """
    w = simai.run(build, 'a', 25, lib=simai.model()['xmldata'].Library())
    labels = [label for _, label in w.sim.test.counters]
    samples = [(t, dict(zip(labels, values))) for t, values in w.sim.series if 22 <= t < 25]
    assert [t for t, _ in samples] == [22, 23, 24]
    assert all(row['兵营'] == 1 and row['电厂'] == 0 for _, row in samples), samples


@pytest.mark.parametrize('build,target,home', [('aibldtrue', 0, 4), ('aibldfalse', 4, 0)])
def test_is_building_idle(build, target, home):
    """Replay engine_aibuilding a's displayed s40 readings; idle queue only."""
    w = simai.run(build, 'a', 41, lib=simai.model()['xmldata'].Library())
    labels = [label for _, label in w.sim.test.counters]
    samples = [dict(zip(labels, values)) for t, values in w.sim.series if t == 40]
    assert len(samples) == 1
    assert samples[0]['到陆厂'] == target, samples
    assert samples[0]['在家'] == home, samples
    assert samples[0]['基地数'] == 1, samples


@pytest.mark.parametrize('build,power,barracks', [
    ('aiosallies', 3, 0),
    pytest.param('aiossoviet', 2, 1, marks=pytest.mark.xfail(
        strict=True, reason='E82 engine_aiopenside a: Allied player with Soviet opening Side '
        'builds two power plants and one barracks on [s55,s60); default model builds '
        'three plants and no barracks. B owns Side selection/fallback; '
        'see work/re/handoff-e.md and work/re/e_openside_e82.md.')),
])
def test_opening_side(build, power, barracks):
    """Replay engine_aiopenside a's measured counters on [s55,s60)."""
    w = simai.run(build, 'a', 60, lib=simai.model()['xmldata'].Library())
    labels = [label for _, label in w.sim.test.counters]
    samples = [(t, dict(zip(labels, values))) for t, values in w.sim.series if 55 <= t < 60]
    assert [t for t, _ in samples] == list(range(55, 60))
    assert all(row['电厂数'] == power and row['兵营数'] == barracks for _, row in samples), samples


# the barracks' four infantry, engine_aiskirm t's counters (the unit builder's draw is among them on the bench)
BARRACKS_INFANTRY = {'AlliedScoutInfantry', 'AlliedAntiInfantryInfantry', 'AlliedAntiVehicleInfantry', 'AlliedEngineer'}
COUNTED = {'维和总数': 'AlliedAntiInfantryInfantry', '标枪总数': 'AlliedAntiVehicleInfantry'}


def _orders(w, kind, until):
    """[(second, template)] the AI ordered by `kind` ('state build' = the build states, 'produce' = the unit
    builder's uniform draw) before mission second `until` -- the model's own log, to split a counter by source."""
    return [(f / simai.FPS, t) for b in w.brains.values() for f, k, t in b.ai.log
            if k == kind and f / simai.FPS < until]


@pytest.mark.parametrize('build,chosen,other,draws', [
    # bench t (aiskvinf, 2026-11-12): 9 dogs, 1 engineer -- the dogs are mostly a build state's (B handoff 143),
    # so the bench does not tell how many draws there were: no draw count here (test_against_conscripts_dogs pins it)
    ('aiskvinf', '维和总数', '标枪总数', None),
    # bench t (aiskvveh, 2026-11-12): dog s23 and engineer s144, the only non-Javelins = the two draws
    ('aiskvveh', '标枪总数', '维和总数', 2),
])
def test_best_unit_expected_infantry_choice(build, chosen, other, draws):
    """engine_aiskirm z: on [s150,s160) >=4 counter infantry, zero of the other type from the build states.

    Use the default model configuration and the probe's displayed counters. Bench E78: the other type's counter
    stays 0; the model's one (the s136 draw) is the unit builder's uniform pick, which the bench makes too (t: a dog
    s23, an engineer s144) -- so the other type is split by source: none from the build states, every one the
    counter shows drawn, each draw one of the barracks' infantry, and as many draws as the bench shows.
    """
    w = simai.run(build, 'z', 160, lib=simai.model()['xmldata'].Library())
    labels = [label for _, label in w.sim.test.counters]
    samples = [(t, dict(zip(labels, values))) for t, values in w.sim.series if 150 <= t < 160]
    assert [t for t, _ in samples] == list(range(150, 160))
    assert all(row[chosen] >= 4 for _, row in samples), samples
    states, drawn = _orders(w, 'state build', 160), _orders(w, 'produce', 160)
    assert not [o for o in states if o[1] == COUNTED[other]], states
    assert all(row[other] == sum(1 for _, t in drawn if t == COUNTED[other]) for _, row in samples), (samples, drawn)
    assert all(t in BARRACKS_INFANTRY for _, t in drawn), drawn
    if draws is not None:
        assert len(drawn) == draws, drawn


@pytest.mark.xfail(strict=True, reason='B round 140 bench t: against ten Conscripts the barracks makes 9 attack dogs '
    'by s152 (6 by s43); the model makes one (a draw) -- AlliedAntiInfantryOnlyBuildState (ObjectOfTypeExists '
    'ENEMIES INFANTRY, only the dog) weighs 0 in the model. B owns the model; see work/re/handoff-b.md 143.')
def test_against_conscripts_dogs():
    """engine_aiskirm t, aiskvinf (bench 2026-11-12, B round 140): 维和 5 / 标枪 0 / 警犬 9 / 工程师 1 on [s152,s157)."""
    w = simai.run('aiskvinf', 't', 157, lib=simai.model()['xmldata'].Library())
    labels = [label for _, label in w.sim.test.counters]
    samples = [dict(zip(labels, values)) for t, values in w.sim.series if 152 <= t < 157]
    assert len(samples) == 5
    assert all(r['维和总数'] == 5 and r['标枪总数'] == 0 and r['警犬总数'] == 9 and r['工程师总数'] == 1
               for r in samples), samples


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
