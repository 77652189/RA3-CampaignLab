"""自由号空天航母 (the Liberty carrier), as worked out in experimental/campaign/make_campnew38.py (its comments and
docs/plan.md hold the bench history): a copy of the Kirov that launches the aircraft carrier's drones and takes them
home, whose one button is the deck jump -- it jumps itself (TeleportSpecialAbilityUpdate) and its SourceWeapon /
DestinationWeapon pick up the ground units under the deck as it leaves and put them down where it lands (the
Chronosphere's store / send). Optional: a deck factory (a SpawnBehavior budding units every 20 s) and deck riders
(units with an AttachUpdate that sit on the carrier and ride the jump with it; they stack on one spot).

liberty(tag=...) gives every id of its own a suffix, so two variants can stand on one map for an A/B run.
"""
import os
import re

import make_campnew2 as c2
from parts import Unit

SAGE = os.path.join(c2.SDK, 'SageXML')
RETAIL_RIDER = 'AlliedAntiVehicleVehicleTech1'      # the Guardian


def sub1(x, old, new):
    assert x.count(old) == 1, (old[:60], x.count(old))
    return x.replace(old, new, 1)


def liberty(id='CNV_Liberty', tag='', reload='20s', drone_range=600, drones_home=True, factory=None, riders=None,
            show_jump=True, deck_radius=150):
    """factory: the template the deck builds (None: no factory). riders: the rider template (left out of the deck's
    store / send, which would detach them). Returns the carrier's Unit; .names: power, unit."""
    s = f'_{tag}' if tag else ''
    ids = dict(power=f'SpecialPower_CNV_ChronoDeck{s}', command=f'Command_CNV_ChronoDeck{s}',
               commandset=f'CNV_LibertyCommandSet{s}', button=f'Button_CNV_ChronoDeck{s}',
               store=f'SpecialPower_CNV_DeckStore{s}', send=f'SpecialPower_CNV_DeckSend{s}',
               filter=f'CNV_DeckFilter{s}', store_w=f'CNV_DeckStoreTrigger{s}', send_w=f'CNV_DeckSendTrigger{s}',
               drones=f'CNV_LibertyDrones{s}')
    not_rider = f'\n\t\t\t<ExcludeThing>{riders}</ExcludeThing>' if riders else ''
    pick = f'''		<ObjectFilter Rule="ANY" Include="INFANTRY VEHICLE" StatusBitFlagsExclude="SUBMERGED NOT_IN_WORLD">
			<IncludeThing>{id}</IncludeThing>{not_rider}
		</ObjectFilter>
'''
    decl = f'''	<SpecialPowerTemplate id="{ids['power']}" ReloadTime="{reload}" TargetType="LOCATION"
		Flags="FOGGED_SHROUDED_CELLS_OK CAN_NOT_BE_SCRAMBLED" WaypointModeTerminal="false"/>
	<LogicCommand Type="SPECIAL_POWER" id="{ids['command']}">
		<SpecialPower>{ids['power']}</SpecialPower>
	</LogicCommand>
	<LogicCommandSet id="{ids['commandset']}">
		<Cmd>{ids['command']}</Cmd>
		<Cmd>Command_AttackMove</Cmd>
	</LogicCommandSet>
	<SpecialPowerTemplate id="{ids['store']}" ReloadTime="0s" TargetType="LOCATION"
		Flags="WATER_OK CAN_NOT_BE_SCRAMBLED" WaypointModeTerminal="false">
{pick}	</SpecialPowerTemplate>
	<ObjectFilterAsset id="{ids['filter']}">
		<Filter Rule="ANY" Include="INFANTRY VEHICLE" Relationship="SAME_PLAYER ALLIES"
			StatusBitFlagsExclude="SUBMERGED NOT_IN_WORLD">
			<IncludeThing>{id}</IncludeThing>{not_rider.replace(chr(9) * 3, chr(9) * 4)}
		</Filter>
	</ObjectFilterAsset>
	<SpecialPowerTemplate id="{ids['send']}" ReloadTime="0s" TargetType="LOCATION"
		Flags="WATER_OK CAN_NOT_BE_SCRAMBLED" WaypointModeTerminal="false">
{pick}	</SpecialPowerTemplate>
'''
    for w, power in ((ids['store_w'], ids['store']), (ids['send_w'], ids['send'])):
        decl += f'''	<WeaponTemplate id="{w}" RadiusDamageAffects="SELF ALLIES" AttackRange="10000"
		Flags="NOT_ATTRACTED_BY_MAGNETS">
		<FiringDuration MinSeconds="0.1s" MaxSeconds="0.1s"/>
		<Nuggets>
			<SpecialPowerNugget SpecialPowerTemplate="{power}"/>
		</Nuggets>
	</WeaponTemplate>
'''
    store_ocl, send_ocl = ((' OCL="OCL_ChronospherePersistent"', ' OCL="OCL_Chronosphere"') if show_jump else ('', ''))
    modules = f'''			<SpecialPower id="ModuleTag_CNV_ChronoDeck" SpecialPowerTemplate="{ids['power']}"
				UpdateModuleStartsAttack="true"/>
			<TeleportSpecialAbilityUpdate id="ModuleTag_CNV_ChronoDeckUpdate" SpecialPowerTemplate="{ids['power']}"
				StartAbilityRange="99999.0" UnpackTime="0.5s" PackTime="0s" MaxDistance="2000" FadeInTime="1s"
				SourceWeapon="{ids['store_w']}" DestinationWeapon="{ids['send_w']}"/>
			<StoreObjectsSpecialPower id="ModuleTag_CNV_DeckStore" SpecialPowerTemplate="{ids['store']}"
				Radius="{deck_radius}" TeleportLinkID="7" CanAffectObjectFilter="{ids['filter']}"{store_ocl}/>
			<TeleportStoredObjectsSpecialPower id="ModuleTag_CNV_DeckSend" SpecialPowerTemplate="{ids['send']}"
				StoreObjectsLinkID="7" CanAffectObjectFilter="{ids['filter']}"{send_ocl}/>
			<TeleportStoredObjectsUpdate id="ModuleTag_CNV_DeckSendUpdate" SpecialPowerTemplate="{ids['send']}"
				GetObjectsCurrentlyAtStorePosition="true" Telefrag="INSTANT_DEATH_TELEPORTER_ONLY" TargetFX="FX_None"
				FadeInTime="1s" DelayTime="0s"
				DisabledTypesToProcess="USER_PARALYZED EMP HELD PARALYZED UNDERPOWERED TEMPORARILY_BUSY">
				<CollidesWithOnTeleport Rule="ANY" Include="INFANTRY STRUCTURE VEHICLE"
					Exclude="BRIDGE BRIDGE_SEGMENT BRIDGE_ENDCAP"/>
			</TeleportStoredObjectsUpdate>
'''
    if drones_home:     # the aircraft carrier's three: KindOf AIRFIELD, parking for drones only, a horde contain
        modules += '''			<SlaughterHordeContain id="ModuleTag_CNV_DroneHome" CashBackPercent="0" ResetInitialTeamOnCapture="true">
				<CanAlwaysEnterObjectFilter Rule="NONE">
					<IncludeThing>AlliedAttackDrone</IncludeThing>
				</CanAlwaysEnterObjectFilter>
			</SlaughterHordeContain>
			<ParkingPlaceBehavior id="ModuleTag_CNV_DroneParking" NumRows="2" NumCols="2" ApproachHeight="10"
				ParkInHangars="true" DoorOpenTime="0.5s">
				<CanParkHereFilter Rule="NONE" Relationship="ALLIES">
					<IncludeThing>AlliedAttackDrone</IncludeThing>
				</CanParkHereFilter>
			</ParkingPlaceBehavior>
'''
    if factory:
        modules += f'''			<SpawnBehavior id="ModuleTag_CNV_DeckFactory" SpawnNumberData="2" InitialBurst="0"
				SpawnReplaceDelayData="20s" SpawnedRequireSpawner="false" ExitByBudding="true">
				<Die DeathTypes="ALL"/>
				<SpawnTemplate>{factory}</SpawnTemplate>
			</SpawnBehavior>
'''
    x = open(os.path.join(SAGE, 'Soviet', 'Units', 'SovietBomberAircraft.xml'), encoding='utf-8').read()
    x = sub1(x, 'id="SovietBomberAircraft"', f'id="{id}"')
    x = sub1(x, 'EditorName="SovietBomberAircraft"', f'EditorName="{id}"')
    x = sub1(x, 'Template="SovietBomberAircraftBombWeapon"', f'Template="{ids["drones"]}"')
    x = sub1(x, 'VisionRange="150"', f'VisionRange="{drone_range + 50}"')      # it launches only at what it sees
    if drones_home:
        x = sub1(x, 'KindOf="CAN_CAST_REFLECTIONS', 'KindOf="AIRFIELD CAN_CAST_REFLECTIONS')
    assert x.count('CheckVisionRange="true"') == 2
    x = x.replace('CheckVisionRange="true"', 'CheckVisionRange="false"')
    x = sub1(x, 'CommandSet="SovietBomberAircraftCommandSet"', f'CommandSet="{ids["commandset"]}"')
    x = sub1(x, '\t\t</Behaviors>', modules + '\t\t</Behaviors>')
    x = sub1(x, '</AssetDeclaration>', decl + drone_weapon(ids['drones'], drone_range) + '</AssetDeclaration>')
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
    link = [f'WeaponTemplate:{ids["drones"]}', f'SpecialPowerTemplate:{ids["power"]}', f'LogicCommand:{ids["command"]}',
            f'LogicCommandSet:{ids["commandset"]}', f'UnitAbilityButtonTemplate:{ids["button"]}',
            f'SpecialPowerTemplate:{ids["store"]}', f'SpecialPowerTemplate:{ids["send"]}',
            f'ObjectFilterAsset:{ids["filter"]}', f'WeaponTemplate:{ids["store_w"]}', f'WeaponTemplate:{ids["send_w"]}']
    return Unit(id, x, files={ui_file: ui}, also=[ui_file], link=link, names=dict(ids, unit=id))


