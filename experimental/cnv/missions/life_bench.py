"""Engine probe mission: how long an object with a LifetimeUpdate lives, and how long an ice engineer's power takes
to leave a wall (checks/engine_life.py; the simulator's rules R1 and R5, docs/story/sim-vs-bench-a4.md).

Festival's west field. At A a script creates A4's kind of ice wall (a square, lifetime 30 s) by name; at B the ice
core (seed, lifetime 5.5 s) that, when its life is up, leaves an unnamed wall of the same kind where it stood -- the
engineer's way, without the engineer. At C and D two ice engineers (A4's: he builds the core, horn.py) are told to
freeze: engineer 1 stands within his StartAbilityRange of C (no walk), engineer 2 400 short of D.
"""
from maps import festival
from parts import Mission
from units import icewall as iw

WALL, SEED, ENG = 'CNV_LifeWall', 'CNV_LifeSeed', 'CNV_LifeEng'
LIFE, SIDE, CORE = 30, 160, 20              # the wall's lifetime (s) and side; the core's side (horn.py's sizes)
SPOTS = {'A': (-300.0, -300.0), 'B': (-300.0, 0.0), 'C': (100.0, -300.0), 'D': (100.0, 250.0)}
ENGINEERS = {1: (100.0, -410.0), 2: (100.0, -150.0)}      # 110 south of C; 400 south of D


def mission():
    m = Mission(name='CampLife', map=festival, facts={'life': LIFE})
    wall = iw.wall(WALL, length=SIDE, shape='square', lifetime=LIFE)
    eng = iw.engineer(ENG, wall_id=SEED, stand=iw.clear_of(wall), voice=None)
    m.units += [wall, iw.seed(SEED, WALL, size=CORE), eng]
    for k, (dx, dy) in SPOTS.items():
        m.waypoint(f'life {k}', f'CNV Life {k}', 'west field', dx, dy)
    for k, (dx, dy) in ENGINEERS.items():
        m.put(ENG, 'west field', dx, dy, role=f'engineer {k}', name=f'UNIT - CNV Life Eng {k}', angle=90.0)
    return m


MISSION = {'engine_life': mission}
