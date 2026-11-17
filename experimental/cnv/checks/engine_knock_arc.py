"""C: retail shotgun's narrow-arc payload versus its unfiltered control.

Copy the retail MetaImpactNugget, including Arc=5d and forbidden flailing,
onto a V4 warhead so a detonation is positively observed. The other lane
removes only those two restrictions. Both neighbours stand 20 east of the
victim (inside Radius40, transverse to the incoming rocket). Prediction:
plain neighbour moves, restricted neighbour stays; both victims99/near100.
No delay, stunned victim, instant-shot dispatch or whole-shotgun coverage.
Bench 11-11: health99/100/99/100. Plain neighbour moves at frames175..177
to (2320,3740,212.5); restricted victim AND neighbour remain stationary.
This establishes a payload difference, not an arc-axis rule. The incoming
direction/arc dispatch interface remains a gap; do not register filter cover.
"""
import os
import re

import labpaths
from checks import engine_knock_probe as probe


def retail_shock():
    with open(os.path.join(labpaths.SDK3, 'SageXML', 'GlobalData', 'Weapon.xml'), encoding='utf-8') as f:
        text = f.read()
    weapon = re.search(r'<WeaponTemplate\s+id="AlliedAntiInfantryInfantryShotgun".*?</WeaponTemplate>',
                       text, re.S).group(0)
    shock, = re.findall(r'<MetaImpactNugget\b[^>]*/>', weapon)
    assert 'ShockWaveArc="5d"' in shock and 'ForbiddenTargetModelCondition="STUNNED_FLAILING"' in shock
    return shock


def mission():
    m = probe.mission()
    m.name = 'CampKArc'
    for lane in ('yuri', 'rocket'):
        victim = next(o for o in m.objects if o.name == probe.name(lane, 'man'))
        near = next(o for o in m.objects if o.name == probe.name(lane, 'near'))
        near.x = victim.x + 20
    return m


def check(m):
    t = probe.check(m, 'retail')
    shock = retail_shock()
    for lane, uid in (('yuri', 'CNV_KnockYuri'), ('rocket', 'CNV_KnockRocket')):
        gun = probe.rocket_gun(uid)
        payload = shock if lane == 'yuri' else re.sub(
            r'\s+(?:ShockWaveArc|ForbiddenTargetModelCondition)="[^"]*"', '', shock)
        gun.xml, n = re.subn(r'<MetaImpactNugget\b[^>]*/>', lambda _: payload, gun.xml)
        assert n == 1
        m.units = [gun if u.id == uid else u for u in m.units]
    # Both guns are projectiles now: retain their half-second pre-attack delay.
    for script in t.scripts:
        script.do = [(a[0], a[1], probe.ORDER + 2.0)
                     if a[0] == 'SET_MILLISECOND_TIMER' and a[1] == 'Knock Stop 0' else a
                     for a in script.do]
    return t


MISSION = {'engine_knock_arc': mission}
CHECKS = {'engine_knock_arc': {'a': check}}
