"""苏军「磁钩坦克」机制验证 (CampNew34): the Apocalypse's harpoon on a slower, cheaper tank, no new model yet.

Design (user, 2026-10-19): a control front-liner -- the magnetic harpoon pulls one enemy vehicle in front of it and the
pulled vehicle cannot fire while held; Hammers / Terror Drones finish it. Slow, tough, little damage of its own (the
opposite of 游隼: 游隼 feeds on control, this one makes it).

Stand-in: a copy of the Apocalypse (its model, its harpoon wiring: GrapplingHookUpdate, the retail harpoon toggle
command and button) with: our hook weapon (the retail harpoon + an AttributeModifierNugget locking the target:
NO_ATTACK SCRAMBLED, the retail weapon scrambler's status; RATE_OF_FIRE 0 % as on the Cryocopter's freeze did not stop
a held Guardian firing), no crush kill at the end of the pull (the Apocalypse's single
fire weapon kills the target outright; ours only locks), a weak grind that keeps the lock on while held, the Hammer's
cannon, 900 health, speed 60, 1100, no tech structure needed.

Scene: hook tank A with an enemy Guardian 280 north (out of the Guardian's 150 range: the hook has 300) and two
Hammers to finish the catch; hook tank B with an enemy Apocalypse 120 north. Bench (2026-10-20): A pulls the Guardian
in, the Hammers kill it; B left to fight the Apocalypse dies in ~8 s, B hooking it keeps its health from the hook on
-- with the lock or without (CNV_NO_LOCK=1): a held target does not fire anyway. The lock stays for its look (the
Tesla shader marks the held unit) and 1.5 s after a release.

  python -I -X utf8 experimental/campaign/make_campnew34.py            -> Documents\\Red Alert 3\\Mods\\CampNew34
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
NAME = 'CampNew34'
c4.NAME = c2.NAME = NAME
c2.SRC_DIR = os.path.join(c2.SDK, 'Mods', NAME, 'data')
c2.BUILT = os.path.join(c2.SDK, 'BuiltMods', 'mods', NAME.lower(), 'data')
c2.OUT = c4.OUT = os.path.join(os.path.expanduser('~'), 'Documents', 'Red Alert 3', 'Mods', NAME)
c7.MAP_MOD = NAME + 'Map'

SAGE = os.path.join(c2.SDK, 'SageXML', 'Soviet', 'Units')
UNIT = 'CNV_MagHookProbe'
LOCK_TIME = os.environ.get('CNV_LOCK', '1.5s')     # refreshed by the grind every 0.5 s while held
c7.EXTRA_TEMPLATES[UNIT] = {'file': f'DATA:CNVUnits/Data/{UNIT}.xml', 'EditorSorting': 'UNIT'}
c7.EXTRA_OWN += [b'AttributeModifier:AttributeModifier_CNV_MagLock', b'WeaponTemplate:CNV_MagHook',
                 b'WeaponTemplate:CNV_MagGrind', b'AttributeModifier:AttributeModifier_CNV_HookHold',
                 b'AttributeModifier:AttributeModifier_CNV_HookCooldown',
                 b'WeaponTemplate:CNV_MagCoil']

# v2 (user, 2026-10-20: the Hammer's gun and armour made it a better Hammer): no anti-tank gun -- a short Tesla coil,
# TESLA damage (infantry armour takes 1000 %, tank armour 100 %) and DeathType ELECTROCUTED (an Empire unit it kills
# hands on no 复仇, make_campnew31.DEATH); 1000 (the Hammer's price), 700 health, speed 60. It cannot kill a caught
# tank alone. A hold lasts 6 s: the hook gives its owner HOLD_BIT for 6 s and the grapple needs it; the hook reloads
# in 10 s (4 s after a release).
# C&C3 bits no RA3 XML uses. CARRYING_FLAG for the hold let go after ~1 s (bench; the engine's capture-the-flag
# logic clears it?); HAS_TIBERIUM_GROWTH_MOD held as 鸣神's link bit (also used there: not both units in one mod yet)
HOLD_BIT, HOLD_TIME, HOOK_RELOAD = os.environ.get('CNV_HOLD_BIT', 'HAS_TIBERIUM_GROWTH_MOD'), '6s', '10s'
COOLDOWN_BIT = 'DOES_CONTAIN_TIBERIUM'
COIL_DAMAGE = 12          # x 2 shots per 2.2 s: ~11 per s on a tank, ~110 on infantry
LOCK = f'''			<AttributeModifierNugget Radius="10" PartitionFilterTestType="SPHERE"
				AttributeModifierName="AttributeModifier_CNV_MagLock">
				<SpecialObjectFilter Rule="ANY" Relationship="ENEMIES NEUTRAL" Include="VEHICLE"/>
			</AttributeModifierNugget>
'''
# the hold timer sits on the target: the hook marks it with HOLD_BIT for 6 s (the grind does not renew it) and the
# grapple keeps only targets with the bit (KeepAliveObjectFilter). On the hooker instead (AttributeModifierOwnerName,
# grapple RequiredStatus) the hook never held at all (bench: no pull, the tank died to the Apocalypse in 7 s)
HOLD = LOCK + LOCK.replace('AttributeModifier_CNV_MagLock', 'AttributeModifier_CNV_HookHold')
DECL = f'''	<AttributeModifier id="AttributeModifier_CNV_MagLock" Category="NONE" Duration="{LOCK_TIME}"
		StartFX="FX_None" ObjectStatusToSet="NO_ATTACK SCRAMBLED" Shader="ShaderOverride_ObjectsTeslaSingularity">
	</AttributeModifier>
	<AttributeModifier id="AttributeModifier_CNV_HookHold" Category="NONE" Duration="{HOLD_TIME}"
		StackingLimit="1" ObjectStatusToSet="{HOLD_BIT}">
	</AttributeModifier>
	<AttributeModifier id="AttributeModifier_CNV_HookCooldown" Category="NONE" Duration="{HOOK_RELOAD}"
		StackingLimit="1" ObjectStatusToSet="{COOLDOWN_BIT}">
	</AttributeModifier>
	<WeaponTemplate id="CNV_MagGrind" AttackRange="1.0" WeaponSpeed="999999.0" ClipSize="1"
		Flags="NOT_ATTRACTED_BY_MAGNETS" RequiredAntiMask="ANTI_GROUND ANTI_WATER ANTI_STRUCTURE"
		AcceptableAimDelta="1d" CanFireWhileMoving="false" ReAcquireDetailType="PER_ATTACK">
		<FiringDuration MinSeconds="0.5s" MaxSeconds="0.5s"/>
		<ClipReloadTime MinSeconds="0.5s" MaxSeconds="0.5s"/>
		<Nuggets>
			<DamageNugget Damage="5.0" DamageType="EXPLOSIVE" DeathType="NORMAL">
				<SpecialObjectFilter Rule="ALL" Exclude="ORE_NODE"/>
			</DamageNugget>
{LOCK}		</Nuggets>
	</WeaponTemplate>
'''


def sub1(x, old, new):
    assert x.count(old) == 1, (old[:60], x.count(old))
    return x.replace(old, new, 1)


def hook_weapon():
    """The retail harpoon under our id, its nuggets + the lock (the first hit locks before the pull starts)."""
    w = open(os.path.join(c2.SDK, 'SageXML', 'GlobalData', 'Weapon.xml'), encoding='utf-8').read()
    m = re.search(r'\t<WeaponTemplate\s+id="SovietAntiVehicleVehicleTech3Harpoon".*?</WeaponTemplate>\n', w, re.S)
    x = m.group(0).replace('id="SovietAntiVehicleVehicleTech3Harpoon"', 'id="CNV_MagHook"')
    # cooldown: the hook gives its owner COOLDOWN_BIT for HOOK_RELOAD and does not fire under it. A 10 s clip reload
    # instead also ran from the start (bench: no hook in the first 10 s, the tank died first)
    x = sub1(x, 'RequiredFiringObjectStatus="GENERIC_TOGGLE_STATE"',
             f'RequiredFiringObjectStatus="GENERIC_TOGGLE_STATE"\n\t\tForbiddenFiringObjectStatus="{COOLDOWN_BIT}"')
    cooldown = LOCK.replace('AttributeModifierName="AttributeModifier_CNV_MagLock">',
                            'AttributeModifierName="AttributeModifier_CNV_MagLock"\n'
                            '\t\t\t\tAttributeModifierOwnerName="AttributeModifier_CNV_HookCooldown">')
    return sub1(x, '\t\t</Nuggets>', HOLD.replace(LOCK, cooldown, 1) + '\t\t</Nuggets>')


def coil_weapon():
    """The Tesla tank's gun (its own fire FX, two shots a clip) at 125 range and COIL_DAMAGE."""
    w = open(os.path.join(c2.SDK, 'SageXML', 'GlobalData', 'Weapon.xml'), encoding='utf-8').read()
    m = re.search(r'\t<WeaponTemplate\s+id="SovietAntiVehicleVehicleTech2TeslaGun".*?</WeaponTemplate>\n', w, re.S)
    x = m.group(0).replace('id="SovietAntiVehicleVehicleTech2TeslaGun"', 'id="CNV_MagCoil"')
    x = sub1(x, 'AttackRange="150.0"', 'AttackRange="125.0"')
    return sub1(x, 'Damage="100.0"', f'Damage="{COIL_DAMAGE}.0"')


