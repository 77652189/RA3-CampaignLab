"""Engine probe mission: the ice engineer's skill -- its 20 s reload, its ForbiddenObjectRange 32 and PATHABLE_ONLY, as a
script (NAMED_FIRE_SPECIAL_POWER_AT_WAYPOINT) meets them (checks/engine_skill.py; docs/engine/specialpower.md sec. 2).

Festival. Offsets from 'west field' (open grass) unless said:
  a  engineer Ea at (-250, -250); cast points C1 (-250, -130), C2 (-354, -310), C3 (-146, -310): each 120 from him
     (within his StartAbilityRange), 208 apart.
  b  three engineers 110 south of spots B1..B3 (x 200, y -300 / 0 / 300); beside each spot a player tank (named,
     NO_ATTACK) at a different distance east: tank 1 20, tank 2 40, tank 3 60.
  c  from 'gate 1' (plaza 1's gate, on the cliff's line): engineer Ec on the plaza's flat top (100, +50), cast points
     P1 (100, -10) and P2 (100, -70) on the cliff; d: on the grass an engineer Ed at (-300, 150) with a plain point
     D (100, 150) 400 away (he walks first).
"""
from maps import festival
from parts import Mission
from units import icewall as iw

WALL, SEED, ENG, TANK = 'CNV_SkillWall', 'CNV_SkillSeed', 'CNV_SkillEng', 'AlliedAntiVehicleVehicleTech1'
LIFE, SIDE, CORE = 10, 160, 20
A_ENG = (-250.0, -250.0)
A_SPOTS = {1: (-250.0, -130.0), 2: (-354.0, -310.0), 3: (-146.0, -310.0)}
B_SPOTS = {1: (200.0, -300.0), 2: (200.0, 0.0), 3: (200.0, 300.0)}
B_DIST = {1: 20.0, 2: 40.0, 3: 60.0}            # tank's centre east of the spot
C_ENG, C_SPOTS = (60.0, 50.0), {1: (90.0, -10.0), 2: (90.0, -70.0)}      # from 'gate 1'
D_ENG, D_SPOT = (-300.0, 150.0), (100.0, 150.0)                              # from 'west field': 400 apart
W_ENG, W_SPOT = (-790.0, 25.0), (-850.0, 25.0)       # the west shore (x ~360): engineer on land, the point 100 out in the sea


def mission(name='CampSkill'):
    m = Mission(name=name, map=festival, facts={'life': LIFE})
    wall = iw.wall(WALL, length=SIDE, shape='square', lifetime=LIFE)
    eng = iw.engineer(ENG, wall_id=SEED, stand=iw.clear_of(wall), voice=None)
    m.units += [wall, iw.seed(SEED, WALL, size=CORE), eng]
    m.spawns |= {TANK}
    m.put(ENG, 'west field', *A_ENG, role='engineer a', name='UNIT - CNV Skill Eng A', angle=90.0)
    for k, (dx, dy) in A_SPOTS.items():
        m.waypoint(f'a{k}', f'CNV Skill A{k}', 'west field', dx, dy)
    for k, (dx, dy) in B_SPOTS.items():
        m.waypoint(f'b{k}', f'CNV Skill B{k}', 'west field', dx, dy)
        m.put(ENG, 'west field', dx, dy - 110.0, role=f'engineer b{k}', name=f'UNIT - CNV Skill Eng B{k}', angle=90.0)
        m.put(TANK, 'west field', dx + B_DIST[k], dy, role=f'tank {k}', name=f'UNIT - CNV Skill Tank {k}')
    m.put(ENG, 'gate 1', *C_ENG, role='engineer c', name='UNIT - CNV Skill Eng C', angle=90.0)
    for k, (dx, dy) in C_SPOTS.items():
        m.waypoint(f'c{k}', f'CNV Skill C{k}', 'gate 1', dx, dy)
    m.put(ENG, 'west field', *D_ENG, role='engineer d', name='UNIT - CNV Skill Eng D', angle=90.0)
    m.waypoint('d', 'CNV Skill D', 'west field', *D_SPOT)
    m.waypoint('d start', 'CNV Skill D Start', 'west field', *D_ENG)
    m.put(ENG, 'west field', *W_ENG, role='engineer w', name='UNIT - CNV Skill Eng W', angle=270.0)
    m.waypoint('w', 'CNV Skill W', 'west field', *W_SPOT)
    return m


MISSION = {'engine_skill': mission}
