"""冰幕工兵 (A4, campaign only; docs/story/units.md 4, outline.md A4: the engineers freeze walls of ice that seal the
festival grounds; work/story/unit_roster.md mechanism 7). An Allied engineer who raises an ice wall at a point: a
long, thin building that blocks the way, can be shot to pieces and melts after `lifetime` (LifetimeUpdate, as the
Nanoswarm's dome). Stand-ins: the Allied engineer; the wall wears the bunker's model (art last).

He walks to the spot and builds it (docs/story/units.md 6: exposed while he builds), the Soviet engineer's bunker
way: AssembleStructureSpecialAbilityUpdate, its power aimed LOCATION_AND_ANGLE (placing, a drag turns the wall).
The other way, build=False, an OCLSpecialPower (the superweapons': the wall appears at the aimed point, at most
`reach` from him), stays for ice_spawn's linking check. Both need the wall compiled though the map places none
(parts.assemble links every unit since).

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


def wall(id='CNV_IceWall', length=200, thick=24, lifetime=30, health=1500, what='', shape='bar', spot=False):
    """lifetime None: it never melts (the festival's sculptures and snow banks, units/festival.py).

    shape: 'bar' (length x thick), 'disc' (a cylinder `length` across) or 'square' (length x length) -- the last two
    block about the same whichever way they are turned. spot: placing judged by a small circle at the middle only,
    so it goes in snug between other buildings. Bench 2026-10-23: built by the engineer the bar comes out at 45
    degrees (the default placing angle), both when a script fires the power and when it is placed by hand; a drag on
    the bench did not turn the placing (posted mouse messages), and a second button for the other direction cannot
    show (one ability slot per unit). The 45-degree bar left plaza gates open; a disc, and a square with a spot,
    placed by the map, did not hold them either (a cylinder does not block the way; a placing spot seems to stand in
    for the shape in pathfinding). A square without a spot, left by a seed() core, holds."""
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
    body = {'bar': f'Type="BOX" MajorRadius="{length / 2}" MinorRadius="{thick / 2}"',
            'square': f'Type="BOX" MajorRadius="{length / 2}" MinorRadius="{length / 2}"',
            'disc': f'Type="CYLINDER" MajorRadius="{length / 2}"'}[shape]
    place = f'<PlacementShape Type="CYLINDER" MajorRadius="{thick}" Height="20.0"/>\n\t\t\t' if spot else ''
    x = re.sub(r'<Geometry>.*?</Geometry>', f'''<Geometry>
			{place}<Shape {body} Height="20.0" ContactPointGeneration="STRUCTURE">
				<Offset x="0.0" y="0.0" z="0.0"/>
			</Shape>
		</Geometry>''', x, count=1, flags=re.S)
    if lifetime is not None:
        x = sub1(x, '</Behaviors>', f'''	<LifetimeUpdate id="ModuleTag_CNV_Melt" DeathType="FADED" MinLifetime="{lifetime}s"
				MaxLifetime="{lifetime}s"/>
		</Behaviors>''')
    form = {'bar': f'长 {length}、厚 {thick}', 'disc': f'直径 {length} 的圆冰堆', 'square': f'{length} 见方的冰块'}[shape]
    return Unit(id, x, what=what or f'冰墙：{form}的建筑，挡路、能打碎（{health} 血），{lifetime} 秒后化掉',
                params=dict(length=length, thick=thick, lifetime=lifetime, health=health, shape=shape, spot=spot))


def seed(id='CNV_IceSeed', wall_id='CNV_IceWall', angle=0, assembly=5, size=40):
    """What the engineer builds when the wall must go where a whole wall could not be placed: a small core (placed
    anywhere a `size` square fits) that melts as his building ends and leaves the wall `wall_id` where it stood --
    created by an object creation list that ignores other objects, so the wall may lie over its neighbours' edges.
    Shot down while he builds, it leaves nothing (only its melting makes the wall).

    angle: asked of the creation list as an ABSOLUTE_ANGLE (retail's time bomb way) -- bench 2026-10-23
    (ice_turns): it does not turn the wall; bars left at 0 and at 90 both let a runner by where a square held. Give
    it a square (wall(shape='square')), which blocks whichever way it comes out."""
    ocl = f'OCL_{id}_Wall'
    u = wall(id, length=size, thick=size, lifetime=assembly + 0.5, health=400,
             what=f'冰核：工兵造的 {size} 见方小块，造好时化掉，原地按绝对 {angle} 度留下 {wall_id}；造的时候被打掉就没有墙')
    u.xml = sub1(u.xml, '</Behaviors>', f'''	<CreateObjectDie id="ModuleTag_CNV_Wall" CreationList="{ocl}">
				<DieMuxData DeathTypes="FADED"/>
			</CreateObjectDie>
		</Behaviors>''')
    u.xml = sub1(u.xml, '</AssetDeclaration>', f'''	<ObjectCreationList id="{ocl}">
		<CreateObject Options="IGNORE_ALL_OBJECTS" Disposition="ON_GROUND_ALIGNED ABSOLUTE_ANGLE"
			DispositionAngle="{angle}d" Count="1">
			<CreateObject>{wall_id}</CreateObject>
		</CreateObject>
	</ObjectCreationList>
</AssetDeclaration>''')
    u.link = [f'ObjectCreationList:{ocl}']
    u.params.update(wall=wall_id, angle=angle)
    return u


def clear_of(w, size=15):
    """An engineer's `stand` that keeps him (`size` across) out of wall w however it lies about the spot: its
    half-diagonal and his size."""
    p = w.params
    side = p['length'] if p['shape'] in ('square', 'disc') else p['thick']
    return round(((p['length'] / 2) ** 2 + (side / 2) ** 2) ** 0.5 + size)


def retail_engineer(id='CNV_SovEngineer', structure='SovietBunker'):
    """Retail's Soviet engineer under our id, his bunker power as it is, building `structure` (the walk-and-build
    way, kept as a check)."""
    x = open(os.path.join(SAGE, 'Soviet', 'Units', 'SovietEngineer.xml'), encoding='utf-8').read()
    x = sub1(x, 'id="SovietEngineer"', f'id="{id}"')
    x = sub1(x, 'EditorName="SovietEngineer"', f'EditorName="{id}"')
    x = sub1(x, '<StructureTemplate>SovietBunker</StructureTemplate>', f'<StructureTemplate>{structure}</StructureTemplate>')
    return Unit(id, x, abilities={'freeze': 'SpecialPower_ConstructSovietBunker'},
                what=f'对照：原版苏联工程师，freeze = 原版造地堡的技能，造 {structure}', params=dict(wall=structure))


def engineer(id='CNV_IceEngineer', wall_id='CNV_IceWall', reach=300, reload='20s', build=True, assembly='5s',
             stand=30):
    """build (the user's decision, 2026-10-22): he walks to the spot and stands building for `assembly` -- exposed
    meanwhile -- the Soviet engineer's bunker way (AssembleStructure), its LOCATION_AND_ANGLE target: placing, a drag
    turns the wall. build=False: the wall appears at a point within `reach` (an OCL; ice_spawn's linking check).

    stand: how far from the spot he stops to build. A core's wall comes out bigger than the core, over whatever stands
    there (seed: it ignores other objects): bench 2026-10-26 (ice_turns clear), at 30 a 160 square came out round
    him and he could not walk out of it -- give him the wall's half-diagonal and his own size."""
    ids = dict(power=f'SpecialPower_{id}_Freeze', command=f'Command_{id}_Freeze', commandset=f'{id}CommandSet',
               button=f'Button_{id}_Freeze', ocl=f'OCL_{id}_Wall')
    x = open(os.path.join(SAGE, 'Allied', 'Units', 'AlliedEngineer.xml'), encoding='utf-8').read()
    x = sub1(x, 'id="AlliedEngineer"', f'id="{id}"')
    x = sub1(x, 'EditorName="AlliedEngineer"', f'EditorName="{id}"')
    x = sub1(x, 'CommandSet="AlliedEngineerCommandSet"', f'CommandSet="{ids["commandset"]}"')
    # retail's define, renamed: two engineers of ours in one build would define it twice (BinaryAssetBuilder: Critical)
    x = x.replace('ALLIED_HEALTH_TENT_RADIUS', f'{id.upper()}_TENT_RADIUS')
    if build:
        x = sub1(x, '</Behaviors>', f'''	<SpecialPower id="ModuleTag_CNV_FreezeTrigger" SpecialPowerTemplate="{ids['power']}"
				UpdateModuleStartsAttack="true"/>
			<AssembleStructureSpecialAbilityUpdate id="ModuleTag_CNV_Freeze" SpecialPowerTemplate="{ids['power']}"
				StartAbilityRange="{stand}" BusyDuringAssembly="true" NewObjectAssemblyTime="{assembly}"
				ModelConditionsOnAssembly="BUILD_VARIATION_ONE">
				<StructureTemplate>{wall_id}</StructureTemplate>
			</AssembleStructureSpecialAbilityUpdate>
		</Behaviors>''')
        power = f'''<SpecialPowerTemplate id="{ids['power']}" ReloadTime="{reload}" RadiusCursorRadius="1"
		ForbiddenObjectRange="32" TargetType="LOCATION_AND_ANGLE" Flags="PATHABLE_ONLY FOGGED_SHROUDED_CELLS_OK"
		WaypointModeTerminal="false"/>'''
        state = '<AssembleStructure StateData="ButtonStateAbilityConstructSovietBunker"/>'
    else:
        x = sub1(x, '</Behaviors>', f'''	<OCLSpecialPower id="ModuleTag_CNV_Freeze" SpecialPowerTemplate="{ids['power']}"
				UpdateModuleStartsAttack="false" AvailableAtStart="true" OCL="{ids['ocl']}" CreateLocation="CREATE_AT_LOCATION"/>
		</Behaviors>''')
        power = f'''<ObjectCreationList id="{ids['ocl']}">
		<CreateObject Disposition="ON_GROUND_ALIGNED" Options="DO_NOT_TREAT_AS_STRUCTURE CREATE_AT_TARGET IGNORE_ALL_OBJECTS">
			<CreateObject>{wall_id}</CreateObject>
		</CreateObject>
	</ObjectCreationList>
	<SpecialPowerTemplate id="{ids['power']}" ReloadTime="{reload}" TargetType="LOCATION" MaxCastRange="{reach}"
		Flags="LIMIT_DISTANCE PATHABLE_ONLY FOGGED_SHROUDED_CELLS_OK" WaypointModeTerminal="false"/>'''
        state = '<TargetedSpecialPower StateData="ButtonStateAbilityConstructSovietBunker" ValidTargetCursor="TargetAbility"/>'
    x = sub1(x, '</AssetDeclaration>', f'''	{power}
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
			{state}
		</Data>
	</UnitAbilityButtonTemplate>
</AssetDeclaration>
'''
    ui_file = f'{id}_UI.xml'
    return Unit(id, x, files={ui_file: ui}, also=[ui_file],
                link=[f'SpecialPowerTemplate:{ids["power"]}', f'LogicCommand:{ids["command"]}',
                      f'LogicCommandSet:{ids["commandset"]}', f'UnitAbilityButtonTemplate:{ids["button"]}'] +
                     ([] if build else [f'ObjectCreationList:{ids["ocl"]}']),
                names=ids, abilities={'freeze': ids['power']},
                what=(f'冰幕工兵（盟军工程师底）：freeze 走到一点站着造 {assembly}，造出一道 {wall_id}（放置时拖动可转方向）'
                      if build else f'冰幕工兵（盟军工程师底）：freeze 在 {reach} 以内的一点冻出一道 {wall_id}'),
                params=dict(wall=wall_id, reach=reach, reload=reload, build=build, assembly=assembly, stand=stand))
