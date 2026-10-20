"""帝国「鸣神」突击机甲 rough unit (CampNew32): CampNew31's mechanics on our own two-form model, at the design numbers.

The Guardian's logic and TruckDraw (make_campnew24.unit_xml) with the 疾行 model (CNNaruF); the 信号 model (CNNaruS,
cnv_narukami.py signal) under the USER_2 model condition (USER_1 is the Guardian's painter laser), set by the deploy
state. On it, from CampNew31: the transform (own power / command / button, ToggleStatusSpecialAbilityUpdate: 疾行 ->
信号 = TRANSFORMATION_TOGGLE_STATE, IMMOBILE, USER_2; every toggle grants the 2 s dash), the signal aura (only while
deployed, Empire units only) and the 复仇 death pulse. Gun: the Mecha Tengu's (anti-infantry / light), off while
deployed. Side Japan, 400 health, speed 130, 900. Design numbers: zone 250, 复仇 radius 200, +20 % damage +15 %
speed per stack, 3 stacks, 20 s (CampNew31 probed 200 / 150).

Scene: two 鸣神, four Empire warriors (CampNew31's copies with the death module) and a retail Tsunami tank in front
of three Hammers 460 north (CampNew30's first group).

  python -I -X utf8 experimental/campaign/make_campnew32.py            -> Documents\\Red Alert 3\\Mods\\CampNew32
"""
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(os.path.dirname(HERE), 'units'))
import make_campnew31 as c31                    # noqa: E402

c29, c28, c23, c26 = c31.c29, c31.c28, c31.c23, c31.c26
c24 = c29.c24
c7, c6, c4, c2 = c23.c7, c23.c6, c23.c4, c23.c2
newmap, to_w3x = c23.newmap, c23.to_w3x
NAME = 'CampNew32'
c4.NAME = c2.NAME = NAME
c2.SRC_DIR = os.path.join(c2.SDK, 'Mods', NAME, 'data')
c2.BUILT = os.path.join(c2.SDK, 'BuiltMods', 'mods', NAME.lower(), 'data')
c2.OUT = c4.OUT = os.path.join(os.path.expanduser('~'), 'Documents', 'Red Alert 3', 'Mods', NAME)
c7.MAP_MOD = NAME + 'Map'

UNIT, FAST, SIGNAL = 'CNV_Narukami', 'CNNaruF', 'CNNaruS'
WORK = os.path.join(os.path.dirname(os.path.dirname(HERE)), 'work', 'units')
SRC = {FAST: os.path.join(WORK, 'narukami_fast'), SIGNAL: os.path.join(WORK, 'narukami_signal')}
# cnv_narukami.py TURRET_AT / PITCH_AT per form, TIP_AT (v2: the turret is the head in the signal form)
TURRET = {FAST: ((4.0, 0.0, 10.4), (1.0, 0.0, 1.2)), SIGNAL: ((0.0, 0.0, 6.0 + 18.6 * 1.3), (0.52, 0.0, 2.08))}
TIP = (8.0, 0.0, 0.0)
SCALE = c23.SCALE * 0.8


def pivots(model):
    t, p = TURRET[model]
    return [('BODY', None, (0, 0, 0)),
            ('Bone_Turret', None, t), ('Bone_Turret_Pitch', 'Bone_Turret', p),
            ('BONE_GUN_MUZZLE', 'Bone_Turret_Pitch', TIP), ('FXBone_Muzzle', 'Bone_Turret_Pitch', TIP),
            ('FX_Laser', 'Bone_Turret_Pitch', TIP), ('FX_Damage01', None, (-6, 0, 8)),
            ('FXTracksL', None, (-12, 8.8, 0)), ('FXTracksR', None, (-12, -8.8, 0))] + \
        [(f'Bone_{kind}_{fr}_{side}', None, (8 if fr == 'Front' else -8, 8.8 if side == 'Left' else -8.8, 1.6))
         for kind in ('Tread', 'Tracks') for fr in ('Front', 'Rear') for side in ('Left', 'Right')]
AURA_RANGE, PULSE_RADIUS = 250, 200
# median diffuse luminance, no retail Allied grading (it turned the red drums grey): Empire armour is grey-white with
# gunmetal parts in the retail line-up; 120 and 85 read paper-white next to it
LEVEL = 60

# the probe units stay out (their XML declares the same transform power); 鸣神 joins the Empire list
for t in (c31.SIGNAL, c31.NARUKAMI):
    c7.EXTRA_TEMPLATES.pop(t, None)
c7.EXTRA_TEMPLATES[UNIT] = {'file': f'DATA:CNVUnits/Data/{UNIT}.xml', 'EditorSorting': 'UNIT'}
# producible: button / portrait on the Empire's orange plates (button_icon.py button_japan / portrait_japan), built
# from CNV_JWarFactory (a copy of the Empire war factory)
BUTTON, PORTRAIT, JFACTORY = f'Button_{UNIT}', f'Portrait_{UNIT}', 'CNV_JWarFactory'
c7.EXTRA_TEMPLATES[JFACTORY] = {'file': f'DATA:CNVUnits/Data/{JFACTORY}.xml', 'EditorSorting': 'STRUCTURE'}
c7.EXTRA_OWN += [b'LogicCommand:Command_Construct' + UNIT.encode(), b'LogicCommandSet:' + JFACTORY.encode()] + \
    [p + n.encode() for n in (BUTTON, PORTRAIT) for p in (b'PackedTextureImage:', b'Texture:')]
