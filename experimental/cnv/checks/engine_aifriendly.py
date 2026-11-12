"""E85 FriendlyUnit: count arrivals and surviving MCV targets through Mission.

Prediction s40: aifriend friendly/enemy=4/0, aienemy=0/4; MCVs=2.
StaticDefense and SAME_PLAYER follow SDK consumers; only HeuristicType changes.
No internal target score is an engine observation. See work/re/e_friendly_e85.md.
E85 engine: both builds FAIL their original prediction; s40 arrivals=0/0,
MCVs alive=1/1 (friendly s1-s55, enemy s1-s71). Predictions remain unchanged.
The pair cannot distinguish target selection from StaticDefense recruitment.
"""
from parts import Script, Test, counted, square


def a(m):
    t = Test()
    t.scripts.append(Script('Friendly reveal', [], [('MAP_REVEAL_ALL_PERM', m.player('p1'))]))
    t.scripts.append(Script('Friendly keep', [], [
        ('UNIT_SET_HEALTH', m.role(role).name, 100.0) for role in ('friendly', 'enemy')], once=False))
    for role, label in (('friendly', '到友车'), ('enemy', '到敌车')):
        o = m.find(m.role(role).name)
        area = 'Friendly ' + role
        t.areas[area] = square(o.x, o.y, 340.0)
        counted('Friendly_' + role, label, t, template=m.cnv_units[0], area=area, player=m.player('s1'))
        t.expect.append((label, 40, '==', m.facts['expect ' + role], 41))
    for role, label, player in (('friendly', '友车存活', 's1'), ('enemy', '敌车存活', 'p1')):
        counted('Friendly_alive_' + role, label, t, template='AlliedMCV', player=m.player(player))
        t.expect.append((label, 40, '==', 1, 41))
    t.bench = [('bench_watch', dict(seconds=54, every=1, sheet=False, lines=4))]
    return t


CHECKS = {name: {'a': a} for name in ('aifriend', 'aienemy')}
