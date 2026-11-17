"""B208: AllNearbyNodesFullHeuristic -- the Peacekeepers (CNVNodesFull) and Guardians (control) at home.

Prediction (missions/ainodesfull_bench.py; B210: a node is full at 3 own collectors, the refinery's own included):
Guardians leave on every build; Peacekeepers leave only on ainf3 (two refineries, three collectors each).
"""
from parts import Script, Test, counted, square

LABELS = ('满态在家', '常量在家')


def a(m):
    t = Test()
    t.areas['NodesFull home'] = square(*m.site('east base'), 450)
    t.scripts.append(Script('NodesFull keep target', [],
                            [('UNIT_SET_HEALTH', m.role('player target').name, 100.0)], once=False))
    for i, (unit, label) in enumerate(zip(m.cnv_units, LABELS)):
        counted(f'NodesFull_home{i}', label, t, template=unit, player=m.player('s1'), area='NodesFull home')
    # B210: a refinery's node is full at 3 collectors (its own + 2 placed): only ainf3
    full = m.facts.get('ai refineries') == 2 and m.facts.get('ai miners', 0) >= 2
    for second, values in ((8, (4, 4)), (60, (0 if full else 4, 0)), (110, (0 if full else 4, 0))):
        for label, value in zip(LABELS, values):
            t.expect.append((label, second, '==', value, second + 10))
    t.bench = [('bench_watch', dict(seconds=125, every=2, sheet=False, lines=3))]
    return t


CHECKS = {'ainf0': {'a': a}, 'ainf1': {'a': a}, 'ainf2': {'a': a}, 'ainf3': {'a': a}, 'ainf4': {'a': a}, 'ainf5': {'a': a}}
