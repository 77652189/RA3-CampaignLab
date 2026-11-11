"""Creation-veterancy upgrades each add one level (retail BaseVehicle), capped at 4.

PREDICT: one HEROIC creation grant does not itself make a heroic unit; three
distinct creation upgrades do. Repeating an already-held upgrade adds no level.
Read the mirage's heroic WEAPON_UPGRADED_01 bit, with no combat or experience.
Bench 2026-11-10 PASS: s1-s4 0/0/1/0, s5-s13 0/1/1/0.
These are heroic-state booleans, not numeric rank readings.
"""
from maps import probe_range
from parts import Mission, Script, Test, status, counted

CREATION = tuple('Upgrade_CreationVeterancy_' + x for x in ('VETERAN', 'ELITE', 'HEROIC'))


def mission():
    m = Mission(name='CampLevel', map=probe_range, units=[])
    for lane in ('base', 'high', 'order', 'removed'):
        m.put('AlliedAntiVehicleVehicleTech3', lane + ' gun', role=lane,
              name='Level ' + lane)
    return m


def check(m):
    t = Test()
    grant = lambda lane, up: ('NAMED_RECEIVE_UPGRADE', up, m.role(lane).name)
    t.scripts = [Script('Test - start', [], [
        ('MAP_REVEAL_ALL_PERM', m.player('p1')),
        ('SET_MILLISECOND_TIMER', 'Level late', 6.0),
        grant('high', CREATION[2]),
        *[grant('order', up) for up in CREATION],
        *[grant('removed', CREATION[0]) for _ in range(3)]]),
        Script('Test - late', [('TIMER_EXPIRED', 'Level late')], [
            grant('high', CREATION[0]), grant('high', CREATION[1])])]
    for lane in ('base', 'high', 'order', 'removed'):
        c = 'Level ' + lane
        t.counters.append((c, lane + ' rank'))
        t.scripts += [
            Script('Test - zero ' + lane, [], [('SET_COUNTER', c, 0)], once=False),
            Script('Test - heroic ' + lane,
                   [('UNIT_HAS_OBJECT_STATUS', m.role(lane).name, status('WEAPON_UPGRADED_01'))],
                   [('SET_COUNTER', c, 1)], once=False)]
    t.expect = [('base rank', 2, '==', 0, 12), ('high rank', 2, '==', 0, 4),
                ('high rank', 8, '==', 1, 12), ('order rank', 2, '==', 1, 12),
                ('removed rank', 2, '==', 0, 12)]
    t.bench = [('bench_watch', dict(seconds=12.0, every=.5, sheet=False, lines=4))]
    return t


MISSION = {'engine_levelup': mission}
CHECKS = {'engine_levelup': {'a': check}}


def damage_mission():
    m = mission()
    m.name = 'CampLevelD'
    for lane in ('base', 'high', 'order', 'removed'):
        m.put('JapanAntiVehicleVehicleTech1', lane + ' gun', 0, 100,
              side='s1', role=lane + ' target', name='Level target ' + lane)
    return m


def damage_check(m):
    """PREDICT: one shot, 200/250/250/312.5 damage into 380 HP, 100% armor.

    Creation grants add the veteran DAMAGE_MULT125 as well as the heroic gun.
    Direct veterancy upgrades (engine_statusbits a) only selected the gun.
    Bench 11-10 PASS: s5-s15 47/34/34/17, with no Tsunami healing.
    """
    t = Test()
    lanes = ('base', 'high', 'order', 'removed')
    start = [('MAP_REVEAL_ALL_PERM', m.player('p1')),
             ('SET_MILLISECOND_TIMER', 'Level fire', 6.0),
             ('SET_MILLISECOND_TIMER', 'Level stop', 6 + 4 / 15)]
    fire, stop = [], []
    for n, lane in enumerate(lanes):
        gun, target = m.role(lane).name, m.role(lane + ' target').name
        start += [('UNIT_CHANGE_OBJECT_STATUS', name, 'NO_ATTACK', 1) for name in (gun, target)]
        start += [('NAMED_RECEIVE_UPGRADE', up, gun) for up in CREATION[:n]]
        fire += [('UNIT_CHANGE_OBJECT_STATUS', gun, 'NO_ATTACK', 0), ('NAMED_ATTACK_NAMED', gun, target)]
        stop += [('UNIT_CHANGE_OBJECT_STATUS', gun, 'NO_ATTACK', 1)]
        counted('Level hp ' + lane, lane + ' HP', t, health=target)
    t.scripts[:0] = [Script('Test - start', [], start),
                     Script('Test - fire', [('TIMER_EXPIRED', 'Level fire')], fire),
                     Script('Test - stop', [('TIMER_EXPIRED', 'Level stop')], stop)]
    t.expect = [(lane + ' HP', 10, '==', hp, 14) for lane, hp in zip(lanes, (47, 34, 34, 17))]
    t.bench = [('bench_watch', dict(seconds=14.0, every=.5, sheet=False, lines=4))]
    return t


MISSION['engine_leveldamage'] = damage_mission
CHECKS['engine_leveldamage'] = {'a': damage_check}


def health_mission():
    m = mission()
    m.name = 'CampLevelH'
    return m


def health_check(m):
    """PREDICT: 500/500/625/625 max HP leaves 80/80/84/84% after NAMED_DAMAGE 100.

    Freeze each reading immediately after script damage in the same script, before
    heroic AutoHeal can tick. No enemy, weapon, armor or combat experience involved.
    Only promotion from full health is measured; injured promotion remains unmodeled.
    Bench 2026-11-10 PASS: frozen counters s4-s14 80/80/84/84.
    """
    t = Test()
    start = [('MAP_REVEAL_ALL_PERM', m.player('p1')),
             ('SET_MILLISECOND_TIMER', 'Level hurt', 6.0)]
    hurt = []
    for n, lane in enumerate(('base', 'high', 'order', 'removed')):
        name, counter = m.role(lane).name, 'Level frozen ' + lane
        start += [('UNIT_CHANGE_OBJECT_STATUS', name, 'NO_ATTACK', 1)]
        start += [('NAMED_RECEIVE_UPGRADE', up, name) for up in CREATION[:n]]
        start += [('SET_COUNTER', counter, -1)]
        hurt += [('NAMED_DAMAGE', name, 100),
                 ('SET_UNIT_HEALTH_PERCENTAGE_TO_COUNTER', name, counter)]
        t.counters.append((counter, lane + ' frozen HP'))
    t.scripts = [Script('Test - start', [], start),
                 Script('Test - freeze damage', [('TIMER_EXPIRED', 'Level hurt')], hurt)]
    t.expect = [(lane + ' frozen HP', 8, '==', hp, 12)
                for lane, hp in zip(('base', 'high', 'order', 'removed'), (80, 80, 84, 84))]
    t.bench = [('bench_watch', dict(seconds=12.0, every=.5, sheet=False, lines=4))]
    return t


MISSION['engine_levelhealth'] = health_mission
CHECKS['engine_levelhealth'] = {'a': health_check}
