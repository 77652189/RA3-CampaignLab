"""盟军招牌「自由号」空天航母机制验证 (CampNew38), slice 1: a slow hovering capital ship that launches drone bombers.

Design (docs/story/units.md 5.2): a huge hovering carrier; its deck launches drone bombers; its 超时空甲板 sends a
group of nearby ground units to any point in view every few minutes (slice 2); it flies slowly and fears anti-air;
the chrono deck runs on a power station (A7: the station dies, the deck goes dark). Story: FutureTech gives it to the
Allies, the hawk commander takes it in A7 (the player's boss), the player takes it back in A8.

Stand-in: a copy of the Kirov (retail: a slow hovering airship whose weapon slot works) with its bomb bay replaced by
CNV_LibertyDrones: the aircraft carrier's drone weapon (OCL_AlliedAttackDrones, 5 drones a clip, 10 s reload) at
range 600 instead of 1000; the turret's CheckVisionRange off (it would not launch beyond its own sight).
First tried on the SDK SampleMod's Harbinger gunship (CampNew16's): the copy flew to its target and never fired,
with the drones or with its own autocannon (bench 2026-10-21, _013526 / _013753), so the Kirov.
The catch on both: vision. The Kirov sees 150 and would neither launch nor close in on a Hammer 450 away (CampNew35's
lesson again; CheckVisionRange off did not help). At vision 650 (_020052): drones out from 6 s, the middle Hammer
dies at ~13 s, a second by 25 s; the carrier stays put. Open: the drones do not go home -- they gather in a line
beside the carrier (a dozen by 25 s).
Chrono deck 2a (bench _020745: select, the ability slot, a point ~300 east): it turns at 3 s, vanishes and reappears
there at 4 s, then launches drones from its new place. Carrying ground units needs a TransportContain and an unload,
and the panel has one ability slot, taken by the jump.

Scene: our carrier south, three enemy Hammers 450 north. Bench: box-select the carrier, right-click a Hammer.

  python -I -X utf8 experimental/campaign/make_campnew38.py            -> Documents\\Red Alert 3\\Mods\\CampNew38
"""
import math
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import make_campnew29 as c29                    # noqa: E402

c28, c23 = c29.c28, c29.c23
c26, c7, c6, c4, c2 = c28.c26, c23.c7, c23.c6, c23.c4, c23.c2
newmap = c23.newmap
NAME = 'CampNew38'
c4.NAME = c2.NAME = NAME
c2.SRC_DIR = os.path.join(c2.SDK, 'Mods', NAME, 'data')
c2.BUILT = os.path.join(c2.SDK, 'BuiltMods', 'mods', NAME.lower(), 'data')
c2.OUT = c4.OUT = os.path.join(os.path.expanduser('~'), 'Documents', 'Red Alert 3', 'Mods', NAME)
c7.MAP_MOD = NAME + 'Map'

