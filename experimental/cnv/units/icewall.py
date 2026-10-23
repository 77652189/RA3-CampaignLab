"""冰幕工兵 (A4, campaign only; docs/story/units.md 4, outline.md A4: the engineers freeze walls of ice that seal the
festival grounds; work/story/unit_roster.md mechanism 7). An Allied engineer who raises an ice wall at a point: a
long, thin building that blocks the way, can be shot to pieces and melts after `lifetime` (LifetimeUpdate, as the
Nanoswarm's dome). Stand-ins: the Allied engineer; the wall wears the bunker's model (art last).

The wall comes from an OCLSpecialPower (the superweapons' way: an object creation list at the aimed point, at most
`reach` from him). Retail's Soviet engineer's way -- AssembleStructureSpecialAbilityUpdate, he walks there and builds
-- works with our wall too (bench 2026-10-22, retail_engineer: built by s4), should the design want him exposed while
he builds. Both need the wall compiled though the map places none (parts.assemble links every unit since).

Published: engineer: abilities freeze = its special power (NAMED_FIRE_SPECIAL_POWER_AT_WAYPOINT). wall: what it is,
params length / lifetime / health.
"""
import os
import re

import make_campnew2 as c2
from parts import Unit

SAGE = os.path.join(c2.SDK, 'SageXML')


def sub1(x, old, new):
    assert x.count(old) == 1, (old[:60], x.count(old))
    return x.replace(old, new, 1)


def cut(x, tag, id):
    """Drop the module <tag id="id" ...>...</tag>."""
    y, n = re.subn(rf'\s*<{tag}\s+id="{id}".*?</{tag}>', '', x, count=1, flags=re.S)
    assert n == 1, (tag, id)
    return y


def wall(id='CNV_IceWall', length=200, thick=24, lifetime=30, health=1500):
    x = open(os.path.join(SAGE, 'Soviet', 'Structures', 'SovietBunker.xml'), encoding='utf-8').read()
    x = sub1(x, 'id="SovietBunker"', f'id="{id}"')
    x = sub1(x, 'EditorName="SovietBunker"', f'EditorName="{id}"')
    x = sub1(x, 'KindOf="+GARRISON +FS_FACTORY +AUTO_RALLYPOINT +IGNORE_FOR_VICTORY', 'KindOf="+IGNORE_FOR_VICTORY')
    x = sub1(x, ' +GARRISONABLE_UNTIL_DESTROYED"', '"')
    x = re.sub(r'\s*<GameDependency>.*?</GameDependency>', '', x, count=1, flags=re.S)
    x = cut(x, 'GarrisonContain', 'ModuleTag_Garrison')
    x = cut(x, 'AttributeModifierAuraUpdate', 'ModuleTag_AttributeModifierAura')
    x = re.sub(r'\s*<InvisibilityBehavior\s+id="ModuleTag_Invisibility"\s*/>', '', x, count=1)
    x = sub1(x, 'MaxHealth="1500"', f'MaxHealth="{health}"')
    x = re.sub(r'<Geometry>.*?</Geometry>', f'''<Geometry>
			<Shape Type="BOX" MajorRadius="{length / 2}" MinorRadius="{thick / 2}" Height="20.0"
				ContactPointGeneration="STRUCTURE">
				<Offset x="0.0" y="0.0" z="0.0"/>
			</Shape>
		</Geometry>''', x, count=1, flags=re.S)
    x = sub1(x, '</Behaviors>', f'''	<LifetimeUpdate id="ModuleTag_CNV_Melt" DeathType="FADED" MinLifetime="{lifetime}s"
				MaxLifetime="{lifetime}s"/>
		</Behaviors>''')
    return Unit(id, x, what=f'冰墙：长 {length}、厚 {thick} 的建筑，挡路、能打碎（{health} 血），{lifetime} 秒后化掉',
                params=dict(length=length, thick=thick, lifetime=lifetime, health=health))


