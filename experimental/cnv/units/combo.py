"""合体机甲 (J4, campaign only; docs/story/units.md 4, work/story/unit_roster.md mechanism 6): two machines that
join into one and part again. Stand-ins: the King Oni as the parent, the Tsunami as the child.

C&C3's combine modules, which the schema keeps and RA3 never uses, do not work (bench 2026-10-22): a parent's
CombinedInfoModule without a DockingBone crashes the game loading the mission (0xC0000005); with one (B_SPINE01),
with or without MaxCombineChildren, the child's CombineSpecialPower aimed at the parent drives it off towards the
map's corner, and nothing ever carries COMBINED_PARENT / COMBINED_CHILD.

So the join is retail's IFV way: the parent has one seat that only the child fits (TransportContain), the child
drives in, and while it is aboard the parent carries CONTAINER_OCCUPIED and switches weapons by it (as the IFV does).
Everyone out (Command_Evacuate on the parent) parts them. The switch here is to the King Oni's veteran beam, which
has the same range and damage: a placeholder until the design says what joining buys (bench 2026-10-22: joined at
s10, parted at s29, both alive).

Published: parent: abilities part (the parent's unload button: NAMED_USE_COMMANDBUTTON_ABILITY). The join is the
child entering the parent (NAMED_GARRISON_SPECIFIC_BUILDING).
"""
import os
import re

import make_campnew2 as c2
from parts import Unit

SAGE = os.path.join(c2.SDK, 'SageXML', 'Japan', 'Units')
JOINED = 'CONTAINER_OCCUPIED'                   # the parent's status while the child is aboard
PART_COMMAND = 'Command_Evacuate'


def sub1(x, old, new):
    assert x.count(old) == 1, (old[:60], x.count(old))
    return x.replace(old, new, 1)


def parent(id='CNV_ComboParent', child_id='CNV_ComboChild'):
    commands = f'{id}CommandSet'
    x = open(os.path.join(SAGE, 'JapanAntiVehicleVehicleTech3.xml'), encoding='utf-8').read()
    x = sub1(x, 'id="JapanAntiVehicleVehicleTech3"', f'id="{id}"')
    x = sub1(x, 'EditorName="JapanAntiVehicleVehicleTech3"', f'EditorName="{id}"')
    x = sub1(x, 'CommandSet="JapanAntiVehicleVehicleTech3CommandSet"', f'CommandSet="{commands}"')
    # bench 2026-10-22: with one seat neither a script nor a right click put the child in -- a vehicle takes five
    # (BaseVehicle TransportSlotCount, the Twinblade's ContainMax); retail's transports also carry KindOf TRANSPORT
    x = sub1(x, 'CAN_BE_FAVORITE_UNIT T3_UNIT"', 'CAN_BE_FAVORITE_UNIT T3_UNIT TRANSPORT"')
    # joined: the veteran beam instead of the plain one
    x = sub1(x, 'Template="JapanAntiVehicleVehicleTech3BeamWeapon"\n\t\t\t\t\t\tForbiddenObjectStatus="SPECIALABILITY_ACTIVE '
                'GENERIC_TOGGLE_STATE WEAPON_UPGRADED_01"/>',
             'Template="JapanAntiVehicleVehicleTech3BeamWeapon"\n\t\t\t\t\t\tForbiddenObjectStatus="SPECIALABILITY_ACTIVE '
             f'GENERIC_TOGGLE_STATE WEAPON_UPGRADED_01 {JOINED}"/>\n'
             '\t\t\t\t\t<Weapon\n\t\t\t\t\t\tOrdering="PRIMARY_WEAPON"\n'
             '\t\t\t\t\t\tTemplate="JapanAntiVehicleVehicleTech3BeamWeapon_Veteran"\n'
             f'\t\t\t\t\t\tForbiddenObjectStatus="SPECIALABILITY_ACTIVE GENERIC_TOGGLE_STATE"\n\t\t\t\t\t\tObjectStatus="{JOINED}"/>')
    # as the Twinblade's (it carries one vehicle): CONTAINER_OCCUPIED is set by ObjectStatusWhileContaining, not by
    # being occupied; ConditionForEntry INVALID and a vehicle's PassengerData as it has them
    x = sub1(x, '</Behaviors>', f'''	<TransportContain id="ModuleTag_CNV_Seat" ObjectStatusOfContained="UNSELECTABLE ENCLOSED"
				ObjectStatusWhileContaining="{JOINED}" ContainMax="5" AllowEnemiesInside="false"
				AllowAlliesInside="true" AllowNeutralInside="false" AllowOwnPlayerInsideOverride="true" ShowPips="true"
				EnterSound="VehicleEnter" ExitSound="VehicleExit" KillPassengersOnDeath="true"
				ConditionForEntry="INVALID" ExtendedExitContainerChecks="true">
				<PassengerFilter Rule="NONE">
					<IncludeThing>{child_id}</IncludeThing>
				</PassengerFilter>
				<DieMuxData DeathTypes="ALL"/>
				<PassengerData BonePrefix="NONE" MaxPassengers="1">
					<Filter Rule="NONE" Include="VEHICLE"/>
				</PassengerData>
			</TransportContain>
		</Behaviors>''')
    x = sub1(x, '</AssetDeclaration>', f'''	<LogicCommandSet id="{commands}">
		<Cmd>Command_AttackMove</Cmd>
		<Cmd>{PART_COMMAND}</Cmd>
		<Cmd>Command_TriggerRushAttackSpecialPower</Cmd>
	</LogicCommandSet>
</AssetDeclaration>''')
    return Unit(id, x, link=[f'LogicCommandSet:{commands}'], abilities={'part': PART_COMMAND},
                what=f'合体机甲母体（鬼王底）：{child_id} 开进来就合体（换成更强的光束），part 拆开',
                params=dict(child=child_id))


def child(id='CNV_ComboChild'):
    x = open(os.path.join(SAGE, 'JapanAntiVehicleVehicleTech1.xml'), encoding='utf-8').read()
    x = re.sub(r'\s*<GameObject\s+id="JapanAntiVehicleVehicleTech1_Naval".*?</GameObject>', '', x, flags=re.S)
    x = sub1(x, 'id="JapanAntiVehicleVehicleTech1"', f'id="{id}"')
    x = sub1(x, 'EditorName="JapanAntiVehicleVehicleTech1"', f'EditorName="{id}"')
    return Unit(id, x, what='合体机甲子体（海啸底）：开进母体就合体')
