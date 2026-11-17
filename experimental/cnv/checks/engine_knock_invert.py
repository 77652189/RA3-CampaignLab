"""C: MagneticSingularity payload versus only InvertShockWave=false.

Both lanes use the retail filter and probe Hammers, with a neighbour 80 east
of the direct victim (inside Radius100). Prediction: inverse pulls the
neighbour west, ordinary pushes east; health99/100 in each lane. Arrival,
filter eligibility and horizontal Physics are observed, not assumed covered.
No Arc, delay, native player-power lifetime or whole-nugget coverage.
"""
import os
import re

import labpaths
from checks import engine_knock_arc as arc
from checks import engine_knock_probe as probe


def retail_shock():
    with open(os.path.join(labpaths.SDK3, 'SageXML', 'GlobalData', 'Weapon.xml'), encoding='utf-8') as f:
        text = f.read()
    weapon = re.search(r'<WeaponTemplate\s+id="MagneticSingularityWeapon".*?</WeaponTemplate>', text, re.S).group(0)
    shock, = re.findall(r'<MetaImpactNugget\b.*?</MetaImpactNugget>', weapon, re.S)
    assert 'InvertShockWave="true"' in shock
    return shock


def mission():
    m = arc.mission()
    m.name = 'CampKInv'
    for lane in ('yuri', 'rocket'):
        victim = next(o for o in m.objects if o.name == probe.name(lane, 'man'))
        near = next(o for o in m.objects if o.name == probe.name(lane, 'near'))
        victim.template = near.template = probe.PROBE_TANK
        near.x = victim.x + 80
    return m


def check(m, plain=False):
    t = arc.check(m)
    shock = retail_shock()
    if plain:
        # Second run isolates the numerical inversion from the retail filter.
        shock = re.sub(r'<SpecialObjectFilter\b.*?</SpecialObjectFilter>', '', shock, flags=re.S)
    for lane, uid in (('yuri', 'CNV_KnockYuri'), ('rocket', 'CNV_KnockRocket')):
        gun = probe.rocket_gun(uid)
        payload = shock if lane == 'yuri' else shock.replace('InvertShockWave="true"', 'InvertShockWave="false"')
        gun.xml, n = re.subn(r'<MetaImpactNugget\b[^>]*/>', lambda _: payload, gun.xml)
        assert n == 1
        m.units = [gun if u.id == uid else u for u in m.units]
    if plain:
        # First run's capture clock lagged the mission clock: keep its failed
        # 12..14s verdict; this independent run observes a longer stable tail.
        t.bench = [('bench_watch', dict(seconds=24, every=.5, sheet=False, lines=4))]
        t.expect = [(label, 22, '==', hp, 24) for label, hp in
                    [('yuri man', 99), ('yuri near', 100), ('rocket man', 99), ('rocket near', 100)]]
    return t


MISSION = {'engine_knock_invert': mission}
CHECKS = {'engine_knock_invert': {'a': check, 'b': lambda m: check(m, plain=True)}}
