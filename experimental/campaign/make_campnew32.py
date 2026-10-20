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
EMPIRE = c31.EMPIRE.replace(f'<IncludeThing>{c31.NARUKAMI}</IncludeThing>', f'<IncludeThing>{UNIT}</IncludeThing>')
DECL = c31.DECL.replace(c31.EMPIRE, EMPIRE).replace(f'Radius="{c31.PULSE_RADIUS}"', f'Radius="{PULSE_RADIUS}"')
AURA = c31.AURA.replace(c31.EMPIRE, EMPIRE).replace(f'Range="{c31.AURA_RANGE}"', f'Range="{AURA_RANGE}"').replace(
    'InitiallyActive="true"', 'InitiallyActive="true" RequiredObjectStatusFlags="TRANSFORMATION_TOGGLE_STATE"')
assert f'Radius="{PULSE_RADIUS}"' in DECL and f'Range="{AURA_RANGE}"' in AURA and UNIT in AURA
assert 'RequiredObjectStatusFlags' in AURA       # the zone only while deployed (missing in the first CampNew32 run)
# the deploy's model condition comes from the deploy modifier (ModelConditionsSet, as retail modifiers do): the
# ToggleState's ModelConditions did not swap the TruckDraw's model (CampNew32 bench, second run)
NARUKAMI_DECL = c31.NARUKAMI_DECL.replace('ObjectStatusToSet="IMMOBILE">', 'ObjectStatusToSet="IMMOBILE" '
                                          'ModelConditionsSet="USER_2">')
assert 'ModelConditionsSet="USER_2"' in NARUKAMI_DECL
c4.c3.STRINGS.update({
    'Name:' + UNIT: '鸣神突击机甲',
    'Type:' + UNIT: '信号突击机甲',
    'Desc:' + UNIT: '疾行形态高速骚扰；展开成信号形态时，信号区内阵亡的帝国单位把复仇意志传给周围的帝国单位。'
                    '收回形态时短暂冲刺。',
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
             TOGGLE + c31.DEATH + AURA + '\t\t\t<!-- the target painter trigger -->')
    x = sub1(x, '</AssetDeclaration>', NARUKAMI_DECL + '</AssetDeclaration>')
    with open(path, 'w', encoding='utf-8', newline='\r\n') as f:
        f.write(x.replace('\r\n', '\n'))
    with open(os.path.join(c26.DATA, c31.NARUKAMI_UI_FILE), 'w', encoding='utf-8', newline='\r\n') as f:
        f.write('<?xml version="1.0" encoding="UTF-8"?>\n<AssetDeclaration xmlns="uri:ea.com:eala:asset" '
                'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">\n' + c31.NARUKAMI_UI + '</AssetDeclaration>\n')
    for model in (FAST, SIGNAL):
        print('model', model, to_w3x.convert(SRC[model], model, pivots(model), c23.PARTS, scale=SCALE, level=LEVEL, grade=False,
                                             retail_maps=True, **c24.AI_TONE), 'triangles')


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


def generate(m):
    unit_xml()
    c31.copy_unit('JapanAntiInfantryInfantry', c31.WARRIOR, c31.DEATH, DECL)
    c31._generate(m)                             # CampNew29's scene: factory, power plant, our tanks, Hammers
    objs = next(n for _, n in m.walk() if n.name == 'ObjectsList')
    head = lambda k: k.head[:60]                 # noqa: E731
    p1 = next(k for k in objs.kids if b'CNV_LightTank2' in head(k))
    s1 = next(k for k in objs.kids if b'SovietAntiVehicleVehicleTech1' in head(k))
    units = (b'CNV_LightTank2', b'CNV_ShrinkVehicle', b'AlliedSupportAircraft', b'SovietAntiVehicleVehicleTech1')
    if LINEUP:                                   # the base's own units too (its MCV stood in the line)
        units += (b'Allied',)
    objs.kids[:] = [k for k in objs.kids if not any(u in head(k) for u in units)]
    if LINEUP:                                   # the look to match: retail Empire units in a row at the screen centre
        place = [(p1, t, (LINEUP_X0 + 55 * k, LINEUP_Y), math.pi * 0.75) for k, t in enumerate(LINEUP)]
    else:
        place = [(p1, UNIT, N1, math.pi / 2), (p1, UNIT, N2, math.pi / 2),
                 (p1, 'JapanAntiVehicleVehicleTech1', TSUNAMI, math.pi / 2)]
        place += [(p1, c31.WARRIOR, at, math.pi / 2) for at in WARRIORS]
        place += [(s1, 'SovietAntiVehicleVehicleTech1', at, -math.pi / 2) for at in HAMMERS]
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