EMPIRE = c31.EMPIRE.replace(f'<IncludeThing>{c31.NARUKAMI}</IncludeThing>', f'<IncludeThing>{UNIT}</IncludeThing>')
# 复仇 tiers you can see (user, 2026-10-19: the zone's reach and a unit's stacks were not readable; take the Empire
# protocols' look). One modifier per stack instead of StackingLimit 3: tier k sets a free status bit (the next pulse's
# filter) and a free model condition, under which every Empire unit (override_units) draws Emperor's Rage's ground
# glow (FXEmperorsRage, the protocol's own decal) bigger per tier. A pulse applies tier 3 to units holding tier 2,
# tier 2 to units holding tier 1, then tier 1 -- in that order, so one death adds one tier, and refreshes the ones
# below. One death fires one pulse (the dying unit's module), however many 鸣神 zones cover it: two 鸣神 never
# double a death. No shader any more (the Iron Curtain red was for the bench and read as an Iron Curtain).
# C&C3 status bits no RA3 XML uses, one per tier: tier k needs tier k-1's bit and skips units that hold its own (a
# tier applied again to a unit holding it dropped that unit's glow on the bench). The pulses fire highest tier first
# with delays (PULSE_DELAY), so each sees only earlier deaths' bits: the death modules' run order was not the listed
# one (bench: one death climbed two tiers in either listing)
TIER_BITS = ['HAS_TIBERIUM_UPGRADE', 'STEAL_NEXT_UNIT_TRAPPED', 'IS_HIDEOUT']
PULSE_DELAY = ['0.6s', '0.3s', '0s']
# model conditions no retail XML uses (SPECIAL_DAMAGED for tier 3 never showed: the engine runs that one itself)
TIER_CONDS = ['SPECIAL_WEAPON_TWO', 'SPECIAL_WEAPON_THREE', 'SPECIAL_WEAPON_FOUR']
TIER_DECAL = [40, 60, 80]          # glow size per tier (30 / 46 / 62: tier 1 hid under a vehicle at game zoom)


def vengeance_decl():
    mods = ''.join(
        f'\t<AttributeModifier id="AttributeModifier_CNV_Vengeance{k + 1}" Category="NONE" Duration="20s" '
        'StackingLimit="1"\n\t\t' + (f'ObjectStatusToSet="{TIER_BITS[k]}" ' if TIER_BITS[k] else '') +
        f'ModelConditionsSet="{TIER_CONDS[k]}">\n'
        '\t\t<Modifier Type="DAMAGE_MULT" Value="120%"/>\n\t\t<Modifier Type="SPEED" Value="115%"/>\n'
        '\t</AttributeModifier>\n' for k in range(3))
    # one weapon per tier (PULSES), fired by one death module each (DEATH), highest tier first
    weapons = ''
    for k in (2, 1, 0):
        need = (f' StatusBitFlags="{TIER_BITS[k - 1]}"' if k else '') + f' StatusBitFlagsExclude="{TIER_BITS[k]}"'
        weapons += (f'\t<WeaponTemplate id="{PULSES[k]}" Flags="NOT_ATTRACTED_BY_MAGNETS" AttackRange="999999.0"\n'
                    '\t\tRequiredAntiMask="ANTI_GROUND ANTI_STRUCTURE ANTI_WATER" RadiusDamageAffects="ALLIES">\n'
                    '\t\t<Nuggets>\n'
                    f'\t\t\t<AttributeModifierNugget Radius="{PULSE_RADIUS}" PartitionFilterTestType="SPHERE"\n'
                    f'\t\t\t\tAttributeModifierName="AttributeModifier_CNV_Vengeance{k + 1}">\n'
                    f'\t\t\t\t<SpecialObjectFilter Rule="NONE"{need}>{EMPIRE}\n\t\t\t\t</SpecialObjectFilter>\n'
                    '\t\t\t</AttributeModifierNugget>\n\t\t</Nuggets>\n\t</WeaponTemplate>\n')
    link = c31.DECL[:c31.DECL.index('\t<AttributeModifier id="AttributeModifier_CNV_Vengeance"')]
    return link + mods + weapons


PULSES = ['CNV_VengeancePulse', 'CNV_VengeancePulse2', 'CNV_VengeancePulse3']
DEATH = ''.join(c31.DEATH.replace('ModuleTag_CNV_Vengeance"', f'ModuleTag_CNV_Vengeance{k + 1}"')
                .replace('DeathWeapon="CNV_VengeancePulse"', f'DeathWeapon="{PULSES[k]}" DelayTime="{PULSE_DELAY[k]}"')
                for k in (2, 1, 0))
assert DEATH.count('<FireWeaponWhenDead') == 3 and 'CNV_VengeancePulse3' in DEATH


