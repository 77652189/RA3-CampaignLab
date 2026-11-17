"""Packed native status (100) + goal count (10 each) + home count, four lanes.

The mask reads original UNIT_HAS_OBJECT_STATUS, never model target selection.
Script-set bits do not establish real flight, links or candidate qualification.
"""
from parts import Script, Test, counted, square, status


def a(m):
    t = Test()
    for i, bit in enumerate(m.facts['vital bits']):
        name = m.role(f'vital sample {i}').name
        counter = f'Vital_packed{i}'
        t.scripts.append(Script(f'Vital reset {i}', [], [('SET_COUNTER', counter, 0)], once=False))
        t.scripts.append(Script(f'Vital read {i}', [('UNIT_HAS_OBJECT_STATUS', name, status(bit))],
            [('INCREMENT_COUNTER', 100, counter)], once=False))
        t.scripts.append(Script(f'Vital keep sample {i}', [], [('UNIT_SET_HEALTH', name, 100.0)], once=False))
    x, y = m.site('east base')
    t.areas['Vital home'] = [(x-400,y-400),(x+400,y-400),(x+400,y+500),(x-400,y+500)]
    for i, unit in enumerate(m.cnv_units):
        goal = m.find(m.role(f'vital goal {i}').name)
        area = f'Vital goal {i}'
        t.areas[area] = square(goal.x, goal.y, 340)
        for location, label, ar in [('goal', f'目标{i}', area), ('home', f'家{i}', 'Vital home')]:
            counted(f'Vital_{location}{i}', label, t, template=unit, area=ar, player=m.player('s1'))
            for n in range(1, 9):
                t.scripts.append(Script(f'Vital pack {location} {i} {n}',
                    [('COUNTER', f'Vital_{location}{i}', 2, n)],
                    [('INCREMENT_COUNTER', n * (10 if location == 'goal' else 1), f'Vital_packed{i}')], once=False))
    members = [r for r in m.cast if r.startswith(('peacekeeper ', 'guardian ', 'vital member '))]
    t.scripts.append(Script('Vital keep teams', [], [
        ('UNIT_SET_HEALTH', m.role(role).name, 100.0) for role in members], once=False))
    t.counters = [(f'Vital_packed{i}', f'路{i}') for i in range(4)]
    for _, label in t.counters:
        t.expect += [(label, 2, '>=', 100, 3), (label, 4.5, '<=', 99, 5.5),
                     (label, 55, '==', 140 if m.facts['vital matching'] else 4, 60)]
    t.bench = [('bench_watch', dict(seconds=65, every=0.5, sheet=False, lines=len(t.counters)))]
    return t


CHECKS = {name: {'a': a} for name in ('aivitalon', 'aivitaloff')}
