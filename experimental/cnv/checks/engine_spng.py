"""SpecialPowerNugget upgrade gates, PREDICT 1011099075/1011099080/1011099080/1011099075.

Reuse engine_spn's measured one-shot self ARMOR150% dispatch and two hits.
All casters have the matching module. RequiredUpgrade on base/high;
ForbiddenUpgrade on order/removed. Grant one inert OBJECT upgrade to the
caster on base/order, to the victim on high/removed, before firing.
Prediction: gates read the caster, so only base/removed activate the buff.
Both hits and the victim's 10 damage marker are unchanged from engine_spn.
Add 10 million only when the grant receiver has WEAPON_UPGRADED_01, supplied
by a StatusBitsUpgrade, to positively verify the grant reached that object.
No player upgrade, multiple gates, inherited handler, OCL or disguise claim.
MEASURED 2026-11-11: first run PASS, 150.6s, CampSPNGA_mcp_1111_011028.
Final packed values match prediction; early caster HP85/90/90/85, late
75/80/80/75. All grant proof bits set; all victims retain HP99 after marking.
"""
import re

from checks import engine_spn
from model import Script, status

UPGRADE = 'Upgrade_CNVSPNGate'
VALUES = (1011099075, 1011099080, 1011099080, 1011099075)


def mission():
    m = engine_spn.mission()
    m.name = 'CampSPNG'
    for i, lane in enumerate(engine_spn.CASES):
        power = 'CNV_SPNPower' + lane.title()
        caster, victim = m.units[i*3:i*3+2]
        gate = 'RequiredUpgrade' if lane in ('base', 'high') else 'ForbiddenUpgrade'
        nugget = (f'<SpecialPowerNugget SpecialPowerTemplate="{power}">'
                  f'<{gate}>{UPGRADE}</{gate}></SpecialPowerNugget>')
        # Remove the original nugget, including its infantry-only negative control.
        caster.xml = re.sub(r'<SpecialPowerNugget\b.*?</SpecialPowerNugget>', '', caster.xml, flags=re.S)
        caster.xml = caster.xml.replace('</Nuggets>', nugget + '</Nuggets>')
        if lane == 'order':
            caster.xml = caster.xml.replace('<Behaviors>', '<Behaviors>' +
                f'<SpecialPower id="ModuleTag_SPN" SpecialPowerTemplate="{power}" '
                'AttributeModifier="AttributeMod_TargetPainted" AttributeModifierAffectsSelf="true"/>', 1)
        for u in (caster, victim):
            u.xml = u.xml.replace('<Behaviors>', '<Behaviors>' +
                '<StatusBitsUpgrade id="ModuleTag_SPNGate" StatusToSet="WEAPON_UPGRADED_01">'
                f'<TriggeredBy>{UPGRADE}</TriggeredBy></StatusBitsUpgrade>', 1)
        # One asset definition, shared by every lane's weak references.
        if lane == 'base':
            caster.xml = caster.xml.replace('</AssetDeclaration>',
                f'<UpgradeTemplate id="{UPGRADE}" Type="OBJECT"/></AssetDeclaration>')
            caster.link.append('UpgradeTemplate:' + UPGRADE)
    return m


def check(m):
    t = engine_spn.check(m)
    grants = []
    for lane, (counter, _) in zip(engine_spn.CASES, t.counters):
        receiver = 'SPN ' + lane + (' caster' if lane in ('base', 'order') else ' victim')
        grants.append(('NAMED_RECEIVE_UPGRADE', UPGRADE, receiver))
        t.scripts.append(Script('Test - grant proof ' + lane,
            [('UNIT_HAS_OBJECT_STATUS', receiver, status('WEAPON_UPGRADED_01'))],
            [('INCREMENT_COUNTER', 10000000, counter)], once=False))
    # The original first script starts timers; grants are applied before the first shot.
    t.scripts.insert(1, Script('Test - grant upgrades', [], grants))
    t.expect = [(label, 14, '==', value, 16) for (_, label), value in zip(t.counters, VALUES)]
    return t


MISSION = {'engine_spng': mission}
CHECKS = {'engine_spng': {'a': check}}
