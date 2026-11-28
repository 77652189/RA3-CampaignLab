"""Soviet Crane with and without SlaughterHordeContain.

A named enter order recycles each 1000-credit Hammer for 750 credits to the
tank owner at its own or a friendly retail crane. A Hammer damaged to 50%
before the order also returns 750, and a same-owner Apocalypse returns 1500.
With one-way friendship and neutrality, the crane owner's relationship controls
entry. The module-off control stays outside the approach area. Exact entry reach
and timing are inferred.
"""
from parts import Script, Test, square


FRIEND = (2, 0.0, 'Friend')
NEUTRAL = (1, 0.0, 'Neutral')


def check(m, allied=False, *, one_way=False, damaged=False, apocalypse=False):
    t = Test()
    player, frame, alive, approach, wallet = m.player('p1'), 'Frame', 'Alive', 'Approach', 'Wallet'
    t.counters = [(key, key) for key in (frame, alive, approach, wallet)]
    orders = []
    t.scripts = [
        Script('Test - start', [], [('MAP_REVEAL_ALL_PERM', player), ('PLAYER_SET_MONEY', player, 0)]),
        Script('Test - frame', [('COUNTER', frame, 0, 225)], [('INCREMENT_COUNTER', 1, frame)], once=False),
        Script('Test - reset alive', [], [('SET_COUNTER', alive, 0)], once=False),
        Script('Test - wallet', [], [('SET_PLAYER_MONEY_TO_COUNTER', player, wallet)], once=False),
    ]
    lanes = [('on', 1), ('off', 2)]
    if apocalypse:
        lanes.append(('apoc', 4))
    alive_scale = 1
    if allied:
        other, other_wallet = m.player('s2'), 'Ally Wallet'
        # Four HUD lines fit. Reserve enough decimal places for all approach bits.
        alive_scale = 100 if one_way else 10
        t.counters = [(frame, frame), (alive, 'State'), (wallet, wallet), (other_wallet, other_wallet)]
        t.scripts[2].do = [('SET_COUNTER_TO_COUNTER', alive, approach)]
        t.scripts[0].do.extend([
            ('PLAYER_SET_MONEY', other, 0),
            ('PLAYER_RELATES_PLAYER', player, other, NEUTRAL if one_way else FRIEND),
            ('PLAYER_RELATES_PLAYER', other, player, FRIEND),
        ])
        t.scripts.append(Script('Test - ally wallet', [],
                                [('SET_PLAYER_MONEY_TO_COUNTER', other, other_wallet)], once=False))
        lanes.append(('ally', 4))
    if one_way:
        site = 'switch gun'
        m.put('SovietCrane', site, name='Crane reverse', role='crane reverse')
        m.put('SovietAntiVehicleVehicleTech1', site, 0, 200, side='s2',
              name='Tank reverse', role='tank reverse')
        m.waypoint('reverse', 'Crane pad reverse', site)
        lanes.append(('reverse', 8))
    for tag, bit in lanes:
        tank, crane = m.role(f'tank {tag}').name, m.role(f'crane {tag}').name
        orders.append(('NAMED_GARRISON_SPECIFIC_BUILDING', tank, crane))
        area = f'Crane approach {tag}'
        t.areas[area] = square(*m.point(tag), 145)
        t.scripts.extend([
            Script(f'Test - live tank {tag}', [('NAMED_NOT_DESTROYED', tank)],
                   [('INCREMENT_COUNTER', bit * alive_scale, alive)], once=False),
            Script(f'Test - approach {tag}', [('NAMED_INSIDE_AREA', tank, area)],
                   [('INCREMENT_COUNTER', bit, approach)]),
        ])
    t.scripts.append(Script('Test - enter', [('COUNTER', frame, 2, 45)], orders))
    if damaged:
        tank = m.role('tank on').name
        health = 'Health'
        t.counters[2] = (health, health)
        t.scripts.extend([
            Script('Test - damage', [('COUNTER', frame, 2, 20)], [('NAMED_DAMAGE', tank, 275)]),
            Script('Test - health', [('NAMED_NOT_DESTROYED', tank)],
                   [('SET_UNIT_HEALTH_PERCENTAGE_TO_COUNTER', tank, health)], once=False),
        ])
    t.expect = [(frame, 0, 'ever==', 225)]
    if one_way:
        t.expect += [('State', 0, 'ever==', 1005), (wallet, 0, 'ever==', 1500),
                     (other_wallet, 0, '==', 0)]
    elif allied:
        t.expect += [('State', 0, 'ever==', 25), (wallet, 0, 'ever==', 1500),
                     (other_wallet, 0, '==', 0)]
    elif apocalypse:
        # The frame counter stops at 225 (15 logic seconds). Judge the final state.
        t.expect += [(alive, 15, '==', 2), (approach, 15, '==', 5), (wallet, 15, '==', 2250)]
    else:
        t.expect += [(alive, 0, 'ever==', 2), (wallet, 0, 'ever==', 750)]
    if damaged:
        t.expect += [(health, 0, 'ever==', 50)]
    t.bench = [('bench_watch', dict(seconds=37, every=.5, sheet=False, lines=4))]
    return t


CHECKS = {'engine_cranerecycle': {'a': check, 'b': lambda m: check(m, damaged=True)},
          'engine_cranerecycleapoc': {'a': lambda m: check(m, apocalypse=True)},
          'engine_cranerecycleally': {
              'a': lambda m: check(m, allied=True),
              'c': lambda m: check(m, allied=True, one_way=True),
          }}
