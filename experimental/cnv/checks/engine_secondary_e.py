"""E174 prediction: engineer secondary adds the retail Repair upgrade to host.

Only the listener include is removed in the control. Sample at frames 60,
180 and 360; enter instantly at 90 and exit at 240. Each snapshot encodes
host alive=1, crew alive=2, crew ENCLOSED=4, player's Repair upgrade=8.
Prediction on: 3/15/3; off: 3/7/3. These are module-consumption observations,
not a claim about all passengers, weapon updates, visuals or exact timing.
See work/re/e174_secondary.md for measurements and remaining gaps.
"""
from model import Script, Test
from checks import engine_scripts8 as s8


def check(m):
    t = Test()
    host, crew = m.role('host').name, m.role('crew').name
    t.counters = [('E174Frame', '完成帧'), ('E174Before', '进入前'),
                  ('E174Inside', '驻留时'), ('E174After', '退出后')]
    t.scripts = [
        Script('Test - clock', [('COUNTER', 'E174Frame', 0, 360)],
               [('INCREMENT_COUNTER', 1, 'E174Frame')], once=False),
        Script('Test - start', [], [('MAP_REVEAL_ALL_PERM', m.player())]),
        Script('Test - enter', [('COUNTER', 'E174Frame', 2, 90)],
               [('NAMED_GARRISON_SPECIFIC_BUILDING_INSTANTLY', crew, host)]),
        Script('Test - exit', [('COUNTER', 'E174Frame', 2, 240)],
               [('NAMED_EXIT_BUILDING', crew)])]
    for frame, counter in [(60, 'E174Before'), (180, 'E174Inside'), (360, 'E174After')]:
        for bit, cond in [
            (1, ('NAMED_NOT_DESTROYED', host)),
            (2, ('NAMED_NOT_DESTROYED', crew)),
            (4, ('UNIT_HAS_OBJECT_STATUS', crew, 'ENCLOSED')),
            (8, ('PLAYER_HAS_NUM_UNITS_WITH_UPGRADE', m.player(), 1, 'Uprade_IFV_Repair'))]:
            t.scripts.append(Script(f'Test - {counter} {bit}',
                                    [('COUNTER', 'E174Frame', 2, frame), cond],
                                    [('INCREMENT_COUNTER', bit, counter)]))
    t.expect = [('完成帧', 0, 'ever==', 360), ('进入前', 0, 'ever==', 3),
                ('驻留时', 0, 'ever==', 15 if m.facts['enabled'] else 7),
                ('退出后', 0, 'ever==', 3)]
    t.bench = [('bench_watch', dict(seconds=65, every=1, sheet=False, lines=4))]
    return t


def repair(m):
    """engine_secondrep_e: the engineer in at 1 s, the three Guardians to 50 % at 2 s; 血N / 血F / 血C their health %,
    态 = 1 crew ENCLOSED + 10 the host's Uprade_IFV_Repair. Before the bench (the weapon's data, one 5 point shot a
    FiringDuration of 0.1 s): N back to 100 within about 7 s, F and C stay 50."""
    t = Test()
    crew = m.role('crew').name
    s8.at(t, 'in', 1.0, [('NAMED_GARRISON_SPECIFIC_BUILDING_INSTANTLY', crew, m.role('host').name),
                         ('MAP_REVEAL_ALL_PERM', m.player())])
    s8.at(t, 'hurt', 2.0, [('UNIT_SET_HEALTH', m.role(r).name, 50.0) for r in 'NFC'])
    for r in 'NFC':
        t.counters.append(('E174Hp' + r, '血' + r))
        t.scripts.append(Script('Test - E174 hp ' + r, [],
                                [('SET_UNIT_HEALTH_PERCENTAGE_TO_COUNTER', m.role(r).name, 'E174Hp' + r)], once=False))
    s8.total(t, 'E174State', '态', [(1, ('UNIT_HAS_OBJECT_STATUS', crew, 'ENCLOSED')),
                                    (10, ('PLAYER_HAS_NUM_UNITS_WITH_UPGRADE', m.player(), 1, 'Uprade_IFV_Repair'))])
    s8.watch(t, 14.0)
    return t


def turret(m):
    """engine_turretgar_e: at 1 s c, d put in, a, b, e sent in (walking); 4 s worn hurt 900 (10 %); 7 s worn killed,
    blast hit 5000; 10 s a and b told out. 驻 = a / b ENCLOSED 1 / 10 + cap CONTAINER_OCCUPIED 100; 敌 = e ENCLOSED 1 +
    foe CONTAINER_OCCUPIED 10 + e alive 100; 死 = c ENCLOSED 1 + c alive 10 + d ENCLOSED 100 + d alive 1000; 血 = worn's
    health %. From the data: 驻 101 (one seat), 0 after 10 s; 敌 100 (no enemies inside); 死 1111, kept at 10 %
    (GARRISONABLE_UNTIL_DESTROYED), 0 once both turrets die (KillPassengersOnDeath)."""
    t = Test()
    n = {r: m.role(r).name for r in ('cap', 'foe', 'worn', 'blast', 'a', 'b', 'c', 'd', 'e')}
    put, walk = 'NAMED_GARRISON_SPECIFIC_BUILDING_INSTANTLY', 'NAMED_GARRISON_SPECIFIC_BUILDING'
    s8.at(t, 'in', 1.0, [(put, n['c'], n['worn']), (put, n['d'], n['blast']), (walk, n['a'], n['cap']),
                         (walk, n['b'], n['cap']), (walk, n['e'], n['foe']), ('MAP_REVEAL_ALL_PERM', m.player())])
    s8.at(t, 'hurt', 4.0, [('NAMED_DAMAGE', n['worn'], 900)])
    s8.at(t, 'kill', 7.0, [('NAMED_KILL', n['worn']), ('NAMED_DAMAGE', n['blast'], 5000)])
    s8.at(t, 'out', 10.0, [('NAMED_EXIT_BUILDING', n['a']), ('NAMED_EXIT_BUILDING', n['b'])])

    def has(r, bit):
        return ('UNIT_HAS_OBJECT_STATUS', n[r], bit)
    s8.total(t, 'E239Cap', '驻', [(1, has('a', 'ENCLOSED')), (10, has('b', 'ENCLOSED')),
                                  (100, has('cap', 'CONTAINER_OCCUPIED'))])
    s8.total(t, 'E239Foe', '敌', [(1, has('e', 'ENCLOSED')), (10, has('foe', 'CONTAINER_OCCUPIED')),
                                  (100, ('NAMED_NOT_DESTROYED', n['e']))])
    s8.total(t, 'E239Die', '死', [(1, has('c', 'ENCLOSED')), (10, ('NAMED_NOT_DESTROYED', n['c'])),
                                  (100, has('d', 'ENCLOSED')), (1000, ('NAMED_NOT_DESTROYED', n['d']))])
    t.counters.append(('E239Hp', '血'))
    t.scripts.append(Script('Test - E239 hp', [], [('SET_UNIT_HEALTH_PERCENTAGE_TO_COUNTER', n['worn'], 'E239Hp')],
                            once=False))
    s8.watch(t, 14.0)
    return t


CHECKS = {name: {'a': check} for name in ('engine_secondon_e', 'engine_secondoff_e')}
CHECKS['engine_secondrep_e'] = {'r': repair}
CHECKS['engine_turretgar_e'] = {'g': turret}