def unit_xml():
    x = open(os.path.join(SAGE, 'SovietAntiVehicleVehicleTech3.xml'), encoding='utf-8').read()
    x = sub1(x, 'id="SovietAntiVehicleVehicleTech3"', f'id="{UNIT}"')
    x = sub1(x, 'EditorName="SovietAntiVehicleVehicleTech3"', f'EditorName="{UNIT}"')
    x = re.sub(r'\s*<GameDependency>\s*<RequiredObject>SovietTechStructure</RequiredObject>\s*</GameDependency>', '', x)
    x = sub1(x, 'Amount="2000"', 'Amount="1000"')
    x = sub1(x, 'MaxHealth="3000"', 'MaxHealth="700"')
    # the Hammer's armour, no self-repair: a T1~T2 tank (with the Apocalypse's, a Guardian hardly scratched it)
    x = sub1(x, 'Armor="SovietAntiVehicleVehicleTech3Armor"', 'Armor="SovietAntiVehicleVehicleTech1Armor"')
    x, n = re.subn(r'\s*<AutoHealBehavior\s+id="Upgrade_PassiveHeal".*?</AutoHealBehavior>', '', x, flags=re.S)
    assert n == 1
    x, n = re.subn(r'(<LocomotorSet\s+Locomotor="SovietAntiVehicleVehicleTech3Locomotor"\s+Condition="NORMAL"\s+'
                   r'Speed=")50\.0(")', r'\g<1>60.0\2', x)
    assert n == 1
    x = sub1(x, 'Template="SovietAntiVehicleVehicleTech3Harpoon"', 'Template="CNV_MagHook"')
    x = sub1(x, 'Template="SovietAntiVehicleVehicleTech3Cannon"\n', 'Template="CNV_MagCoil"\n')
    x = sub1(x, 'Template="SovietAntiVehicleVehicleTech3Cannon_Veteran"', 'Template="CNV_MagCoil"')
    x = sub1(x, '<KeepAliveObjectFilter\n\t\t\t\t\tRule="ANY"\n',
             f'<KeepAliveObjectFilter\n\t\t\t\t\tRule="ANY"\n\t\t\t\t\tStatusBitFlags="{HOLD_BIT}"\n')
    x = sub1(x, 'SingleFireWeapon="SovietHarpoonCrushWeapon"', 'SingleFireWeapon="CNV_MagGrind"')
    x = sub1(x, 'ContinuousFireWeapon="SovietHarpoonGrindWeapon"', 'ContinuousFireWeapon="CNV_MagGrind"')
    # the Apocalypse crushes vehicles (CrusherLevel 30 > their 20): a pulled target died on arrival (first bench
    # runs, both Guardians). The Hammer's levels: it holds a pulled vehicle instead
    x = sub1(x, 'CrusherLevel="30"\n\t\t\tCrushableLevel="31"', 'CrusherLevel="20"\n\t\t\tCrushableLevel="20"')
    x = sub1(x, '</AssetDeclaration>', DECL + hook_weapon() + coil_weapon() + '</AssetDeclaration>')
    assert 'SovietHarpoonCrushWeapon' not in x
    with open(os.path.join(c26.DATA, UNIT + '.xml'), 'w', encoding='utf-8', newline='\r\n') as f:
        f.write(x.replace('\r\n', '\n'))


