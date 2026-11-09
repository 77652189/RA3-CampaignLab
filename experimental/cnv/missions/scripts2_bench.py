"""Engine probe mission (inventory: the inferred script items, checks/engine_scripts2.py): PLAYER_RELATES_PLAYER (one
way? '<All Players>'?) and PLAYER_HAS_OBJECT_COMPARISON (are the dying counted?).

Island map (+y is north):
  west field  `mcv a` the player's AlliedMCV (unarmed) at (-50, 0); `gun a` the enemy's (s1, Soviet_1, no AI)
              Guardian 120 east of it, facing it -- only the enemy can shoot here
  east field  `mcv b` the enemy's AlliedMCV at (0, 0); `gun b` the player's Guardian 120 west of it, facing it --
              only the player can shoot here (~1800 from the west pair)
  east 3      `tank 1`, `tank 2` the player's Guardians, 60 apart (~900 from east field): counted, one killed
Published (the cast): mcv a, gun a, mcv b, gun b, tank 1, tank 2.
"""
from maps import island
from parts import Mission

TANK, MCV = 'AlliedAntiVehicleVehicleTech1', 'AlliedMCV'


def _n(part):
    return f'UNIT - CNV S2 {part}'


def mission(name='CampScr2'):
    m = Mission(name=name, map=island, units=[], facts={})
    m.spawns |= {TANK, MCV}
    m.put(MCV, 'west field', -50.0, 0.0, angle=0.0, name=_n('Mcv A'), role='mcv a')
    m.put(TANK, 'west field', 70.0, 0.0, side='s1', angle=3.1416, name=_n('Gun A'), role='gun a')
    m.put(MCV, 'east field', 0.0, 0.0, side='s1', angle=3.1416, name=_n('Mcv B'), role='mcv b')
    m.put(TANK, 'east field', -120.0, 0.0, angle=0.0, name=_n('Gun B'), role='gun b')
    for k, dx in enumerate((-30.0, 30.0), 1):
        m.put(TANK, 'east 3', dx, 0.0, angle=0.0, name=_n(f'Tank {k}'), role=f'tank {k}')
    return m


MISSION = {'engine_scripts2': mission}
