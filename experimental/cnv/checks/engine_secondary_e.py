"""E174 prediction: engineer secondary adds the retail Repair upgrade to host.

Only the listener include is removed in the control. Sample at frames 60,
180 and 360; enter instantly at 90 and exit at 240. Each snapshot encodes
host alive=1, crew alive=2, crew ENCLOSED=4, player's Repair upgrade=8.
Prediction on: 3/15/3; off: 3/7/3. These are module-consumption observations,
not a claim about all passengers, weapon updates, visuals or exact timing.
See work/re/e174_secondary.md for measurements and remaining gaps.
"""
from model import Script, Test


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


CHECKS = {name: {'a': check} for name in ('engine_secondon_e', 'engine_secondoff_e')}
