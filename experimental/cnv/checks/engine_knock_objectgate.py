"""Isolate the retail RushAttack forbidden object-status gate.

Both lanes use enemy probe infantry, neighbour 20 east. The retail payload
keeps numerical fields and ForbiddenTargetObjectStatus; Arc, model-condition
and infantry filter are removed to isolate this gate, not claim full Rush.
a retains the gate, b deletes only it. Yuri neighbour has the scripted bit;
rocket neighbour does not. Predict a rejects yuri, b admits both. Native
leech lifecycle and the removed restrictions remain gaps.
"""
import os
import re

import labpaths
from model import status
from checks import engine_knock_nocoll as nocoll

BIT = 'LEECHED_TARGET_ACTIVE'


def payload():
    with open(os.path.join(labpaths.SDK3, 'SageXML', 'GlobalData', 'Weapon.xml'), encoding='utf-8') as f:
        text = f.read()
    weapon = re.search(r'<WeaponTemplate\s+id="JapanAntiVehicleVehicleTech3RushAttackWeapon".*?</WeaponTemplate>', text, re.S).group(0)
    shock, = re.findall(r'<MetaImpactNugget\b.*?</MetaImpactNugget>', weapon, re.S)
    shock = re.sub(r'\s+(?:ShockWaveArc|ForbiddenTargetModelCondition)="[^"]*"', '', shock)
    shock = re.sub(r'<SpecialObjectFilter\b.*?</SpecialObjectFilter>', '', shock, flags=re.S)
    assert f'ForbiddenTargetObjectStatus="{BIT}"' in shock
    return shock


def mission():
    m = nocoll.mission()
    m.name = 'CampKOG'
    return m


def check(m, without_gate=False):
    t = nocoll.check(m)
    for script in t.scripts:
        script.do = [tuple(BIT if x == 'NO_COLLISIONS' else x for x in action) for action in script.do]
        # Rebuild status condition because status() publishes a numeric enum.
        if script.name.startswith('Test - status '):
            script.when = [(a[0], a[1], status(BIT)) for a in script.when]
    shock = payload()
    if without_gate:
        shock = shock.replace(f'ForbiddenTargetObjectStatus="{BIT}"', '')
    for unit in m.units:
        if unit.id in ('CNV_KnockYuri', 'CNV_KnockRocket'):
            unit.xml, n = re.subn(r'<MetaImpactNugget\b.*?</MetaImpactNugget>', lambda _: shock, unit.xml, flags=re.S)
            assert n == 1
    return t


MISSION = {'engine_knock_objectgate': mission}
CHECKS = {'engine_knock_objectgate': {'a': check, 'b': lambda m: check(m, without_gate=True)}}
