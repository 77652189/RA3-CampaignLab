"""RepairUpdate through a woken AI, with funded / zero-credit controls.

Prediction from the data and D's repair analysis: a 1000 HP, cost-800 plant
starting at half health gains 10 HP/s; total cost is about 100 (the missing
fraction enters twice). No build states, combat or income can spend money.
CNVProbe reads repair activation and accumulators; it does not start repair.
The legacy engine_repair:a UI activation diagnostic is kept separately.

Bench 2026-11-11 E48: starting funded with 10000 and no later money reset
reaches 100/50/9900 at s49 and remains there. The read-only probe reports
active at frame 5, cost=200, r=1/1500; stopped at frame 756.
E41's late funding failed because the no-economy AI latch was already set.
Zero-credit control measures that latch, not inability to pay an active repair.
Unmeasured repair configurations and player input remain separate gaps.
E49 repairq:a starts at 25% health: cost=300, active frame 5 to 1131;
the bench reaches 100/50/9775 at s74 and holds through s103.
E51 repairt:a starts at 75% health: cost=100, active frame 5 to 381;
the bench reaches 100/50/9975 at s24 and holds through s51.
"""
from parts import Script, Test, counted


def check(m):
    t = Test()
    t.scripts.append(Script('Repair reveal', [], [('MAP_REVEAL_ALL_PERM', m.player('p1'))]))
    for role in ('repair', 'control'):
        counted('AI Repair ' + role, role + ' HP', t, health=m.role(role).name)
    t.counters.append(('AI Repair Money', '资金'))
    t.scripts.append(Script('Repair money', [],
                            [('SET_PLAYER_MONEY_TO_COUNTER', m.player('s1'), 'AI Repair Money')], once=False))
    initial = m.facts['initial health']
    start, end, seconds, money = {25: (90, 95, 100, 9775),
                                  50: (75, 80, 80, 9900),
                                  75: (40, 45, 50, 9975)}.get(initial, (75, 80, 80, 9900))
    if not m.facts['funded']:
        money = 0
    repairs = m.facts['funded'] and m.facts.get('repairs at medium', 1)
    if not repairs and m.facts['funded']:   # repairoff: no repair -> nothing spent
        money = 10000
    t.expect = [('repair HP', start, '==', 100 if repairs else initial, end),
                ('control HP', 1, '==', 50, end),
                ('资金', start, '==', money, end)]
    t.bench = [('bench_watch', dict(seconds=seconds, every=1, sheet=False, lines=3))]
    return t


CHECKS = {key: {'a': check} for key in ('repairai', 'repairzero', 'repairq', 'repairt', 'repairoff', 'repairmed')}