def tier_draw():
    """The 复仇 ground glow, a second draw module like the Allied engineer's heal-radius decal (an invisible model
    carrying an additive decal); the highest tier's state first."""
    out = ('\t\t\t<ScriptedModelDraw id="ModuleTag_CNV_VengeanceGlow" OkToChangeModelColor="true">\n'
           '\t\t\t\t<ModelConditionState ParseCondStateType="PARSE_DEFAULT">\n\t\t\t\t\t<Model Name="" />\n'
           '\t\t\t\t</ModelConditionState>\n')
    # every combination of the three flags, drawn at its highest tier: the engine picks the state matching the most
    # flags and RA3 has no ConditionsNo, so with one state per flag all three tied once a unit held them all (bench:
    # the third tier did not show); tiers also expire in any order, so all seven subsets are listed
    for mask in sorted(range(1, 8), key=lambda m: -bin(m).count('1')):
        k = mask.bit_length() - 1
        conds = ' '.join(TIER_CONDS[j] for j in range(3) if mask >> j & 1)
        out += (f'\t\t\t\t<ModelConditionState ParseCondStateType="PARSE_NORMAL" ConditionsYes="{conds}">\n'
                '\t\t\t\t\t<Model Name="FXInvisBone" />\n'
                f'\t\t\t\t\t<ShadowInfo Type="ADDITIVE_DECAL" SizeX="{TIER_DECAL[k]}" SizeY="{TIER_DECAL[k]}" '
                'Texture="FXEmperorsRage" OverrideLODVisibility="true" MaxHeight="200" />\n'
                '\t\t\t\t</ModelConditionState>\n')
    return out + '\t\t\t</ScriptedModelDraw>\n'


def zone_draw():
    """The signal zone's edge while deployed (USER_2): the engineer's heal-radius ring (Decal_Heal_CO, house
    colour, size = 2 x radius), shown to every player -- the enemy should see where not to kill."""
    return ('\t\t\t<ScriptedModelDraw id="ModuleTag_CNV_SignalZoneRing" OkToChangeModelColor="true">\n'
            '\t\t\t\t<ModelConditionState ParseCondStateType="PARSE_DEFAULT">\n\t\t\t\t\t<Model Name="" />\n'
            '\t\t\t\t</ModelConditionState>\n'
            '\t\t\t\t<ModelConditionState ParseCondStateType="PARSE_NORMAL" ConditionsYes="USER_2">\n'
            '\t\t\t\t\t<Model Name="FXInvisBone" />\n'
            f'\t\t\t\t\t<ShadowInfo Type="ADDITIVE_DECAL" SizeX="{2 * AURA_RANGE}" SizeY="{2 * AURA_RANGE}" '
            'OverrideLODVisibility="true" MaxHeight="200" UseHouseColor="true" Texture="Decal_Heal_CO" />\n'
            '\t\t\t\t</ModelConditionState>\n\t\t\t</ScriptedModelDraw>\n')


def add_draw(x, start, draw):
    """`draw` before the </Draws> of the GameObject whose tag begins at `start`."""
    end = x.index('</Draws>', start)
    return x[:end] + draw.lstrip() + '\t\t' + x[end:]


DECL = vengeance_decl()
AURA = c31.AURA.replace(c31.EMPIRE, EMPIRE).replace(f'Range="{c31.AURA_RANGE}"', f'Range="{AURA_RANGE}"').replace(
    'InitiallyActive="true"', 'InitiallyActive="true" RequiredObjectStatusFlags="TRANSFORMATION_TOGGLE_STATE"')
assert f'Radius="{PULSE_RADIUS}"' in DECL and f'Range="{AURA_RANGE}"' in AURA and UNIT in AURA
assert 'RequiredObjectStatusFlags' in AURA       # the zone only while deployed (missing in the first CampNew32 run)
# the deploy's model condition comes from the deploy modifier (ModelConditionsSet, as retail modifiers do): the
# ToggleState's ModelConditions did not swap the TruckDraw's model (CampNew32 bench, second run)
NARUKAMI_DECL = c31.NARUKAMI_DECL.replace('ObjectStatusToSet="IMMOBILE">', 'ObjectStatusToSet="IMMOBILE" '
                                          'ModelConditionsSet="USER_2">')
assert 'ModelConditionsSet="USER_2"' in NARUKAMI_DECL
# own button states: the Tengu's showed its own tooltip (机甲模式 / 天狗机甲模式, user in game); the Tengu's icons stay
NARUKAMI_UI = '''	<ButtonSingleStateData id="ButtonState_CNV_NarukamiDeploy">
		<State Image="JUA_Tengu_MechaMode" Title="NAME:CNV_NarukamiDeploy" Description="DESC:CNV_NarukamiDeploy" />
	</ButtonSingleStateData>
	<ButtonSingleStateData id="ButtonState_CNV_NarukamiRetract">
		<State Image="JUA_Tengu_JetMode" Title="NAME:CNV_NarukamiRetract" Description="DESC:CNV_NarukamiRetract" />
	</ButtonSingleStateData>
''' + c31.NARUKAMI_UI.replace('ButtonStateJAIV_TransformOff', 'ButtonState_CNV_NarukamiRetract').replace(
    'ButtonStateJAIV_Transform', 'ButtonState_CNV_NarukamiDeploy')
