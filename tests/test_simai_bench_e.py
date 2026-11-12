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


@pytest.mark.xfail(strict=True, reason='E85 engine_aifriendly a: both types yield zero arrivals with both MCVs alive; '
                  'default model sends four to the selected MCV. StaticDefense/selection boundary unresolved; '
                  'see work/re/handoff-e.md and work/re/e_friendly_e85.md.')
@pytest.mark.parametrize('build,friendly,enemy', [('aifriend', 0, 0), ('aienemy', 0, 0)])
def test_friendly_unit_target(build, friendly, enemy):
    """E85 engine_aifriendly a: arrivals plus independent target survival."""
    w = simai.run(build, 'a', 41, lib=simai.model()['xmldata'].Library())
    labels = [label for _, label in w.sim.test.counters]
    samples = [dict(zip(labels, values)) for t, values in w.sim.series if t == 40]
    assert len(samples) == 1
    assert (samples[0]['友车存活'], samples[0]['敌车存活']) == (1, 1), samples
    assert (samples[0]['到友车'], samples[0]['到敌车']) == (friendly, enemy), samples


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
        'builds two power plants and one barracks on [s55,s60). The model now skips the other '
        'side\'s opening and counts the opening complete (B handoff 147, D 66), but builds no '
        'structures without an opening (the structure build states are not modelled, B handoff '
        '123/124), so 0/0.')),
])
def test_opening_side(build, power, barracks):
    """Replay engine_aiopenside a's measured counters on [s55,s60)."""
    w = simai.run(build, 'a', 60, lib=simai.model()['xmldata'].Library())
    labels = [label for _, label in w.sim.test.counters]
    samples = [(t, dict(zip(labels, values))) for t, values in w.sim.series if 55 <= t < 60]
    assert [t for t, _ in samples] == list(range(55, 60))
    assert all(row['电厂数'] == power and row['兵营数'] == barracks for _, row in samples), samples


def test_an_opening_of_another_side_is_not_run():
    """engine_aiopenside a, aiossoviet (bench E82): the only opening has Side Soviet, the player is Allied. The engine
    skips it and, no candidate left, counts the opening complete (D 66): on [s19,s29) the bench has no power plant
    (the opening's first order) but a barracks. The model draws no opening and has no power plant there either."""
    w = simai.run('aiossoviet', 'a', 29, lib=simai.model()['xmldata'].Library())
    labels = [label for _, label in w.sim.test.counters]
    rows = [dict(zip(labels, values)) for t, values in w.sim.series if 19 <= t < 29]
    assert len(rows) == 10 and all(row['电厂数'] == 0 for row in rows), rows
    brain, = w.brains.values()
    assert brain.ai.opening is None and brain.ai.opening_done()
    assert ('opening', None) in [(k, d) for _, k, d in brain.ai.log]


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
    states, every = _orders(w, 'state build', 160), _orders(w, 'produce', 160)
    assert not [o for o in states if o[1] == COUNTED[other]], states
    # the war factory draws too (B round 143: an IFV s135 in aiskvinf) -- t / z count only the barracks' infantry
    drawn = [(s, t) for s, t in every if t in BARRACKS_INFANTRY]
    assert all(row[other] == sum(1 for _, t in drawn if t == COUNTED[other]) for _, row in samples), (samples, drawn)
    if draws is not None:
        assert len(drawn) == draws, drawn


def test_against_conscripts_the_dogs_reach_their_cap_of_six():
    """engine_aiskirm t, aiskvinf (bench 2026-11-12, B round 140): 警犬 6 by s43, held at 6 to s145 -- the
    AlliedAntiInfantryOnlyBuildState (ENEMIES ANY INFANTRY) dogs, BEST_UNIT_EXPECTED, scored with the dog's whole
    bite (its Maul's own 1 and its warhead's 200: simunits ai_parts), up to the parent personality's cap of 6."""
    w = simai.run('aiskvinf', 't', 146, lib=simai.model()['xmldata'].Library())
    labels = [label for _, label in w.sim.test.counters]
    rows = [(t, dict(zip(labels, values))) for t, values in w.sim.series if 43 <= t < 146]
    assert [t for t, _ in rows] == list(range(43, 146))
    assert all(r['警犬总数'] == 6 for _, r in rows), rows
    assert sum(1 for _, t in _orders(w, 'state build', 146) if t == 'AlliedScoutInfantry') >= 5


@pytest.mark.xfail(strict=True, reason='B round 143 bench t: after s145 the engine builds dogs 7-9 (s146-s152) over the '
    'cap of six, and an engineer (s144); the model holds six (and draws a Javelin) -- as aiskcap past s150 '
    '(test_after_s150_the_capped_unit_is_built_again): what the cap counts. B owns the model; see '
    'work/re/handoff-b.md 146.')
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
    'Javelins on [s70,s100); model makes two and one, and 3 -> 5 Peacekeepers on [s150,s200) against the '
    'engine\'s 5 -> 9 -- the build rate, not the cap (the MEDIUM cap two no longer binds in the model either: '
    'test_a_child_cap_under_the_parents_line_does_not_bind). B owns the model; see work/re/handoff-b.md 144.')
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


def test_a_child_cap_under_the_parents_line_does_not_bind():
    """engine_aicap b (E80): a MEDIUM Peacekeeper Cap 2 in a personality inheriting 1AlliedBalanced does not hold --
    the bench's MEDIUM run made 5 Peacekeepers by s150 (9 by s199), on the control's track (5 -> 9). SpecificUnitCap
    takes the first matching line, the parent's Peacekeeper Cap 20 first (B round 141, work/re/d65_b_fields.md).
    The rule only: the two runs alike and past 2; how fast they build is test_specific_unit_cap's (xfail)."""
    lib = simai.model()['xmldata'].Library()
    runs = {}
    for build in ('aicapmed', 'aicapctrl'):
        w = simai.run(build, 'b', 151, lib=lib)
        labels = [label for _, label in w.sim.test.counters]
        runs[build] = [(t, dict(zip(labels, v))) for t, v in w.sim.series]
    assert runs['aicapmed'] == runs['aicapctrl']
    assert max(r['维和总数'] for _, r in runs['aicapmed']) > 2, runs['aicapmed'][-1]


@pytest.mark.parametrize('build,land,water', [
    ('ailocland', 4, 0),
    ('ailocboth', 4, 0),
    ('ailocwater', 0, 4),
])
def test_target_location(build, land, water):
    """Replay engine_ailocation a's displayed arrival counters at s40."""
    w = simai.run(build, 'a', 41, lib=simai.model()['xmldata'].Library())
    labels = [label for _, label in w.sim.test.counters]
    samples = [dict(zip(labels, values)) for t, values in w.sim.series if t == 40]
    assert len(samples) == 1
    assert samples[0]['到陆厂'] == land, samples
    assert samples[0]['到水厂'] == water, samples
