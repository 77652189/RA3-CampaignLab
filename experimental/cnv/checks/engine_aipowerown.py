"""C: own-defense inclusion, measured s40 home/total/enemy/tower=4/4/8/1 vs 0/4/8/1.

Only IncludeOwnDefenses changes; see work/re/c_powerown_report.md.
Measured 2026-11-13: off s1-s46=4/4/8/1; on s15-s46=0/4/8/1.
Consumes published mission sites, roles, players, units and facts.
"""
from parts import Script, Test, counted, square


def check(m):
    t = Test()
    t.areas['Own defense home'] = square(*m.site('east base'), 450)
    t.scripts.append(Script('Own defense reveal', [], [('MAP_REVEAL_ALL_PERM', m.player('p1'))]))
    t.scripts.append(Script('Own defense keep target', [],
        [('UNIT_SET_HEALTH', m.role('player target').name, 100.0)], once=False))
    tank, = m.cnv_units
    for key, label, template, area, player, expected in (
            ('CPO_home', '坦克在家', tank, 'Own defense home', 's1', m.facts['home at 40']),
            ('CPO_total', '坦克总数', tank, None, 's1', 4),
            ('CPO_enemy', '玩家坦克', tank, None, 'p1', 8),
            ('CPO_tower', '己方防御塔', m.facts['defense template'], None, 's1', 1)):
        counted(key, label, t, template=template, area=area, player=m.player(player))
        t.expect.append((label, 40, '==', expected, 41))
    t.bench = [('bench_watch', dict(seconds=45, every=1, sheet=False, lines=4))]
    return t


CHECKS = {name: {'a': check} for name in ('aipownoff', 'aipownon')}
