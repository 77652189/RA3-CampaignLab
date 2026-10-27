"""S5 tests (the plan: docs/story/plans/s5.md). Counted: any of the Allied fleet in the canal south of the lock (it
got through: the mission is lost).

trap: the control room's guards are killed by test script at RAZE_AT -- what the burrowers' squad does in play --
  and the control room kept at full health; the fleet sets out on time, held, and never gets through; the hold
  runs out and the mission is over.
escape: nothing is done; the fleet sets out on time, gets through and the mission is lost soon after.
"""
import plan
from parts import Script, Test, counted, square

RAZE_AT, AREA = 5.0, 250.0
THROUGH = 120.0                                 # escape: from setting out, through the lock by then


def sets_out():
    """When the fleet sets out (s5.md 规则: its first rule), normal difficulty."""
    when = plan.load('s5')['规则'][0]['当']
    return plan.spans(when.split('+')[1])[1][0]


def setup(m):
    t = Test()
    t.scripts.append(Script('Test - reveal', [], [('MAP_REVEAL_ALL_PERM', m.player('p1'))]))
    t.areas['Test south canal'] = square(*m.site('south canal'), AREA)
    counted('Test Through', '冲过船闸', t, template=m.role('fleet 1').template, player=m.player('s1'),
            area='Test south canal')
    return t


def trap(m):
    t = setup(m)
    guards = [r.name for g in ('control guard', 'control tank') for r in m.roles(g)]
    t.scripts += [Script('Test - raze', [], [('SET_MILLISECOND_TIMER', 'Test - raze timer', RAZE_AT)]),
                  Script('Test - raze now', [('TIMER_EXPIRED', 'Test - raze timer')],
                         [('NAMED_KILL', g) for g in guards]),
                  Script('Test - keep the room up', [], [('UNIT_SET_HEALTH', m.role('control room').name, 100.0)],
                         once=False)]
    hold = plan.spans(plan.load('s5')['段'][1]['开场'][-1]['倒计时'].split('+')[1])[1][0]
    end = RAZE_AT + hold
    t.expect += [('冲过船闸', 1, '==', 0, end - 10), ('ENDED', end - 10, '', None)]   # the counters go with the end
    t.bench = [('bench_watch', dict(seconds=end + 30, every=5, sheet=False, lines=len(t.counters)))]
    return t


def escape(m):
    t = setup(m)
    out = sets_out()
    t.expect += [('冲过船闸', out, 'ever>', 0, out + THROUGH), ('ENDED', out, '', None)]
    t.bench = [('bench_watch', dict(seconds=out + THROUGH + 30, every=5, sheet=False, lines=len(t.counters)))]
    return t
