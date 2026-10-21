"""帝国「烟花兵」机制验证 (CampNew37): anti-air bursts that linger a few seconds where they went off, no new model yet.

Design (docs/story/units.md, user 2026-10-20): the Empire has no anti-air infantry and weak early ground anti-air (the
Archer Maiden tried and failed: poor against aircraft, too strong against armour). The firework trooper does not chase
aircraft; it closes air space: a burst hangs in the air for a few seconds and every aircraft passing through it is
hurt. Good over ore fields and base entrances, poor at hunting. No ground attack; shorter range than the IFV (300).

Stand-in: a copy of the Tank Buster (its instant plasma shot and laser) with the weapon cut to CNV_Hanabi: anti-air
only, range 250, the damage split into PULSES delayed pulses (FLAK, radius 60, CIRCLE: the aircraft's altitude does
not matter) over ~2.5 s. Question for the bench: do delayed pulses stay where the shot landed (an air-denial cloud) or
follow the target (plain damage over time)?

Scene: CampNew36's raid -- a Soviet ore truck, four of our Vindicators south of it, our airfield to fly home to -- with
three firework troopers beside the truck instead of the balloon (CampNew36's CNV_NO_BALLOON run is the control).

Bench (2026-10-21): the raid loses 1 Vindicator of 4, the truck is still bombed (about the balloon's result); the
troopers walk after the aircraft. Cloud or follow is not settled: a lone 400 pulse 2 s after the shot killed only 1 of
4 planes flying past (as if it stayed) but that one fell ~200 beyond the troopers (as if it followed). For a real
cloud: a WeaponOCLNugget object at the burst (the carrier's drones), hurting aircraft around itself for a while.
v2 (the cloud, below): the pulse flashes sit on the ground under where each plane was hit and go on there after the
plane has flown on -- the cloud stays. 2 of 4 Vindicators went down (on the way home), the truck was still bombed.
Set up (CNV_SCENE=deploy): packed they walk and hold fire; set up they fire within 2 s and both hovering Vindicators
go down; they ignore a move order. The raid scene's troopers are the enemy's: run it with CNV_DEPLOY=0.

  python -I -X utf8 experimental/campaign/make_campnew37.py            -> Documents\\Red Alert 3\\Mods\\CampNew37
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
NAME = 'CampNew37'
c4.NAME = c2.NAME = NAME
c2.SRC_DIR = os.path.join(c2.SDK, 'Mods', NAME, 'data')
c2.BUILT = os.path.join(c2.SDK, 'BuiltMods', 'mods', NAME.lower(), 'data')
c2.OUT = c4.OUT = os.path.join(os.path.expanduser('~'), 'Documents', 'Red Alert 3', 'Mods', NAME)
c7.MAP_MOD = NAME + 'Map'

SAGE = os.path.join(c2.SDK, 'SageXML', 'Japan', 'Units')
UNIT = 'CNV_HanabiProbe'
c7.EXTRA_TEMPLATES[UNIT] = {'file': f'DATA:CNVUnits/Data/{UNIT}.xml', 'EditorSorting': 'UNIT'}
c7.EXTRA_OWN += [b'WeaponTemplate:CNV_Hanabi']

RANGE = int(os.environ.get('CNV_HANABI_RANGE', '250'))
PULSE = os.environ.get('CNV_HANABI_PULSE', '15')
PULSES = int(os.environ.get('CNV_HANABI_PULSES', '5'))
RADIUS = os.environ.get('CNV_HANABI_RADIUS', '80')       # v1's delayed pulses had 60; the cloud's bench run 80
TROOPERS = int(os.environ.get('CNV_HANABI_N', '3'))
# the probe for "cloud or follow": CNV_HANABI_PULSES=1 CNV_HANABI_DELAY0=2.0 CNV_HANABI_PULSE=400 -- a killing pulse 2 s
# after the shot: if it follows the target, the hit aircraft die where they are; if it stays, they are long gone
DELAY0 = float(os.environ.get('CNV_HANABI_DELAY0', '0.3'))


# v2 (2026-10-21, cloud or follow unsettled with delayed pulses): CNV_HANABI_CLOUD=1 (default) -- each shot leaves a
# CNV_HanabiCloud on the ground under the target (an OCL with CREATE_AT_TARGET, as the vacuum bomb's seed), living
# CLOUD_TIME and firing CNV_HanabiPulse every 0.5 s (FireWeaponUpdate, as the Cryo Satellite's beam object): FLAK, a
# flat CIRCLE radius so the altitude does not matter, aircraft only. The pulse's fire FX marks where the cloud sits.
# The shot itself keeps one 10 hit. CNV_HANABI_CLOUD=0: v1's delayed pulses
CLOUD = os.environ.get('CNV_HANABI_CLOUD', '1') == '1'
DEPLOY = os.environ.get('CNV_DEPLOY', '1') == '1'
# CNV_SCENE: raid (default; run it with CNV_DEPLOY=0) | deploy (our three troopers, two enemy Vindicators hovering
# 145 north: walk packed -> no fire; set up -> fire; move order -> stay)
SCENE_KIND = os.environ.get('CNV_SCENE', 'raid')
TOGGLE = '''			<SpecialPower id="ModuleTag_CNV_HanabiTrigger" SpecialPowerTemplate="SpecialPower_ToggleTargetPainter"/>
			<ToggleStatusSpecialAbilityUpdate id="ModuleTag_CNV_HanabiToggle" Options="RECONSTITUTE_STORED_COMMAND"
				SpecialPowerTemplate="SpecialPower_ToggleTargetPainter">
				<ToggleState>
					<SkirmishAiInfo ToggleHint="TOGGLE_DEFAULT"/>
				</ToggleState>
				<ToggleState ObjectStatus="GENERIC_TOGGLE_STATE" AttributeModifier="AttributeModifier_CNV_HanabiSet">
					<SkirmishAiInfo ToggleHint="TOGGLE_DEFAULT"/>
				</ToggleState>
			</ToggleStatusSpecialAbilityUpdate>
'''
# IMMOBILE_ALLOW_ROTATE, not IMMOBILE: set up with IMMOBILE they never fired (bench _011509) -- infantry turn the whole
# body to aim (the shot's AcceptableAimDelta is 10d), the vehicles that took IMMOBILE have turrets
DEPLOY_DECL = '''	<AttributeModifier id="AttributeModifier_CNV_HanabiSet" Category="NONE" ObjectStatusToSet="IMMOBILE_ALLOW_ROTATE"/>
	<LogicCommandSet id="CNV_HanabiCommandSet">
		<Cmd>Command_ToggleTargetPainter</Cmd>
		<Cmd>Command_AttackMove</Cmd>
		<Cmd>Command_MoveToPositionAndCollect</Cmd>
	</LogicCommandSet>
'''
if DEPLOY:
    c7.EXTRA_OWN += [b'AttributeModifier:AttributeModifier_CNV_HanabiSet', b'LogicCommandSet:CNV_HanabiCommandSet']
CLOUD_TIME = os.environ.get('CNV_HANABI_TIME', '2.5s')
if CLOUD:
    c7.EXTRA_OWN += [b'GameObject:CNV_HanabiCloud', b'WeaponTemplate:CNV_HanabiPulse',
                     b'ObjectCreationList:OCL_CNV_HanabiCloud']
CLOUD_DECL = f'''	<WeaponTemplate id="CNV_HanabiPulse" RadiusDamageAffects="ENEMIES" AttackRange="10000"
		FireFX="FX_SovBatteryFire" Flags="NOT_ATTRACTED_BY_MAGNETS"
		RequiredAntiMask="ANTI_AIRBORNE_VEHICLE ANTI_AIRBORNE_INFANTRY ANTI_GROUND">
		<FiringDuration MinSeconds="0.25s" MaxSeconds="0.25s"/>
		<Nuggets>
			<DamageNugget Damage="{PULSE}.0" Radius="{RADIUS}.0" DamageTaperOff="0" PartitionFilterTestType="CIRCLE"
				DamageType="FLAK" DamageFXType="SOVIET_FLAK" DeathType="EXPLODED">
				<SpecialObjectFilter Rule="ANY" Include="AIRCRAFT"/>
			</DamageNugget>
		</Nuggets>
	</WeaponTemplate>
	<ObjectCreationList id="OCL_CNV_HanabiCloud">
		<CreateObject Disposition="ON_GROUND_ALIGNED" Options="CREATE_AT_TARGET IGNORE_ALL_OBJECTS">
			<CreateObject>CNV_HanabiCloud</CreateObject>
		</CreateObject>
	</ObjectCreationList>
	<GameObject id="CNV_HanabiCloud" TransportSlotCount="0" IsTrainable="false" Side="Japan" EditorSorting="SYSTEM"
		KindOf="UNATTACKABLE NOT_AUTOACQUIRABLE INERT">
		<DisplayName>CNV_HanabiCloud</DisplayName>
		<ArmorSet Armor="NoArmor"/>
		<Behaviors>
			<LifetimeUpdate id="ModuleTag_LifetimeUpdate" MinLifetime="{CLOUD_TIME}" MaxLifetime="{CLOUD_TIME}"/>
			<FireWeaponUpdate id="ModuleTag_FireWeaponUpdate" FireInterval="0.5s">
				<FireWeaponNugget WeaponName="CNV_HanabiPulse" FireDelay="0s"/>
			</FireWeaponUpdate>
			<DestroyDie id="ModuleTag_Die">
				<DieMuxData DeathTypes="ALL"/>
			</DestroyDie>
		</Behaviors>
		<Body>
			<PropBody id="ModuleTag_Body"/>
		</Body>
		<Geometry IsSmall="true">
			<Shape Type="CYLINDER" MajorRadius="20.0" Height="20.0"/>
		</Geometry>
	</GameObject>
'''


def nuggets():
    if CLOUD:
        return ('''			<DamageNugget Damage="10.0" DamageType="FLAK" DamageFXType="SOVIET_FLAK" DeathType="EXPLODED"/>
			<WeaponOCLNugget WeaponOCL="OCL_CNV_HanabiCloud"/>
''')
    return ''.join(f'''			<DamageNugget Damage="{PULSE}.0" Radius="{RADIUS}.0" DamageTaperOff="0"
				DelayTimeSeconds="{DELAY0 + 0.5 * k:.1f}s" PartitionFilterTestType="CIRCLE"
				DamageType="FLAK" DamageFXType="SOVIET_FLAK" DeathType="EXPLODED"/>
''' for k in range(PULSES))


def sub1(x, old, new):
    assert x.count(old) == 1, (old[:60], x.count(old))
    return x.replace(old, new, 1)


def hanabi_weapon():
    w = open(os.path.join(c2.SDK, 'SageXML', 'GlobalData', 'Weapon.xml'), encoding='utf-8').read()
    m = re.search(r'\t*<WeaponTemplate\s+id="JapanAntiVehicleInfantryPlasmaBazooka".*?</WeaponTemplate>\n', w, re.S)
    x = m.group(0).replace('id="JapanAntiVehicleInfantryPlasmaBazooka"', 'id="CNV_Hanabi"')
    x = sub1(x, 'AttackRange="175.0"', f'AttackRange="{RANGE}.0"')
    x = sub1(x, 'RequiredAntiMask="ANTI_GROUND ANTI_STRUCTURE ANTI_WATER"',
             'RequiredAntiMask="ANTI_AIRBORNE_VEHICLE ANTI_AIRBORNE_INFANTRY"')
    x, n = re.subn(r'\s*<DamageNugget\s+id="DefaultDamageNugget".*?/>', '\n' + nuggets().rstrip('\n'), x, flags=re.S)
    assert n == 1
    return x


def unit_xml():
    x = open(os.path.join(SAGE, 'JapanAntiVehicleInfantry.xml'), encoding='utf-8').read()
    # the file's second object (the Ambush power's Tank Buster) inherits from the first: gone with the rename
    x, n = re.subn(r'\s*<GameObject\s+id="JapanAntiVehicleInfantry_Ambush".*?</GameObject>', '', x, flags=re.S)
    assert n == 1
    x = sub1(x, 'id="JapanAntiVehicleInfantry"', f'id="{UNIT}"')
    x = sub1(x, 'EditorName="JapanAntiVehicleInfantry"', f'EditorName="{UNIT}"')
    x = sub1(x, 'Template="JapanAntiVehicleInfantryPlasmaBazooka"', 'Template="CNV_Hanabi"')
    # 守点: the troopers walked after the Vindicators (bench). AIUpdate's StandGround (in the schema, no retail unit
    # sets it) keeps an idle unit from chasing. CNV_STAND=0: as retail
    # StandGround="true" (bench _010909), also with StopChaseDistance 1 (_011159): they still walked after the planes.
    # So 架设: the Guardian's painter toggle, as the balloon truck's -- set up = IMMOBILE and the only state that fires
    if DEPLOY:
        x = sub1(x, 'Template="CNV_Hanabi"/>', 'Template="CNV_Hanabi"\n\t\t\t\t\t\tObjectStatus="GENERIC_TOGGLE_STATE"/>')
        x = sub1(x, 'CommandSet="JapanAntiVehicleInfantryCommandSet"', 'CommandSet="CNV_HanabiCommandSet"')
        x = sub1(x, '</Behaviors>', TOGGLE + '\t\t</Behaviors>')
    else:                                        # CNV_DEPLOY=0 (the raid: nobody sets enemy troopers up): speed 1
        x = sub1(x, 'Condition="NORMAL"\n\t\t\tSpeed="50"', 'Condition="NORMAL"\n\t\t\tSpeed="1"')
    x = sub1(x, '</AssetDeclaration>', (CLOUD_DECL if CLOUD else '') + (DEPLOY_DECL if DEPLOY else '')
             + hanabi_weapon() + '</AssetDeclaration>')
    with open(os.path.join(c26.DATA, UNIT + '.xml'), 'w', encoding='utf-8', newline='\r\n') as f:
        f.write(x.replace('\r\n', '\n'))


TRUCK = (1180, 2635)                             # screen ~(558, 229) at the start camera
SCENE = [('SovietMiner', TRUCK, False)]
# CNV_HANABI_AT=x,y moves the troopers (the cloud-or-follow run: 1000,2400, west of the hovering Vindicators, which are
# then sent east across the middle of the view)
AT = tuple(float(v) for v in os.environ.get('CNV_HANABI_AT', f'{TRUCK[0]},{TRUCK[1] - 40}').split(','))
SCENE += [(UNIT, (AT[0] + dx, AT[1]), False) for dx in (-40, 0, 40)[:TROOPERS]]
# hovering: drawn around screen y 410, not at their ground point's 586 (box-select there)
X0 = float(os.environ.get('CNV_PLANES_X0', '1105'))     # the fly-past run: 950 (out of range of troopers at 1400)
SCENE += [('AlliedAntiGroundAircraft', (X0 + 50 * k, 2335), True) for k in range(4)]
SCENE.append(('AlliedAirfield', (1180, 2060), True))
if SCENE_KIND == 'deploy':                       # ours: three troopers (screen ~(536, 586)); theirs: two Vindicators
    SCENE = [(UNIT, (1180 + dx, 2335), True) for dx in (-30, 0, 30)]
    SCENE += [('AlliedAntiGroundAircraft', (x, 2480), False) for x in (1150, 1210)]

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
    print('CNV37: removed', len(gone), 'units;', len(SCENE), 'placed')


c6.edit = generate

if __name__ == '__main__':
    if c23.game_running():
        c2.OUT = c4.OUT = os.path.join(os.path.dirname(os.path.dirname(HERE)), 'work', 'staging', NAME)
        print('RA3 is running -> staging at', c4.OUT)
    c4.main()
