"""黑尔的克隆体 (the clones' mind control; docs/story/units.md 6: a clone controls a unit for as long as it lives, killing
the clone frees it -- the user's choice C, 2026-10-22; work/story/unit_roster.md mechanism 5).

The taking: the spy's bribe (DominateEnemySpecialPower, PermanentlyConvert true as retail's): the enemy units within
`radius` of the clone change hands at once (bench 2026-10-22: pressed at s10, the unit wore the new colour by s14).
The letting go is the map's: each clone stands on a side of its own (an idle player of the map: maps.island SPARE),
so what it took is all that side owns besides itself; when the clone dies the mission hands that side's units back
(PLAYER_TRANSFER_OWNERSHIP_PLAYER) -- a change of owner, health and rank kept (the RA2 way the user described, a
swap for a copy, is not needed).

Tried and dropped (bench 2026-10-22): PermanentlyConvert false takes nothing; TemporaryOwnerSpecialPower (schema
only, C&C3's) kills its own bearer within 4 s.
Stand-in: the Allied spy, his bribe swapped for ours (art last).

maiden(): the mind maiden, ours, the same power: she takes a held unit back while its clone lives.

Published: abilities control = the power's command (NAMED_USE_COMMANDBUTTON_ABILITY).
"""
import os
import re

import make_campnew2 as c2
from parts import Unit

SAGE = os.path.join(c2.SDK, 'SageXML', 'Allied', 'Units')


def sub1(x, old, new):
    assert x.count(old) == 1, (old[:60], x.count(old))
    return x.replace(old, new, 1)


def maiden(id='CNV_MindMaiden', radius=80, reload='15s'):
    """心灵巫女 (J8): ours, the same bribe the other way -- she takes back a unit a clone holds, one at a time (a small
    radius: she walks up to it). Which units she may take is the level's to narrow (her filter takes any enemy
    infantry or vehicle for now; J8 would keep her to the player's own faction's types)."""
    u = clone(id=id, radius=radius, reload=reload)
    u.what = f'心灵巫女（间谍底）：control 把身边 {radius} 内被控的单位拿回来'
    return u


def clone(id='CNV_Clone', radius=65, reload='10s'):
    ids = dict(power=f'SpecialPower_{id}_Control', command=f'Command_{id}_Control', commandset=f'{id}CommandSet',
               button=f'Button_{id}_Control')
    x = open(os.path.join(SAGE, 'AlliedInfiltrationInfantry.xml'), encoding='utf-8').read()
    x = sub1(x, 'id="AlliedInfiltrationInfantry"', f'id="{id}"')
    x = sub1(x, 'EditorName="AlliedInfiltrationInfantry"', f'EditorName="{id}"')
    x = sub1(x, 'CommandSet="AlliedInfiltrationInfantryCommandSet"', f'CommandSet="{ids["commandset"]}"')
    x = re.sub(r'\s*<GameDependency>.*?</GameDependency>', '', x, count=1, flags=re.S)   # Allied tech 2
    bribe = re.search(r'\s*<SpecialPower\s+id="ModuleTag_Bribe".*?</DominateEnemySpecialPower>', x, flags=re.S)
    assert bribe, 'the spy has no bribe'
    x = x[:bribe.start()] + f'''
			<SpecialPower id="ModuleTag_CNV_ControlTrigger" SpecialPowerTemplate="{ids['power']}"
				UpdateModuleStartsAttack="true"/>
			<DominateEnemySpecialPower id="ModuleTag_CNV_Control" Options="BUSY_DURING_PACK"
				SpecialPowerTemplate="{ids['power']}" UnpackTime="0s" PackTime="1s" StartAbilityRange="0.0"
				DominateRadius="{radius}" PermanentlyConvert="true">
				<AttributeModifierAffects Rule="ANY" Relationship="ENEMIES" Include="VEHICLE INFANTRY"/>
			</DominateEnemySpecialPower>''' + x[bribe.end():]
    x = sub1(x, '</AssetDeclaration>', f'''	<SpecialPowerTemplate id="{ids['power']}" ReloadTime="{reload}" TargetType="NONE"
		Flags="NEEDS_OBJECT_FILTER" WaypointModeTerminal="false">
		<ObjectFilter Rule="ANY" Relationship="ENEMIES" Include="INFANTRY VEHICLE" Exclude="AIRCRAFT"/>
	</SpecialPowerTemplate>
	<LogicCommand Type="SPECIAL_POWER" id="{ids['command']}">
		<SpecialPower>{ids['power']}</SpecialPower>
	</LogicCommand>
	<LogicCommandSet id="{ids['commandset']}">
		<Cmd>{ids['command']}</Cmd>
	</LogicCommandSet>
</AssetDeclaration>''')
    ui = f'''<?xml version="1.0" encoding="UTF-8"?>
<AssetDeclaration xmlns="uri:ea.com:eala:asset" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
	<UnitAbilityButtonTemplate id="{ids['button']}" LogicCommand="{ids['command']}">
		<Data>
			<SpecialPower StateData="ButtonStateAbilityBribe"/>
		</Data>
	</UnitAbilityButtonTemplate>
</AssetDeclaration>
'''
    ui_file = f'{id}_UI.xml'
    return Unit(id, x, files={ui_file: ui}, also=[ui_file],
                link=[f'SpecialPowerTemplate:{ids["power"]}', f'LogicCommand:{ids["command"]}',
                      f'LogicCommandSet:{ids["commandset"]}', f'UnitAbilityButtonTemplate:{ids["button"]}'],
                names=ids, abilities={'control': ids['command']},
                what=f'克隆体（间谍底）：control 收买身边 {radius} 内的敌方单位；每个克隆体要站在自己的一方，'
                     '死后由关卡把那一方的单位还回去',
                params=dict(radius=radius, reload=reload))
