"""A9 checks (the plan's, docs/story/plans/a9.md).

win: the whole run in a few seconds: the nine balls razed one after another by test script (the player's tool, the
  beacons and the army, is not exercised: the live play does that); the three phases follow (the first ball, the
  rotation, the last three), the goals complete, the mission is won (ended, and no lost flag). It also builds the mission
  -- the balls' unit (units/tower_ball.py), the four rhythm devices -- through the real map compile.
"""
from parts import Script, Test

KILLS = 3.0                                     # seconds between two razes
FIRST = 8.0
WIN_BY = FIRST + KILLS * 9 + 25.0


def lost_counter(t):
    """A counter for the lost flag the plan's Lose scripts set ('Mission Lost'), so an end reads as won or lost."""
    t.counters.append(('Test Lost', '输了'))
    t.scripts += [Script('Test - lost zero', [], [('SET_COUNTER', 'Test Lost', 0)], once=False),
                  Script('Test - lost on', [('FLAG', 'Mission Lost', 1)], [('SET_COUNTER', 'Test Lost', 1)], once=False)]


def win(m):
    t = Test()
    for k in range(9):
        timer = f'Test Raze {k}'
        t.scripts += [Script(f'Test - raze set {k}', [], [('SET_MILLISECOND_TIMER', timer, FIRST + KILLS * k)]),
                      Script(f'Test - raze {k}', [('TIMER_EXPIRED', timer)],
                             [('NAMED_KILL', m.role(f'ball {k + 1}').name)])]
    lost_counter(t)
    # the counters vanish when the mission ends (checks/a8.py win): the lost flag can only be read before the end
    # (the bench's seconds run some seconds ahead of the mission's: the last raze is at 32, the counter reads garbage from
    # s31 on the bench -- bench 2026-11-04 -- so the lost flag is judged until six seconds before the last raze)
    t.expect += [('输了', 0, '==', 0, FIRST + KILLS * 8 - 6), ('ENDED', WIN_BY, '', None)]
    t.bench = [('bench_watch', dict(seconds=WIN_BY, every=2, sheet=False, lines=len(t.counters)))]
    return t


# the checks per build (cnv/registry.py): build name -> {check name: check(mission) -> Test}
CHECKS = {
    'a9': {'win': win},
}
