r"""The convoy truck (experimental/cnv/units/convoy.py, retail's ore collector) carrying a container instead of
ore (convoy_kit.py's CNConvoyCargo), on a bench scene to look at -- CampConvoyLook:

  west field: one truck standing, one sent 400 north at 3 s (does the cargo ride with it), a retail Guardian for
  scale.

  python -I -X utf8 experimental/units/convoy_look.py         -> Documents\Red Alert 3\Mods\CampConvoyLook
(from a worktree set CNV_SDK to the shared SDK; run convoy_kit.py first)

dress(unit) is the whole change the unit module needs: the collector's ore draw (ModuleTag_Draw_Ore, the gold
filling its bin as it mines) becomes one of the container, drawn at the truck's origin (the model carries its place
in the bin).
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), 'cnv'))
import parts                                    # noqa: E402  (puts experimental/campaign on the path)
from maps import island                         # noqa: E402
from units import convoy                        # noqa: E402

NAME = 'CampConvoyLook'                         # <= 15 characters, no underscore
CARGO = 'CNConvoyCargo'
GUARDIAN = 'AlliedAntiVehicleVehicleTech1'


def dress(unit, model=CARGO):
    x, n = re.subn(r'<ScriptedModelDraw\s+id="ModuleTag_Draw_Ore".*?</ScriptedModelDraw>', f'''<ScriptedModelDraw id="ModuleTag_Draw_Cargo" OkToChangeModelColor="false">
				<ModelConditionState ParseCondStateType="PARSE_DEFAULT">
					<Model Name="{model.upper()}" />
				</ModelConditionState>
				<AnimationState ParseCondStateType="PARSE_DEFAULT">
				</AnimationState>
			</ScriptedModelDraw>''', unit.xml, count=1, flags=re.S)
    assert n == 1, n
    x, n = re.subn(r'<Includes>', f'<Includes>\n\t\t<Include type="all" source="ART:{model}.w3x" />', x, count=1)
    assert n == 1, n
    unit.xml = x
    unit.params['model'] = model
    return unit


def mission():
    truck = dress(convoy.truck('CNV_ConvoyTruckL'))
    m = parts.Mission(name=NAME, map=island, units=[truck])
    m.put(truck.id, 'west field', 60, 60, name='UNIT - CNV Look Truck', role='truck', angle=0.0)
    m.put(truck.id, 'west field', 250, -200, name='UNIT - CNV Look Truck B', role='truck moving')
    m.put(GUARDIAN, 'west field', 60, 150, role='guardian', angle=0.0)
    m.waypoint('goal', 'CNV Look Goal', 'west field', 250, 200)
    m.scripts += [
        parts.Script('Look - start', [], [('MAP_REVEAL_ALL_PERM', m.player('p1')),
                                          ('SET_MILLISECOND_TIMER', 'Look - go timer', 3.0)]),
        parts.Script('Look - go', [('TIMER_EXPIRED', 'Look - go timer')],
                     [('MOVE_NAMED_UNIT_TO', m.role('truck moving').name, m.mark('goal'))]),
    ]
    return m


if __name__ == '__main__':
    print(parts.assemble(mission()))
