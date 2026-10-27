r"""The Liberty (experimental/cnv/units/liberty.py, a copy of the Kirov) in liberty_kit.py's look -- the flying
Liberty Island fortress CNLiberty, retail's statue CNLibStatue on its core, the turning rings CNLibRings -- on a
bench scene, CampLibLook:

  west field: one Liberty hovering, sent 500 north at 3 s (does it read from the RTS camera, do the statue and the
  rings ride with it), Guardians and a war factory for scale.

  python -I -X utf8 experimental/units/liberty_look.py        -> Documents\Red Alert 3\Mods\CampLibLook
(from a worktree set CNV_SDK to the shared SDK; run tripo_unit.py libertyisle and liberty_kit.py first)

liberty.liberty() wears it by default since 2026-10-27 (liberty.dress).
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), 'cnv'))
import parts                                    # noqa: E402  (puts experimental/campaign on the path)
from maps import island                         # noqa: E402
from units import liberty as lib                # noqa: E402

NAME = 'CampLibLook'                            # <= 15 characters, no underscore
GUARDIAN = 'AlliedAntiVehicleVehicleTech1'
FACTORY = 'AlliedWarFactory'


def mission():
    carrier = lib.liberty('CNV_LibertyL')
    m = parts.Mission(name=NAME, map=island, units=[carrier])
    m.put(carrier.id, 'west field', 150, 0, name='UNIT - CNV Look Liberty', role='carrier', angle=0.0)
    m.put(GUARDIAN, 'west field', 150, -260, role='guardian', angle=0.0)
    m.put(GUARDIAN, 'west field', 200, -260, role='guardian 2', angle=0.0)
    m.put(FACTORY, 'west field', 420, -300, role='factory', angle=0.0)
    m.waypoint('goal', 'CNV Look Goal', 'west field', 150, 500)
    m.scripts += [
        parts.Script('Look - start', [], [('MAP_REVEAL_ALL_PERM', m.player('p1')),
                                          ('SET_MILLISECOND_TIMER', 'Look - go timer', 3.0)]),
        parts.Script('Look - go', [('TIMER_EXPIRED', 'Look - go timer')],
                     [('MOVE_NAMED_UNIT_TO', m.role('carrier').name, m.mark('goal'))]),
    ]
    return m


if __name__ == '__main__':
    print(parts.assemble(mission()))
