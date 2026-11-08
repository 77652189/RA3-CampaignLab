"""Engine probe: does a POWERED defence building fire while its owner is short of power (checks/engine_powerdef.py)?

The west field (island map), offsets from 'west field':
  coil   (0, 0)         s1's SovietBaseDefenseAdvanced (tesla coil: EnergyProduction -75, KindOf +POWERED,
                        weapon SovietBaseDefenseAdvancedTeslaGun AttackRange 350, Damage 450 TESLA)
  plant  (-130, 0)      s1's SovietPowerPlant (EnergyProduction +100): placed for on / cut; made at 10 s for back
  tanks  6 player tanks 'AlliedAntiVehicleVehicleTech1', NO_ATTACK, 175 north of the coil (half the range), 40 apart
SageXML (sdk3/XMLFiles/Soviet/Structures): SovietBaseDefenseAdvanced.xml line 64-66, SovietPowerPlant.xml line 52.
Published waypoint: plant (where back makes the plant).
"""
from maps import island
from parts import Mission

COIL, PLANT, TANK = 'SovietBaseDefenseAdvanced', 'SovietPowerPlant', 'AlliedAntiVehicleVehicleTech1'
N_TANKS, DIST, GAP = 6, 175.0, 40.0
PLANT_AT = (-130.0, 0.0)
VARIANTS = ('on', 'off', 'cut', 'back')


def tank_name(k):
    return f'UNIT - CNV Pd Tank {k}'


def mission(name, variant):
    m = Mission(name=name, map=island, facts={'variant': VARIANTS.index(variant), 'tanks': N_TANKS})
    m.spawns |= {PLANT}
    m.put(COIL, 'west field', 0.0, 0.0, side='s1', role='coil', name='UNIT - CNV Pd Coil')
    if variant in ('on', 'cut'):
        m.put(PLANT, 'west field', *PLANT_AT, side='s1', role='plant', name='UNIT - CNV Pd Plant')
    for k in range(N_TANKS):
        m.put(TANK, 'west field', (k - (N_TANKS - 1) / 2) * GAP, DIST, role=f'tank {k}', name=tank_name(k))
    m.waypoint('plant', 'CNV Pd Plant', 'west field', *PLANT_AT)
    return m


MISSION = {f'powerdef_{v}': (lambda v=v: mission('CampPd' + {'back': 'Bk'}.get(v, v.capitalize()), v)) for v in VARIANTS}
