"""TimeSinceLastExpansionHeuristic.Time: retail 60s / 240s, constant control.

Pre-run predictions are retained in the expectations. Only initial, no-expansion
timing is observed; reset after expansion and exact-frame equality remain gaps.
The check reads the mission's published units, roles and site, with no content
imports. See work/re/c_lastexp_report.md for source scope and raw readings.

Measured one run PASS: s19-s62 home=4/4/0, s64-s242=0/4/0,
s244-s345=0/0/0. All twelve predeclared windows pass. Sampling does not
establish the exact activation frame or reset after a real expansion.
"""
from parts import Script, Test, counted, square


def a(m):
    t = Test()
    t.areas['LastExp home'] = square(*m.site('east base'), 450)
    t.scripts.append(Script('LastExp keep target', [],
        [('UNIT_SET_HEALTH', m.role('player target').name, 100.0)], once=False))
    for i, (unit, label) in enumerate(zip(m.cnv_units, ('六十在家', '二四零家', '常量在家'))):
        counted(f'LastExp_home{i}', label, t, template=unit,
                player=m.player('s1'), area='LastExp home')
    for second, values in ((40, (4, 4, 0)), (100, (0, 4, 0)),
                           (220, (0, 4, 0)), (275, (0, 0, 0))):
        for label, value in zip(('六十在家', '二四零家', '常量在家'), values):
            t.expect.append((label, second, '==', value, second + 10))
    t.bench = [('bench_watch', dict(seconds=290, every=2, sheet=False, lines=3))]
    return t


CHECKS = {'ailastexp': {'a': a}}
