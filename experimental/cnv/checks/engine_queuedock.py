"""E152 QueueDock prediction: named miner harvests, returns, pays 250 and leaves.

Both arms remove the refinery's SpawnBehavior to avoid a second miner claiming
the node. Only off removes QueueDock. Original prediction: off should not unload; no
timing or bone/path calibration is assumed. Native DOCKING object status is
observed separately from the XML's DOCKING_ACTIVE model animation condition.

Same-frame state decimal digits: miner docking=1, harvesting=10, refinery
docking=100, miner in pad=1000, both alive=10000. Progress latches: harvested=1,
docked=10, paid=100, left pad after full payment=1000. Money is read every frame.

MEASURED E152: on f329=250, f351 left pad, f597=500; both alive,
DOCKING/HARVESTING bits always zero through f1139. Off capture ended at f197
with money/progress=0, before on's first payment. Its old wallet-only judge
said PASS despite truncation; the frame gate below rejects that record.
D165/E164 supersedes the off interpretation: native faults on its first
delivery to the refinery without QueueDock. It is not a zero-income control;
judge that diagnostic with teamlog.dock_phases faults, not these wallet rules.
On native Unload lasts 30 frames and delivers 250; the simulator rejects the
missing dock at selection. See work/re/e164_queuedock.md. The on f786 snapshot
remains strict xfail; no path or bone timing was fitted.
"""
from parts import NOT, Script, Test, square, status


def check(m):
    t = Test()
    miner, refinery = m.role('miner').name, m.role('refinery').name
    t.areas['E152 Pad'] = square(*m.facts['dock pad'])
    t.counters = [('E152Frame', '帧数'), ('E152Money', '资金'),
                  ('E152State', '同帧'), ('E152Progress', '阶段')]
    t.scripts = [Script('Test - E152 start', [], [
        ('MAP_REVEAL_ALL_PERM', m.player('p1')), ('PLAYER_SET_MONEY', m.player('p1'), 0)]),
        Script('Test - E152 frame', [], [('INCREMENT_COUNTER', 1, 'E152Frame'),
            ('SET_COUNTER', 'E152State', 0),
            ('SET_PLAYER_MONEY_TO_COUNTER', m.player('p1'), 'E152Money')], once=False)]
    docking = ('UNIT_HAS_OBJECT_STATUS', miner, status('DOCKING'))
    harvesting = ('UNIT_HAS_OBJECT_STATUS', miner, status('HARVESTING'))
    for tag, bit, conds in [
        ('dock', 1, [docking]), ('harvest', 10, [harvesting]),
        ('host', 100, [('UNIT_HAS_OBJECT_STATUS', refinery, status('DOCKING'))]),
        ('pad', 1000, [('NAMED_INSIDE_AREA', miner, 'E152 Pad')]),
        ('alive', 10000, [('NAMED_DESTROYED', miner, NOT), ('NAMED_DESTROYED', refinery, NOT)])]:
        t.scripts.append(Script('Test - E152 state ' + tag, conds,
            [('INCREMENT_COUNTER', bit, 'E152State')], once=False))
    for tag, bit, conds in [
        ('harvested', 1, [harvesting]), ('docked', 10, [docking]),
        ('paid', 100, [('COUNTER', 'E152Money', 3, 250)]),
        ('left', 1000, [('FLAG', 'E152 paid', 1),
                         ('NAMED_INSIDE_AREA', miner, 'E152 Pad', NOT)])]:
        t.scripts.append(Script('Test - E152 progress ' + tag, conds,
            [('INCREMENT_COUNTER', bit, 'E152Progress'), ('SET_FLAG', 'E152 ' + tag, 1)]))
    t.expect = [('资金', 0, 'ever>=', 250, 50)] if m.facts['queuedock'] else [('资金', 0, '==', 0, 50)]
    # Fifty logical seconds, independent of capture speed; a short zero-wallet
    # record cannot prove the negative control. The original off prediction stays.
    t.expect.append(('帧数', 0, 'ever>=', 750))
    t.bench = [('bench_watch', dict(seconds=50, every=0.5, sheet=False, lines=4))]
    return t


CHECKS = {'engine_queuedock': {'a': check}, 'queuedockoff': {'a': check}}
