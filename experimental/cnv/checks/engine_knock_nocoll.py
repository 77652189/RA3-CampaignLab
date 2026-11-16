"""Sickle NO_COLLISIONS exclusion, with an independently observed bit.

Both lanes retain the complete retail landing payload and enemy infantry.
a sets only yuri neighbour NO_COLLISIONS, b swaps that bit to rocket.
Prediction: the set neighbour receives no shock; the clear neighbour moves.
Counters retain direct health99 and publish neighbour bits1/0 or0/1.
Scripted status only: native collision-state lifecycle and stun timing gap.
"""
from model import Script, status
from checks import engine_knock_relation as relation
from checks import engine_knock_probe as probe


def mission():
    m = relation.mission()
    m.name = 'CampKNC'
    for lane in ('yuri', 'rocket'):
        next(o for o in m.objects if o.name == probe.name(lane, 'near')).side = 's1'
    return m


def check(m, swap=False):
    t = relation.check(m)
    # Both payloads must be retail ENEMIES; the only variable is a status bit.
    for unit in m.units:
        if unit.id in ('CNV_KnockYuri', 'CNV_KnockRocket'):
            unit.xml = unit.xml.replace('Relationship="ALLIES"', 'Relationship="ENEMIES"')
    start = next(s for s in t.scripts if s.name == 'Test - start')
    t.counters = [c for c in t.counters if c[1].endswith('man')]
    t.scripts = [s for s in t.scripts if not (s.name.startswith('Test - health') and s.name.endswith('near'))]
    t.expect = [(lane + ' man', 22, '==', 99, 24) for lane in ('yuri', 'rocket')]
    for lane in ('yuri', 'rocket'):
        bit = int((lane == 'yuri') != swap)
        target = probe.name(lane, 'near')
        start.do.append(('UNIT_CHANGE_OBJECT_STATUS', target, 'NO_COLLISIONS', bit))
        counter = 'CNV_KNC_' + lane
        t.counters.append((counter, lane + ' status'))
        t.scripts.append(Script('Test - reset ' + lane, [], [('SET_COUNTER', counter, 0)], once=False))
        t.scripts.append(Script('Test - status ' + lane,
            [('UNIT_HAS_OBJECT_STATUS', target, status('NO_COLLISIONS'))],
            [('SET_COUNTER', counter, 1)], once=False))
        t.expect.append((lane + ' status', 22, '==', bit, 24))
    t.bench = [('bench_watch', dict(seconds=24, every=.5, sheet=False, lines=4))]
    return t


MISSION = {'engine_knock_nocoll': mission}
CHECKS = {'engine_knock_nocoll': {'a': check, 'b': lambda m: check(m, swap=True)}}
