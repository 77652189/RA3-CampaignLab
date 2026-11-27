"""Soviet Crane with and without SlaughterHordeContain.

INFERRED: a named enter order recycles its own 1000-credit Hammer for 750
credits only with the module. An approach latch distinguishes refusal from
an order that moves the tank. Wallets and survival do not expose entry events.
"""
from parts import Script, Test, square


def check(m):
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
    for tag, bit in [('on', 1), ('off', 2)]:
        tank, crane = m.role(f'tank {tag}').name, m.role(f'crane {tag}').name
        orders.append(('NAMED_GARRISON_SPECIFIC_BUILDING', tank, crane))
        area = f'Crane approach {tag}'
        t.areas[area] = square(*m.point(tag), 145)
        t.scripts.extend([
            Script(f'Test - live tank {tag}', [('NAMED_NOT_DESTROYED', tank)],
                   [('INCREMENT_COUNTER', bit, alive)], once=False),
            Script(f'Test - approach {tag}', [('NAMED_INSIDE_AREA', tank, area)],
                   [('INCREMENT_COUNTER', bit, approach)]),
        ])
    t.scripts.append(Script('Test - enter', [('COUNTER', frame, 2, 45)], orders))
    t.expect = [(frame, 0, 'ever==', 225), (alive, 0, 'ever==', 2), (wallet, 0, 'ever==', 750)]
    t.bench = [('bench_watch', dict(seconds=37, every=.5, sheet=False, lines=4))]
    return t


CHECKS = {'engine_cranerecycle': {'a': check}}
