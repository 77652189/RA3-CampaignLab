"""帝国「鸣神」机制验证 (CampNew31): the signal zone and 复仇意志 on retail stand-ins, no new model yet.

Signal zone: an AttributeModifierAuraUpdate on the signal unit gives allies in range AttributeModifier_CNV_SignalLink,
whose ObjectStatusToSet is LINK (a C&C3 Tiberium bit nothing in RA3 sets). 复仇意志: a FireWeaponWhenDead on each
Empire unit taking part, DieMuxData RequiredStatus = LINK, fires CNV_VengeancePulse: an AttributeModifierNugget giving
allies around the dead unit AttributeModifier_CNV_Vengeance (damage / speed up, 20 s, up to 3 stacks, the Iron
Curtain shader so the bench sees who has it).

Stand-ins: the signal unit = a copy of the Sudden Transport (unarmed: on the bench only the aura is new), the dying
units = copies of the Imperial Warrior with the death module, the receivers = Sudden Transports. Group A stands in the
signal zone, group B (control) outside it; a Soviet Sickle south of each group kills its warriors. Expected: group A's
receiver turns red when a warrior dies, group B's does not. The player's retail units of the base map are left out
(the base's Guardians would shoot the Sickles).

  python -I -X utf8 experimental/campaign/make_campnew31.py            -> Documents\\Red Alert 3\\Mods\\CampNew31
  CNV_SHOW_LINK=1: the link modifier also gets the Chrono Rift shader (does the aura reach the right units?)
"""
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import make_campnew29 as c29                    # noqa: E402

c28, c23 = c29.c28, c29.c23
c26, c7, c6, c4, c2 = c28.c26, c23.c7, c23.c6, c23.c4, c23.c2
newmap = c23.newmap
NAME = 'CampNew31'
c4.NAME = c2.NAME = NAME
c2.SRC_DIR = os.path.join(c2.SDK, 'Mods', NAME, 'data')
c2.BUILT = os.path.join(c2.SDK, 'BuiltMods', 'mods', NAME.lower(), 'data')
c2.OUT = c4.OUT = os.path.join(os.path.expanduser('~'), 'Documents', 'Red Alert 3', 'Mods', NAME)
c7.MAP_MOD = NAME + 'Map'

SAGE = os.path.join(c2.SDK, 'SageXML', 'Japan', 'Units')
WARRIOR, SIGNAL = 'CNV_JWarrior', 'CNV_SignalProbe'
LINK = 'HAS_TIBERIUM_GROWTH_MOD'
# probe radii, smaller than the design's 250 / 200 so both groups fit the bench view apart
AURA_RANGE, PULSE_RADIUS = 200, 150
SHOW_LINK = os.environ.get('CNV_SHOW_LINK') == '1'
A = c28.A
GROUPS = {'A': A[0] - 120, 'B': A[0] + 260}       # x of each group; group A has the signal unit
W_Y, R_Y, S_Y, K_Y = A[1] + 280, A[1] + 400, A[1] + 340, A[1] + 120

