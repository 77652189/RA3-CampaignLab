"""C: retail Joypad element disable/restore observation probe.

Untouched baseline through 4 s; disable the two retail button names at 4 s;
restore tech store at 8 s; restore assault directive at 12 s. The phase counter
marks script execution only, NOT element enabled state or input acceptance.
Prediction: one untouched power plant remains alive throughout all four phases.
This is a liveness/control prediction, not whole-action simulation equivalence.
No mouse or keyboard event is passed off as native Joypad input: the current
bench publishes keyboard/mouse injection but no controller input/state contract.
Observe the real run before deciding whether a native UI gate can be measured.
Evidence and remaining gate: work/re/c_joypad_report.md.
BENCH 11-16: one run, 17 readings f40..182, all phases 0/1/2/3 observed,
untouched alive=1 throughout; final phase/alive/frame=3/1/182, NOEXPECT.
These are script markers, not native Joypad state. No enabled/accept/reject
field is published; the native gate remains unmeasured and the action TODO.
"""
from maps import probe_border
from parts import Mission, Script, Test
from checks import engine_scripts8 as s8


def mission():
    m = Mission(name='CampJoypad', map=probe_border, units=[], facts={})
    m.put('AlliedPowerPlant', 'stop row', 0., -500., side='p1',
          name='CNV Joypad untouched', role='untouched')
    return m


def a(m):
    t = Test()
    phase = 'CNV_Joypad_Phase'
    t.counters.append((phase, '脚本阶段'))
    t.scripts.append(Script('Test - joypad baseline', [], [
        ('MAP_REVEAL_ALL_PERM', m.player('p1')), ('SET_COUNTER', phase, 0)]))
    buttons = ('buttonopenplayertechstore', 'buttonaiassaultdirective')
    for seconds, number, changes in (
            (4., 1, [(button, 1) for button in buttons]),
            (8., 2, [(buttons[0], 0)]),
            (12., 3, [(buttons[1], 0)])):
        s8.at(t, f'joypad phase {number}', seconds, [
            *[('DISABLE_JOYPAD_COMMANDBAR_BUTTON', button, disabled)
              for button, disabled in changes], ('SET_COUNTER', phase, number)])
    s8.total(t, 'CNV_Joypad_Alive', '未操作存活', [
        (1, ('NAMED_NOT_DESTROYED', m.role('untouched').name))])
    s8.frames(t, 'CNV_Joypad_Clock', '逻辑帧', [])
    s8.watch(t, 16.)
    return t


MISSION = {'engine_joypad': mission}
CHECKS = {'engine_joypad': {'a': a}}
