"""盟军「时滞炮车」机制验证 (CampNew35): a zero-damage shell that pushes its target out of time, no new model yet.

Design (docs/story/units.md, user 2026-10-20): the Allied ground siege piece. It deals no damage; a hit takes the target
out of time -- a unit for 8 s, a structure for 15 s: it cannot move or fire and cannot be hurt, then comes back as it
was. One shot every 30 s. Siege by tempo: phase two of three towers, kill the third.

Stand-in: a copy of the Guardian (its model, turret, painter) with the cannon replaced by CNV_PhaseShell: the
Guardian's shell flight, range 350, a warhead carrying only the phase modifiers (UNATTACKABLE NO_ATTACK
NON_AUTOACQUIRABLE IN_STASIS, speed 0 %, the retail Chrono Rift shader). The 30 s cooldown is CampNew34's trick: the
shot gives its owner COOLDOWN_BIT for 30 s and the weapon does not fire under it (a long clip reload would also run
from the start).

Scene: two of our Guardians 140 south of an enemy Apocalypse (it beats them alone), the phase tank 300 south of it.
CNV_NO_PHASE=1: the same shell without the phase (the control).

Bench (2026-10-20): the Apocalypse turns blue at 1 s, stops moving and firing, is back before 8 s; our Guardians hold
fire meanwhile and shoot again as soon as it returns; the second shot at 29 s. Two Guardians still lose, dying at
10 / 15 s instead of 3 / 10 s. It only fired once its own vision reached the target (see VisionRange below).

  python -I -X utf8 experimental/campaign/make_campnew35.py            -> Documents\\Red Alert 3\\Mods\\CampNew35
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
NAME = 'CampNew35'
c4.NAME = c2.NAME = NAME
c2.SRC_DIR = os.path.join(c2.SDK, 'Mods', NAME, 'data')
c2.BUILT = os.path.join(c2.SDK, 'BuiltMods', 'mods', NAME.lower(), 'data')
c2.OUT = c4.OUT = os.path.join(os.path.expanduser('~'), 'Documents', 'Red Alert 3', 'Mods', NAME)
c7.MAP_MOD = NAME + 'Map'

SAGE = os.path.join(c2.SDK, 'SageXML', 'Allied', 'Units')
UNIT = 'CNV_PhaseProbe'
c7.EXTRA_TEMPLATES[UNIT] = {'file': f'DATA:CNVUnits/Data/{UNIT}.xml', 'EditorSorting': 'UNIT'}
c7.EXTRA_OWN += [b'AttributeModifier:AttributeModifier_CNV_PhaseUnit',
                 b'AttributeModifier:AttributeModifier_CNV_PhaseStructure',
                 b'AttributeModifier:AttributeModifier_CNV_PhaseTag',
                 b'AttributeModifier:AttributeModifier_CNV_PhaseCooldown',
                 b'WeaponTemplate:CNV_PhaseShell', b'WeaponTemplate:CNV_PhaseWarhead']

UNIT_TIME, STRUCTURE_TIME = os.environ.get('CNV_PHASE_UNIT', '8s'), os.environ.get('CNV_PHASE_STRUCTURE', '15s')
RELOAD, RANGE = os.environ.get('CNV_PHASE_RELOAD', '30s'), 350
COOLDOWN_BIT = 'DOES_CONTAIN_TIBERIUM'           # a C&C3 bit no RA3 XML uses (as in CampNew34)
PHASE_STATUS = os.environ.get('CNV_PHASE_STATUS', 'UNATTACKABLE NO_ATTACK NON_AUTOACQUIRABLE IN_STASIS')
NO_PHASE = os.environ.get('CNV_NO_PHASE') == '1'


def nugget(modifier, include, owner=None):
    own = f'\n\t\t\t\tAttributeModifierOwnerName="{owner}"' if owner else ''
    return f'''			<AttributeModifierNugget Radius="10" PartitionFilterTestType="SPHERE"
				AttributeModifierName="{modifier}"{own}>
				<SpecialObjectFilter Rule="ANY" Relationship="ENEMIES" Include="{include}"/>
			</AttributeModifierNugget>
'''


PHASE = '' if NO_PHASE else (nugget('AttributeModifier_CNV_PhaseUnit', 'VEHICLE INFANTRY')
                             + nugget('AttributeModifier_CNV_PhaseStructure', 'STRUCTURE'))
DECL = f'''	<AttributeModifier id="AttributeModifier_CNV_PhaseUnit" Category="NONE" Duration="{UNIT_TIME}"
		StackingLimit="1" ObjectStatusToSet="{PHASE_STATUS}" Shader="ShaderOverride_ObjectsChronoRift">
		<Modifier Type="SPEED" Value="0%"/>
	</AttributeModifier>
	<AttributeModifier id="AttributeModifier_CNV_PhaseStructure" Category="NONE" Duration="{STRUCTURE_TIME}"
		StackingLimit="1" ObjectStatusToSet="{PHASE_STATUS}" Shader="ShaderOverride_ObjectsChronoRift">
	</AttributeModifier>
	<AttributeModifier id="AttributeModifier_CNV_PhaseTag" Category="NONE" Duration="0.1s">
	</AttributeModifier>
	<AttributeModifier id="AttributeModifier_CNV_PhaseCooldown" Category="NONE" Duration="{RELOAD}"
		StackingLimit="1" ObjectStatusToSet="{COOLDOWN_BIT}">
	</AttributeModifier>
	<WeaponTemplate id="CNV_PhaseWarhead" RadiusDamageAffects="ENEMIES"
		RequiredAntiMask="ANTI_GROUND ANTI_STRUCTURE ANTI_WATER" Flags="NOT_ATTRACTED_BY_MAGNETS">
		<Nuggets>
			<DamageNugget Damage="1.0" DamageType="CANNON" DamageFXType="ALLIED_CANNON" DeathType="EXPLODED"/>
{PHASE}		</Nuggets>
	</WeaponTemplate>
'''
# the 1 damage: with the phase modifiers only, the tank turned to the Apocalypse and never fired (bench 2026-10-20;
# auto-targeting seems to skip a weapon that cannot hurt its target)


def sub1(x, old, new):
    assert x.count(old) == 1, (old[:60], x.count(old))
    return x.replace(old, new, 1)


def shell_weapon():
    """The Guardian's cannon under our id: range 350, our warhead, the owner cooldown."""
    w = open(os.path.join(c2.SDK, 'SageXML', 'GlobalData', 'Weapon.xml'), encoding='utf-8').read()
    m = re.search(r'\t*<WeaponTemplate\s+id="AlliedAntiVehicleVehicleTech1Cannon".*?</WeaponTemplate>\n', w, re.S)
    x = m.group(0).replace('id="AlliedAntiVehicleVehicleTech1Cannon"', 'id="CNV_PhaseShell"')
    x = sub1(x, 'AttackRange="150.0"', f'AttackRange="{RANGE}.0"')
    x = sub1(x, 'CanFireWhileMoving="true"', f'CanFireWhileMoving="true"\n\t\tForbiddenFiringObjectStatus="{COOLDOWN_BIT}"')
    x = x.replace('WarheadTemplate="AlliedAntiVehicleVehicleTech1Warhead"', 'WarheadTemplate="CNV_PhaseWarhead"')
    cooldown = nugget('AttributeModifier_CNV_PhaseTag', 'VEHICLE INFANTRY STRUCTURE',
                      owner='AttributeModifier_CNV_PhaseCooldown')
    return sub1(x, '\t\t\t<InformTargetNugget />', cooldown + '\t\t\t<InformTargetNugget />')


