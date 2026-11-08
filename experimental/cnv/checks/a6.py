"""A6 checks (the plan's, docs/story/plans/a6.md).

win: the phases in a few seconds: the outer tower razed by test script, then the three inner ones one after another;
  the last phase begins and Tanya (who has not left the camp) is in it: the goals complete, the mission is won (ended,
  and no lost flag). The player's part (the climb, the spotter and the guns: the plan's `待做` 1) is the live play's.
lose: Tanya razed by test script: the mission ends lost, the lost flag 0 before.
"""
import playcheck
from parts import Script, Test

FIRST = 8.0
STEP = 3.0
ROLES = ['tower a', 'tower n', 'tower w', 'tower e']
WIN_BY = FIRST + STEP * len(ROLES) + 16.0
LOSE_AT = 8.0
LOSE_BY = LOSE_AT + 14.0


def lost_counter(t):
    """A counter for the lost flag the plan's Lose scripts set ('Mission Lost'), so an end reads as won or lost."""
    t.counters.append(('Test Lost', '输了'))
    t.scripts += [Script('Test - lost zero', [], [('SET_COUNTER', 'Test Lost', 0)], once=False),
                  Script('Test - lost on', [('FLAG', 'Mission Lost', 1)], [('SET_COUNTER', 'Test Lost', 1)], once=False)]


def raze(t, name, k, at):
    timer = f'Test Raze {k}'
    t.scripts += [Script(f'Test - raze set {k}', [], [('SET_MILLISECOND_TIMER', timer, at)]),
                  Script(f'Test - raze {k}', [('TIMER_EXPIRED', timer)], [('NAMED_KILL', name)])]


def win(m):
    t = Test()
    for k, role in enumerate(ROLES):
        raze(t, m.role(role).name, k, FIRST + STEP * k)
    lost_counter(t)
    # the counters vanish when the mission ends: the lost flag can only be read before the end
    t.expect += [('输了', 0, '==', 0, FIRST + STEP * (len(ROLES) - 1) - 2), ('ENDED', WIN_BY, '', None)]
    t.bench = [('bench_watch', dict(seconds=WIN_BY, every=3, sheet=False, lines=len(t.counters)))]
    return t


def lose(m):
    t = Test()
    raze(t, m.role('tanya').name, 0, LOSE_AT)
    lost_counter(t)
    t.expect += [('输了', 0, '==', 0, LOSE_AT - 3), ('ENDED', LOSE_BY, '', None)]
    t.bench = [('bench_watch', dict(seconds=LOSE_BY, every=2, sheet=False, lines=len(t.counters)))]
    return t


# the checks per build (cnv/registry.py): build name -> {check name: check(mission) -> Test}
CHECKS = {
    'a6': {'win': win, 'lose': lose, 'play': playcheck.make('a6')},
}
