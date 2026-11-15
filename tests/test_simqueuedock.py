"""E152: named QueueDock probe and measured replay (see work/re/e152_queuedock.md)."""
import importlib.util
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('queuedock_bootstrap', ROOT / 'experimental/cnv/simbench.py')
bootstrap = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bootstrap)


def test_queuedock_probe_is_a_single_module_control():
    import build
    from parts import contract, merged
    arms = [build.resolve(name, 'a')[:2] for name in ('engine_queuedock', 'queuedockoff')]
    for m, t in arms:
        assert not contract(merged(m, t))
        assert m.role('miner').template == 'AlliedMiner'
        assert len(m.objects) == 2
        assert 'SpawnBehavior' not in m.units[0].xml
        # Observation, not a scripted money grant or a forced harvesting/docking state.
        assert not any(a[0] == 'UNIT_CHANGE_OBJECT_STATUS' for s in t.scripts for a in s.do)
        assert [a for s in t.scripts for a in s.do if a[0] == 'PLAYER_SET_MONEY'] == [
            ('PLAYER_SET_MONEY', m.player('p1'), 0)]
    on, off = [m.units[0].xml for m, _ in arms]
    assert re.sub(r'<QueueDockBehavior\b.*?/>', '', on, count=1, flags=re.S) == off


def test_queuedock_short_zero_wallet_record_is_inconclusive():
    """The actual off run stopped at f197; its zero wallet cannot pass acceptance."""
    import build
    _, t, _ = build.resolve('queuedockoff', 'a')
    # First and last observed samples from E152's incomplete control.
    results = build.judge(t, [(1.2, [49, 0, 10000, 0]), (11.0, [197, 0, 10000, 0])])
    assert results[0][0]  # the old wallet-only judge gave a misleading PASS
    assert not all(ok for ok, _ in results)


@pytest.mark.xfail(strict=True, reason='E152 on f786 wallet/pad snapshot does not replay; '
                   'native dock/harvest stages are unobserved. See work/re/e152_queuedock.md')
def test_queuedock_on_named_measured_snapshot():
    """E152 on f786: wallet 500, alive/outside pad, paid then left; stage bits zero."""
    import build
    import sim
    from parts import Script
    m, t, _ = build.resolve('engine_queuedock', 'a')
    t.scripts.append(Script('Test - E152 measured snapshot', [
        ('COUNTER', 'E152Frame', 2, 786), ('COUNTER', 'E152Money', 2, 500),
        ('COUNTER', 'E152State', 2, 10000), ('COUNTER', 'E152Progress', 2, 1100)],
        [('SET_COUNTER', 'E152Matched', 1)]))
    engine = sim.Sim(m, t).run(56)
    assert engine.eng.value('E152Matched') == 1, {
        name: engine.eng.value(name) for name in ('E152Money', 'E152State', 'E152Progress')}