SAGE = os.path.join(c2.SDK, 'SageXML', 'Soviet', 'Units')
UNIT = 'CNV_LibertyProbe'
c7.EXTRA_TEMPLATES[UNIT] = {'file': f'DATA:CNVUnits/Data/{UNIT}.xml', 'EditorSorting': 'UNIT'}
c7.EXTRA_OWN += [b'WeaponTemplate:CNV_LibertyDrones']
DRONE_RANGE = 600
# slice 2, 超时空甲板 (CNV_CHRONO=1, default): a targeted ability (the Sickle's leap button and command style, one
# ability slot) driving TeleportSpecialAbilityUpdate -- in the schema, no retail unit uses it. Probe 2a: does the
# carrier jump to the clicked point? (2b: carrying a group of ground units with it.) The Kirov's afterburner goes.
CHRONO = os.environ.get('CNV_CHRONO', '1') == '1'
CHRONO_RELOAD = os.environ.get('CNV_CHRONO_RELOAD', '20s')       # design: every few minutes; short for the bench
UI_FILE = 'CNV_Liberty_UI.xml'
CHRONO_DECL = f'''	<SpecialPowerTemplate id="SpecialPower_CNV_ChronoDeck" ReloadTime="{CHRONO_RELOAD}" TargetType="LOCATION"
		Flags="FOGGED_SHROUDED_CELLS_OK CAN_NOT_BE_SCRAMBLED" WaypointModeTerminal="false"/>
	<LogicCommand Type="SPECIAL_POWER" id="Command_CNV_ChronoDeck">
		<SpecialPower>SpecialPower_CNV_ChronoDeck</SpecialPower>
	</LogicCommand>
	<LogicCommandSet id="CNV_LibertyCommandSet">
		<Cmd>Command_CNV_ChronoDeck</Cmd>
		<Cmd>Command_AttackMove</Cmd>
	</LogicCommandSet>
'''
CHRONO_UI = '''	<UnitAbilityButtonTemplate id="Button_CNV_ChronoDeck" LogicCommand="Command_CNV_ChronoDeck">
		<Data>
			<TargetedSpecialPower StateData="ButtonStateAbilityLeap" ValidTargetCursor="TargetAbility"/>
		</Data>
	</UnitAbilityButtonTemplate>
'''
CHRONO_MODULES = '''			<SpecialPower id="ModuleTag_CNV_ChronoDeck" SpecialPowerTemplate="SpecialPower_CNV_ChronoDeck"
				UpdateModuleStartsAttack="true"/>
			<TeleportSpecialAbilityUpdate id="ModuleTag_CNV_ChronoDeckUpdate" SpecialPowerTemplate="SpecialPower_CNV_ChronoDeck"
				StartAbilityRange="99999.0" UnpackTime="0.5s" PackTime="0s" MaxDistance="2000" FadeInTime="1s"/>
'''
# v2 甲板跃迁 (user 2026-10-21: the Griffin's way -- the big unit hides the effect, the Chronosphere's code underneath).
# CNV_CHRONO_MODE=jump (default, below the deck block): works -- bench _152425, the carrier and the three Guardians
# under it arrive together at 4 s in their formation, the one outside the deck stays.
# CNV_CHRONO_MODE=deck (first try): every 0.5 s a FireWeaponUpdate fires CNV_DeckStoreTrigger, whose SpecialPowerNugget
# fires SpecialPower_CNV_DeckStore = the Chronosphere's StoreObjectsSpecialPower (select) at the carrier's own spot,
# radius DECK; the one button is its TeleportStoredObjectsSpecialPower (send) with GetObjectsCurrentlyAtStorePosition.
# The filter takes our ground units and the carrier itself (the Chronosphere's leaves aircraft out).
# CNV_CHRONO_MODE=self: 2a, the carrier alone (TeleportSpecialAbilityUpdate).
CHRONO_MODE = os.environ.get('CNV_CHRONO_MODE', 'jump')
DECK = int(os.environ.get('CNV_DECK_RADIUS', '150'))
# CNV_DECK_SHOW=1: each select drops the Chronosphere's lasting marker (does the timer select at all?)
STORE_OCL = ' OCL="OCL_ChronospherePersistent"' if os.environ.get('CNV_DECK_SHOW') == '1' else ''
# first deck run (_150502 / _150716): the select ran every 0.5 s (marker seen) and the button fired (it went into
# cooldown), nothing moved, with the Chronosphere's send filter (none) and GetObjectsCurrentlyAtStorePosition true
SEND_FILTER = os.environ.get('CNV_SEND_FILTER', 'CNV_DeckFilter')
AT_STORE = os.environ.get('CNV_AT_STORE', 'true')
STORE_EVERY = os.environ.get('CNV_STORE_EVERY', '0.5s')
SEND_OCL = ' OCL="OCL_Chronosphere"' if os.environ.get('CNV_DECK_SHOW') == '1' else ''   # does the send fire?
# the Chronosphere's power templates carry their own ObjectFilter (who gets picked up); without one nothing moved
TEMPLATE_FILTER = f'''		<ObjectFilter Rule="ANY" Include="INFANTRY VEHICLE" StatusBitFlagsExclude="SUBMERGED NOT_IN_WORLD">
			<IncludeThing>{UNIT}</IncludeThing>
		</ObjectFilter>
'''
DECK_DECL = f'''	<SpecialPowerTemplate id="SpecialPower_CNV_DeckStore" ReloadTime="0s" TargetType="LOCATION"
		Flags="WATER_OK CAN_NOT_BE_SCRAMBLED" WaypointModeTerminal="false">
{TEMPLATE_FILTER}	</SpecialPowerTemplate>
	<ObjectFilterAsset id="CNV_DeckFilter">
		<Filter Rule="ANY" Include="INFANTRY VEHICLE" Relationship="SAME_PLAYER ALLIES"
			StatusBitFlagsExclude="SUBMERGED NOT_IN_WORLD">
			<IncludeThing>{UNIT}</IncludeThing>
		</Filter>
	</ObjectFilterAsset>
	<WeaponTemplate id="CNV_DeckStoreTrigger" RadiusDamageAffects="SELF ALLIES" AttackRange="10000"
		Flags="NOT_ATTRACTED_BY_MAGNETS">
		<FiringDuration MinSeconds="0.1s" MaxSeconds="0.1s"/>
		<Nuggets>
			<SpecialPowerNugget SpecialPowerTemplate="SpecialPower_CNV_DeckStore"/>
		</Nuggets>
	</WeaponTemplate>
'''
DECK_MODULES = f'''			<StoreObjectsSpecialPower id="ModuleTag_CNV_DeckStore" SpecialPowerTemplate="SpecialPower_CNV_DeckStore"
				Radius="{DECK}" TeleportLinkID="7" CanAffectObjectFilter="CNV_DeckFilter"{STORE_OCL}/>
			<TeleportStoredObjectsSpecialPower id="ModuleTag_CNV_DeckSend" SpecialPowerTemplate="SpecialPower_CNV_ChronoDeck"
				StoreObjectsLinkID="7" CanAffectObjectFilter="{SEND_FILTER}"{SEND_OCL}/>
			<TeleportStoredObjectsUpdate id="ModuleTag_CNV_DeckSendUpdate" SpecialPowerTemplate="SpecialPower_CNV_ChronoDeck"
				GetObjectsCurrentlyAtStorePosition="{AT_STORE}" Telefrag="INSTANT_DEATH_TELEPORTER_ONLY" TargetFX="FX_None"
				FadeInTime="1s" DelayTime="0s"
				DisabledTypesToProcess="USER_PARALYZED EMP HELD PARALYZED UNDERPOWERED TEMPORARILY_BUSY">
				<CollidesWithOnTeleport Rule="ANY" Include="INFANTRY STRUCTURE VEHICLE"
					Exclude="BRIDGE BRIDGE_SEGMENT BRIDGE_ENDCAP"/>
			</TeleportStoredObjectsUpdate>
			<FireWeaponUpdate id="ModuleTag_CNV_DeckStoreTimer" FireInterval="{STORE_EVERY}">
				<FireWeaponNugget WeaponName="CNV_DeckStoreTrigger" FireDelay="0s"/>
			</FireWeaponUpdate>
'''
# deck runs: with the templates' ObjectFilter the Guardians under the deck went to the target (_152020), the one outside
# stayed, the carrier did not come (the Chronosphere's send seems to leave aircraft out). So CNV_CHRONO_MODE=jump
# (default): the button is 2a's self-jump; its SourceWeapon selects what is under the deck as it leaves and its
# DestinationWeapon sends that to where it arrives (SpecialPowerNuggets) -- no timer.
JUMP_DECL = f'''	<SpecialPowerTemplate id="SpecialPower_CNV_DeckSend" ReloadTime="0s" TargetType="LOCATION"
		Flags="WATER_OK CAN_NOT_BE_SCRAMBLED" WaypointModeTerminal="false">
{TEMPLATE_FILTER}	</SpecialPowerTemplate>
	<WeaponTemplate id="CNV_DeckSendTrigger" RadiusDamageAffects="SELF ALLIES" AttackRange="10000"
		Flags="NOT_ATTRACTED_BY_MAGNETS">
		<FiringDuration MinSeconds="0.1s" MaxSeconds="0.1s"/>
		<Nuggets>
			<SpecialPowerNugget SpecialPowerTemplate="SpecialPower_CNV_DeckSend"/>
		</Nuggets>
	</WeaponTemplate>
'''
JUMP_MODULES = (CHRONO_MODULES.replace('FadeInTime="1s"/>', 'FadeInTime="1s"\n\t\t\t\tSourceWeapon="CNV_DeckStoreTrigger" '
                                       'DestinationWeapon="CNV_DeckSendTrigger"/>')
                + DECK_MODULES.split('\t\t\t<FireWeaponUpdate')[0]
                .replace('SpecialPowerTemplate="SpecialPower_CNV_ChronoDeck"', 'SpecialPowerTemplate="SpecialPower_CNV_DeckSend"'))
