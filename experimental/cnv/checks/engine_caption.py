"""Engine unit test: when does the caption strip clear, and is the tutorial text box a strip that does not stack?

The strip (the military caption, through ctx.caption, shared with dialogue subtitles) stacks lines and clears them all together. What
sets the moment: a fixed hold after the last line (seen ~5.4 s with 6 s captions), or the last line's own seconds?
  A at A_AT for 15 s alone, B at B_AT for 2 s alone, C at C_AT for 2 s then D a second later for 10 s.
  Fixed hold: each clears ~5.4 s after its last line. Own seconds: A ~15 s, B ~2 s, C+D ~10 s after D.
Then the tutorial text box (DISPLAY_TUTORIAL_TEXT): shown, replaced by a second text, hidden by HIDE_TUTORIAL_TEXT.
'第几步' counts the events so the frames line up; bench_watch says per frame whether the strip changed.
"""
from ctx import caption
from maps import festival
from parts import Mission, Script, Test

A_AT, B_AT, C_AT, TIP_AT = 3.0, 25.0, 35.0, 52.0
RUN = TIP_AT + 10.0
EVENTS = [(A_AT, [caption('SCRIPT:CNVTEST_CAP_A', 15.0)]),
          (B_AT, [caption('SCRIPT:CNVTEST_CAP_B', 2.0)]),
          (C_AT, [caption('SCRIPT:CNVTEST_CAP_C', 2.0)]),
          (C_AT + 1, [caption('SCRIPT:CNVTEST_CAP_D', 10.0)]),
          (TIP_AT, [('DISPLAY_TUTORIAL_TEXT', 'SCRIPT:CNVTEST_TIP_1')]),
          (TIP_AT + 3, [('DISPLAY_TUTORIAL_TEXT', 'SCRIPT:CNVTEST_TIP_2')]),
          (TIP_AT + 6, [('HIDE_TUTORIAL_TEXT',)])]
TEXT = {'SCRIPT:CNVTEST_CAP_A': 'TEST A：15 秒', 'SCRIPT:CNVTEST_CAP_B': 'TEST B：2 秒',
        'SCRIPT:CNVTEST_CAP_C': 'TEST C：2 秒', 'SCRIPT:CNVTEST_CAP_D': 'TEST D：10 秒',
        'SCRIPT:CNVTEST_TIP_1': 'TEST 提示框一', 'SCRIPT:CNVTEST_TIP_2': 'TEST 提示框二'}


def mission():
    m = Mission(name='CampCaption', map=festival, facts={})
    m.put('AlliedAntiVehicleVehicleTech1', 'west field', 250, 30, name='UNIT - CNV Caption Guardian', role='guardian')
    return m


def clears(m):
    t = Test()
    t.strings.update(TEXT)
    t.counters.append(('Test Step', '第几步'))
    t.scripts.append(Script('Test - start', [], [('SET_COUNTER', 'Test Step', 0)] +
                            [('SET_MILLISECOND_TIMER', f'Test - event {k}', at) for k, (at, _) in enumerate(EVENTS)]))
    for k, (_, acts) in enumerate(EVENTS):
        t.scripts.append(Script(f'Test - event {k}', [('TIMER_EXPIRED', f'Test - event {k}')],
                                list(acts) + [('SET_COUNTER', 'Test Step', k + 1)]))
    t.expect += [('第几步', RUN - 2, 'ever==', len(EVENTS))]
    t.bench = [('bench_watch', dict(seconds=TIP_AT + 1.5, every=1, sheet=False, lines=1)),
               ('bench_look', dict(note='the tutorial text box: where, how it looks (TEST 提示框一)')),
               ('bench_watch', dict(seconds=RUN - TIP_AT - 1.5, every=1, sheet=False, lines=1))]
    return t


# a build that is both mission and check (cnv/registry.py)
PAIR_BUILDS = {'caption': lambda: (lambda m: (m, clears(m)))(mission())}
