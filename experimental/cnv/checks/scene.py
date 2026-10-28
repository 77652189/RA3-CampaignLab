"""Scene tests (missions/scene_bench.py). Counted, each latched at 1 once it happened: the camera got to the north
base in phase 2's 过场 (CAMERA_ENTERED_AREA; phase 1's to the harbour: bench 2026-10-27, counted 1 -- four counter
lines are all that fit), each goal shown (its shown flag), and
anything shown too early -- the timed goal before phase 2's 过场 handed the input back, the bonus before the test
script sent the dog. The order is counted, not the second: the bench's seconds start some seconds after the mission's
(bench 2026-10-27, ~8).

look: both scenes take the camera where they say; the timed goal is shown after the hand-back; the bonus once the dog
  (sent by test script SEND_AFTER past phase 2's hand-back) got to the convoy start; nothing too early. The frames
  while phase 2's scene runs show the letterbox and the whole map.
"""
from parts import Script, Test, square

SEND_AFTER, RUN = 8.0, 75.0
CAMERA = 500.0                                  # half-side of the area round a place the camera must enter


def latch(t, counter, label, when):
    t.counters.append((counter, label))
    t.scripts.append(Script(f'Test - {counter} zero', [], [('SET_COUNTER', counter, 0)]))
    t.scripts.append(Script(f'Test - {counter}', when, [('SET_COUNTER', counter, 1)]))


def look(m):
    t = Test()
    t.areas['Test Harbour'] = square(*m.site('harbour'), CAMERA)
    t.areas['Test Camp'] = square(*m.site('north base'), CAMERA)
    latch(t, 'Test Camera 2', '镜头到了北营', [('FLAG', 'CNV_SC_Phase_2', 1), ('CAMERA_ENTERED_AREA', 'Test Camp')])
    latch(t, 'Test Timed', '定时目标亮了', [('FLAG', 'CNV_SC_Objective01_Shown', 1)])
    latch(t, 'Test Near', '奖励目标亮了', [('FLAG', 'CNV_SC_Bonus01_Shown', 1)])
    t.counters.append(('Test Early', '亮早了'))
    t.scripts += [Script('Test - Test Early zero', [], [('SET_COUNTER', 'Test Early', 0)]),
                  Script('Test - early timed', [('FLAG', 'CNV_SC_Objective01_Shown', 1), ('FLAG', 'CNV_SC_Scene_2', 0)],
                         [('SET_COUNTER', 'Test Early', 1)]),
                  Script('Test - early bonus', [('FLAG', 'CNV_SC_Bonus01_Shown', 1), ('FLAG', 'Test_Sent', 0)],
                         [('SET_COUNTER', 'Test Early', 1)])]
    m.waypoint('test convoy start', 'Test convoy start', 'convoy start')
    t.scripts += [Script('Test - send timer', [('FLAG', 'CNV_SC_Scene_2', 1)],
                         [('SET_MILLISECOND_TIMER', 'Test - send', SEND_AFTER)]),
                  Script('Test - send', [('TIMER_EXPIRED', 'Test - send')],
                         [('SET_FLAG', 'Test_Sent', 1), ('MOVE_NAMED_UNIT_TO', m.role('dog').name,
                                                          m.mark('test convoy start'))])]
    t.expect += [('镜头到了北营', 1, 'ever==', 1), ('定时目标亮了', 1, 'ever==', 1),
                 ('奖励目标亮了', 1, 'ever==', 1), ('亮早了', 1, '==', 0)]
    t.bench = [('bench_watch', dict(seconds=RUN, every=2, sheet=False, lines=len(t.counters)))]
    return t