if CHRONO_MODE == 'jump':
    assert 'DestinationWeapon' in JUMP_MODULES and JUMP_MODULES.count('SpecialPower_CNV_DeckSend') == 2
# v2 炮塔 (CNV_TURRETS=1, default): the carrier spawns TURRETS deck turrets that stay glued to it and can be shot off one
# by one -- the war factory's repair-drone wiring: SpawnBehavior on the master, SlavedUpdate on each turret. A turret
# is a copy of the Twinblade (hovers, rockets + autocannon at ground targets) without its transport bay, with a short
# leash, dying with the carrier. No respawn in the probe (SpawnReplaceDelay very long).
TURRETS = int(os.environ.get('CNV_TURRETS', '4'))
TURRET = 'CNV_LibertyTurret'
TURRET_SPAWN = f'''			<SpawnBehavior id="ModuleTag_CNV_DeckTurrets" SpawnNumberData="{TURRETS}" InitialBurst="{TURRETS}"
				SpawnReplaceDelayData="9999s" SpawnedRequireSpawner="true" KillSpawnsOnCaptured="true"
				ExitByBudding="true">
				<Die DeathTypes="ALL"/>
				<SpawnTemplate>{os.environ.get('CNV_SPAWN_TEMPLATE', TURRET)}</SpawnTemplate>
			</SpawnBehavior>
'''
TURRET_SLAVE = '''			<SlavedUpdate id="ModuleTag_CNV_DeckSlave" LeashRange="60" GuardMaxRange="40" GuardWanderRange="10"
				AttackRange="250" AttackWanderRange="20" DieOnMastersDeath="true" StayOnSameLayerAsMaster="true"/>
'''
if TURRETS:
    c7.EXTRA_TEMPLATES[TURRET] = {'file': f'DATA:CNVUnits/Data/{TURRET}.xml', 'EditorSorting': 'UNIT'}


