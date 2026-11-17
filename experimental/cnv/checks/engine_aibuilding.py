"""IsBuildingHeuristic empty-queue probe, PassIfBuilding true versus false.

Prediction: at s40 false has four Twinblades at the land plant, true four
at home. No money is supplied; the existing AI yard remains standing.
This checks only the idle boundary, not KindOf matching in an active queue.
E83 engine readings: false s13-s51 = 4/0/1; true s1-s51 = 0/4/1
(target/home/yard); both PASS, default simulator replay passes at s40.
Evidence: work/re/e_building_e83.md.
"""
from parts import Script, Test, counted, square


def a(m):
    t = Test()
    t.scripts.append(Script('Building reveal', [], [('MAP_REVEAL_ALL_PERM', m.player('p1'))]))
    t.scripts.append(Script('Building keep', [], [
        ('UNIT_SET_HEALTH', m.role(role).name, 100.0) for role in ('land', 'water')], once=False))
    target = m.find(m.role('land').name)
    t.areas['Building target'] = square(target.x, target.y, 340.0)
    x, y = m.site('east base')
    t.areas['Building home'] = [(x - 300, y - 400), (x + 300, y - 400),
                                (x + 300, y + 450), (x - 300, y + 450)]
    for key, label in (('target', '到陆厂'), ('home', '在家')):
        counted('Building_' + key, label, t, template=m.cnv_units[0],
                area='Building ' + key, player=m.player('s1'))
        t.expect.append((label, 40, '==', m.facts['expect ' + key], 41))
    counted('Building_yards', '基地数', t, template='AlliedConstructionYard', player=m.player('s1'))
    t.expect.append(('基地数', 40, '==', 1, 41))
    t.bench = [('bench_watch', dict(seconds=50, every=1, sheet=False, lines=3))]
    return t


CHECKS = {name: {'a': a} for name in ('aibldtrue', 'aibldfalse')}