def unit_xml():
    x = open(os.path.join(SAGE, 'AlliedAntiVehicleVehicleTech1.xml'), encoding='utf-8').read()
    x = sub1(x, 'id="AlliedAntiVehicleVehicleTech1"', f'id="{UNIT}"')
    x = sub1(x, 'EditorName="AlliedAntiVehicleVehicleTech1"', f'EditorName="{UNIT}"')
    x = sub1(x, 'Template="AlliedAntiVehicleVehicleTech1Cannon"', 'Template="CNV_PhaseShell"')
    # the Guardian sees 200: at 300 the tank turned to the Apocalypse and never fired (bench). The Athena sees 500
    x = sub1(x, 'VisionRange="200"', 'VisionRange="400"')
    x = sub1(x, '</AssetDeclaration>', DECL + shell_weapon() + '</AssetDeclaration>')
    with open(os.path.join(c26.DATA, UNIT + '.xml'), 'w', encoding='utf-8', newline='\r\n') as f:
        f.write(x.replace('\r\n', '\n'))


A = c28.A
SCENE = [(UNIT, (A[0], A[1] - 100), True),
         ('AlliedAntiVehicleVehicleTech1', (A[0] - 60, A[1] + 60), True),
         ('AlliedAntiVehicleVehicleTech1', (A[0] + 60, A[1] + 60), True),
         ('SovietAntiVehicleVehicleTech3', (A[0], A[1] + 200), False)]

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
    print('CNV35: removed', len(gone), 'units;', len(SCENE), 'placed', '(no phase)' if NO_PHASE else '')


c6.edit = generate

if __name__ == '__main__':
    if c23.game_running():
        c2.OUT = c4.OUT = os.path.join(os.path.dirname(os.path.dirname(HERE)), 'work', 'staging', NAME)
        print('RA3 is running -> staging at', c4.OUT)
    c4.main()