A = c28.A
SCENE = [(UNIT, (A[0] - 120, A[1] + 60), True), (UNIT, (A[0] + 160, A[1] + 60), True),
         ('AlliedAntiVehicleVehicleTech1', (A[0] - 40, A[1] + 330), False),      # off the beach
         ('SovietAntiVehicleVehicleTech1', (A[0] - 200, A[1] - 20), True),    # two Hammers to finish A's catch
         ('SovietAntiVehicleVehicleTech1', (A[0] - 40, A[1] - 20), True),
         # the control: an enemy Apocalypse (a Guardian hardly marked B's health bar, so firing or not was unreadable)
         ('SovietAntiVehicleVehicleTech3', (A[0] + 160, A[1] + 180), False)]
# CNV_SCENE=hold: B and the enemy Apocalypse only (does a hold end after 6 s, and come back after the reload?)
if os.environ.get('CNV_SCENE') == 'hold':       # a Guardian 200 out: an Apocalypse killed B after the first release
    SCENE = [SCENE[1], ('AlliedAntiVehicleVehicleTech1', (A[0] + 160, A[1] + 260), False)]
# CNV_SCENE=coil: the coil alone -- A against four Imperial Warriors 100 north, B against a Guardian 100 north
if os.environ.get('CNV_SCENE') == 'coil':
    SCENE = [(UNIT, (A[0] - 120, A[1] + 60), True), (UNIT, (A[0] + 160, A[1] + 60), True),
             ('AlliedAntiVehicleVehicleTech1', (A[0] + 160, A[1] + 160), False)] + \
        [('JapanAntiInfantryInfantry', (A[0] - 180 + 40 * k, A[1] + 160), False) for k in range(4)]

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
    print('CNV34: removed', len(gone), 'units;', len(SCENE), 'placed')


c6.edit = generate

if __name__ == '__main__':
    if c23.game_running():
        c2.OUT = c4.OUT = os.path.join(os.path.dirname(os.path.dirname(HERE)), 'work', 'staging', NAME)
        print('RA3 is running -> staging at', c4.OUT)
    c4.main()
