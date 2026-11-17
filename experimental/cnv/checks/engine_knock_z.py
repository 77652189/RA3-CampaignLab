"""C line: omitted ShockWaveZMult (SDK default 1), one projectile detonation.

Reuse engine_knock_probe land, removing only the rocket warhead's explicit Z.
The neighbour has geometry height 93 instead of 13 so its half-height is 40
above the detonation. This makes Z observable rather than multiplying zero.
Before bench: centre (2300,3750,219), neighbour (2360,3750,212.5), height93.
Predict v=(3.7451,0,2.4967), fourteen frames to landing (2420,3740,212.5).
Health remains target99/neighbour100, no death. Arrival frame and direct-hit
noise are not predicted; replay starts at the observed collision event.
"""
import copy

from checks import engine_knock_probe as probe

TALL = 'CNV_KnockTall'


def mission():
    m = probe.mission()
    m.name = 'CampKZ'
    for o in m.objects:
        if o.name == probe.name('rocket', 'near'):
            o.template = TALL
    return m


def check(m):
    t = probe.check(m, 'land')
    gun = next(u for u in m.units if u.id == 'CNV_KnockRocket')
    assert gun.xml.count('ShockWaveZMult="8.5"') == 1
    gun.xml = gun.xml.replace(' ShockWaveZMult="8.5"', '', 1)
    tall = copy.deepcopy(next(u for u in m.units if u.id == probe.PROBE))
    tall.id = TALL
    tall.names = dict(unit=TALL)
    tall.xml = tall.xml.replace(probe.PROBE, TALL)
    assert tall.xml.count('Height="13.0"') == 1
    tall.xml = tall.xml.replace('Height="13.0"', 'Height="93.0"', 1)
    tall.what = '击飞默认Z探针：维和兵几何高度93，物理参数仍为默认'
    m.units.append(tall)
    return t


MISSION = {'engine_knock_z': mission}
CHECKS = {'engine_knock_z': {'a': check}}