TURRET_DRONE = f'''<?xml version="1.0" encoding="UTF-8"?>
<AssetDeclaration xmlns="uri:ea.com:eala:asset" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
	<Includes>
		<Include type="all" source="DATA:GlobalData/GlobalDefines.xml" />
		<Include type="all" source="ART:AURepairDrone_SKN.w3x" />
		<Include type="all" source="ART:AURepairDrone_IDLA.w3x" />
		<Include type="instance" source="DATA:BaseObjects/BaseObject.xml" />
	</Includes>
	<GameObject id="{TURRET}" inheritFrom="BaseObject" Side="Allies" EditorSorting="UNIT" EditorName="{TURRET}"
		KindOf="DRONE AIRCRAFT NO_COLLIDE CAN_ATTACK SCORE VEHICLE" ShockwaveResistance="120.0">
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
					<Weapon Ordering="PRIMARY_WEAPON" Template="{os.environ.get('CNV_TURRET_GUN', 'SovietAntiGroundAircraftAutoCannon')}" />
				</WeaponSlotHardpoint>
				<WeaponSlotHardpoint ID="2">
					<Weapon Ordering="PRIMARY_WEAPON" Template="SovietAntiAirShipFlakCannon" />
				</WeaponSlotHardpoint>
			</WeaponSetUpdate>
{TURRET_SLAVE}			<SlowDeath id="ModuleTag_Death" DestructionDelay="1s" Fade="true" FadeTime="1s">
				<DieMuxData DeathTypes="ALL" />
			</SlowDeath>
			<Physics id="ModuleTag_Physics" />
		</Behaviors>
		<AI>
			<AIUpdate id="ModuleTag_AIUpdate" AutoAcquireEnemiesWhenIdle="YES" StateMachine="UnitAIStateMachine" />
		</AI>
		<Body>
			<ActiveBody id="ModuleTag_Body" MaxHealth="400.0" />
		</Body>
		<Geometry IsSmall="true">
			<Shape Type="CYLINDER" MajorRadius="8.0" Height="8.0" />
		</Geometry>
		<VisionInfo VisionRange="300" ShroudClearingRange="100" />
	</GameObject>
</AssetDeclaration>
'''


