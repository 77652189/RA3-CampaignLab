"""Initial OilDerrick ownership: below75 / above75 / below125 home counts.

Expectations: the mission's cnv_tech_home (share = owned / 4 x 8 players, B 11-25 after C's two runs read 4/0/4).
Check consumes published mission roles.
"""
from parts import Script, Test, counted, square


def check(m):
    t = Test()
    player = m.player('s1')
    t.areas['Tech home'] = square(*m.site('east base'), 450)
    t.scripts.append(Script('Tech reveal', [], [('MAP_REVEAL_ALL_PERM', m.player('p1'))]))
    t.scripts.append(Script('Tech keep target', [],
        [('UNIT_SET_HEALTH', m.role('player target').name, 100.0)], once=False))
    for i, (unit, expected) in enumerate(zip(m.cnv_units, m.cnv_tech_home)):
        label = ('低阈下', '低阈上', '高阈下')[i]
        counted(f'Tech_home{i}', label, t, template=unit, area='Tech home', player=player)
        t.expect.append((label, 40, '==', expected, 41))
    counted('Tech_owned', '油井数', t, template='OilDerrick', player=player)
    t.expect.append(('油井数', 1, '==', m.facts['tech own'], 41))
    t.bench = [('bench_watch', dict(seconds=45, every=1, sheet=False, lines=4))]
    return t


CHECKS = {name: {'a': check} for name in ('aitechlow', 'aitechhigh', 'aitechsl', 'aitechsh', 'aitechsn')}