def retail_engineer(id='CNV_SovEngineer', structure='SovietBunker'):
    """Retail's Soviet engineer under our id, his bunker power as it is, building `structure` (the walk-and-build
    way, kept as a check)."""
    x = open(os.path.join(SAGE, 'Soviet', 'Units', 'SovietEngineer.xml'), encoding='utf-8').read()
    x = sub1(x, 'id="SovietEngineer"', f'id="{id}"')
    x = sub1(x, 'EditorName="SovietEngineer"', f'EditorName="{id}"')
    x = sub1(x, '<StructureTemplate>SovietBunker</StructureTemplate>', f'<StructureTemplate>{structure}</StructureTemplate>')
    return Unit(id, x, abilities={'freeze': 'SpecialPower_ConstructSovietBunker'},
                what=f'对照：原版苏联工程师，freeze = 原版造地堡的技能，造 {structure}', params=dict(wall=structure))


def engineer(id='CNV_IceEngineer', wall_id='CNV_IceWall', reach=300, reload='20s'):
    ids = dict(power=f'SpecialPower_{id}_Freeze', command=f'Command_{id}_Freeze', commandset=f'{id}CommandSet',
               button=f'Button_{id}_Freeze', ocl=f'OCL_{id}_Wall')
    x = open(os.path.join(SAGE, 'Allied', 'Units', 'AlliedEngineer.xml'), encoding='utf-8').read()
    x = sub1(x, 'id="AlliedEngineer"', f'id="{id}"')
    x = sub1(x, 'EditorName="AlliedEngineer"', f'EditorName="{id}"')
    x = sub1(x, 'CommandSet="AlliedEngineerCommandSet"', f'CommandSet="{ids["commandset"]}"')
    x = sub1(x, '</Behaviors>', f'''	<OCLSpecialPower id="ModuleTag_CNV_Freeze" SpecialPowerTemplate="{ids['power']}"
				UpdateModuleStartsAttack="false" AvailableAtStart="true" OCL="{ids['ocl']}" CreateLocation="CREATE_AT_LOCATION"/>
		</Behaviors>''')
    x = sub1(x, '</AssetDeclaration>', f'''	<ObjectCreationList id="{ids['ocl']}">
		<CreateObject Disposition="ON_GROUND_ALIGNED" Options="DO_NOT_TREAT_AS_STRUCTURE CREATE_AT_TARGET IGNORE_ALL_OBJECTS">
			<CreateObject>{wall_id}</CreateObject>
		</CreateObject>
	</ObjectCreationList>
	<SpecialPowerTemplate id="{ids['power']}" ReloadTime="{reload}" TargetType="LOCATION" MaxCastRange="{reach}"
		Flags="LIMIT_DISTANCE PATHABLE_ONLY FOGGED_SHROUDED_CELLS_OK" WaypointModeTerminal="false"/>
	<LogicCommand Type="SPECIAL_POWER" id="{ids['command']}">
		<SpecialPower>{ids['power']}</SpecialPower>
	</LogicCommand>
	<LogicCommandSet id="{ids['commandset']}">
		<Cmd>{ids['command']}</Cmd>
		<Cmd>Command_CaptureBuilding</Cmd>
		<Cmd>Command_MoveToPositionAndCollect</Cmd>
	</LogicCommandSet>
</AssetDeclaration>''')
    ui = f'''<?xml version="1.0" encoding="UTF-8"?>
<AssetDeclaration xmlns="uri:ea.com:eala:asset" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
	<UnitAbilityButtonTemplate id="{ids['button']}" LogicCommand="{ids['command']}">
		<Data>
			<TargetedSpecialPower StateData="ButtonStateAbilityConstructSovietBunker" ValidTargetCursor="TargetAbility"/>
		</Data>
	</UnitAbilityButtonTemplate>
</AssetDeclaration>
'''
    ui_file = f'{id}_UI.xml'
    return Unit(id, x, files={ui_file: ui}, also=[ui_file],
                link=[f'SpecialPowerTemplate:{ids["power"]}', f'LogicCommand:{ids["command"]}',
                      f'LogicCommandSet:{ids["commandset"]}', f'UnitAbilityButtonTemplate:{ids["button"]}',
                      f'ObjectCreationList:{ids["ocl"]}'],
                names=ids, abilities={'freeze': ids['power']},
                what=f'冰幕工兵（盟军工程师底）：freeze 在 {reach} 以内的一点冻出一道 {wall_id}',
                params=dict(wall=wall_id, reach=reach, reload=reload))
