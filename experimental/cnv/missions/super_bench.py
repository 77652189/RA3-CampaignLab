"""Engine probe mission: two superweapons cast by a SCRIPT (read back by checks/engine_super.py).

Niagara. The player (p1) owns a construction yard and power plant (as engine_power), the proton collider
(AlliedSuperWeaponAdvanced, SpecialPowerParticleCannon) and the Soviet superweapon (SovietSuperWeapon,
SpecialPowerIronCurtain), both at 'west field' on their own pads.
  proton  targets: four AlliedBaseDefense (800 hp, small) of an enemy side s1 (no AI personality) at centre distances
          0 / 150 / 240 / 300 from the cast point 'Test Proton Spot': along +x for 0 / 150 / 240, the 300 one on the
          -x side (so their footprints do not touch).
  iron    two player tanks (AlliedAntiVehicleVehicleTech1) at 0 and 150 (+x) from 'Test Curtain Spot'.
"""
from maps import niagara
from parts import Mission

COLLIDER, POWER_P = 'AlliedSuperWeaponAdvanced', 'SpecialPowerParticleCannon'
CURTAIN, POWER_I = 'SovietSuperWeapon', 'SpecialPowerIronCurtain'
TARGET, TANK = 'AlliedBaseDefense', 'AlliedAntiVehicleVehicleTech1'
SITE = 'west field'
COLLIDER_AT, CURTAIN_AT = (-300.0, -300.0), (100.0, -175.0)
PROTON_AT, CURTAIN_SPOT = (300.0, 700.0), (-400.0, 100.0)
PROTON_DIST = {0: (0.0, 0.0), 150: (150.0, 0.0), 240: (240.0, 0.0), 300: (-300.0, 0.0)}
TANK_DIST = {0: (0.0, 0.0), 150: (150.0, 0.0)}


def _n(part):
    return f'UNIT - CNV Super {part}'


def mission(name='CampSuper'):
    m = Mission(name=name, map=niagara, units=[], facts={})
    m.sides['s1'] = {'playerFaction': 'PlayerTemplate:Allies'}
    m.spawns |= {COLLIDER, CURTAIN, TARGET, TANK}
    m.put('AlliedConstructionYard', 'base yard', angle=0.0, role='yard', name=_n('Yard'))
    m.put('AlliedPowerPlant', 'base power', angle=0.0, role='power', name=_n('Power'))
    m.put(COLLIDER, SITE, *COLLIDER_AT, angle=0.0, role='collider', name=_n('Collider'))
    m.put(CURTAIN, SITE, *CURTAIN_AT, angle=0.0, role='curtain', name=_n('Curtain'))
    m.waypoint('proton spot', 'Test Proton Spot', SITE, *PROTON_AT)
    m.waypoint('curtain spot', 'Test Curtain Spot', SITE, *CURTAIN_SPOT)
    for d, (dx, dy) in PROTON_DIST.items():
        m.put(TARGET, SITE, PROTON_AT[0] + dx, PROTON_AT[1] + dy, side='s1', angle=0.0, role=f'target {d}',
              name=_n(f'Target {d}'))
    for d, (dx, dy) in TANK_DIST.items():
        m.put(TANK, SITE, CURTAIN_SPOT[0] + dx, CURTAIN_SPOT[1] + dy, angle=0.0, role=f'tank {d}',
              name=_n(f'Tank {d}'))
    return m


MISSION = {'engine_super': mission}