DECL = f'''	<AttributeModifier id="AttributeModifier_CNV_SignalLink" Category="NONE" ObjectStatusToSet="{LINK}"
		Duration="1s"{' Shader="ShaderOverride_ObjectsChronoRift"' if SHOW_LINK else ''}>
		<Modifier Type="VISION" Value="100%"/>
	</AttributeModifier>
	<AttributeModifier id="AttributeModifier_CNV_Vengeance" Category="NONE" Duration="20s" StackingLimit="3"
		Shader="ShaderOverride_ObjectsIronCurtain">
		<Modifier Type="DAMAGE_MULT" Value="120%"/>
		<Modifier Type="SPEED" Value="115%"/>
	</AttributeModifier>
	<WeaponTemplate id="CNV_VengeancePulse" Flags="NOT_ATTRACTED_BY_MAGNETS" AttackRange="999999.0"
		RequiredAntiMask="ANTI_GROUND ANTI_STRUCTURE ANTI_WATER" RadiusDamageAffects="ALLIES">
		<Nuggets>
			<AttributeModifierNugget Radius="{PULSE_RADIUS}" PartitionFilterTestType="SPHERE"
				AttributeModifierName="AttributeModifier_CNV_Vengeance">
				<SpecialObjectFilter Rule="ANY" Include="VEHICLE INFANTRY"/>
			</AttributeModifierNugget>
		</Nuggets>
	</WeaponTemplate>
'''
DEATH = f'''			<FireWeaponWhenDead id="ModuleTag_CNV_Vengeance" DeathWeapon="CNV_VengeancePulse" InitiallyActive="true">
				<DieMuxData DeathTypes="ALL" RequiredStatus="{LINK}"/>
			</FireWeaponWhenDead>
'''
AURA = f'''			<AttributeModifierAuraUpdate id="ModuleTag_CNV_SignalAura" AttributeModifierName="AttributeModifier_CNV_SignalLink"
				RefreshDelay="0.5s" Range="{AURA_RANGE}" InitiallyActive="true" AllowSelf="true">
				<ObjectFilter Rule="ANY" Relationship="ALLIES SAME_PLAYER" Include="VEHICLE INFANTRY"/>
			</AttributeModifierAuraUpdate>
'''
# CNV_PROBE=transform: the transform on a copy of the Mecha Tengu (its ToggleStatusSpecialAbilityUpdate, one button).
# Second state = 信号形态: no jet (normal locomotor, no airborne armour / model), IMMOBILE, the aura on only then
# (RequiredObjectStatusFlags). The toggle's TriggerAttributeModifier (retail: the 1.5 s transform animation) becomes
# the 突进: SPEED 250 % for 2 s on every toggle -- deploying is immobile anyway, so it shows on the way out.
TRANSFORM = os.environ.get('CNV_PROBE') == 'transform'
NARUKAMI = 'CNV_NarukamiProbe'
NARUKAMI_DECL = '''	<AttributeModifier id="AttributeModifier_CNV_SignalDeploy" Category="NONE" ObjectStatusToSet="IMMOBILE">
		<Modifier Type="VISION" Value="100%"/>
	</AttributeModifier>
	<AttributeModifier id="AttributeModifier_CNV_Dash" Category="NONE" Duration="2s">
		<Modifier Type="SPEED" Value="250%"/>
	</AttributeModifier>
	<SpecialPowerTemplate id="SpecialPower_CNV_NarukamiTransform" ReloadTime="2s" TargetType="NONE"
		Flags="NOT_IN_NANOSWARM CAN_NOT_BE_SCRAMBLED NOT_WHILE_BENEATH_BRIDGE" WaypointModeTerminal="false"/>
	<LogicCommand Type="SPECIAL_POWER" id="Command_CNV_NarukamiTransform">
		<SpecialPower>SpecialPower_CNV_NarukamiTransform</SpecialPower>
		<AISpecialPowerInfo Heuristic="TOGGLE" Manager="MICRO_MANAGER"/>
	</LogicCommand>
	<LogicCommandSet id="CNV_NarukamiCommandSet">
		<Cmd>Command_CNV_NarukamiTransform</Cmd>
		<Cmd>Command_AttackMove</Cmd>
		<Cmd>Command_MoveToPositionAndCollect</Cmd>
	</LogicCommandSet>
'''
# own transform power: the retail one reloads in 15 s (CampNew31 bench: the way back out was refused); its button
# (nothing references it: own file, type="all") keeps the Tengu's two button states
NARUKAMI_UI_FILE = 'CNV_Narukami_UI.xml'
NARUKAMI_UI = '''	<UnitAbilityButtonTemplate id="Button_CNV_NarukamiTransform" LogicCommand="Command_CNV_NarukamiTransform">
		<Data>
			<ToggleSpecialPower>
				<StateData>ButtonStateJAIV_Transform</StateData>
				<StateData>ButtonStateJAIV_TransformOff</StateData>
			</ToggleSpecialPower>
		</Data>
	</UnitAbilityButtonTemplate>
'''
c7.EXTRA_OWN += [b'AttributeModifier:AttributeModifier_CNV_SignalDeploy', b'AttributeModifier:AttributeModifier_CNV_Dash',
                 b'SpecialPowerTemplate:SpecialPower_CNV_NarukamiTransform', b'LogicCommand:Command_CNV_NarukamiTransform',
                 b'LogicCommandSet:CNV_NarukamiCommandSet', b'UnitAbilityButtonTemplate:Button_CNV_NarukamiTransform']
c7.EXTRA_ALL.append('DATA:CNVUnits/Data/' + NARUKAMI_UI_FILE)
for t in (WARRIOR, SIGNAL, NARUKAMI):
    c7.EXTRA_TEMPLATES[t] = {'file': f'DATA:CNVUnits/Data/{t}.xml', 'EditorSorting': 'UNIT'}
c7.EXTRA_OWN += [b'AttributeModifier:AttributeModifier_CNV_SignalLink', b'AttributeModifier:AttributeModifier_CNV_Vengeance',
                 b'WeaponTemplate:CNV_VengeancePulse']


def sub1(x, old, new):
    assert x.count(old) == 1, (old[:60], x.count(old))
    return x.replace(old, new, 1)


def copy_unit(src, unit, behaviors, decl=''):
    """The retail unit's XML under a new id, `behaviors` added at the end of its Behaviors, `decl` after it."""
    x = open(os.path.join(SAGE, src + '.xml'), encoding='utf-8').read()
    x = sub1(x, f'id="{src}"', f'id="{unit}"')
    x = sub1(x, f'EditorName="{src}"', f'EditorName="{unit}"')
    x = sub1(x, '</Behaviors>', behaviors.lstrip() + '\t\t</Behaviors>')
    x = sub1(x, '</AssetDeclaration>', decl + '</AssetDeclaration>')
    with open(os.path.join(c26.DATA, unit + '.xml'), 'w', encoding='utf-8', newline='\r\n') as f:
        f.write(x.replace('\r\n', '\n'))


