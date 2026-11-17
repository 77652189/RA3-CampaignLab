"""C: IntervalHeuristic.CountFrom MAP_START/AI_START named controls.

Same map, personality, army and s10 wake; only CountFrom changes.
Pre-run prediction home/total: s24 both 4/4; s32 map=0/4, ai=4/4;
s42 both 0/4. IntervalTime=25s/ActiveTime=30s. First window only,
repeated cycling and exact evaluation frames remain gap.
Measured 2026-11-13, one PASS each: map home=4 s1-27 then 0 s28-46;
ai home=4 s1-37, 2 s38, 0 s39-46; total=4 throughout both runs.
See work/re/c_intervalfrom_report.md. Uses only published mission data.
"""
from parts import Script, Test, counted, square


def check(m):
    t = Test()
    t.areas['Interval home'] = square(*m.site('east base'), 450)
    t.scripts.append(Script('Interval reveal', [], [('MAP_REVEAL_ALL_PERM', m.player('p1'))]))
    t.scripts.append(Script('Interval keep target', [],
        [('UNIT_SET_HEALTH', m.role('player target').name, 100.0)], once=False))
    tank, = m.cnv_units
    counted('CIF_home', '坦克在家', t, template=tank, area='Interval home', player=m.player('s1'))
    counted('CIF_total', '坦克总数', t, template=tank, player=m.player('s1'))
    for second, home in ((24, 4), (32, m.facts['home at 32']), (42, 0)):
        t.expect += [('坦克在家', second, '==', home, second + 1),
                     ('坦克总数', second, '==', 4, second + 1)]
    t.bench = [('bench_watch', dict(seconds=45, every=1, sheet=False, lines=2))]
    return t


CHECKS = {name: {'a': check} for name in ('aiintmap', 'aiintai')}