assert 'JAIV' not in NARUKAMI_UI
c7.EXTRA_OWN += [b'ButtonSingleStateData:ButtonState_CNV_Narukami']
c4.c3.STRINGS.update({
    'NAME:CNV_NarukamiDeploy': '信号形态',
    # 同一瞬间阵亡只算一层 is a property of the build (pulses checked in a fixed order): kept as lore (user, 2026-10-19)
    'DESC:CNV_NarukamiDeploy': '原地展开，升起雷鼓光环。信号区内阵亡的帝国单位，会把复仇意志传给周围的帝国单位'
                               '（伤害、速度提升，最多三层，脚下光纹越大层数越多）。雷鼓每一刻只能传出一道信号：'
                               '同一刻牺牲的战友，意志汇成一层。展开时不能移动、不能开火。',
    'NAME:CNV_NarukamiRetract': '疾行形态',
    'DESC:CNV_NarukamiRetract': '收起光环，冲刺约 2 秒后恢复高速机动。',
    'Name:' + UNIT: '鸣神突击机甲',
    'Type:' + UNIT: '信号突击机甲',
    'Desc:' + UNIT: '疾行形态高速骚扰；展开成信号形态时，信号区内阵亡的帝国单位把复仇意志传给周围的帝国单位，'
                    '战友一个接一个倒下，复仇一层层叠起；同一刻牺牲的战友只汇成一层。收回形态时短暂冲刺。',
})

TOGGLE = '''			<SpecialPower id="ModuleTag_CNV_NarukamiTransform" SpecialPowerTemplate="SpecialPower_CNV_NarukamiTransform"
				UpdateModuleStartsAttack="true"/>
			<ToggleStatusSpecialAbilityUpdate id="ModuleTag_CNV_NarukamiTransformUpdate" Options="RECONSTITUTE_STORED_COMMAND"
				SpecialPowerTemplate="SpecialPower_CNV_NarukamiTransform"
				TriggerAttributeModifier="AttributeModifier_CNV_Dash" AttributeModifierDuration="2s">
				<ToggleState LocomotorSet="NORMAL">
					<SkirmishAiInfo ToggleHint="TOGGLE_DEFAULT"/>
				</ToggleState>
				<ToggleState ObjectStatus="TRANSFORMATION_TOGGLE_STATE" LocomotorSet="NORMAL" ModelConditions="USER_2"
					AttributeModifier="AttributeModifier_CNV_SignalDeploy">
					<SkirmishAiInfo ToggleHint="TOGGLE_TRANSFORM"/>
				</ToggleState>
			</ToggleStatusSpecialAbilityUpdate>
'''


def signal_states():
    """The 信号 model under USER_2 (alone and with the damage states, so a damaged deployed unit keeps its mast)."""
    out = ''
    for cond in ('USER_2', 'USER_2 DAMAGED', 'USER_2 REALLYDAMAGED'):
        out += (f'\t\t\t\t<ModelConditionState ParseCondStateType="PARSE_NORMAL" ConditionsYes="{cond}">\n'
                f'\t\t\t\t\t<Model Name="{SIGNAL.upper()}" />\n'
                '\t\t\t\t\t<Turret TurretNameKey="Bone_Turret" TurretPitch="Bone_turret_pitch" TurretID="1" />\n'
                '\t\t\t\t</ModelConditionState>\n')
    return out


