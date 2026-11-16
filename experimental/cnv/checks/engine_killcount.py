"""Native kill/type/player contrast; prediction and evidence: work/re/c_killcount_report.md.

A orders p1's three Guardians to kill two Conscripts and one Guardian; B orders
s5 instead. Untouched other-side crews remain NO_ATTACK. All victims start at
1% HP and cannot attack/move. Script kills a separate untouched Conscript at
15s; another lives. Predict active infantry/tank kills 2/1, inactive infantry 0,
alive mask 240 (inactive three plus untouched control), excluding script death.
Counters start at 77 to prove each query overwrites rather than increments.
"""
from parts import Script, Test, status
from checks import engine_scripts8 as s8


def check(m, active):
    t = Test()
    other = 's5' if active == 'p1' else 'p1'
    roles = [f'{side} {kind} {i}' for side in ('p1', 's5')
             for i in range(3) for kind in ('gun', 'victim')] + ['script', 'alive']
    setup = [('MAP_REVEAL_ALL_PERM', m.player()),
             ('PLAYER_RELATES_PLAYER', m.player(active), m.player('s4'), (0, 0., 'Enemy')),
             ('PLAYER_RELATES_PLAYER', m.player('s4'), m.player(active), (0, 0., 'Enemy'))]
    for role in roles:
        name = m.role(role).name
        setup += [('UNIT_CHANGE_OBJECT_STATUS', name, status('NO_ATTACK'), 1),
                  ('UNIT_CHANGE_OBJECT_STATUS', name, status('IMMOBILE'), 1)]
        if 'victim' in role:
            setup.append(('UNIT_SET_HEALTH', name, 1.))
    t.scripts.append(Script('Test - kill setup', [], setup))
    for i, sec in enumerate((3., 7., 11.)):
        gun = m.role(f'{active} gun {i}').name
        s8.at(t, f'kill fire {i}', sec, [
            ('UNIT_CHANGE_OBJECT_STATUS', gun, status('NO_ATTACK'), 0),
            ('NAMED_ATTACK_NAMED', gun, m.role(f'{active} victim {i}').name)])
    s8.at(t, 'kill script', 15., [('NAMED_KILL', m.role('script').name)])
    for i, (side, kind, label) in enumerate(((active, 'SovietAntiInfantryInfantry', '主步兵'),
                                           (active, 'AlliedAntiVehicleVehicleTech1', '主坦克'),
                                           (other, 'SovietAntiInfantryInfantry', '另步兵'))):
        counter = f'CNV_Kills_{i}'
        t.counters.append((counter, label))
        t.scripts.append(Script(f'Test - query kills {i}', [], [
            ('SET_COUNTER', counter, 77),
            ('SET_PLAYER_KILLS_OF_TYPE_TO_COUNTER', m.player(side), kind, counter)], once=False))
    victims = [f'{active} victim {i}' for i in range(3)] + ['script'] + [
        f'{other} victim {i}' for i in range(3)] + ['alive']
    s8.total(t, 'CNV_Kills_Alive', '存活码', [
        (1 << i, ('NAMED_NOT_DESTROYED', m.role(role).name)) for i, role in enumerate(victims)])
    t.expect = [('主步兵', 22., '==', 2), ('主坦克', 22., '==', 1),
                ('另步兵', 22., '==', 0), ('存活码', 22., '==', 240)]
    s8.watch(t, 25.)
    return t


def a(m):
    return check(m, 'p1')


def b(m):
    return check(m, 's5')


CHECKS = {'engine_killcount': {'a': a, 'b': b}}