def turret_xml():
    """v2 (CNV_TURRET_BASE=drone, default): the repair drone (spawns and follows: _153352) armed with the Twinblade's
    autocannon and the Bullfrog's flak, 400 health, attackable. v1 (=twinblade): never spawned."""
    if os.environ.get('CNV_TURRET_BASE', 'drone') == 'drone':
        with open(os.path.join(c26.DATA, TURRET + '.xml'), 'w', encoding='utf-8', newline='\r\n') as f:
            f.write(TURRET_DRONE)
        return
    x = open(os.path.join(SAGE, 'SovietAntiGroundAircraft.xml'), encoding='utf-8').read()
    x = sub1(x, 'id="SovietAntiGroundAircraft"', f'id="{TURRET}"')
    x = sub1(x, 'EditorName="SovietAntiGroundAircraft"', f'EditorName="{TURRET}"')
    x, n = re.subn(r'\s*<TransportContain\b.*?</TransportContain>', '', x, flags=re.S)
    assert n == 1
    x = sub1(x, ' TRANSPORT LEAVE_PARKING_ON_BUILD_COMPLETE PRODUCED_AT_HELIPAD"', '"')
    x = sub1(x, 'CommandSet="SovietAntiGroundAircraftCommandSet"', 'CommandSet="SovietBomberAircraftCommandSet"')
    x = sub1(x, '\t\t</Behaviors>', TURRET_SLAVE + '\t\t</Behaviors>')
    x = sub1(x, 'VisionRange="200"', 'VisionRange="300"')
    # spawned Twinblade copies never showed up (_152920, _153139) while the war factory's repair drones spawned and
    # followed the carrier (_153352): the drones run a plain AIUpdate, the Twinblade a JetAIUpdate (airfield logic)
    x, n = re.subn(r'<JetAIUpdate(.*?)StateMachine="TransportHelicopterAIStateMachine">(.*?)</JetAIUpdate>',
                   r'<AIUpdate\1StateMachine="UnitAIStateMachine">\2</AIUpdate>', x, flags=re.S)
    assert n == 1
    with open(os.path.join(c26.DATA, TURRET + '.xml'), 'w', encoding='utf-8', newline='\r\n') as f:
        f.write(x.replace('\r\n', '\n'))


if CHRONO:
    c7.EXTRA_OWN += [b'SpecialPowerTemplate:SpecialPower_CNV_ChronoDeck', b'LogicCommand:Command_CNV_ChronoDeck',
                     b'LogicCommandSet:CNV_LibertyCommandSet', b'UnitAbilityButtonTemplate:Button_CNV_ChronoDeck']
    c7.EXTRA_ALL.append('DATA:CNVUnits/Data/' + UI_FILE)
    if CHRONO_MODE == 'deck':
        CHRONO_DECL = CHRONO_DECL.replace('WaypointModeTerminal="false"/>', 'WaypointModeTerminal="false">\n'
                                          + TEMPLATE_FILTER + '\t</SpecialPowerTemplate>', 1) + DECK_DECL
        CHRONO_MODULES = DECK_MODULES
        c7.EXTRA_OWN += [b'SpecialPowerTemplate:SpecialPower_CNV_DeckStore', b'ObjectFilterAsset:CNV_DeckFilter',
                         b'WeaponTemplate:CNV_DeckStoreTrigger']
    elif CHRONO_MODE == 'jump':
        CHRONO_DECL += DECK_DECL + JUMP_DECL
        CHRONO_MODULES = JUMP_MODULES
        c7.EXTRA_OWN += [b'SpecialPowerTemplate:SpecialPower_CNV_DeckStore', b'ObjectFilterAsset:CNV_DeckFilter',
                         b'WeaponTemplate:CNV_DeckStoreTrigger', b'SpecialPowerTemplate:SpecialPower_CNV_DeckSend',
                         b'WeaponTemplate:CNV_DeckSendTrigger']


