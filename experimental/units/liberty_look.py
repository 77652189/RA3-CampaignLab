r"""The Liberty (experimental/cnv/units/liberty.py, a copy of the Kirov) wearing liberty_kit.py's look -- the flying
Liberty Island fortress CNLiberty with retail's statue CNLibStatue on its core -- on a bench scene, CampLibLook:

  west field: one Liberty hovering, sent 500 north at 3 s (does it read from the RTS camera, does the statue ride
  with it), Guardians and a war factory for scale.

  python -I -X utf8 experimental/units/liberty_look.py        -> Documents\Red Alert 3\Mods\CampLibLook
(from a worktree set CNV_SDK to the shared SDK; run tripo_unit.py libertyisle and liberty_kit.py first)

Look only and not wired into liberty.py (that is the levels line's unit; ask 总控 first): dress() here.
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), 'cnv'))
import parts                                    # noqa: E402  (puts experimental/campaign on the path)
from maps import island                         # noqa: E402
from units import liberty as lib                # noqa: E402
from units.icewall import sub1                  # noqa: E402

NAME = 'CampLibLook'                            # <= 15 characters, no underscore
GUARDIAN = 'AlliedAntiVehicleVehicleTech1'
FACTORY = 'AlliedWarFactory'


def dress(unit, model='CNLiberty', statue='CNLibStatue', rings='CNLibRings'):
    """The carrier drawing `model`, `statue` and `rings` (all at its origin, each carrying its place over the core;
    the rings looping their turn, <rings>_IDLE) in place of the Kirov; the drones still launch from FX_WEAPON
    (CNLiberty carries the Kirov's bone names)."""
    x, n = re.subn(r'<Draws>.*?</Draws>', f'''<Draws>
			<ScriptedModelDraw id="ModuleTag_Draw" OkToChangeModelColor="true">
				<ModelConditionState ParseCondStateType="PARSE_DEFAULT">
					<Model Name="{model.upper()}" />
					<WeaponLaunchBone WeaponSlotType="PRIMARY_WEAPON" BoneName="FX_WEAPON" />
				</ModelConditionState>
				<AnimationState ParseCondStateType="PARSE_DEFAULT">
				</AnimationState>
			</ScriptedModelDraw>
			<ScriptedModelDraw id="ModuleTag_Draw_Statue" OkToChangeModelColor="false">
				<ModelConditionState ParseCondStateType="PARSE_DEFAULT">
					<Model Name="{statue.upper()}" />
				</ModelConditionState>
				<AnimationState ParseCondStateType="PARSE_DEFAULT">
				</AnimationState>
			</ScriptedModelDraw>
			<ScriptedModelDraw id="ModuleTag_Draw_Rings" OkToChangeModelColor="false">
				<ModelConditionState ParseCondStateType="PARSE_DEFAULT">
					<Model Name="{rings.upper()}" />
				</ModelConditionState>
				<AnimationState ParseCondStateType="PARSE_DEFAULT">
					<Animation AnimationName="{rings.upper()}_IDLE" AnimationMode="LOOP" />
				</AnimationState>
			</ScriptedModelDraw>
		</Draws>''', unit.xml, count=1, flags=re.S)
    assert n == 1, n
    unit.xml = sub1(x, '<Includes>', f'<Includes>\n\t\t<Include type="all" source="ART:{model}.w3x" />'
                                     f'\n\t\t<Include type="all" source="ART:{statue}.w3x" />'
                                     f'\n\t\t<Include type="all" source="ART:{rings}.w3x" />'
                                     f'\n\t\t<Include type="all" source="ART:{rings}_IDLE.w3x" />')
    unit.params['look'] = (model, statue, rings)
    return unit


def mission():
    carrier = dress(lib.liberty('CNV_LibertyL'))
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
