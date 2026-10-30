"""超时空信标兵 (A5, campaign only; docs/story/units.md 4, work/story/unit_roster.md mechanism 8): an Allied
trooper who pulls a squad to himself. One targeted button: everyone of ours within `radius` of the point he aims at
(at most `reach` away from him) is teleported to his side -- the A5 plan, he slips into the lock's control room and
the squad comes after him. Built on TeleportToCasterSpecialPower, a module the schema has and retail never uses.
Stand-in: the Peacekeeper (his shotgun stays; the riot shield goes with his command set).

Published: abilities pull = its special power (NAMED_FIRE_SPECIAL_POWER_AT_WAYPOINT fires it at a point -- ignoring
the reach: a mission script can pull from anywhere; a player's click beyond it does nothing).
"""
import os

import make_campnew2 as c2
from parts import Unit
from units import look

SAGE = os.path.join(c2.SDK, 'SageXML', 'Allied', 'Units')


def sub1(x, old, new):
    assert x.count(old) == 1, (old[:60], x.count(old))
    return x.replace(old, new, 1)


@look.named('beacon')
def beacon(id='CNV_Beacon', radius=150, reach=1500, reload='30s', land=(40, 140)):
    """radius: around the aimed point, who is pulled. reach: how far from him he may aim. land: the ring around
    him (min, max) the pulled ones are put down in."""
    ids = dict(power=f'SpecialPower_{id}_Pull', command=f'Command_{id}_Pull', commandset=f'{id}CommandSet',
               button=f'Button_{id}_Pull')
    x = open(os.path.join(SAGE, 'AlliedAntiInfantryInfantry.xml'), encoding='utf-8').read()
    x = sub1(x, 'id="AlliedAntiInfantryInfantry"', f'id="{id}"')
    x = sub1(x, 'EditorName="AlliedAntiInfantryInfantry"', f'EditorName="{id}"')
    x = sub1(x, 'CommandSet="AlliedAntiInfantryInfantryCommandSet"', f'CommandSet="{ids["commandset"]}"')
    x = sub1(x, '</Behaviors>', f'''	<SpecialPower id="ModuleTag_CNV_Pull" SpecialPowerTemplate="{ids['power']}"
				UpdateModuleStartsAttack="true"/>
			<TeleportToCasterSpecialPower id="ModuleTag_CNV_PullUpdate" SpecialPowerTemplate="{ids['power']}"
				StartAbilityRange="99999.0" UnpackTime="0.5s" PackTime="0s" Radius="{radius}"
				MinDestinationRadius="{land[0]}" MaxDestinationRadius="{land[1]}"
				MaxRangeFromCasterSP="{reach}" MaxRangeFromCasterMP="{reach}" KillObjectsIfPlacedInBadSpot="false"/>
		</Behaviors>''')
    x = sub1(x, '</AssetDeclaration>', f'''	<SpecialPowerTemplate id="{ids['power']}" ReloadTime="{reload}" TargetType="LOCATION" MaxCastRange="{reach}"
		Flags="LIMIT_DISTANCE FOGGED_SHROUDED_CELLS_OK CAN_NOT_BE_SCRAMBLED" WaypointModeTerminal="false">
		<ObjectFilter Rule="ANY" Include="INFANTRY VEHICLE" Relationship="SAME_PLAYER ALLIES"
			StatusBitFlagsExclude="SUBMERGED NOT_IN_WORLD"/>
	</SpecialPowerTemplate>
	<LogicCommand Type="SPECIAL_POWER" id="{ids['command']}">
		<SpecialPower>{ids['power']}</SpecialPower>
	</LogicCommand>
	<LogicCommandSet id="{ids['commandset']}">
		<Cmd>{ids['command']}</Cmd>
		<Cmd>Command_AttackMove</Cmd>
	</LogicCommandSet>
</AssetDeclaration>''')
    ui = f'''<?xml version="1.0" encoding="UTF-8"?>
<AssetDeclaration xmlns="uri:ea.com:eala:asset" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
	<UnitAbilityButtonTemplate id="{ids['button']}" LogicCommand="{ids['command']}">
		<Data>
			<TargetedSpecialPower StateData="ButtonStateAbilityLeap" ValidTargetCursor="TargetAbility"/>
		</Data>
	</UnitAbilityButtonTemplate>
</AssetDeclaration>
'''
    ui_file = f'{id}_UI.xml'
    return Unit(id, x, files={ui_file: ui}, also=[ui_file],
                link=[f'SpecialPowerTemplate:{ids["power"]}', f'LogicCommand:{ids["command"]}',
                      f'LogicCommandSet:{ids["commandset"]}', f'UnitAbilityButtonTemplate:{ids["button"]}'],
                names=ids, abilities={'pull': ids['power']},
                what=f'超时空信标兵：pull 对一个点放技能，那里 {radius} 内的我方部队传到他身边（最远 {reach}）',
                params=dict(radius=radius, reach=reach, reload=reload, land=land))