def sub1(x, old, new):
    assert x.count(old) == 1, (old[:60], x.count(old))
    return x.replace(old, new, 1)


def drone_weapon():
    """The Kirov's bomb weapon (fires from this host) with range 600, a 5-shot clip every 10 s and the aircraft
    carrier's drone OCL instead of the bomb. The carrier's own drone weapon was tried first: no launch either -- the
    cause was the Kirov's 150 vision (unit_xml), not the weapon."""
    w = open(os.path.join(c2.SDK, 'SageXML', 'GlobalData', 'Weapon.xml'), encoding='utf-8').read()
    m = re.search(r'\t*<WeaponTemplate\s+id="SovietBomberAircraftBombWeapon".*?</WeaponTemplate>\n', w, re.S)
    x = m.group(0).replace('id="SovietBomberAircraftBombWeapon"', 'id="CNV_LibertyDrones"')
    x = sub1(x, 'AttackRange="5.0"', f'AttackRange="{DRONE_RANGE}.0"')
    x = sub1(x, 'ClipSize="1"', 'ClipSize="5"\n\t\tAutoReloadsClip="AUTO"')
    x = sub1(x, 'MinSeconds="0.8s"\n\t\t\tMaxSeconds="1.0s"', 'MinSeconds="10.0s"\n\t\t\tMaxSeconds="10.0s"')
    x = sub1(x, 'MinSeconds=".1s"\n\t\t\tMaxSeconds=".1s"', 'MinSeconds="0.5s"\n\t\t\tMaxSeconds="0.5s"')
    x, n = re.subn(r'<ProjectileNugget.*?</ProjectileNugget>', '<WeaponOCLNugget WeaponOCL="OCL_AlliedAttackDrones"/>',
                   x, flags=re.S)
    assert n == 1
    return x


def unit_xml():
    x = open(os.path.join(SAGE, 'SovietBomberAircraft.xml'), encoding='utf-8').read()
    x = sub1(x, 'id="SovietBomberAircraft"', f'id="{UNIT}"')
    x = sub1(x, 'EditorName="SovietBomberAircraft"', f'EditorName="{UNIT}"')
    if os.environ.get('CNV_LIB_WEAPON') != 'kirov':      # the control: the Kirov's own bombs, same clicks
        x = sub1(x, 'Template="SovietBomberAircraftBombWeapon"', 'Template="CNV_LibertyDrones"')
    # the Kirov sees 150 (it bombs what is under it): nothing fired at 450 until it could see that far -- CampNew35's
    # lesson (CheckVisionRange off did not help)
    x = sub1(x, 'VisionRange="150"', 'VisionRange="650"')
    assert x.count('CheckVisionRange="true"') == 2           # the turret's and the AI's target choosers
    x = x.replace('CheckVisionRange="true"', 'CheckVisionRange="false"')
    if CHRONO:
        x = sub1(x, 'CommandSet="SovietBomberAircraftCommandSet"', 'CommandSet="CNV_LibertyCommandSet"')
        x = sub1(x, '\t\t</Behaviors>', CHRONO_MODULES + '\t\t</Behaviors>')
        with open(os.path.join(c26.DATA, UI_FILE), 'w', encoding='utf-8', newline='\r\n') as f:
            f.write('<?xml version="1.0" encoding="UTF-8"?>\n<AssetDeclaration xmlns="uri:ea.com:eala:asset" '
                    'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">\n' + CHRONO_UI + '</AssetDeclaration>\n')
    if TURRETS:
        x = sub1(x, '\t\t</Behaviors>', TURRET_SPAWN + '\t\t</Behaviors>')
        turret_xml()
    x = sub1(x, '</AssetDeclaration>', (CHRONO_DECL if CHRONO else '') + drone_weapon() + '</AssetDeclaration>')
    with open(os.path.join(c26.DATA, UNIT + '.xml'), 'w', encoding='utf-8', newline='\r\n') as f:
        f.write(x.replace('\r\n', '\n'))


