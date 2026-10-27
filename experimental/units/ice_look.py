r"""The 冰幕工兵's ice and the festival's sculptures in their own look (experimental/cnv/units/icewall.py and
festival.py wear it by default since 2026-10-26; the models: ice_kit.py), on a bench scene to look at --
CampIceLook:

  west field: a wall placed at the start (lasts 120 s) with a retail Guardian beside it for scale; the engineer
  sent at 5 s to build a core 170 north of him (the core melts into a wall, as in A4); a second placed wall 300
  east with two enemy Hammers ordered at it at 8 s (how it breaks); two ice sculptures, the third Hammer ordered
  at the far one.

  python -I -X utf8 experimental/units/ice_look.py            -> Documents\Red Alert 3\Mods\CampIceLook
(from a worktree set CNV_SDK to the shared SDK; run ice_kit.py first: it writes the models into the SDK's Art)
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), 'cnv'))
import parts                                    # noqa: E402  (puts experimental/campaign on the path)
from maps import island                         # noqa: E402
from units import festival as fest              # noqa: E402
from units import icewall as iw                 # noqa: E402

NAME = 'CampIceLook'                            # <= 15 characters, no underscore
GUARDIAN = 'AlliedAntiVehicleVehicleTech1'
HAMMER = 'SovietAntiVehicleVehicleTech1'


def mission():
    placed = iw.wall('CNV_IceWallL', length=160, shape='square', lifetime=120)
    wall = iw.wall('CNV_IceWallLB', length=160, shape='square')
    core = iw.seed('CNV_IceSeedL', wall.id)
    eng = iw.engineer('CNV_IceEngL', wall_id=core.id)
    sculpt = fest.sculpture('CNV_IceSculptL')
    m = parts.Mission(name=NAME, map=island, units=[placed, wall, core, eng, sculpt])
    m.put(sculpt.id, 'west field', 240, 20, name='UNIT - CNV Look Sculpture', role='sculpture', angle=-1.5708)
    m.put(sculpt.id, 'west field', 470, -20, name='UNIT - CNV Look Sculpture B', role='sculpture target',
          angle=-1.5708)
    # all east of the field's middle: x -220 was the shallows (bench 2026-10-26: he rode there on his jet ski)
    m.put(placed.id, 'west field', 60, 170, name='UNIT - CNV Look Wall', role='wall', angle=0.0)
    m.put(GUARDIAN, 'west field', 190, 190, role='guardian', angle=1.5708)
    m.put(eng.id, 'west field', 60, -170, name='UNIT - CNV Look Engineer', role='engineer')
    m.waypoint('spot', 'CNV Look Spot', 'west field', 60, 0)
    m.put(placed.id, 'west field', 360, 60, name='UNIT - CNV Look Target', role='target', angle=0.0)
    for k, dx in enumerate((-60, 0, 60)):
        m.put(HAMMER, 'west field', 360 + dx, -90, side='s1', name=f'UNIT - CNV Look Hammer {k + 1}',
              role=f'hammer {k + 1}')
    m.scripts += [
        parts.Script('Look - start', [], [('MAP_REVEAL_ALL_PERM', m.player('p1')),
                                          ('SET_MILLISECOND_TIMER', 'Look - freeze timer', 5.0),
                                          ('SET_MILLISECOND_TIMER', 'Look - attack timer', 8.0)]),
        parts.Script('Look - freeze', [('TIMER_EXPIRED', 'Look - freeze timer')],
                     [('NAMED_FIRE_SPECIAL_POWER_AT_WAYPOINT', m.role('engineer').name,
                       m.ability('engineer', 'freeze'), m.mark('spot'))]),
        parts.Script('Look - attack', [('TIMER_EXPIRED', 'Look - attack timer')],
                     [('NAMED_ATTACK_NAMED', h.name, m.role('target').name) for h in m.roles('hammer')[:2]] +
                     [('NAMED_ATTACK_NAMED', m.role('hammer 3').name, m.role('sculpture target').name)]),
    ]
    return m


if __name__ == '__main__':
    print(parts.assemble(mission()))
