"""C: Value=1.0/0.1 with fixed Above=true and 4:8 Guardians.

Pre-run s40 prediction: 1.0 home/total/player=4/4/8, 0.1=0/4/8.
Measured 2026-11-13, one PASS each: 1.0 s1-s46=4/4/8;
0.1 s1-s13=4/4/8, s14=2/4/8, s15-s46=0/4/8.
Only published sites, roles, units, players and facts are consumed.
See work/re/c_powervalue_report.md for predictions and engine evidence.
"""
from parts import Script, Test, counted, square


def check(m):
    t = Test()
    t.areas['Power value home'] = square(*m.site('east base'), 450)
    t.scripts.append(Script('Power value reveal', [], [('MAP_REVEAL_ALL_PERM', m.player('p1'))]))
    t.scripts.append(Script('Power value keep target', [],
        [('UNIT_SET_HEALTH', m.role('player target').name, 100.0)], once=False))
    tank, = m.cnv_units
    for key, label, area, player, expected in (
            ('CPV_home', '坦克在家', 'Power value home', 's1', m.facts['home at 40']),
            ('CPV_total', '坦克总数', None, 's1', 4),
            ('CPV_enemy', '玩家坦克', None, 'p1', 8)):
        counted(key, label, t, template=tank, area=area, player=m.player(player))
        t.expect.append((label, 40, '==', expected, 41))
    t.bench = [('bench_watch', dict(seconds=45, every=1, sheet=False, lines=3))]
    return t


CHECKS = {name: {'a': check} for name in ('aipval1', 'aipval01')}
