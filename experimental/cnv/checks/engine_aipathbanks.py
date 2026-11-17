"""C: condition selection between physically disconnected river banks.

Before running: land control stays off the far bank, amphibious control arrives.
Opening prediction at s22-24: NORMAL power=1/barracks=0, SUPERSONIC power=0/
barracks=1. Physical controls are independent of the opening heuristic. Equal
opening readings leave condition/endpoint/path-result semantics unresolved;
see work/re/c_pathbanks_report.md. No coverage promotion without a split.
Bench 2026-11-13: both builds give barracks/power=1/0 at s22-24;
both physical counters are 1 (alive, not arrived) at s40-44. Both checks
FAIL their pre-run hypotheses. The amphibious positive control is unproven.
The early-registration follow-up aipclandy also yields 1/0 and 1/1: its
opening still returns before bases are available. See work/re/c_pathready_report.md.
"""
from parts import Script, Test, counted, square


def check(m):
    t = Test()
    orders = [('MAP_REVEAL_ALL_PERM', m.player('p1'))]
    for role in ('land control', 'amphib control'):
        orders += m.order('move', [m.role(role).name], m.mark('crossing goal'))
    t.scripts.append(Script('Test - crossing', [], orders))
    area = 'CNV PC Arrival'
    t.areas[area] = square(*m.point('crossing goal'), 160)
    for counter, label, template in (
            ('CNV_PC_Barracks', '兵营', 'AlliedBarracks'),
            ('CNV_PC_Power', '电厂', 'AlliedPowerPlant')):
        counted(counter, label, t, template=template, player=m.player('s1'))
    # Pack survival (1) and arrival (10) into one line per control.
    for counter, label, role in (
            ('CNV_PC_Land', '陆路', 'land control'),
            ('CNV_PC_Amph', '两栖', 'amphib control')):
        name = m.role(role).name
        t.counters.append((counter, label))
        t.scripts += [
            Script(f'Test - {counter} zero', [], [('SET_COUNTER', counter, 0)], once=False),
            Script(f'Test - {counter} alive', [('NAMED_NOT_DESTROYED', name)],
                   [('INCREMENT_COUNTER', 1, counter)], once=False),
            Script(f'Test - {counter} arrived', [('NAMED_INSIDE_AREA', name, area)],
                   [('INCREMENT_COUNTER', 10, counter)], once=False)]
    amphib = m.facts['path amphibious']
    t.expect = [('兵营', 22, '==', int(amphib), 25),
                ('电厂', 22, '==', int(not amphib), 25),
                ('陆路', 40, '==', 1, 45), ('两栖', 40, '==', 11, 45)]
    t.bench = [('bench_watch', dict(seconds=46, every=1, sheet=False, lines=4))]
    return t


CHECKS = {name: {'a': check} for name in ('aipcland', 'aipcamph', 'aipclandy', 'aipcamphy')}
