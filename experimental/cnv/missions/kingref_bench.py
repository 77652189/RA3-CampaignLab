"""Level-line probe mission: why A4's Ghost King stood on the bridge and did not shoot the ice wall when the script
re-gave its attack order every frame (devices/horn.py ghost_scripts before 11-07; checks/engine_kingref.py).

A's engine_reorder probe (missions/reorder_bench.py) showed an Athena-type tank walks and fires under every-frame orders;
A4's King is JapanAntiVehicleVehicleTech3 and its target was a SET_REF pick, so the probe here changes those two things:
the attacker (King) and the way the wall is named (a name, or a SET_REF reference to an unnamed wall).

The west field (island map), offsets from 'west field' (the same layout as the reorder probe):
  S (0, -400)  the attacker's birth point (an enemy s1 King, made at 1 s on the s1 crew 'Reo')
  W (0,  500)  the player's ice wall (no lifetime), 900 from S; named in the 'name' variants, unnamed in the 'ref' ones
Published waypoints: s, mid (0, 0), near (0, 330).
"""
from maps import island
from parts import Mission
from units import icewall as iw

WALL = 'CNV_ReoWall'
VARIANTS = ('kone', 'kevery', 'rone', 'revery', 'aref')
S, W = (0.0, -400.0), (0.0, 500.0)


def mission(name, variant):
    m = Mission(name=name, map=island, facts={'variant': VARIANTS.index(variant)})
    m.units += [iw.wall(WALL, length=60, shape='square', lifetime=None)]
    m.crew('Reo', 's1')
    named = variant in ('kone', 'kevery')
    m.put(WALL, 'west field', *W, role='wall', name='UNIT - CNV Reo Wall' if named else '')
    for part, label, at in (('s', 'S', S), ('mid', 'Mid', (0.0, 0.0)), ('near', 'Near', (0.0, 330.0))):
        m.waypoint(part, f'CNV Reo {label}', 'west field', *at)
    return m


MISSION = {f'kingref_{v}': (lambda v=v: mission('CampKr' + v[:3].capitalize(), v)) for v in VARIANTS}
