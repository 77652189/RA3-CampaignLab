"""C active-queue KindOf match/nonmatch probe; prediction recorded before runs.

At s40 matching FS_POWER sends four helicopters to the target; FS_BARRACKS
keeps four home. Both must complete at least two power plants, and retain
one yard. See work/re/c_buildkind_report.md for observations and limits.
Measured: both PASS, s40 target/home/plants/yard=4/0/4/1 and 0/4/4/1.
"""
from parts import Script, Test, counted, square


def check(m):
    t = Test()
    t.scripts.append(Script('Kind reveal', [], [('MAP_REVEAL_ALL_PERM', m.player('p1'))]))
    t.scripts.append(Script('Kind keep', [], [
        ('UNIT_SET_HEALTH', m.role(role).name, 100.0) for role in ('land', 'water')], once=False))
    target = m.find(m.role('land').name)
    t.areas['Kind target'] = square(target.x, target.y, 340)
    x, y = m.site('east base')
    t.areas['Kind home'] = [(x - 300, y - 400), (x + 300, y - 400),
                            (x + 300, y + 450), (x - 300, y + 450)]
    for key, label in (('target', '到陆厂'), ('home', '在家')):
        counted('Kind_' + key, label, t, template=m.cnv_units[0],
                area='Kind ' + key, player=m.player('s1'))
        t.expect.append((label, 40, '==', m.facts['expect ' + key], 41))
    counted('Kind_plants', '电厂数', t, template='AlliedPowerPlant', player=m.player('s1'))
    counted('Kind_yards', '基地数', t, template='AlliedConstructionYard', player=m.player('s1'))
    t.expect += [('电厂数', 40, '>=', 2, 41), ('基地数', 40, '==', 1, 41)]
    t.bench = [('bench_watch', dict(seconds=50, every=1, sheet=False, lines=4))]
    return t


CHECKS = {name: {'a': check} for name in ('aibkindyes', 'aibkindno')}