def unit_xml():
    c24.unit_xml(UNIT, FAST)                       # the Guardian with the 疾行 model
    path = os.path.join(c26.DATA, UNIT + '.xml')
    x = open(path, encoding='utf-8').read()
    sub1 = c31.sub1
    x = sub1(x, f'<Include type="all" source="ART:{FAST}_IDLE.w3x" />',
             f'<Include type="all" source="ART:{FAST}_IDLE.w3x" />\n\t\t<Include type="all" source="ART:{SIGNAL}.w3x" />')
    x = sub1(x, 'Side="Allies"', 'Side="Japan"')
    x = sub1(x, 'CommandSet="AlliedAntiVehicleVehicleTech1CommandSet"', 'CommandSet="CNV_NarukamiCommandSet"')
    x = sub1(x, 'Description="Desc:AlliedAntiVehicleVehicleTech1"', f'Description="Desc:{UNIT}"')
    x = sub1(x, 'TypeDescription="Type:AlliedAntiVehicleVehicleTech1"', f'TypeDescription="Type:{UNIT}"')
    x = c31.re.sub(r'(<BuildCost Account="=\$ACCOUNT_ORE" Amount=")\d+(")', r'\g<1>900\2', x)
    x = c31.re.sub(r'\s*<GameDependency>\s*<NeededUpgrade>Upgrade_AlliedTech2</NeededUpgrade>\s*</GameDependency>', '', x)
    x = sub1(x, 'MaxHealth="480"', 'MaxHealth="400"')
    x, n = c31.re.subn(r'(<LocomotorSet\b[^>]*Condition="NORMAL"[^>]*Speed=")80\.0(")', r'\g<1>130.0\2', x)
    assert n == 1
    x, n = c31.re.subn(r'Template="AlliedAntiVehicleVehicleTech1Cannon"(\s+)ForbiddenObjectStatus="GENERIC_TOGGLE_STATE"',
                       r'Template="JapanAntiInfantryVehicleGun"\1'
                       r'ForbiddenObjectStatus="GENERIC_TOGGLE_STATE TRANSFORMATION_TOGGLE_STATE"', x, count=1)
    assert n == 1
    x = sub1(x, '<!-- Damage States -->', signal_states().lstrip() + '\t\t\t\t<!-- Damage States -->')
    x = sub1(x, '\t\t\t<!-- the target painter trigger -->',
             TOGGLE + DEATH + AURA + '\t\t\t<!-- the target painter trigger -->')
    x = add_draw(x, x.index('<GameObject'), zone_draw() + tier_draw())
    x = sub1(x, 'ButtonImage="Button_AlliedAntiVehicleVehicleTech1_on"', f'ButtonImage="{BUTTON}"')
    x = sub1(x, 'SelectPortrait="Portrait_AlliedAntiVehicleVehicleTech1"', f'SelectPortrait="{PORTRAIT}"')
    c26.ART, saved = SRC[FAST], c26.ART               # button_icon.py compose button_japan / portrait_japan
    try:
        images = c26.image_assets(BUTTON) + c26.image_assets(PORTRAIT)
    finally:
        c26.ART = saved
    build = (f'\t<LogicCommand Type="UNIT_BUILD" id="Command_Construct{UNIT}">\n\t\t<Object>{UNIT}</Object>\n'
             '\t</LogicCommand>\n')
    # the 复仇 modifiers and pulse weapon live here, once (the death module on other units refers to them)
    x = sub1(x, '</AssetDeclaration>', NARUKAMI_DECL + DECL + images + build + '</AssetDeclaration>')
    with open(path, 'w', encoding='utf-8', newline='\r\n') as f:
        f.write(x.replace('\r\n', '\n'))
    with open(os.path.join(c26.DATA, c31.NARUKAMI_UI_FILE), 'w', encoding='utf-8', newline='\r\n') as f:
        f.write('<?xml version="1.0" encoding="UTF-8"?>\n<AssetDeclaration xmlns="uri:ea.com:eala:asset" '
                'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">\n' + NARUKAMI_UI + '</AssetDeclaration>\n')
    for model in (FAST, SIGNAL):
        print('model', model, to_w3x.convert(SRC[model], model, pivots(model), c23.PARTS, scale=SCALE, level=LEVEL, grade=False,
                                             retail_maps=True, **c24.AI_TONE), 'triangles')


def override_units():
    """Every retail Empire unit with the 复仇 death module, under its retail id (make_campnew7.OVERRIDE): the
    unit's SDK file with the module added at the end of that GameObject's Behaviors."""
    for t in OVERRIDE:
        name = next(n for n in os.listdir(c31.SAGE) if f'id="{t}"' in
                    open(os.path.join(c31.SAGE, n), encoding='utf-8', errors='replace').read())
        x = open(os.path.join(c31.SAGE, name), encoding='utf-8', errors='replace').read()
        start = c31.re.search(r'<GameObject\b[^>]*?\bid="' + t + '"', x).start()
        end = x.index('</Behaviors>', start)
        x = x[:end] + DEATH.lstrip() + '\t\t' + x[end:]
        if '</Draws>' in x[start:]:
            x = add_draw(x, start, tier_draw())
        with open(os.path.join(c26.DATA, t + '.xml'), 'w', encoding='utf-8', newline='\r\n') as f:
            f.write(x.replace('\r\n', '\n'))


def jfactory_xml():
    """CNV_JWarFactory: the retail Empire war factory with 鸣神 after the Tsunami in both command sets (the
    tech-2 upgrade swaps the set: ours too)."""
    src = open(os.path.join(c2.SDK, 'SageXML', 'Japan', 'Structures', 'JapanWarFactory.xml'), encoding='utf-8').read()
    x = c31.sub1(src, 'id="JapanWarFactory"', f'id="{JFACTORY}"')
    x = c31.sub1(x, 'EditorName="JapanWarFactory"', f'EditorName="{JFACTORY}"')
    x = c31.sub1(x, 'CommandSet="JapanWarFactoryCommandSet"', f'CommandSet="{JFACTORY}CommandSet"')
    x = c31.sub1(x, 'CommandSet="JapanWarFactoryCommandSetTech2"', f'CommandSet="{JFACTORY}CommandSetTech2"')
    sets = open(os.path.join(c2.SDK, 'SageXML', 'GlobalData', 'LogicCommandSet.xml'), encoding='utf-8').read()
    body = c31.re.search(r'id="JapanWarFactoryCommandSetBase">(.*?)</LogicCommandSet>', sets, c31.re.S).group(1)
    cmds = c31.re.findall(r'<Cmd>([^<]+)</Cmd>', body)
    cmds.insert(cmds.index('Command_ConstructJapanAntiVehicleVehicleTech1') + 1, f'Command_Construct{UNIT}')
    decl = ''
    for suffix, extra in (('', 'Command_PurchaseJapanWarFactoryTech2'), ('Tech2', 'Command_PurchaseJapanWarFactoryTech3')):
        decl += (f'\t<LogicCommandSet id="{JFACTORY}CommandSet{suffix}">\n' +
                 ''.join(f'\t\t<Cmd>{c}</Cmd>\n' for c in cmds + [extra]) + '\t</LogicCommandSet>\n')
    x = c31.sub1(x, '</AssetDeclaration>', decl + '</AssetDeclaration>')
    x = x.replace('<Includes>', f'<Includes>\n\t\t<Include type="all" source="DATA:CNVUnits/Data/{UNIT}.xml" />', 1)
    with open(os.path.join(c26.DATA, JFACTORY + '.xml'), 'w', encoding='utf-8', newline='\r\n') as f:
        f.write(x.replace('\r\n', '\n'))
    print('Empire factory commands:', cmds)


