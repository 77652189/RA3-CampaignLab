"""C: enemy-defense inclusion, measured s40 0/8/4/1 vs 8/8/4/1.

Only IncludeEnemyDefenses changes; see work/re/c_powerenemy_report.md.

Consumes published mission sites, roles, players, units and facts only.
"""
from parts import Script, Test, counted, square


def check(m):
    t = Test()
    t.areas['Enemy defense home'] = square(*m.site('east base'), 450)
    t.scripts.append(Script('Enemy defense reveal', [], [('MAP_REVEAL_ALL_PERM', m.player('p1'))]))
    t.scripts.append(Script('Enemy defense keep target', [],
        [('UNIT_SET_HEALTH', m.role('player target').name, 100.0)], once=False))
    tank, = m.cnv_units
    for key, label, template, area, player, expected in (
            ('CPE_home', '坦克在家', tank, 'Enemy defense home', 's1', m.facts['home at 40']),
            ('CPE_total', '坦克总数', tank, None, 's1', 8),
            ('CPE_enemy', '玩家坦克', tank, None, 'p1', 4),
            ('CPE_tower', '玩家防御塔', m.facts['defense template'], None, 'p1', 1)):
        counted(key, label, t, template=template, area=area, player=m.player(player))
        t.expect.append((label, 40, '==', expected, 41))
    t.bench = [('bench_watch', dict(seconds=45, every=1, sheet=False, lines=4))]
    return t


CHECKS = {name: {'a': check} for name in ('aipenoff', 'aipenon')}