def narukami_xml():
    copy_unit('JapanAntiInfantryVehicle', NARUKAMI,
              DEATH + AURA.replace('InitiallyActive="true"', 'InitiallyActive="true" '
                                   'RequiredObjectStatusFlags="TRANSFORMATION_TOGGLE_STATE"'), NARUKAMI_DECL)
    path = os.path.join(c26.DATA, NARUKAMI + '.xml')
    x = open(path, encoding='utf-8').read()
    x = sub1(x, 'TriggerAttributeModifier="AttributeModifier_JapanAntiInfantryVehicleTransformation"',
             'TriggerAttributeModifier="AttributeModifier_CNV_Dash"')
    x = sub1(x, 'AttributeModifierDuration="1.5s"', 'AttributeModifierDuration="2s"')
    assert x.count('SpecialPowerTemplate="SpecialPower_JAIV_Transform"') == 2
    x = x.replace('SpecialPowerTemplate="SpecialPower_JAIV_Transform"',
                  'SpecialPowerTemplate="SpecialPower_CNV_NarukamiTransform"')
    x = sub1(x, 'CommandSet="JapanAntiInfantryVehicleCommandSet"', 'CommandSet="CNV_NarukamiCommandSet"')
    with open(os.path.join(c26.DATA, NARUKAMI_UI_FILE), 'w', encoding='utf-8', newline='\r\n') as f:
        f.write('<?xml version="1.0" encoding="UTF-8"?>\n<AssetDeclaration xmlns="uri:ea.com:eala:asset" '
                'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">\n' + NARUKAMI_UI + '</AssetDeclaration>\n')
    x = sub1(x, '''ObjectStatus="TRANSFORMATION_TOGGLE_STATE"
                            LocomotorSet="SUPERSONIC"
                            ArmorSet="AIRBORNE"
                            ModelConditions="USER_1">''', '''ObjectStatus="TRANSFORMATION_TOGGLE_STATE"
                            LocomotorSet="NORMAL"
                            AttributeModifier="AttributeModifier_CNV_SignalDeploy">''')
    with open(path, 'w', encoding='utf-8', newline='\r\n') as f:
        f.write(x.replace('\r\n', '\n'))


_generate = c6.edit


def generate(m):
    copy_unit('JapanAntiInfantryInfantry', WARRIOR, DEATH, DECL)
    copy_unit('JapanLightTransportVehicle', SIGNAL, AURA)
    narukami_xml()
    _generate(m)                                 # CampNew29's scene: factory, power plant, our tanks, Hammers
    objs = next(n for _, n in m.walk() if n.name == 'ObjectsList')
    head = lambda k: k.head[:60]                 # noqa: E731
    p1 = next(k for k in objs.kids if b'CNV_LightTank2' in head(k))
    s1 = next(k for k in objs.kids if b'SovietAntiVehicleVehicleTech1' in head(k))
    units = (b'CNV_LightTank2', b'CNV_ShrinkVehicle', b'AlliedSupportAircraft', b'SovietAntiVehicleVehicleTech1',
             b'AlliedAntiVehicleVehicleTech1', b'AlliedAntiInfantryVehicle', b'AlliedAntiAirVehicle',
             b'AlliedScoutVehicle', b'AlliedMiner', b'AlliedMCV', b'AlliedAntiStructureVehicle', b'AlliedInfantry',
             b'AlliedAntiInfantryInfantry', b'AlliedAntiVehicleInfantry', b'AlliedEngineer', b'AlliedScoutInfantry')
    gone = [k for k in objs.kids if any(u in head(k) for u in units)]
    objs.kids[:] = [k for k in objs.kids if k not in gone]
    place = []
    if TRANSFORM:                                # the probe (left, warriors around it) and an untouched control
        place += [(p1, NARUKAMI, (A[0] - 100, A[1] + 100), math.pi / 2),
                  (p1, NARUKAMI, (A[0] + 200, A[1] + 100), math.pi / 2)]
        place += [(p1, WARRIOR, (A[0] - 100 + dx, A[1] + 100 + dy), math.pi / 2)
                  for dx, dy in ((-90, 0), (90, 0), (0, 90))]
    for g, x in ({} if TRANSFORM else GROUPS).items():
        place += [(p1, WARRIOR, (x + dx, W_Y), math.pi / 2) for dx in (-40, 0, 40)]
        place += [(p1, 'JapanLightTransportVehicle', (x, R_Y), math.pi / 2),
                  (s1, 'SovietAntiInfantryVehicle', (x, K_Y), math.pi / 2)]
        if g == 'A':
            place.append((p1, SIGNAL, (x + 70, S_Y), math.pi / 2))
    for src, template, (x, y), angle in place:
        pr, flags = newmap.typed_props_of(m, src)
        objs.kids.append(newmap.object_node(m, pr, flags, template, x, y, angle=angle,
                                            uniqueID=f'{template} {len(objs.kids)}'))
    print('CNV31: removed', len(gone), 'units;', len(place), 'placed', '(link shown)' if SHOW_LINK else '')


c6.edit = generate

if __name__ == '__main__':
    if c23.game_running():
        c2.OUT = c4.OUT = os.path.join(os.path.dirname(os.path.dirname(HERE)), 'work', 'staging', NAME)
        print('RA3 is running -> staging at', c4.OUT)
    c4.main()