def drone_weapon(wid, rng):
    """The Kirov's bomb weapon (fires from this host) with the range, a 5-shot clip every 10 s and the aircraft
    carrier's drone OCL instead of the bomb."""
    w = open(os.path.join(SAGE, 'GlobalData', 'Weapon.xml'), encoding='utf-8').read()
    m = re.search(r'\t*<WeaponTemplate\s+id="SovietBomberAircraftBombWeapon".*?</WeaponTemplate>\n', w, re.S)
    x = m.group(0).replace('id="SovietBomberAircraftBombWeapon"', f'id="{wid}"')
    x = sub1(x, 'AttackRange="5.0"', f'AttackRange="{rng}.0"')
    x = sub1(x, 'ClipSize="1"', 'ClipSize="5"\n\t\tAutoReloadsClip="AUTO"')
    x = sub1(x, 'MinSeconds="0.8s"\n\t\t\tMaxSeconds="1.0s"', 'MinSeconds="10.0s"\n\t\t\tMaxSeconds="10.0s"')
    x = sub1(x, 'MinSeconds=".1s"\n\t\t\tMaxSeconds=".1s"', 'MinSeconds="0.5s"\n\t\t\tMaxSeconds="0.5s"')
    x, n = re.subn(r'<ProjectileNugget.*?</ProjectileNugget>', '<WeaponOCLNugget WeaponOCL="OCL_AlliedAttackDrones"/>',
                   x, flags=re.S)
    assert n == 1
    return x