A = c28.A
N1, N2 = (A[0] - 60, A[1] + 100), (A[0] + 150, A[1] + 60)
WARRIORS = [(A[0] - 140 + 50 * k, A[1] + 200) for k in range(4)]
TSUNAMI = (A[0] + 30, A[1] + 140)
HAMMERS = [(A[0] + dx, A[1] + 460) for dx in (-60, 0, 60)]
# CNV_LINEUP=1: Mecha Tengu, Striker-VX, King Oni, Tsunami, 鸣神 x2 side by side at the start camera's screen centre
# (calib: ~(1241, 2499)), no enemies, for zoomed comparisons (run_bench.ps1 -Actions wheel)
LINEUP = ['JapanAntiInfantryVehicle', 'JapanAntiAirVehicleTech1', 'JapanAntiVehicleVehicleTech3',
          'JapanAntiVehicleVehicleTech1', UNIT, UNIT] if os.environ.get('CNV_LINEUP') == '1' else []
LINEUP_X0, LINEUP_Y = 1100.0, 2500.0
# CNV_COUNTER=1: the two counters side by side -- three warriors + a Tsunami (the receiver) in a signal zone (CampNew31's
# always-on probe), killed by a Sickle (normal death: 复仇), a Cryocopter + Sickle (frozen: none) or Tesla troopers
# (electrocuted: none). CNV_NO_COUNTER=1 (make_campnew31) for the control without the exemptions.
COUNTER = os.environ.get('CNV_COUNTER') == '1'
COUNTER_Y = 2375.0 + 300
COUNTER_GROUPS = [(1000.0, ['SovietAntiInfantryVehicle']),
                  (1240.0, ['AlliedSupportAircraft', 'SovietAntiInfantryVehicle']),
                  (1480.0, ['SovietHeavyAntiVehicleInfantry'] * 3)]
# CNV_COUNTER=probe: the same three cases without combat (the fight above was too cluttered to read: frozen and
# 复仇 shaders mixed). Warrior copies die by LifetimeUpdate after 6 s: DeathType NORMAL, ELECTROCUTED, or NORMAL
# while frozen (their zone's probe also gives them the retail cryo-beam modifier, status UNDER_FROZEN). Each group
# 300 apart with its own zone (range 200) and a Tsunami 120 south as the receiver.
# CNV_COUNTER=emp: does an EMP on the signal unit switch its zone off (a counter without any change)? Group P's
# zone unit is paralysed (ParalyzeType EMP, as the Tesla trooper's short circuit) from 3 s to 9 s by a helper that
# dies at 3 s; its warriors die at 6 s. Group N beside it: the control.
EMP = os.environ.get('CNV_COUNTER') == 'emp'
PROBE = os.environ.get('CNV_COUNTER') == 'probe' or EMP
COUNTER = COUNTER or PROBE
PROBE_KINDS = [('N', 'NORMAL', False), ('E', 'ELECTROCUTED', False), ('F', 'NORMAL', True)]
PROBE_X, PROBE_Y = [950.0, 1250.0, 1550.0], 2375.0 + 150
if EMP:
    PROBE_KINDS, PROBE_X = [('N', 'NORMAL', False), ('P', 'NORMAL', False)], [1250.0, 1550.0]
EMP_HELPER = 'CNV_ProbeEMPHelper'
EMP_DECL = f'''	<WeaponTemplate id="CNV_ProbeEMP" Flags="NOT_ATTRACTED_BY_MAGNETS" AttackRange="999999.0"
		RequiredAntiMask="ANTI_GROUND ANTI_STRUCTURE ANTI_WATER" RadiusDamageAffects="ALLIES SELF">
		<Nuggets>
			<ParalyzeNugget Radius="120.0" DurationSeconds="6s" ParalyzeType="EMP" ParalyzeFX="FX_None">
				<SpecialObjectFilter Rule="NONE" Relationship="ALLIES SAME_PLAYER">
					<IncludeThing>{c31.SIGNAL}P</IncludeThing>
				</SpecialObjectFilter>
			</ParalyzeNugget>
		</Nuggets>
	</WeaponTemplate>
'''
if EMP:
    c7.EXTRA_TEMPLATES[EMP_HELPER] = {'file': f'DATA:CNVUnits/Data/{EMP_HELPER}.xml', 'EditorSorting': 'UNIT'}
