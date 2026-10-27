"""自由号空天航母 (the Liberty carrier), as worked out in experimental/campaign/make_campnew38.py (its comments and
docs/plan.md hold the bench history): a copy of the Kirov that launches the aircraft carrier's drones and takes them
home, whose one button is the deck jump -- it jumps itself (TeleportSpecialAbilityUpdate) and its SourceWeapon /
DestinationWeapon pick up the ground units under the deck as it leaves and put them down where it lands (the
Chronosphere's store / send). Optional: a deck factory (a SpawnBehavior budding units every 20 s) and deck riders
(units with an AttachUpdate that sit on the carrier and ride the jump with it; they stack on one spot).

liberty(tag=...) gives every id of its own a suffix, so two variants can stand on one map for an A/B run.

It wears the units line's look by default (2026-10-27, dress): the flying Liberty Island fortress CNLiberty (280
across, the Kirov's bone names, turret sockets TURRET01..05 as bones, not wired), retail's statue CNLibStatue on its
core and the turning gyroscope rings CNLibRings -- written into the SDK's Art by experimental/units/liberty_kit.py.
"""
import os
import re

import make_campnew2 as c2
from parts import Unit

SAGE = os.path.join(c2.SDK, 'SageXML')
RETAIL_RIDER = 'AlliedAntiVehicleVehicleTech1'      # the Guardian
LOOK = ('CNLiberty', 'CNLibStatue', 'CNLibRings', 'CNLibCharge')   # liberty_kit.py's: platform, statue, rings, charge
CHARGING = 'USER_1'     # the model condition the jump warning sets for its length (devices/carrier.py): charge drawn


def sub1(x, old, new):
    assert x.count(old) == 1, (old[:60], x.count(old))
    return x.replace(old, new, 1)


def charging(name, seconds):
    """The script action that shows the named carrier charging its jump for `seconds` (its crown's rays lighting one
    by one, the aperture opening: liberty_kit.charge, timed for 15 s); nothing on a carrier not dressed."""
    return ('UNIT_SET_MODELCONDITION_GENERIC', name, CHARGING, float(seconds))


def dress(unit, model=LOOK[0], statue=LOOK[1], rings=LOOK[2], charge=LOOK[3]):
    """The carrier drawing `model`, `statue` and `rings` in place of the Kirov (all at its origin, each carrying its
    place over the core; the rings looping their turn, <rings>_IDLE), and `charge` while CHARGING (its <charge>_CHARGE
    played once); the drones still launch from FX_WEAPON. Look only: geometry, health, locomotor and every behaviour
    stay the Kirov's."""
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
			<ScriptedModelDraw id="ModuleTag_Draw_Charge" OkToChangeModelColor="false">
				<ModelConditionState ParseCondStateType="PARSE_DEFAULT">
					<Model Name="" />
				</ModelConditionState>
				<ModelConditionState ParseCondStateType="PARSE_NORMAL" ConditionsYes="{CHARGING}">
					<Model Name="{charge.upper()}" />
				</ModelConditionState>
				<AnimationState ParseCondStateType="PARSE_DEFAULT">
				</AnimationState>
				<AnimationState ParseCondStateType="PARSE_NORMAL" ConditionsYes="{CHARGING}">
					<Animation AnimationName="{charge.upper()}_CHARGE" AnimationMode="ONCE" />
				</AnimationState>
			</ScriptedModelDraw>
		</Draws>''', unit.xml, count=1, flags=re.S)
    assert n == 1, n
    unit.xml = sub1(x, '<Includes>', f'<Includes>\n\t\t<Include type="all" source="ART:{model}.w3x" />'
                                     f'\n\t\t<Include type="all" source="ART:{statue}.w3x" />'
                                     f'\n\t\t<Include type="all" source="ART:{rings}.w3x" />'
                                     f'\n\t\t<Include type="all" source="ART:{rings}_IDLE.w3x" />'
                                     f'\n\t\t<Include type="all" source="ART:{charge}.w3x" />'
                                     f'\n\t\t<Include type="all" source="ART:{charge}_CHARGE.w3x" />')
    unit.params['look'] = model
    return unit


def liberty(id='CNV_Liberty', tag='', reload='20s', drone_range=600, drones_home=True, factory=None, riders=None,
            show_jump=True, deck_radius=150, turrets=0, turret_id='CNV_LibertyTurret', model=LOOK[0]):
    """factory: the template the deck builds (None: no factory). riders: the rider template (left out of the deck's
    store / send, which would detach them). turrets: how many deck turrets (turret_id, see turret()) it carries from
    the start, not replaced once shot off. model: its look (dress); None keeps the Kirov's. Returns the carrier's
    Unit; .names: power, unit."""
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
    if turrets:         # the war factory's repair drones' wiring; a very long replace delay: none come back
        modules += f'''			<SpawnBehavior id="ModuleTag_CNV_DeckTurrets" SpawnNumberData="{turrets}" InitialBurst="{turrets}"
				SpawnReplaceDelayData="9999s" SpawnedRequireSpawner="true" KillSpawnsOnCaptured="true"
				ExitByBudding="true">
				<Die DeathTypes="ALL"/>
				<SpawnTemplate>{turret_id}</SpawnTemplate>
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
    u = Unit(id, x, files={ui_file: ui}, also=[ui_file], link=link, names=dict(ids, unit=id),
             abilities={'jump': ids['power']},
             what='自由号：发射无人机的空天航母；jump 把自己和甲板下的地面部队一起跃迁到一个点'
                  + (f'；甲板每 20 秒造一辆 {factory}' if factory else '')
                  + (f'；带 {turrets} 座 {turret_id}' if turrets else ''),
             params=dict(reload=reload, drone_range=drone_range, deck_radius=deck_radius, factory=factory,
                         riders=riders, turrets=turrets, turret=turret_id if turrets else None))
    return dress(u, model) if model else u


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


