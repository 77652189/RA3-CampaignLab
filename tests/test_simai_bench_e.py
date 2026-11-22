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
_spec = importlib.util.spec_from_file_location('simai_run', ROOT / 'experimental/cnv/simai_run.py')
simai_run = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(simai_run)
simai = simai_run.simai    # one copy of simai, the run's (R3 13f-2d)

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
    w = simai_run.run('aiaeson', 'a', until=18, lib=simai.model()['xmldata'].Library(), record=True)
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
    w = simai_run.run('aiossoviet', 'a', 29, lib=simai.model()['xmldata'].Library())
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
    w = simai_run.run(build, 'z', 160, lib=simai.model()['xmldata'].Library())
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