# CNV_COUNTER=tiers: the tier glow and no doubling. Group S: one zone, a Tsunami, warriors dying at 6, 10 and 14 s
# (glow should grow 1 -> 2 -> 3). Group D: two zones over a Tsunami, one warrior dying at 6 s (tier 1, not 2).
# A 鸣神 to deploy by hand for the zone ring.
TIERS = os.environ.get('CNV_COUNTER') == 'tiers'
TIER_WARRIORS = [6, 10, 14]
if TIERS:                        # 鸣神 is placed, so its XML carries the 复仇 declarations
    for t in [f'{c31.WARRIOR}T{s}' for s in TIER_WARRIORS] + [f'{c31.SIGNAL}T']:
        c7.EXTRA_TEMPLATES[t] = {'file': f'DATA:CNVUnits/Data/{t}.xml', 'EditorSorting': 'UNIT'}


def tier_units():
    names = ''.join(f'\n\t\t\t\t\t<IncludeThing>{c31.WARRIOR}T{s}</IncludeThing>' for s in TIER_WARRIORS)
    for s in TIER_WARRIORS:
        c31.copy_unit('JapanAntiInfantryInfantry', f'{c31.WARRIOR}T{s}', DEATH +
                      f'\t\t\t<LifetimeUpdate id="ModuleTag_CNV_ProbeLifetime" MinLifetime="{s}s" MaxLifetime="{s}s"/>\n')
    c31.copy_unit('JapanLightTransportVehicle', f'{c31.SIGNAL}T', c31.AURA.replace(c31.EMPIRE, c31.EMPIRE + names))
if COUNTER:
    c7.EXTRA_TEMPLATES[c31.SIGNAL] = {'file': f'DATA:CNVUnits/Data/{c31.SIGNAL}.xml', 'EditorSorting': 'UNIT'}
if PROBE:
    for k, _, _ in PROBE_KINDS:
        for t in (f'{c31.WARRIOR}{k}', f'{c31.SIGNAL}{k}'):
            c7.EXTRA_TEMPLATES[t] = {'file': f'DATA:CNVUnits/Data/{t}.xml', 'EditorSorting': 'UNIT'}


def probe_units():
    names = ''.join(f'\n\t\t\t\t\t<IncludeThing>{c31.WARRIOR}{k}</IncludeThing>' for k, _, _ in PROBE_KINDS)
    for k, death, frozen in PROBE_KINDS:
        c31.copy_unit('JapanAntiInfantryInfantry', f'{c31.WARRIOR}{k}', DEATH +
                      f'\t\t\t<LifetimeUpdate id="ModuleTag_CNV_ProbeLifetime" MinLifetime="6s" MaxLifetime="6s" '
                      f'DeathType="{death}"/>\n')
        aura = c31.AURA.replace(c31.EMPIRE, c31.EMPIRE + names).replace('ModuleTag_CNV_SignalAura',
                                                                        f'ModuleTag_CNV_SignalAura{k}')
        if frozen:
            aura += (f'\t\t\t<AttributeModifierAuraUpdate id="ModuleTag_CNV_ProbeFreeze" '
                     'AttributeModifierName="AttributeModifer_CryoBeam_10" RefreshDelay="0.5s" Range="120" '
                     f'InitiallyActive="true">\n\t\t\t\t<ObjectFilter Rule="NONE" Relationship="ALLIES SAME_PLAYER">'
                     f'\n\t\t\t\t\t<IncludeThing>{c31.WARRIOR}{k}</IncludeThing>\n\t\t\t\t</ObjectFilter>\n'
                     '\t\t\t</AttributeModifierAuraUpdate>\n')
        # the 复仇 declarations live in 鸣神's file, which this scene does not place (first runs: the modifiers and
        # the pulse weapon were unresolved, nothing fired in either run): the first probe carries them
        c31.copy_unit('JapanLightTransportVehicle', f'{c31.SIGNAL}{k}', aura, DECL if k == PROBE_KINDS[0][0] else '')
    if EMP:                                      # a warrior copy outside every filter: dies at 3 s, EMPs zone unit P
        c31.copy_unit('JapanAntiInfantryInfantry', EMP_HELPER,
                      '\t\t\t<FireWeaponWhenDead id="ModuleTag_CNV_ProbeEMP" DeathWeapon="CNV_ProbeEMP" '
                      'InitiallyActive="true">\n\t\t\t\t<DieMuxData DeathTypes="ALL"/>\n\t\t\t</FireWeaponWhenDead>\n'
                      '\t\t\t<LifetimeUpdate id="ModuleTag_CNV_ProbeLifetime" MinLifetime="3s" MaxLifetime="3s"/>\n',
                      EMP_DECL)
# every retail Empire unit gets the 复仇 death module (make_campnew7.OVERRIDE: our recompiled GameObject under the
# retail id in the map stream; bench: retail Imperial Warriors dying in the zone gave 复仇) and the scene uses
# retail warriors; CNV_OVERRIDE=0: our warrior copies instead (CampNew31's way)
OVERRIDE = [] if os.environ.get('CNV_OVERRIDE') == '0' else \
    [t for t in c31.empire_units() if t not in (c31.WARRIOR, c31.SIGNAL, c31.NARUKAMI)]
WARRIOR = 'JapanAntiInfantryInfantry' if OVERRIDE else c31.WARRIOR
for t in OVERRIDE:               # included type="all": map_xml leaves out templates the static stream already has
    c7.EXTRA_ALL.append(f'DATA:CNVUnits/Data/{t}.xml')
