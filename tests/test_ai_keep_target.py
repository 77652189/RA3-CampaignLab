"""E123 named keep-clock replay; raw evidence: work/re/e123_keep_target.md.

Only the state-2 consumer clock is replayed. Candidate scoring, autonomous aim,
target death, unequal Min/Max and other assignment sources remain gaps.
"""
import importlib.util
from pathlib import Path
from types import SimpleNamespace as NS

import pytest

ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location('simai', ROOT / 'experimental/cnv/simai.py')
simai = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(simai)
import teamlog


@pytest.mark.skipif(not simai.available(), reason='no ra3model.ai')
@pytest.mark.parametrize('build,seconds', [('aiegon', 0), ('aikeeptwo', 2)])
def test_keep_target_named_clock_replay(build, seconds):
    """Replay actual candidate/hold/go passes, anchored by written assignments.

    Candidate identities are retained; model score is INFERRED and is not
    validated here. We compare whether the consumer issues an order and its
    stored expiry, without asserting which eligible target wins the score.
    """
    source = ROOT / 'tests/fixtures/e_keep' / (build + '.txt')
    orders = teamlog.target_orders(str(source), 'T')
    passes = teamlog.keep_passes(str(source), 'T')
    assert orders and passes
    first = orders[0]
    assert first['src'] == 'score' and first['wrote']
    assert first['min'] == first['max'] == seconds
    assert first['keep'] == 15 * seconds
    assert first['start'] == first['frame']
    assert first['until'] == first['frame'] + 15 * seconds
    tc = simai.model()['tactics']
    import build as bld
    mission, _, _ = bld.resolve(build, 'a')
    md = tc.MicroData(root='nonexistent')
    for _, text, _ in mission.assets:
        if '<AIMicroManagerData' in text:
            md.add_text(text)
    micro = 'CNVMicroSpow'
    assert md.num(micro, 'TimeToKeepTargetMin') == seconds
    assert md.num(micro, 'TimeToKeepTargetMax') == seconds
    ids = [member for member, _, _ in passes[0]['keep']]
    units = {i: NS(pos=(0, 0)) for i in ids}
    run = tc.Run(NS(members=list(units.values()), template=NS(micro=micro), tactic='Hunt'), None)
    run.mem = [tc.Fighter(i, (0, 0), 100, rate=lambda _: 10, unit=u) for i, u in units.items()]
    block = tc.TacticsBlock(None, None, None, lambda _: (0, 0), micro=md)
    issued = []
    block._attack_one = lambda ai, run, u, f, h, frame: issued.append(f.id)
    held = reassigned = 0
    for p in passes:
        frame = p['frame']
        # kpass lists only members reaching the clock consumer this pass.
        # Readiness and other pre-consumer gates are supplied observations.
        participating = {i for i, _, _ in p['keep']}
        run.team.members = [u for i, u in units.items() if i in participating]
        run.hostile = [tc.Fighter(i, (10, 0), 100) for i, ok in p['cand'] if ok]
        assert run.hostile, (build, p)
        expected = []
        for member, until, decision in p['keep']:
            assert member in units
            assert decision == ('go' if frame >= until else 'hold')
            # Initial pass has no record; later passes must match model state.
            assert run.keep.get(id(units[member]), 0) == until, (build, p, run.keep)
            if decision == 'go':
                expected.append(member)
            else:
                held += 1
        issued.clear()
        block._assign(None, run, frame)
        assert issued == expected, (build, p, issued)
        actual = [o for o in orders if o['frame'] == frame]
        assert sorted(o['mem'] for o in actual) == sorted(expected)
        for o in actual:
            assert o['src'] == 'score' and o['wrote']
            assert (o['min'], o['max'], o['keep']) == (seconds, seconds, seconds * 15)
            assert (o['start'], o['until']) == (frame, frame + seconds * 15)
            assert (o['tgt'], True) in p['cand']
            assert run.keep[id(units[o['mem']])] == o['until']
            reassigned += 1
    assert reassigned >= 4
    assert (held > 0) == (seconds > 0)