A = c28.A
SCENE = [(UNIT, (A[0], A[1] - 60), True)]
SCENE += [('SovietAntiVehicleVehicleTech1', (A[0] + dx, A[1] + 390), False) for dx in (-80, 0, 80)]
# CNV_SCENE=turrets: the Hammers 170 north (inside the turrets' leash-and-attack reach) and an enemy Bullfrog
# (anti-air) with them, to shoot turrets down
SCENE_KIND = os.environ.get('CNV_SCENE', '')
if SCENE_KIND == 'turrets':
    SCENE = [SCENE[0]] + [('SovietAntiVehicleVehicleTech1', (A[0] + dx, A[1] + 170), False) for dx in (-80, 0, 80)]
    SCENE.append(('SovietAntiAirShip_Ground', (A[0] + 140, A[1] + 200), False))
    # turrets fight: two Hammers 120 north (inside the autocannon's 150), an enemy Twinblade (flak target)
    if os.environ.get('CNV_TURRET_FIGHT') == '1':
        SCENE = [SCENE[0], ('SovietAntiVehicleVehicleTech1', (A[0] - 40, A[1] + 60), False),
                 ('SovietAntiVehicleVehicleTech1', (A[0] + 40, A[1] + 60), False),
                 ('SovietAntiGroundAircraft', (A[0] + 120, A[1] + 40), False),
                 ('SovietAntiAirShip_Ground', (A[0] + 140, A[1] + 200), False)]
# a spawned template of ours only loads when one is also placed on the map (spawning failed until then, _154143):
# one turret parked out of the way, south-west (CNV_PLACE_TURRET=0 to leave it out)
if TURRETS and os.environ.get('CNV_PLACE_TURRET', '1') == '1':
    SCENE.append((TURRET, (A[0] - 330, A[1] - 300), True))
# the deck jump: three of our Guardians under the carrier (inside DECK) and one outside it (should stay behind)
if CHRONO and CHRONO_MODE in ('deck', 'jump') and SCENE_KIND != 'turrets':
    SCENE += [('AlliedAntiVehicleVehicleTech1', (A[0] + dx, A[1] - 60 + dy), True)
              for dx, dy in ((-60, 0), (60, 0), (0, -60), (-330, -60))]

_generate = c6.edit


def generate(m):
    unit_xml()
    _generate(m)                                 # CampNew29's scene: factory, power plant, our tanks, Hammers
    objs = next(n for _, n in m.walk() if n.name == 'ObjectsList')
    head = lambda k: k.head[:60]                 # noqa: E731
    p1 = next(k for k in objs.kids if b'CNV_LightTank2' in head(k))
    s1 = next(k for k in objs.kids if b'SovietAntiVehicleVehicleTech1' in head(k))
    gone = [k for k in objs.kids if any(u in head(k) for u in (b'CNV_LightTank2', b'CNV_ShrinkVehicle', b'Allied',
                                                                 b'SovietAntiVehicleVehicleTech1'))
            and b'AlliedWarFactory' not in head(k) and b'AlliedPowerPlant' not in head(k)
            and b'AlliedConstructionYard' not in head(k)]
    objs.kids[:] = [k for k in objs.kids if k not in gone]
    for template, (x, y), ours in SCENE:
        pr, flags = newmap.typed_props_of(m, p1 if ours else s1)
        objs.kids.append(newmap.object_node(m, pr, flags, template, x, y, angle=math.pi / 2 if ours else -math.pi / 2,
                                            uniqueID=f'{template} {len(objs.kids)}'))
    print('CNV38: removed', len(gone), 'units;', len(SCENE), 'placed')


c6.edit = generate

if __name__ == '__main__':
    if c23.game_running():
        c2.OUT = c4.OUT = os.path.join(os.path.dirname(os.path.dirname(HERE)), 'work', 'staging', NAME)
        print('RA3 is running -> staging at', c4.OUT)
    c4.main()
