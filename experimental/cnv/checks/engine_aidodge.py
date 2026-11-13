"""DodgeThreats on/off, native precision-strike beacon, recruited Hunt warriors.

Prediction: both warriors fight inside the 150-half-side square before s30;
with DodgeThreats on at least one leaves during s30..34, off both stay.
Conscripts are kept healthy; powers and injured pullback are off. The beacon
dispatches no damage or push (the ordinary infantry fight still deals damage).
This square tests a movement difference, not the exact 200 safety radius.

MEASURED: named beacon on/off both present, two living warriors; on leaves
(frame 468: near 1, 479: 0), off stays (456..501: near 2). The bench capture
seconds drift against the frame counter: on's automatic seconds-window verdict
is FAIL, off PASS. Keep that diagnostic failure visible; replay by game frames
in tests/test_ai_dodge.py. A clock-stable engine acceptance check remains a gap,
the bounded single-beacon consumer is replayed there. Exact timing, safety-circle
boundaries, general filters and multi-threat choice remain gaps (work/re/e116_dodge.md).
"""
from model import Script, Test, counted, square


def probe(m):
    t = Test()
    s1 = m.player('s1')
    warrior = m.cnv_units[0]
    at = m.facts['threat at']
    end = at + m.facts['threat lifetime']
    area = 'CNV Dodge Sample'
    t.areas[area] = square(*m.point('dodge spot'), m.facts['sample half size'])
    t.scripts += [Script('Dodge - reveal', [], [('MAP_REVEAL_ALL_PERM', m.player('p1'))]),
                  Script('Dodge - frame', [], [('INCREMENT_COUNTER', 1, 'CNV_Dodge_Frame')], once=False),
                  Script('Dodge - health', [],
                         [('UNIT_SET_HEALTH', r.name, 100.0) for r in m.roles('conscript')], once=False)]
    t.counters.append(('CNV_Dodge_Frame', '帧数'))
    counted('CNV_Dodge_Own', '造出', t, template=warrior, player=s1)
    counted('CNV_Dodge_Near', '范围', t, template=warrior, player=s1, area=area)
    # The native beacon's player ownership count stayed 0 on this probe.
    # Query the named object itself, so 0 cannot be mistaken for no threat.
    t.counters.append(('CNV_Dodge_Beacon', '威胁'))
    beacon = m.cnv_named['beacon']
    t.scripts += [Script('Dodge - beacon alive', [('NAMED_NOT_DESTROYED', beacon)],
                         [('SET_COUNTER', 'CNV_Dodge_Beacon', 1)], once=False),
                  Script('Dodge - beacon gone', [('NAMED_DESTROYED', beacon)],
                         [('SET_COUNTER', 'CNV_Dodge_Beacon', 0)], once=False)]
    t.expect += [('造出', at - 3, '==', 2, end), ('范围', at - 3, '==', 2, at - 1),
                 ('威胁', at, 'ever>=', 1, end),
                 ('范围', at + 1, 'ever<=' if m.facts['dodge enabled'] else '==',
                  1 if m.facts['dodge enabled'] else 2, end)]
    t.bench = [('bench_watch', dict(seconds=end + 3, every=1, sheet=False, lines=4))]
    return t


CHECKS = {name: {'r': probe} for name in ('aidodgeon', 'aidodgeoff')}


def timing(m):
    """Fixed 0/2 second contrast, latched in game frames (work/re/e117_dodge_clock.md).

    Prediction: both start with two living warriors in the same square; zero
    leaves sooner after the beacon. Leaving includes walking time, so neither
    latch measures the exact reaction frame. Random ranges remain a gap.

    MEASURED: both born f451; zero first leaves f454, two f486; bad stays 0.
    Replay asserts their order, not exact departure frames (model: 475/505).
    """
    t = probe(m)
    frame, born, left, bad = ('CNV_Dodge_Frame', 'CNV_Dodge_Born',
                              'CNV_Dodge_Left', 'CNV_Dodge_Bad')
    live = [('NAMED_NOT_DESTROYED', m.cnv_named['beacon'])]
    t.scripts += [
        Script('Dodge - born latch', live,
               [('SET_COUNTER_TO_COUNTER', born, frame)]),
        Script('Dodge - leave latch', live + [('COUNTER', born, 3, 1),
                                             ('COUNTER', 'CNV_Dodge_Near', 0, 2)],
               [('SET_COUNTER_TO_COUNTER', left, frame)])]
    # Keep the same count scripts, but display the latches within the four-line HUD.
    # Any missing member, or a pre-beacon departure, invalidates this contrast.
    for counter in ('CNV_Dodge_Own', 'CNV_Dodge_Near'):
        for op, value in ((0, 2), (4, 2)):
            t.scripts.append(Script(f'Dodge - prerequisite {counter} {op}',
                [('COUNTER', frame, 3, 405), ('COUNTER', frame, 0, 450),
                 ('COUNTER', counter, op, value)], [('SET_COUNTER', bad, 1)]))
    for op in (0, 4):
        t.scripts.append(Script(f'Dodge - survival {op}', live +
            [('COUNTER', 'CNV_Dodge_Own', op, 2)], [('SET_COUNTER', bad, 1)]))
    t.counters = [(frame, '帧数'), (born, '出现'), (left, '离开'), (bad, '失配')]
    t.expect = [('出现', 1, 'ever>=', 1, 45), ('离开', 1, 'ever>=', 1, 45),
                ('失配', 1, '==', 0, 45)]
    t.bench = [('bench_watch', dict(seconds=45, every=1, sheet=False, lines=4))]
    return t


CHECKS.update({name: {'r': timing} for name in ('aidodgezero', 'aidodgetwo')})
