"""J7 tests (the plan: docs/story/plans/j7.md). Counted: the launch tower's health.

win: the tower razed by test script at RAZE_AT -- the mission is over (won) at once.
late: nothing is done -- the countdown runs out and the mission is over (lost).
"""
import plan
from parts import Script, Test, counted

RAZE_AT = 10.0


def launch():
    """The countdown (normal difficulty): the first phase's opening shows it."""
    shown = next(a for a in plan.load('j7')['段'][0]['开场'] if isinstance(a, dict) and '倒计时' in a)
    return plan.spans(shown['倒计时'].split('+')[1])[1][0]


def setup(m):
    t = Test()
    t.scripts.append(Script('Test - reveal', [], [('MAP_REVEAL_ALL_PERM', m.player('p1'))]))
    counted('Test Tower', '发射塔血量', t, health=m.role('launch tower').name)
    return t


def win(m):
    t = setup(m)
    t.scripts += [Script('Test - raze timer', [], [('SET_MILLISECOND_TIMER', 'Test - raze timer', RAZE_AT)]),
                  Script('Test - raze', [('TIMER_EXPIRED', 'Test - raze timer')],
                         [('NAMED_KILL', m.role('launch tower').name)])]
    t.expect += [('ENDED', RAZE_AT, '', None)]
    t.bench = [('bench_watch', dict(seconds=RAZE_AT + 30, every=2, sheet=False, lines=len(t.counters)))]
    return t


def late(m):
    t = setup(m)
    end = launch()
    t.expect += [('ENDED', end - 10, '', None)]
    t.bench = [('bench_watch', dict(seconds=end + 30, every=6, sheet=False, lines=len(t.counters)))]
    return t
