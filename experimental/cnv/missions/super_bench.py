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
TANK_DIST = {0: (0.0, 0.0), 150: (150.0, 0.0), 200: (-200.0, 0.0), 250: (0.0, -250.0),
             350: (350.0, 0.0), 450: (318.0, -318.0), 600: (25.0, -595.0)}     # i / j use 0 and 150; k 150-250; l 350-600
FOE_AT = {0: (0.0, 200.0), 150: (150.0, 200.0), 200: (-200.0, 200.0), 250: (0.0, -450.0),   # an enemy tank behind each
          350: (350.0, 200.0), 450: (459.0, -459.0), 600: (20.0, -800.0)}
NFOE_AT = {0: (0.0, 300.0), 150: (150.0, 300.0)}     # n (nanoswarm, ring 200): these foes start outside the one-shot ring
NANO, POWER_N = 'JapanSuperWeapon', 'SpecialPowerNanoSwarmHive'
PSI, POWER_D = 'JapanSuperWeaponAdvanced', 'SpecialPowerTelekineticProjectorDevice'     # the Psionic Decimator
NANO_AT, PSI_AT, PSI_SPOT = (500.0, -300.0), (-800.0, -300.0), (190.0, -750.0)
PSI_DIST = {0: (0.0, 0.0), 150: (150.0, 0.0), 250: (250.0, 0.0), 350: (350.0, 0.0)}
VAC, POWER_V = 'SovietSuperWeaponAdvanced', 'SpecialPowerVacuumBomb'
VAC_AT, VAC_SPOT = (-300.0, -500.0), (270.0, -600.0)
VAC_DIST = {0: (0.0, 0.0), 150: (150.0, 0.0), 280: (280.0, 0.0), 350: (-350.0, 0.0)}

# g / h: curtain radius with one foe per tank (checks/engine_super.py): spot and tank directions, far from any base
RAD_SPOTS = {'g': ('Test Radius Spot', (-110.0, 1355.0)), 'h': ('Test Radius Far', (1170.0, -75.0)),
             'a': ('Test Radius Edge', (1170.0, -75.0))}
RAD_DIRS = {'g': {100: (0, -1), 300: (1, 0), 500: (-1, 0), 800: (0, 1)},
            'a': {850: (-1, 0), 950: (0, -1), 1050: (0, 1), 1150: (1, 0)},
            'h': {1200: (-1, 0), 1600: (0, -1), 2000: (0, 1), 2400: (0.7071, -0.7071)}}


def _n(part):
    return f'UNIT - CNV Super {part}'


def mission(name='CampSuper'):
    m = Mission(name=name, map=niagara, units=[], facts={})
    m.sides['s1'] = {'playerFaction': 'PlayerTemplate:Allies'}
    m.spawns |= {COLLIDER, CURTAIN, TARGET, TANK, VAC, NANO, PSI}
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
    m.put(VAC, SITE, *VAC_AT, angle=0.0, role='vacuum', name=_n('Vacuum'))
    m.waypoint('vacuum spot', 'Test Vacuum Spot', SITE, *VAC_SPOT)
    for d, (dx, dy) in VAC_DIST.items():
        m.put(TARGET, SITE, VAC_SPOT[0] + dx, VAC_SPOT[1] + dy, side='s1', angle=0.0, role=f'vtarget {d}',
              name=_n(f'VTarget {d}'))
    for d, (dx, dy) in FOE_AT.items():
        m.put(TANK, SITE, CURTAIN_SPOT[0] + dx, CURTAIN_SPOT[1] + dy, side='s1', angle=0.0,
              role=f'foe {d}', name=_n(f'Foe {d}'))
    for d, (dx, dy) in NFOE_AT.items():
        m.put(TANK, SITE, CURTAIN_SPOT[0] + dx, CURTAIN_SPOT[1] + dy, side='s1', angle=0.0,
              role=f'nfoe {d}', name=_n(f'NFoe {d}'))
    m.put(NANO, SITE, *NANO_AT, angle=0.0, role='nano', name=_n('Nano'))
    m.put(PSI, SITE, *PSI_AT, angle=0.0, role='psi', name=_n('Psi'))
    m.waypoint('psi spot', 'Test Psi Spot', SITE, *PSI_SPOT)
    for d, (dx, dy) in PSI_DIST.items():
        m.put(TARGET, SITE, PSI_SPOT[0] + dx, PSI_SPOT[1] + dy, side='s1', angle=0.0, role=f'dtarget {d}',
              name=_n(f'DTarget {d}'))
    for w, (key, (sx, sy)) in RAD_SPOTS.items():
        m.waypoint(f'radius spot {w}', key, SITE, sx, sy)
        for d, (ux, uy) in RAD_DIRS[w].items():
            m.put(TANK, SITE, sx + d * ux, sy + d * uy, angle=0.0, role=f'rtank {d}', name=_n(f'RTank {d}'))
            m.put(TANK, SITE, sx + (d + 150) * ux, sy + (d + 150) * uy, side='s1', angle=0.0, role=f'rfoe {d}',
                  name=_n(f'RFoe {d}'))
    return m


MISSION = {'engine_super': mission, 'engine_scripts8bs': lambda: mission('CampS8bS')}   # checks/engine_scripts8b