c7.OVERRIDE += OVERRIDE


def generate(m):
    unit_xml()
    jfactory_xml()
    if OVERRIDE:
        override_units()
    else:
        c31.copy_unit('JapanAntiInfantryInfantry', WARRIOR, DEATH)
    c31._generate(m)                             # CampNew29's scene: factory, power plant, our tanks, Hammers
    objs = next(n for _, n in m.walk() if n.name == 'ObjectsList')
    head = lambda k: k.head[:60]                 # noqa: E731
    p1 = next(k for k in objs.kids if b'CNV_LightTank2' in head(k))
    s1 = next(k for k in objs.kids if b'SovietAntiVehicleVehicleTech1' in head(k))
    units = (b'CNV_LightTank2', b'CNV_ShrinkVehicle', b'AlliedSupportAircraft', b'SovietAntiVehicleVehicleTech1',
             b'CNV_WarFactory')          # the Empire's factory goes where CampNew26's Allied copy stood
    if LINEUP or COUNTER or TIERS:               # the base's own units too (MCV in the line; Guardians shot killers)
        units += (b'Allied',)
    objs.kids[:] = [k for k in objs.kids if not any(u in head(k) for u in units)]
    if LINEUP:                                   # the look to match: retail Empire units in a row at the screen centre
        place = [(p1, t, (LINEUP_X0 + 55 * k, LINEUP_Y), math.pi * 0.75) for k, t in enumerate(LINEUP)]
    elif TIERS:
        tier_units()
        sx, dx, y = 1120.0, 1360.0, 2375.0 + 150    # group S off the shore (at 1000 its warriors swam out of range)
        place = [(p1, f'{c31.WARRIOR}T{s}', (sx - 40 + 40 * k, y), math.pi / 2) for k, s in enumerate(TIER_WARRIORS)]
        place += [(p1, 'JapanAntiVehicleVehicleTech1', (sx, y - 110), math.pi / 2),
                  (p1, f'{c31.SIGNAL}T', (sx, y + 90), math.pi / 2)]
        place += [(p1, f'{c31.WARRIOR}T6', (dx, y), math.pi / 2),
                  (p1, 'JapanAntiVehicleVehicleTech1', (dx, y - 110), math.pi / 2),
                  (p1, f'{c31.SIGNAL}T', (dx - 60, y + 90), math.pi / 2),
                  (p1, f'{c31.SIGNAL}T', (dx + 60, y + 90), math.pi / 2),
                  (p1, UNIT, (1550.0, 2375.0 + 20), math.pi / 2)]
    elif PROBE:
        probe_units()
        place = []
        for x, (k, _, _) in zip(PROBE_X, PROBE_KINDS):
            place += [(p1, f'{c31.WARRIOR}{k}', (x + dx, PROBE_Y), math.pi / 2) for dx in (-35, 0, 35)]
            place += [(p1, 'JapanAntiVehicleVehicleTech1', (x, PROBE_Y - 120), math.pi / 2),
                      (p1, f'{c31.SIGNAL}{k}', (x, PROBE_Y + 90), math.pi / 2)]
            if k == 'P':
                place.append((p1, EMP_HELPER, (x + 40, PROBE_Y + 90), math.pi / 2))
    elif COUNTER:                                # the counters: one group per kind of killer, each in its own zone
        c31.copy_unit('JapanLightTransportVehicle', c31.SIGNAL, c31.AURA, DECL)     # 复仇 declarations: see probe
        place = []
        for x, killers in COUNTER_GROUPS:
            place += [(p1, WARRIOR, (x + dx, COUNTER_Y), math.pi / 2) for dx in (-35, 0, 35)]
            place += [(p1, 'JapanAntiVehicleVehicleTech1', (x, COUNTER_Y - 80), math.pi / 2),
                      (p1, c31.SIGNAL, (x, COUNTER_Y - 150), math.pi / 2)]
            place += [(s1, t, (x + 30 * k - 15 * (len(killers) - 1), COUNTER_Y + 140), -math.pi / 2)
                      for k, t in enumerate(killers)]
    else:
        place = [(p1, UNIT, N1, math.pi / 2), (p1, UNIT, N2, math.pi / 2),
                 (p1, 'JapanAntiVehicleVehicleTech1', TSUNAMI, math.pi / 2)]
        place += [(p1, WARRIOR, at, math.pi / 2) for at in WARRIORS]
        place += [(s1, 'SovietAntiVehicleVehicleTech1', at, -math.pi / 2) for at in HAMMERS]
        place.append((p1, JFACTORY, c26.FACTORY_AT, math.pi))
    for src, template, (x, y), angle in place:
        pr, flags = newmap.typed_props_of(m, src)
        objs.kids.append(newmap.object_node(m, pr, flags, template, x, y, angle=angle,
                                            uniqueID=f'{template} {len(objs.kids)}'))
    print('CNV32:', len(place), 'placed')


c6.edit = generate

if __name__ == '__main__':
    if c23.game_running():
        c2.OUT = c4.OUT = os.path.join(os.path.dirname(os.path.dirname(HERE)), 'work', 'staging', NAME)
        print('RA3 is running -> staging at', c4.OUT)
    c4.main()
