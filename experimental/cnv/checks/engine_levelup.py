"""Creation-veterancy upgrades each add one level (retail BaseVehicle), capped at 4.

PREDICT: one HEROIC creation grant does not itself make a heroic unit; three
distinct creation upgrades do. Repeating an already-held upgrade adds no level.
Read the mirage's heroic WEAPON_UPGRADED_01 bit, with no combat or experience.
Bench 2026-11-10 PASS: s1-s4 0/0/1/0, s5-s13 0/1/1/0.
These are heroic-state booleans, not numeric rank readings.
"""
from maps import probe_range
from parts import Mission, Script, Test, status

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
