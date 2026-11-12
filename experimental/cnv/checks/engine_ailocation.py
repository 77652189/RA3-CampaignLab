"""AITargetingHeuristic.Location: count arrivals at the published land/water targets.

Targets stay at full health. At s40 the selected plant must have all four
Twinblades nearby and the other none. Engine E81, one run each, all PASS:
Land and Water Land: land=4/water=0 from s13-s51; Water: 0/4 from s16-s51.
The default simulator has 0/0 for Water (strict xfail); Location stays a gap.
Evidence and limits: work/re/e_location_e81.md.
"""
from parts import Script, Test, counted, square


def a(m):
    t = Test()
    t.scripts.append(Script('Location reveal', [], [('MAP_REVEAL_ALL_PERM', m.player('p1'))]))
    t.scripts.append(Script('Location keep', [], [
        ('UNIT_SET_HEALTH', m.role(role).name, 100.0) for role in ('land', 'water')], once=False))
    for role, label in (('land', '到陆厂'), ('water', '到水厂')):
        o = m.find(m.role(role).name)
        area = 'Location ' + role
        t.areas[area] = square(o.x, o.y, 340.0)
        counted('Location_' + role, label, t, template=m.cnv_units[0], area=area, player=m.player('s1'))
        t.expect.append((label, 40, '==', 4 * m.facts['expect ' + role], 41))
    t.bench = [('bench_watch', dict(seconds=50, every=1, sheet=False, lines=2))]
    return t


CHECKS = {name: {'a': a} for name in ('ailocland', 'ailocwater', 'ailocboth')}
