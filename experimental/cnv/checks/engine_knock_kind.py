"""Sickle retail INFANTRY inclusion versus removal of only that inclusion.

Enemy infantry and a real Hammer stand 40 east of identical infantry targets.
a retains the retail payload; b removes Include=INFANTRY, retaining relation,
status exclusion and forbidden conditions. Predict only b dispatches to Hammer.
Bench 11-16: both health99/100/99/100; a pushes infantry, rejects Hammer.
b unexpectedly dispatches no shock at all (empty Rule=ANY is not an all-kind
positive control). Original prediction retained; see work/re/c_kind_report.md.
No synthetic KindOf, native status lifecycle or retail landing-entry claim.
"""
import re

from checks import engine_knock_relation as relation
from checks import engine_knock_probe as probe


def mission():
    m = relation.mission()
    m.name = 'CampKKind'
    for lane in ('yuri', 'rocket'):
        victim = next(o for o in m.objects if o.name == probe.name(lane, 'man'))
        near = next(o for o in m.objects if o.name == probe.name(lane, 'near'))
        near.side = victim.side
        near.x = victim.x + 40
        if lane == 'rocket':
            near.template = probe.PROBE_TANK
    return m


def check(m, plain=False):
    t = relation.check(m)
    payload = relation.retail_shock()
    if plain:
        assert payload.count('Include="INFANTRY"') == 1
        payload = payload.replace('Include="INFANTRY"', '')
    for uid in ('CNV_KnockYuri', 'CNV_KnockRocket'):
        gun = next(u for u in m.units if u.id == uid)
        gun.xml, n = re.subn(r'<MetaImpactNugget\b.*?</MetaImpactNugget>',
                             lambda _: payload, gun.xml, flags=re.S)
        assert n == 1
    t.expect = [(lane + ' ' + part, 22, '==', 99 if part == 'man' else 100, 24)
                for lane in ('yuri', 'rocket') for part in ('man', 'near')]
    t.bench = [('bench_watch', dict(seconds=24, every=.5, sheet=False, lines=4))]
    return t


MISSION = {'engine_knock_kind': mission}
CHECKS = {'engine_knock_kind': {'a': check, 'b': lambda m: check(m, plain=True)}}
