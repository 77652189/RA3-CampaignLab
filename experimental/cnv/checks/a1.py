"""A1 checks (the plan's, docs/story/plans/a1.md).

win: the three phases in a few seconds: the north bomber razed, then the south one, then the dock's guards one after
  another (the player's tools -- the swim along the shoals, the army -- are not exercised: the live play does that);
  the goals complete, the mission is won (ended, and no lost flag). It builds the mission through the real map compile.
walk: I20 (CampShell acceptance 2026-11-05b): the whole squad sent to the south bridgehead at the start, as anyone would:
  no patrol falls (they stand 160 up the deck, out of reach) and the mission goes on to the end of the walk.
trap: the "who sees whom" rule: one bridge guard razed while the north bomber lives -> the fuse is lit, the mission
  ends lost soon after (the lost flag is read before the end: 0 until the raze).
"""
import playcheck
from parts import Script, Test

FIRST = 8.0
KILLS = 3.0
DOCK = ['dock mag 1', 'dock mag 2', 'dock mag 3', 'dock tank 1', 'dock tank 2']
WIN_BY = FIRST + KILLS * (2 + len(DOCK)) + 25.0
TRAP_BY = FIRST + 14.0


def lost_counter(t):
    """A counter for the lost flag the plan's Lose scripts set ('Mission Lost'), so an end reads as won or lost."""
    t.counters.append(('Test Lost', '输了'))
    t.scripts += [Script('Test - lost zero', [], [('SET_COUNTER', 'Test Lost', 0)], once=False),
                  Script('Test - lost on', [('FLAG', 'Mission Lost', 1)], [('SET_COUNTER', 'Test Lost', 1)], once=False)]


def raze(t, m, role, k, at):
    timer = f'Test Raze {k}'
    t.scripts += [Script(f'Test - raze set {k}', [], [('SET_MILLISECOND_TIMER', timer, at)]),
                  Script(f'Test - raze {k}', [('TIMER_EXPIRED', timer)], [('NAMED_KILL', m.role(role).name)])]


WALK_BY = FIRST + 40.0
SQUAD = ['tanya', 'hawk 1', 'hawk 2', 'peace 1', 'peace 2', 'peace 3', 'peace 4']


def walk(m):
    t = Test()
    t.scripts += [Script('Test - walk set', [], [('SET_MILLISECOND_TIMER', 'Test Walk', FIRST)]),
                  Script('Test - walk', [('TIMER_EXPIRED', 'Test Walk')],
                         [('MOVE_NAMED_UNIT_TO', m.role(r).name, m.mark('south bridgehead')) for r in SQUAD])]
    lost_counter(t)
    t.counters += [('CNV_A1_Lost_2', '巡逻倒')]
    t.expect += [('输了', 0, '==', 0, WALK_BY), ('巡逻倒', 0, '==', 0, WALK_BY)]
    t.bench = [('bench_watch', dict(seconds=WALK_BY, every=2, sheet=False, lines=len(t.counters)))]
    return t


def win(m):
    t = Test()
    for k, role in enumerate(['north bomber', 'south bomber'] + DOCK):
        raze(t, m, role, k, FIRST + KILLS * k)
    lost_counter(t)
    # the counters vanish when the mission ends (checks/a8.py win): the lost flag can only be read before the end
    t.expect += [('输了', 0, '==', 0, FIRST + KILLS * (1 + len(DOCK)) - 6), ('ENDED', WIN_BY, '', None)]
    t.bench = [('bench_watch', dict(seconds=WIN_BY, every=2, sheet=False, lines=len(t.counters)))]
    return t


def trap(m):
    t = Test()
    raze(t, m, 'deck guard 1', 0, FIRST)
    lost_counter(t)
    t.expect += [('输了', 0, '==', 0, FIRST - 3), ('ENDED', TRAP_BY, '', None)]
    t.bench = [('bench_watch', dict(seconds=TRAP_BY, every=2, sheet=False, lines=len(t.counters)))]
    return t


# the checks per build (cnv/registry.py): build name -> {check name: check(mission) -> Test}
CHECKS = {
    'a1': {'win': win, 'trap': trap, 'walk': walk, 'play': playcheck.make('a1')},
}
