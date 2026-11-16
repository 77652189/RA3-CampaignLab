"""EnemyGarrison occupancy/ownership guard; native tgt records judge selection.

Prediction: occupied enemy row house selected; same-site ordinary enemy plant
not eligible. Both NamedObject slots identify the surviving placed control.
Evidence: work/re/c_enemygarr_report.md.
"""
from model import status
from parts import Test, Script


def a(m):
    t = Test()
    control, occupant = (m.role(r).name for r in ('garr control', 'garr occupant'))
    names = [m.role(r).name for r in ('plant', 'barracks', 'tank')]
    names += [m.role(f'ai guardian {i}').name for i in range(1, 5)]
    names += [control, occupant]
    t.scripts.append(Script('EGarr keep', [],
        [('UNIT_SET_HEALTH', n, 100.0) for n in names], once=False))
    t.scripts.append(Script('EGarr reveal', [], [('MAP_REVEAL_ALL_PERM', m.player('p1'))]))
    rows = [('control alive', ('NAMED_NOT_DESTROYED', control)),
            ('enemy owner', ('NAMED_OWNED_BY_PLAYER', m.player('p1'), control)),
            ('occupant inside', ('UNIT_HAS_OBJECT_STATUS', occupant, status('ENCLOSED')))]
    for i, (label, cond) in enumerate(rows):
        c = f'EGarr{i}'
        t.counters.append((c, label))
        t.scripts.append(Script(c + ' reset', [], [('SET_COUNTER', c, 0)], once=False))
        t.scripts.append(Script(c + ' read', [cond], [('SET_COUNTER', c, 1)], once=False))
        t.expect.append((label, 1, '==', int(i != 2 or m.facts['enemy garrison']), 15))
    t.bench = [('bench_watch', dict(seconds=15, every=1, sheet=False, lines=3))]
    return t


CHECKS = {build: {'a': a} for build in ('aiegarron', 'aiegarroff')}