def aimed(wid, retail, reach):
    """A retail weapon under our id that fires all round (AcceptableAimDelta 360d: a hovering drone has no turret to
    turn) out to `reach`."""
    w = open(os.path.join(SAGE, 'GlobalData', 'Weapon.xml'), encoding='utf-8').read()
    m = re.search(rf'\t*<WeaponTemplate\s+id="{retail}".*?</WeaponTemplate>\n', w, re.S)
    x = sub1(m.group(0), f'id="{retail}"', f'id="{wid}"')
    x, n = re.subn(r'AttackRange="[0-9.]+"', f'AttackRange="{reach}.0"', x, count=1)
    assert n == 1, retail
    x = re.sub(r'\s*AcceptableAimDelta="[^"]*"', '', x)
    return sub1(x, f'id="{wid}"', f'id="{wid}"\n\t\tAcceptableAimDelta="360d"')


GROUND_GUN, AIR_GUN = 'SovietAntiGroundAircraftAutoCannon', 'SovietAntiAirShipFlakCannon'   # Twinblade's, Bullfrog's


def turret(id='CNV_LibertyTurret', fixed=False, reach=300, health=400, slaved=True, category=True, base='BaseObject',
           chooser=True):
    """A deck turret: the war factory's repair drone (it spawns and follows the carrier: SlavedUpdate) with a gun at
    ground and one at aircraft (the Twinblade's, the Bullfrog's), `health` to be shot off.

    Why the v2 probe's turret never fired (make_campnew38.py; bench 2026-10-22): its AIUpdate had no target chooser.
    chooser (UnitAITargetChooserData CanPickDynamicTargets true, the armoured train's fix) is all it takes: placed on
    its own, with or without it, aimed all round or not, on BaseObject or BaseVehicle -- it fired only with it; on the
    carrier, with retail's weapons, two turrets took a Hammer from 100 to 15 % in 40 s. fixed: our copies of the two
    weapons, all round (360d) and out to `reach`, instead of retail's (no difference seen)."""
    guns = (f'{id}_Ground', f'{id}_Air') if fixed else (GROUND_GUN, AIR_GUN)
    decl = (aimed(guns[0], GROUND_GUN, reach) + aimed(guns[1], AIR_GUN, reach)) if fixed else ''
    category = ' WeaponCategory="CANNON"' if category else ''
    chooser = '<UnitAITargetChooserData CanPickDynamicTargets="true"/>' if chooser else ''
    slave = f'''			<SlavedUpdate id="ModuleTag_CNV_DeckSlave" LeashRange="60" GuardMaxRange="40" GuardWanderRange="10"
				AttackRange="{reach}" AttackWanderRange="20" DieOnMastersDeath="true" StayOnSameLayerAsMaster="true"/>
'''
    x = f'''<?xml version="1.0" encoding="UTF-8"?>
<AssetDeclaration xmlns="uri:ea.com:eala:asset" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
	<Includes>
		<Include type="all" source="DATA:GlobalData/GlobalDefines.xml" />
		<Include type="all" source="ART:AURepairDrone_SKN.w3x" />
		<Include type="all" source="ART:AURepairDrone_IDLA.w3x" />
		<Include type="instance" source="DATA:BaseObjects/{base}.xml" />
	</Includes>
	<GameObject id="{id}" inheritFrom="{base}" Side="Allies" EditorSorting="UNIT" EditorName="{id}"
		KindOf="DRONE AIRCRAFT NO_COLLIDE CAN_ATTACK SCORE VEHICLE" ShockwaveResistance="120.0"{category}>
		<DisplayName>NAME:RepairDrone</DisplayName>
		<LocomotorSet Locomotor="BaseRepairDroneLocomotor" Condition="NORMAL" Speed="150.0" />
		<ArmorSet Armor="SovietAntiGroundAircraftArmor" />
		<Draws>
			<ScriptedModelDraw id="ModuleTag_Draw" OkToChangeModelColor="true">
				<ModelConditionState ParseCondStateType="PARSE_DEFAULT">
					<Model Name="AURepairDrone_SKN" />
				</ModelConditionState>
				<AnimationState ParseCondStateType="PARSE_DEFAULT" StateName="STATE_bored">
					<Animation AnimationName="AURepairDrone_IDLA" AnimationMode="LOOP" />
				</AnimationState>
			</ScriptedModelDraw>
		</Draws>
		<Behaviors>
			<WeaponSetUpdate id="ModuleTag_WeaponSetUpdate">
				<WeaponSlotHardpoint ID="1">
					<Weapon Ordering="PRIMARY_WEAPON" Template="{guns[0]}" />
				</WeaponSlotHardpoint>
				<WeaponSlotHardpoint ID="2">
					<Weapon Ordering="PRIMARY_WEAPON" Template="{guns[1]}" />
				</WeaponSlotHardpoint>
			</WeaponSetUpdate>
{slave if slaved else ''}			<SlowDeath id="ModuleTag_Death" DestructionDelay="1s" Fade="true" FadeTime="1s">
				<DieMuxData DeathTypes="ALL" />
			</SlowDeath>
			<Physics id="ModuleTag_Physics" />
		</Behaviors>
		<AI>
			<AIUpdate id="ModuleTag_AIUpdate" AutoAcquireEnemiesWhenIdle="YES" StateMachine="UnitAIStateMachine">
				{chooser}
			</AIUpdate>
		</AI>
		<Body>
			<ActiveBody id="ModuleTag_Body" MaxHealth="{health}.0" />
		</Body>
		<Geometry IsSmall="true">
			<Shape Type="CYLINDER" MajorRadius="8.0" Height="8.0" />
		</Geometry>
		<VisionInfo VisionRange="{reach + 50}" ShroudClearingRange="{reach + 50}" />
	</GameObject>
{decl}</AssetDeclaration>
'''
    return Unit(id, x, link=[f'WeaponTemplate:{g}' for g in guns] if fixed else [],
                what=f'自由号甲板炮塔（维修无人机底）：对地、对空各一门' + (f'，全向、射程 {reach}' if fixed else '（原版武器原样）') +
                     f'，{health} 血，跟着航母、能被单独打掉',
                params=dict(fixed=fixed, reach=reach, health=health, slaved=slaved))


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
    return Unit(id, x, names=dict(unit=id), what=f'甲板乘员：闲着时自己登上 {parent}，跟着它跃迁；在甲板上时状态 ATTACHED',
                params=dict(parent=parent, ride_range=ride_range, flags=flags))


ATTACHED = (102, 0.0, 'ATTACHED')       # the ObjectStatus script argument (index in ObjectStatus.xsd's order)
