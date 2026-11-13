"""C: Sickle landing payload; change only its ENEMIES filter to ALLIES.

Both V4 lanes target enemy infantry with a friendly infantry neighbour 20 east.
Prediction: retail pushes the enemy only; ALLIES pushes the neighbour only.
This isolates relationship filtering with identical forbidden conditions and
NO_COLLISIONS exclusion. No stunned-state or full retail landing coverage.
Bench 11-13: health99/100/99/100; enemy-only versus friendly-only motion.
Relation/condition dispatch stays a gap (strict replay xfails).
"""
import os
import re

import labpaths
from checks import engine_knock_arc as arc
from checks import engine_knock_probe as probe


def retail_shock():
    with open(os.path.join(labpaths.SDK3, 'SageXML', 'GlobalData', 'Weapon.xml'), encoding='utf-8') as f:
        text = f.read()
    weapon = re.search(r'<WeaponTemplate\s+id="SovietAntiInfantryVehicleLandWeapon".*?</WeaponTemplate>',
                       text, re.S).group(0)
    shock, = re.findall(r'<MetaImpactNugget\b.*?</MetaImpactNugget>', weapon, re.S)
    assert 'Relationship="ENEMIES"' in shock
    return shock


def mission():
    m = arc.mission()
    m.name = 'CampKRel'
    for lane in ('yuri', 'rocket'):
        near = next(o for o in m.objects if o.name == probe.name(lane, 'near'))
        near.side = 'p1'
    return m


def check(m):
    t = arc.check(m)
    shock = retail_shock()
    for lane, uid in (('yuri', 'CNV_KnockYuri'), ('rocket', 'CNV_KnockRocket')):
        gun = probe.rocket_gun(uid)
        payload = shock if lane == 'yuri' else shock.replace('Relationship="ENEMIES"', 'Relationship="ALLIES"')
        gun.xml, n = re.subn(r'<MetaImpactNugget\b[^>]*/>', lambda _: payload, gun.xml)
        assert n == 1
        m.units = [gun if u.id == uid else u for u in m.units]
    return t


MISSION = {'engine_knock_relation': mission}
CHECKS = {'engine_knock_relation': {'a': check}}