RIDE_FLAGS = ('SAME_PLAYER_ONLY STICK_TO_PARENT TELEPORT INSTANT_TELEPORT_ON_PARENT_TELEPORT USE_GEOMETRY '
              'MOVE_ORDER_FORCES_DETACH SCAN_FOR_NEW_PARENT_WHEN_DETACHED')


def rider(id='CNV_LibRider', parent='CNV_Liberty', ride_range=150, flags=RIDE_FLAGS):
    """A Guardian that boards the carrier when idle within ride_range, sits on it (all riders on one spot: the
    AttachUpdate has no offset) and rides its jump; a move order takes it off. While on: status ATTACHED."""
    x = open(os.path.join(SAGE, 'Allied', 'Units', RETAIL_RIDER + '.xml'), encoding='utf-8').read()
    x = sub1(x, f'id="{RETAIL_RIDER}"', f'id="{id}"')
    x = sub1(x, f'EditorName="{RETAIL_RIDER}"', f'EditorName="{id}"')
    x = sub1(x, '\t\t</Behaviors>', f'''			<AttachUpdate id="ModuleTag_CNV_Deck" Range="{ride_range}" IdleScanDelay="0.5s"
				Flags="{flags}"
				AttachedObjectStatus="NO_COLLISIONS ATTACHED">
				<ObjectFilter Rule="NONE" Relationship="SAME_PLAYER">
					<IncludeThing>{parent}</IncludeThing>
				</ObjectFilter>
			</AttachUpdate>
		</Behaviors>''')
    return Unit(id, x, names=dict(unit=id))


ATTACHED = (102, 0.0, 'ATTACHED')       # the ObjectStatus script argument (index in ObjectStatus.xsd's order)
