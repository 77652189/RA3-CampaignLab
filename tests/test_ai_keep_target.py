"""E123 named keep-clock replay; raw evidence: work/re/e123_keep_target.md.

Only the state-2 consumer clock is replayed. Candidate scoring, autonomous aim,
unequal Min/Max and other assignment sources remain gaps. E125 additionally
replays a recorded target's death before expiry (work/re/e125_keep_validity.md).
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


@pytest.mark.skipif(not simai.available(), reason='no ra3model.ai')
def test_keep_target_named_death_replay():
    """Replay death/validity observations, independently of candidate membership.

    The simulator's world view contains only living objects. Translating the
    host's 'dead' into absence from that view is an INFERRED bridge. Scoring,
    membership/readiness and the death's cause are supplied observations.
    Removal without death and eligibility-only loss remain bench gaps.
    """
    source = ROOT / 'tests/fixtures/e_keep/aikeepdead.txt'
    orders = teamlog.target_orders(str(source), 'T')
    passes = teamlog.keep_passes(str(source), 'T')
    tc = simai.model()['tactics']
    import build as bld
    mission, _, _ = bld.resolve('aikeeptwo', 'a')
    md = tc.MicroData(root='nonexistent')
    for _, text, _ in mission.assets:
        if '<AIMicroManagerData' in text:
            md.add_text(text)
    units = {o['mem']: NS(pos=(0, 0)) for o in orders if o['frame'] == 527}
    run = tc.Run(NS(members=list(units.values()), template=NS(micro='CNVMicroSpow'), tactic='Hunt'), None)
    run.mem = [tc.Fighter(i, (0, 0), 100, rate=lambda _: 10, unit=u) for i, u in units.items()]
    block = tc.TacticsBlock(None, None, None, lambda _: (0, 0), micro=md)
    block._view = NS()  # a supplied live-object world, as in SimAI.look
    issued = []
    block._attack_one = lambda ai, run, u, f, h, frame: issued.append(f.id)
    # Anchor observed assignments before the continuous validity window.
    for o in orders:
        if o['frame'] == 527:
            run.keep[id(units[o['mem']])] = o['until']
            run.keep_target[id(units[o['mem']])] = o['tgt']
            block._things[o['tgt']] = NS()
    early = held = 0
    for p in passes:
        frame = p['frame']
        if frame <= 527:
            continue
        participating = {i for i, _, _ in p['keep']}
        run.team.members = [u for i, u in units.items() if i in participating]
        run.hostile = [tc.Fighter(i, (10, 0), 100) for i, ok in p['cand'] if ok]
        reasons = {i: (target, reason) for i, target, reason in p['why']}
        assert set(reasons) == participating
        for member, until, decision in p['keep']:
            key = id(units[member])
            target, reason = reasons[member]
            assert run.keep_target[key] == target
            if reason == 'dead':
                assert until == 0 and frame < run.keep[key]
                block._things.pop(target)
                early += 1
            else:
                assert reason == 'ok'
                assert target in block._things
                assert run.keep[key] == until
            assert decision == ('go' if frame >= until else 'hold')
            held += decision == 'hold'
        issued.clear()
        block._assign(None, run, frame)
        expected = [i for i, _, decision in p['keep'] if decision == 'go']
        assert issued == expected, (p, issued)
        actual = [o for o in orders if o['frame'] == frame]
        assert sorted(o['mem'] for o in actual) == sorted(expected)
        for o in actual:
            assert o['src'] == 'score' and o['wrote']
            assert (o['min'], o['max'], o['keep']) == (2, 2, 30)
            assert (o['start'], o['until']) == (frame, frame + 30)
            key = id(units[o['mem']])
            assert run.keep[key] == o['until']
            assert run.keep_target[key] == o['tgt']
    # hold rows: f535 x2, f543 x1, f551 x1, f559 x1, f567 x2.
    assert early == 1 and held == 7
