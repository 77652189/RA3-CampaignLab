"""E151: CaptureSpecialAbilityUpdate, original Command_CaptureBuilding input.

SDK prediction: CAPTURABLE flags use the object-target capture power (2s
unpack, 10s preparation, 1s pack, range 30), not EngineerContain. Neutral
and enemy flags should change to p1 without consuming the engineer; own
flag stays owned, and removing the update should prevent neutral capture.
These predictions are UNMEASURED; exact movement/stage timing is a gap.
Four decimal digits encode final p1 ownership, engineers alive separately.
No direct ownership transfer or B-line recruitment is used.

MEASURED 2026-11-15: a returned owners=100, alive=1111, before=1 through
observed f45..575. The positive capture prediction below failed and remains
unchanged. This is an input/qualification gap, not capture-effect coverage;
no accepted cast or per-stage observation was available. Paused pending that
evidence; see work/re/e151_capture.md. Do not repeat the same input blindly.
"""
from parts import NOT, Script, Test, counted


def check(m):
    t = Test()
    t.counters = [('E151Frame', '帧数'), ('E151Owners', '归属'),
                  ('E151Alive', '存活'), ('E151Before', '前置')]
    t.scripts = [Script('Test - E151 start', [], [
        ('MAP_REVEAL_ALL_PERM', m.player('p1')),
        ('SET_MILLISECOND_TIMER', 'E151Cast', 10.0)]),
        Script('Test - E151 frame', [], [('INCREMENT_COUNTER', 1, 'E151Frame')], once=False),
        Script('Test - E151 reset', [], [('SET_COUNTER', 'E151Owners', 0),
                                        ('SET_COUNTER', 'E151Alive', 0)], once=False)]
    before = [('TIMER_EXPIRED', 'E151Cast', NOT)]
    cast = []
    for tag, owner, bit in [('neutral', 'neutral', 1), ('enemy', 's1', 10),
                             ('own', 'p1', 100), ('off', 'neutral', 1000)]:
        flag, man = m.role(tag + ' flag').name, m.role(tag + ' man').name
        before += [('NAMED_DESTROYED', man, NOT), ('NAMED_DESTROYED', flag, NOT)]
        if owner == 'neutral':
            before += [('NAMED_OWNED_BY_PLAYER', m.player(side), flag, NOT) for side in ('p1', 's1')]
        else:
            before.append(('NAMED_OWNED_BY_PLAYER', m.player(owner), flag))
        cast.append(('NAMED_USE_COMMANDBUTTON_ABILITY_ON_NAMED', man, 'Command_CaptureBuilding', flag))
        t.scripts += [Script('Test - E151 owner ' + tag,
            [('NAMED_OWNED_BY_PLAYER', m.player('p1'), flag)],
            [('INCREMENT_COUNTER', bit, 'E151Owners')], once=False),
            Script('Test - E151 alive ' + tag, [('NAMED_DESTROYED', man, NOT)],
            [('INCREMENT_COUNTER', bit, 'E151Alive')], once=False)]
    t.scripts += [Script('Test - E151 before', before, [('SET_COUNTER', 'E151Before', 1)]),
                  Script('Test - E151 cast', [('TIMER_EXPIRED', 'E151Cast')], cast)]
    t.expect = [('前置', 2, '==', 1, 35), ('归属', 28, '==', 111, 35),
                ('存活', 28, '==', 1111, 35)]
    t.bench = [('bench_watch', dict(seconds=35, every=1, sheet=False, lines=4))]
    return t


# A403: is the update in a building capture? Each lane's input; its engineer: missions/capture_special.OFF.
HOW = {'base': 'press', 'high': 'press', 'order': 'enter', 'removed': 'enter'}


def check_off(m):
    """A403: CAPTURABLE (the update's only target, its power's filter) is CaptureFlag / ControlPoint alone, which no
    retail mission and none of our nine places; a building capture is EngineerContain's. Each lane's counter: the
    plant's health + 1000 owned by p1 + 10000 engineer alive; pressed (Command_CaptureBuilding) or entered
    (NAMED_GARRISON_SPECIFIC_BUILDING) at s10. Bench CampCapOffA_mcp_1127_082109 PASS: 10050 to s11, 1050 from s12."""
    t = Test()
    press = {'press': lambda man, plant: ('NAMED_USE_COMMANDBUTTON_ABILITY_ON_NAMED', man, 'Command_CaptureBuilding', plant),
             'enter': lambda man, plant: ('NAMED_GARRISON_SPECIFIC_BUILDING', man, plant)}
    t.scripts = [Script('Test - start', [], [('MAP_REVEAL_ALL_PERM', m.player('p1')),
                                             ('SET_MILLISECOND_TIMER', 'Engineer enter', 10.0),
                                             *[('UNIT_SET_HEALTH', 'Plant ' + lane, 50.0) for lane in HOW]]),
                 Script('Test - enter', [('TIMER_EXPIRED', 'Engineer enter')],
                        [press[how]('Man ' + lane, 'Plant ' + lane) for lane, how in HOW.items()])]
    for lane in HOW:
        c = 'Cap ' + lane
        counted(c, lane, t, health='Plant ' + lane)
        t.scripts += [Script('Test - owner ' + lane, [('NAMED_OWNED_BY_PLAYER', m.player('p1'), 'Plant ' + lane)],
                             [('INCREMENT_COUNTER', 1000, c)], once=False),
                      Script('Test - alive ' + lane, [('NAMED_NOT_DESTROYED', 'Man ' + lane)],
                             [('INCREMENT_COUNTER', 10000, c)], once=False)]
    t.expect = [(lane, 30, '==', 1050, 34) for lane in HOW]
    t.bench = [('bench_watch', dict(seconds=36, every=1, sheet=False, lines=4))]
    return t


CHECKS = {'engine_capture': {'a': check}, 'engine_capoff': {'a': check_off}}
