"""A2 checks (the plan's, docs/story/plans/a2.md).

win: the whole run at 1/20 of its time (every timer the plan sets is cut to a twentieth: the three phases end after 9 s
  each), then the far bank's rocket cars are razed by test script in the last phase: the goals complete, the mission
  is won (ended, and no lost flag). The waves fire at the same fast pace but have the length of the road to walk (the
  dam holds for the minute this takes); the player's part (what to send against which wave) is the live play's.
lose: two of the dam's three sections razed by test script: the mission ends lost ("the dam fell"), the lost flag
  0 before.
"""
from parts import Script, Test

SCALE = 20.0
PHASE = 180.0 / SCALE                      # one phase of the plan: 3:00
RAZE_AT = 3 * PHASE + 4.0                  # the last phase has begun (the bench's seconds start a little after the mission's)
WIN_BY = RAZE_AT + 14.0
FIRST, SECOND = 8.0, 10.0
LOSE_BY = SECOND + 14.0


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
    for s in m.scripts:
        s.do = [(a[0], a[1], a[2] / SCALE) if a[0] == 'SET_MILLISECOND_TIMER' else a for a in s.do]
    t = Test()
    for k, r in enumerate(m.roles('rocket')):
        raze(t, r.name, k, RAZE_AT + 0.5 * k)
    lost_counter(t)
    # the counters vanish when the mission ends: the lost flag can only be read before the end
    t.expect += [('输了', 0, '==', 0, RAZE_AT - 2), ('ENDED', WIN_BY, '', None)]
    t.bench = [('bench_watch', dict(seconds=WIN_BY, every=3, sheet=False, lines=len(t.counters)))]
    return t


def lose(m):
    t = Test()
    raze(t, m.role('dam w').name, 0, FIRST)
    raze(t, m.role('dam m').name, 1, SECOND)
    lost_counter(t)
    t.expect += [('输了', 0, '==', 0, FIRST - 3), ('ENDED', LOSE_BY, '', None)]
    t.bench = [('bench_watch', dict(seconds=LOSE_BY, every=2, sheet=False, lines=len(t.counters)))]
    return t


# the checks per build (cnv/registry.py): build name -> {check name: check(mission) -> Test}
CHECKS = {
    'a2': {'win': win, 'lose': lose},
}
