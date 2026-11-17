"""SortByDistance: named candidate departure, latched at script-frame precision.

First departure identity: 0 none, 1 far, 2 near, 3 both in the same frame.
Far is inserted first; near is closer to the fixed enemy structure but farther
from the AI yard. Prediction: off sends far, on sends near. An 80-unit square
around each initial position observes departure, not actual team membership.
No exact distance metric, tie rule or production/release path is established.

RESULTS (2026-11-11): aisort0:a / aisort1:a both PASS, 5 assertions each.
Both candidates remain in place through s9. Off: far first at frame 177,
near stays through s45. On: near first at frame 178, far stays through s45.
INFERRED: the switch changes selection toward the tactical target; actual
dynamic-team membership remains a gap. See work/re/c_sort_report.md.
"""
from model import Script, Test, counted, square


def a(m):
    t = Test()
    t.scripts += [Script('Sort - reveal', [], [('MAP_REVEAL_ALL_PERM', m.player('p1'))]),
                  Script('Sort - clock', [], [('INCREMENT_COUNTER', 1, 'CNV_SD_Clock')], once=False)]
    outside = []
    for identity, name, pos in m.cnv_candidates:
        area = f'CNV Sort {identity}'
        t.areas[area] = square(*pos, m.facts['departure radius'])
        counted(f'CNV_SD_{identity}', '远在原位' if identity == 'far' else '近在原位',
                t, named=name, area=area)
        outside.append(('NAMED_OUTSIDE_AREA', name, area))
    t.counters += [('CNV_SD_First', '首离身份'), ('CNV_SD_Frame', '首离帧')]
    # Evaluate the simultaneous case before either singleton: script order
    # cannot turn a same-frame departure into a false winner.
    for identity, conditions in ((3, outside), (1, outside[:1]), (2, outside[1:])):
        t.scripts.append(Script(f'Sort - first {identity}',
                                [('COUNTER', 'CNV_SD_First', 2, 0), *conditions],
                                [('SET_COUNTER', 'CNV_SD_First', identity),
                                 ('SET_COUNTER_TO_COUNTER', 'CNV_SD_Frame', 'CNV_SD_Clock')]))
    near = m.facts['sort by distance']
    t.expect = [('远在原位', 1, '==', 1, 9), ('近在原位', 1, '==', 1, 9),
                ('首离身份', 35, '==', 2 if near else 1, 36),
                ('远在原位', 35, '==', near, 36), ('近在原位', 35, '==', 1 - near, 36)]
    t.bench = [('bench_watch', dict(seconds=44, every=1, sheet=False, lines=4))]
    return t


CHECKS = {name: {'a': a} for name in ('aisort0', 'aisort1')}
