"""Rush infantry filter combined with the scripted leech-status gate.

a keeps the retail infantry selector, b removes only that selector. Each
lane has an infantry neighbour and a synthetic non-infantry copy (only its
INFANTRY KindOf removed, same Physics). Yuri neighbours have the bit; rocket
neighbours do not. Predict only rocket infantry moves in a, both rocket
neighbours in b. Arc/model conditions/native leech lifecycle remain gaps.
"""
from copy import deepcopy
import re

from model import Script, status
from checks import engine_knock_objectgate as gate
from checks import engine_knock_probe as probe

NONINF = 'CNV_KGNonInf'


def mission():
    m = gate.mission()
    m.name = 'CampKKG'
    for lane in ('yuri', 'rocket'):
        near = next(o for o in m.objects if o.name == probe.name(lane, 'near'))
        other = deepcopy(near)
        other.template, other.name, other.x = NONINF, probe.name(lane, 'noninf'), near.x + 20
        m.objects.append(other)
    return m


def payload(without_filter=False):
    # Reuse the exact retail numeric/status fields; restore its original selector.
    shock = gate.payload().replace('</MetaImpactNugget>',
        '<SpecialObjectFilter Rule="ANY" Include="INFANTRY"></SpecialObjectFilter></MetaImpactNugget>')
    if without_filter:
        shock = re.sub(r'<SpecialObjectFilter\b.*?</SpecialObjectFilter>', '', shock, flags=re.S)
    return shock


def check(m, without_filter=False):
    t = gate.check(m)
    unit = deepcopy(next(u for u in m.units if u.id == probe.PROBE))
    unit.id, unit.xml = NONINF, unit.xml.replace(probe.PROBE, NONINF)
    unit.xml, n = re.subn(r'(\bKindOf=")([^"]*)(")',
        lambda match: match[1] + ' '.join(k for k in match[2].split() if k != 'INFANTRY') + match[3], unit.xml)
    assert n == 1
    unit.what = '筛选对照：维和探针复制件只移除INFANTRY标签；不是原版非步兵消费者'
    m.units.append(unit)
    for u in m.units:
        if u.id in ('CNV_KnockYuri', 'CNV_KnockRocket'):
            u.xml = re.sub(r'<MetaImpactNugget\b.*?</MetaImpactNugget>',
                           lambda _: payload(without_filter), u.xml, flags=re.S)
    start = next(s for s in t.scripts if s.name == 'Test - start')
    for lane in ('yuri', 'rocket'):
        target = probe.name(lane, 'noninf')
        start.do += [('UNIT_CHANGE_OBJECT_STATUS', target, 'NO_ATTACK', 1),
                     ('UNIT_CHANGE_OBJECT_STATUS', target, gate.BIT, int(lane == 'yuri'))]
        # Existing reset/status scripts encode infantry as 1, noninf as 10.
        t.scripts.append(Script('Test - noninf status ' + lane,
            [('UNIT_HAS_OBJECT_STATUS', target, status(gate.BIT))],
            [('INCREMENT_COUNTER', 10, 'CNV_KNC_' + lane)], once=False))
    t.expect = [(label, start, op, 11 if label == 'yuri status' else value, end)
                for label, start, op, value, end in t.expect]
    return t


MISSION = {'engine_knock_kindgate': mission}
CHECKS = {'engine_knock_kindgate': {'a': check, 'b': lambda m: check(m, without_filter=True)}}
