"""PLAYER gate prediction: 1011099075/1011099080/1011099080/1011099075.

engine_spng geometry/timing unchanged. Each lane has a distinct PLAYER upgrade
so the common p1/s1 owners cannot contaminate another lane. GIVE_PLAYER_UPGRADE
awards caster owner in base/order and victim owner in high/removed. Status proof
on the receiver verifies delivery; required/forbidden gates should read caster
owner. Only direct single-shot zero-reload self ARMOR powers are claimed.
MEASURED 2026-11-11: CampSPNGPA_mcp_1111_012717 PASS, 167.8s.
Final packed values match prediction; early caster85/90/90/85, late75/80/80/75.
All four grant proof bits set, victims99%, both sides alive.
The earlier attempt failed compilation (TargetType accidentally changed); no readings.
"""
from checks import engine_spng, engine_spn


def mission():
    m = engine_spng.mission()
    m.name = 'CampSPNGP'
    for i, lane in enumerate(engine_spn.CASES):
        upgrade = engine_spng.UPGRADE + lane.title()
        for u in m.units[i*3:i*3+2]:
            u.xml = u.xml.replace(engine_spng.UPGRADE, upgrade)
            u.xml = u.xml.replace(f'id="{upgrade}" Type="OBJECT"', f'id="{upgrade}" Type="PLAYER"')
        caster = m.units[i*3]
        if lane == 'base':
            caster.link = [x.replace(engine_spng.UPGRADE, upgrade) for x in caster.link]
        else:
            caster.xml = caster.xml.replace('</AssetDeclaration>',
                f'<UpgradeTemplate id="{upgrade}" Type="PLAYER"/></AssetDeclaration>')
            caster.link.append('UpgradeTemplate:' + upgrade)
    return m


def check(m):
    t = engine_spng.check(m)
    grant = next(s for s in t.scripts if s.name == 'Test - grant upgrades')
    grant.do = [('GIVE_PLAYER_UPGRADE', m.player('p1' if lane in ('base', 'order') else 's1'),
                      engine_spng.UPGRADE + lane.title()) for lane in engine_spn.CASES]
    return t


MISSION = {'engine_spngp': mission}
CHECKS = {'engine_spngp': {'a': check}}
