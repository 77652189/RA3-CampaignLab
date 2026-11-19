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


@pytest.mark.xfail(strict=True, raises=AssertionError, reason=(
    'D78 same-run commands diverge: retail orders the centre (3850, 3400) at f158 and stands west at f191. '
    'old cause gone: the model used to stand east, and the E96 candidate only reached the measured point at f214 '
    'and repeated orders; now the f166 comparison fails first because the model has already ordered west '
    '(1859.93, 3200.99) at f153, while retail still has the centre order. Readiness and member destinations '
    'still need to line up with the bench. See work/re/e97_aesthetics_same_frame.md.'))
def test_tactic_aesthetics_replays_same_frame_commands():
    """Replay D78 CampAIAesOnA_mcp_1112_111517 without shifting frame clocks.

    At f166 the last command is f158 to the centre; f196 and f256 retain
    f191's west stand point. All three samples have state 8 and one member.
    Command coordinates were logged to one decimal place. This checks the
    issued point, independently of formation offsets or square occupancy.
    """
    w = simai.run('aiaeson', 'a', until=18, lib=simai.model()['xmldata'].Library(), record=True)
    brain, = w.brains.values()
    observed = {166: (3850.0, 3400.0), 196: (1859.9, 3201.0), 256: (1859.9, 3201.0)}
    for frame, point in observed.items():
        rows = [row for row in brain.rec['frames'] if row['frame'] == frame]
        assert len(rows) == 1, (frame, rows)
        row, = rows
        assert row['state'] == 8, (frame, row)
        assert len(row['members']) == 1, (frame, row)
        member, = row['members']
        assert member['alive'], (frame, member)
        orders = [o for o in brain.rec['orders'] if o['frame'] <= frame and o['member'] == member['name']]
        assert orders, frame
        assert orders[-1]['point'] == pytest.approx(point, abs=0.05), (frame, orders[-1])


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
    # bench t (aiskvveh, 2026-11-12): dog s23 and engineer s144, the only non-Javelins = the two picks. The engineer
    # is AlliedCaptureTech_MEDIUM's CreateUnits order (A rounds 192 / 199), which the unit builder makes in place of
    # its own pick (model AIPlayer.order_wanted, INFERRED) and logs as 'produce' -- so it counts here as a draw
    # How many uniform picks land before s160 is the draw's luck, not a rule (B handoff: do not assert luck): seed 1
    # drew three after B round 164, two again since (an XPASS on the model's 12dfca8 and after B round 194) -- so
    # the bench's two or the one more seen, never a strict xfail that flips whenever the draws move
    ('aiskvveh', '标枪总数', '维和总数', (2, 3)),
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
        assert draws[0] <= len(drawn) <= draws[1], drawn


@pytest.mark.xfail(strict=True, raises=AssertionError, reason=(
    'old cause gone: after the team formed before the wake (B round 164), seed 1 drew a Peacekeeper where a dog '
    'was and stalled at five. Seeds 1-4 gave six dogs on 1 of 4 with that change, 2 of 4 without; the stream moved '
    'again, as the docstring records (work/logs/b166_seeds_*.log); A owns the draw. Now the bench holds six dogs '
    'at s43-s145, but the replay has four at s43 and five at s44, reaching six by s47. The cause of the current '
    'delay is unconfirmed.'))
def test_against_conscripts_the_dogs_reach_their_cap_of_six():
    """engine_aiskirm t, aiskvinf (bench 2026-11-12, B round 140): 警犬 6 by s43, held at 6 to s145 -- the
    AlliedAntiInfantryOnlyBuildState (ENEMIES ANY INFANTRY) dogs, BEST_UNIT_EXPECTED, scored with the dog's whole
    bite (its Maul's own 1 and its warhead's 200: simunits ai_parts), up to the parent personality's cap of 6.

    Rng-sensitive: red from lab edd0f6c0 to A round 200 (the uniform 'produce' draw at s136 landed on a dog, A round
    195); green again since A round 200's CreateUnits hold rule moved the stream."""
    w = simai.run('aiskvinf', 't', 146, lib=simai.model()['xmldata'].Library())
    labels = [label for _, label in w.sim.test.counters]
    rows = [(t, dict(zip(labels, values))) for t, values in w.sim.series if 43 <= t < 146]
    assert [t for t, _ in rows] == list(range(43, 146))
    assert all(r['警犬总数'] == 6 for _, r in rows), rows
    assert sum(1 for _, t in _orders(w, 'state build', 146) if t == 'AlliedScoutInfantry') >= 5


@pytest.mark.xfail(strict=True, reason='B round 217: both runs alike but 2 Peacekeepers by s150 (needs > 2). '
                   'Bisected (public + time-synced model): first red at model 05d99e0 (C, Husk targets get no '
                   'generic neutral fallback); with that reverted, first red at public 1afb989a (D169, ore nodes '
                   'block by their own circle / an unpacking miner starts no ore trip). Each alone turns it red: '
                   'the AI builds slower, not the cap rule. Owners C / D (work/re/handoff-b.md 217).')
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
