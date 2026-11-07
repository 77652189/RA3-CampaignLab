"""Engine probe mission (R8, docs/story/sim-vs-bench-a4.md last section): how far does a unit on its own look for
enemies and go after them -- idle, guarding, attack-moving (checks/engine_acquire.py).

The west field (island map), offsets from 'west field':
  S (0, -400)          the attacker's birth point (an enemy s1 'AlliedAntiVehicleVehicleTech1', weapon range 150,
                       vision 200, shroud 500; made at 1 s on the s1 crew 'Aq')
  T                    the player's tank, named, NO_ATTACK: idle / guard (0, -400 + d) straight north of S;
                       attack-move (300, -400 + d) beside the path, d to the side of the path's middle
  E (600, -400)        the attack-move end
Published waypoints: s, e.
"""
from maps import island
from parts import Mission

TANK = 'AlliedAntiVehicleVehicleTech1'
S, E = (0.0, -400.0), (600.0, -400.0)
VARIANTS = ('idle180', 'idle260', 'idle400', 'guard260', 'guard400', 'am260', 'am400', 'idle200', 'idle220', 'idle240')


def target(variant):
    d = float(variant[-3:])
    return (300.0, S[1] + d) if variant.startswith('am') else (0.0, S[1] + d)


def mission(name, variant):
    m = Mission(name=name, map=island, facts={'variant': VARIANTS.index(variant)})
    m.crew('Aq', 's1')
    m.put(TANK, 'west field', *target(variant), role='tank', name='UNIT - CNV Aq Tank')
    for part, label, at in (('s', 'S', S), ('e', 'E', E), ('t', 'T', target(variant))):
        m.waypoint(part, f'CNV Aq {label}', 'west field', *at)
    return m


MISSION = {f'acquire_{v}': (lambda v=v: mission('CampAq' + v[0].upper() + str(VARIANTS.index(v)), v)) for v in VARIANTS}
