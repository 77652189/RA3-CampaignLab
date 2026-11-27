"""Soviet Crane with and without SlaughterHordeContain.

A named enter order recycles each 1000-credit Hammer for 750 credits to the
tank owner at its own or a mutual ally's retail crane. The module-off control
stays outside the approach area. Exact entry reach and timing are inferred.
"""
from parts import Script, Test, square


def check(m, allied=False):
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
    if allied:
        other, other_wallet = m.player('s2'), 'Ally Wallet'
        # Four HUD lines fit. State is 10 * the alive bits + the approach latch bits.
        t.counters = [(frame, frame), (alive, 'State'), (wallet, wallet), (other_wallet, other_wallet)]
        t.scripts[2].do = [('SET_COUNTER_TO_COUNTER', alive, approach)]
        t.scripts[0].do.extend([
            ('PLAYER_SET_MONEY', other, 0),
            ('PLAYER_RELATES_PLAYER', player, other, (2, 0.0, 'Friend')),
            ('PLAYER_RELATES_PLAYER', other, player, (2, 0.0, 'Friend')),
        ])
        t.scripts.append(Script('Test - ally wallet', [],
                                [('SET_PLAYER_MONEY_TO_COUNTER', other, other_wallet)], once=False))
        lanes.append(('ally', 4))
    for tag, bit in lanes:
        tank, crane = m.role(f'tank {tag}').name, m.role(f'crane {tag}').name
        orders.append(('NAMED_GARRISON_SPECIFIC_BUILDING', tank, crane))
        area = f'Crane approach {tag}'
        t.areas[area] = square(*m.point(tag), 145)
        t.scripts.extend([
            Script(f'Test - live tank {tag}', [('NAMED_NOT_DESTROYED', tank)],
                   [('INCREMENT_COUNTER', bit * (10 if allied else 1), alive)], once=False),
            Script(f'Test - approach {tag}', [('NAMED_INSIDE_AREA', tank, area)],
                   [('INCREMENT_COUNTER', bit, approach)]),
        ])
    t.scripts.append(Script('Test - enter', [('COUNTER', frame, 2, 45)], orders))
    t.expect = [(frame, 0, 'ever==', 225)]
    if allied:
        t.expect += [('State', 0, 'ever==', 25), (wallet, 0, 'ever==', 1500),
                     (other_wallet, 0, '==', 0)]
    else:
        t.expect += [(alive, 0, 'ever==', 2), (wallet, 0, 'ever==', 750)]
    t.bench = [('bench_watch', dict(seconds=37, every=.5, sheet=False, lines=4))]
    return t


CHECKS = {'engine_cranerecycle': {'a': check},
          'engine_cranerecycleally': {'a': lambda m: check(m, allied=True)}}
