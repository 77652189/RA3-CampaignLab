"""Engine-mechanic tests (missions/mech_bench.py).

thin: the three runners are sent north at GO_AT through the thin-ice square; a script kills each heavy one the frame it
  is inside it, never the light one. Read as the units' health (0 once dead) and the light one's arrival.
shown: at SHOW_AT an info box goes up on the near unit and a radar event on the far one; the counters only say the
  actions ran without taking the mission down (the game gives scripts no way to read the screen) -- the picture is
  looked at by hand (bench_look), see docs/story/drive-probe.md.
"""
from parts import Script, Test, counted, square

GO_AT = 10.0
ICE = 150.0                                     # half-side of the thin-ice square
GOAL = 150.0
SHOW_AT = 6.0
INFO = 'SCRIPT:CNVTEST_INFO'


def thin(m):
    t = Test()
    t.scripts.append(Script('Test - start', [], [('MAP_REVEAL_ALL_PERM', m.player('p1')),
                                                 ('SET_MILLISECOND_TIMER', 'Test - go timer', GO_AT)]))
    t.scripts.append(Script('Test - go', [('TIMER_EXPIRED', 'Test - go timer')],
                            [('MOVE_NAMED_UNIT_TO', m.role(k).name, m.mark('goal')) for k in ('heavy A', 'heavy B', 'light')]))
    t.areas['Test Ice'] = square(*m.point('ice'), ICE)
    t.areas['Test Goal'] = square(*m.point('goal'), GOAL)
    for k in ('heavy A', 'heavy B'):
        t.scripts.append(Script(f'Test - sink {k}', [('NAMED_INSIDE_AREA', m.role(k).name, 'Test Ice')],
                                [('NAMED_KILL', m.role(k).name)]))
    counted('Test A Health', 'A 重车血量', t, health=m.role('heavy A').name)
    counted('Test B Health', 'B 重车血量', t, health=m.role('heavy B').name)
    counted('Test Light Health', '轻车血量', t, health=m.role('light').name)
    counted('Test Light There', '轻车到达', t, named=m.role('light').name, area='Test Goal')
    t.expect += [('A 重车血量', 0, '==', 100, GO_AT - 1), ('A 重车血量', GO_AT, 'ever==', 0),
                 ('B 重车血量', GO_AT, 'ever==', 0), ('轻车血量', 0, '==', 100), ('轻车到达', GO_AT, 'ever==', 1)]
    t.bench = [('bench_watch', dict(seconds=GO_AT + 40, every=3, sheet=False, lines=len(t.counters),
                                    until='c4==1'))]
    return t


def bar(m):
    """A bar built of an info box: the same unit's box shown again each second with one more # in its text, no
    removal in between (A4 card C's thaw bar). Looked at by hand: the frames show whether the box was replaced
    in place, stacked, or ignored after the first."""
    t = Test()
    steps = 6
    t.counters.append(('Test Step', '第几步'))
    t.scripts.append(Script('Test - zero', [], [('SET_COUNTER', 'Test Step', 0)]))
    t.scripts.append(Script('Test - start', [], [('MAP_REVEAL_ALL_PERM', m.player('p1')),
                                                 ('SET_MILLISECOND_TIMER', 'Test - bar 0', SHOW_AT)]))
    for k in range(steps):
        t.strings[f'{INFO}{k}'] = '解冻 [' + '#' * k + '-' * (steps - 1 - k) + ']'
        nxt = [('SET_MILLISECOND_TIMER', f'Test - bar {k + 1}', 2.0)] if k + 1 < steps else []
        t.scripts.append(Script(f'Test - bar {k}', [('TIMER_EXPIRED', f'Test - bar {k}')],
                                [('NAMED_SHOW_INFOBOX', m.role('near').name, f'{INFO}{k}', 20.0, 'Allied_UnitIntro'),
                                 ('SET_COUNTER', 'Test Step', k + 1)] + nxt))
    t.expect += [('第几步', SHOW_AT + 2 * steps + 4, 'ever==', steps)]
    t.bench = [('bench_watch', dict(seconds=SHOW_AT + 2 * steps + 6, every=2, sheet=False, lines=len(t.counters)))]
    return t


def shown(m):
    t = Test()
    t.strings[INFO] = 'TEST：信息框'
    t.counters.append(('Test Done', '已执行'))
    t.scripts.append(Script('Test - zero', [], [('SET_COUNTER', 'Test Done', 0)]))
    t.scripts.append(Script('Test - start', [], [('MAP_REVEAL_ALL_PERM', m.player('p1')),
                                                 ('SET_MILLISECOND_TIMER', 'Test - show timer', SHOW_AT)]))
    t.scripts.append(Script('Test - show', [('TIMER_EXPIRED', 'Test - show timer')],
                            [('NAMED_SHOW_INFOBOX', m.role('near').name, INFO, 20.0, 'Allied_UnitIntro'),
                             ('OBJECT_CREATE_RADAR_EVENT', m.role('far').name, 0),
                             ('SET_COUNTER', 'Test Done', 1)]))
    t.expect += [('已执行', SHOW_AT + 2, 'ever==', 1)]
    t.bench = [('bench_watch', dict(seconds=SHOW_AT + 8, every=2, sheet=False, lines=len(t.counters)))]
    return t
