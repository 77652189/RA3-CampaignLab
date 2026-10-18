"""收缩射线车 (CNV_ShrinkVehicle), rough, for the Cryocopter / 游隼 combo (CampNew29): on CampNew28's battle map,
one shrink vehicle next to the two 游隼, buildable from the CNV War Factory.

The unit is the Guardian's logic (make_campnew24.unit_xml) with the Cryocopter's shrink ray: SpecialPower +
WeaponFireSpecialAbilityUpdate (SpecialPower_ShrinkRay, weapon AlliedSupportAircraftShrinkRay, slot 2), a LaserDraw
(FXShrinkRay) and a LaserState from bone FXWEAPON_01 -- laser id 2, the Guardian's dormant target painter uses 1.
Its command set holds the retail Command_AlliedSupportAircraftShrinkRay, whose button (ButtonShrinkRay) is in the
static stream. Shrunk enemy vehicles become crushable (CrushableLevel 1 under SHRINK_EFFECT), which 游隼
(CrusherLevel 20) runs over.

  python -I -X utf8 experimental/campaign/make_campnew29.py   -> Documents\\Red Alert 3\\Mods\\CampNew29
"""
import math
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(os.path.dirname(HERE), 'units'))
import make_campnew28 as c28                    # noqa: E402

c27, c26, c23 = c28.c27, c28.c26, c28.c23
c24 = c23 and c26.c25.c24
c7, c6, c4, c2 = c23.c7, c23.c6, c23.c4, c23.c2
newmap, to_w3x = c23.newmap, c23.to_w3x
NAME = 'CampNew29'
c4.NAME = c2.NAME = NAME
c2.SRC_DIR = os.path.join(c2.SDK, 'Mods', NAME, 'data')
c2.BUILT = os.path.join(c2.SDK, 'BuiltMods', 'mods', NAME.lower(), 'data')
c2.OUT = c4.OUT = os.path.join(os.path.expanduser('~'), 'Documents', 'Red Alert 3', 'Mods', NAME)
c7.MAP_MOD = NAME + 'Map'

UNIT, MODEL = 'CNV_ShrinkVehicle', 'CNShrink'
SRC = os.path.join(os.path.dirname(os.path.dirname(HERE)), 'work', 'units', 'shrinkvehicle')
BUTTON, PORTRAIT = f'Button_{UNIT}_on', f'Portrait_{UNIT}'
COMMANDS = f'{UNIT}CommandSet'
c7.EXTRA_TEMPLATES[UNIT] = {'file': 'DATA:CNVUnits/Data/' + UNIT + '.xml', 'EditorSorting': 'UNIT'}
c7.EXTRA_OWN += [b'LogicCommandSet:' + COMMANDS.encode(), b'LogicCommand:Command_Construct' + UNIT.encode()] + \
    [p + n.encode() for n in (BUTTON, PORTRAIT) for p in (b'PackedTextureImage:', b'Texture:')]
c4.c3.STRINGS.update({
    'Name:' + UNIT: '收缩射线车',
    'Type:' + UNIT: '缩小支援车',
    'Desc:' + UNIT: '冷冻直升机与游隼的协同支援车。缩小射线让敌方载具变小、变脆、射程缩短，并可被游隼直接碾压。',
})
SHRINK_AT = (c28.A[0] - 40, c28.A[1] - 60)          # just behind the two 游隼
T, P, TIP = (-1.0, 0.0, 7.8), (0.3, 0.0, 4.6), (5.8, 0.0, 0.0)   # cnv_shrinkvehicle.py TURRET_AT / PITCH_AT / TIP
SCALE = c23.SCALE * 0.8                            # as 游隼
PIVOTS = [('BODY', None, (0, 0, 0)),
          ('Bone_Turret', None, T), ('Bone_Turret_Pitch', 'Bone_Turret', P),
          ('BONE_GUN_MUZZLE', 'Bone_Turret_Pitch', TIP), ('FXBone_Muzzle', 'Bone_Turret_Pitch', TIP),
          ('FXWEAPON_01', 'Bone_Turret_Pitch', TIP),
          ('FX_Laser', 'Bone_Turret_Pitch', TIP), ('FX_Damage01', None, (-8, 0, 8)),
          ('FXTracksL', None, (-14, 9.5, 0)), ('FXTracksR', None, (-14, -9.5, 0))] + \
    [(f'Bone_{kind}_{fr}_{side}', None, (8 if fr == 'Front' else -8, 9.5 if side == 'Left' else -9.5, 2.2))
     for kind in ('Tread', 'Tracks') for fr in ('Front', 'Rear') for side in ('Left', 'Right')]

SHRINK_DRAW = '''			<LaserDraw
				id="ModuleTag_LaserDraw_ShrinkRay"
				Texture1_UTile="1" Texture1_VTile="5" Texture1_UScrollRate="0" Texture1_VScrollRate="1"
				Texture1_NumFrames="1" Texture1_FrameRate="30"
				Texture2_UTile="1" Texture2_VTile="1" Texture2_UScrollRate="0" Texture2_VScrollRate="1"
				Texture2_NumFrames="1" Texture2_FrameRate="30"
				FadeInTime="0.2s" FadeOutTime="0.2s" LaserWidth="15" WeaponSlotID="2" LaserStateID="2">
				<FXShader ShaderName="Laser.fx" TechniqueIndex="0">
					<Constants>
						<Texture Name="Texture1"><Value>FXShrinkRay</Value></Texture>
						<Texture Name="Texture2"><Value>FXShrinkRay</Value></Texture>
						<Float Name="ColorEmissive"><Value>3.0</Value><Value>3.0</Value><Value>3.0</Value></Float>
					</Constants>
				</FXShader>
			</LaserDraw>
		</Draws>'''
SHRINK_BEHAVIORS = '''		<Behaviors>
			<LaserState id="ModuleTag_LaserStateShrinkRay" LaserId="2" OriginBoneName="FXWEAPON_01" />
			<SpecialPower id="ModuleTag_ShrinkRaySpecialPower" SpecialPowerTemplate="SpecialPower_ShrinkRay"
				UpdateModuleStartsAttack="true" />
			<WeaponFireSpecialAbilityUpdate id="ModuleTag_ShrinkRaySpecialAbilityUpdate"
				SpecialPowerTemplate="SpecialPower_ShrinkRay" WeaponSlotType="PRIMARY_WEAPON" WeaponSlotID="2"
				SpecialWeapon="AlliedSupportAircraftShrinkRay" StartAbilityRange="300" UnpackTime="0s" PackTime="1s"
				TriggerSound="ALL_CryocopterShrinkrayFire" />'''


def sub1(x, old, new):
    assert old in x, old[:80]
    return x.replace(old, new, 1)


def unit_xml():
    c24.unit_xml(UNIT, MODEL)                        # the Guardian with our model and idle animation
    path = os.path.join(c26.DATA, UNIT + '.xml')
    x = open(path, encoding='utf-8').read()
    x = sub1(x, 'ButtonImage="Button_AlliedAntiVehicleVehicleTech1_on"', f'ButtonImage="{BUTTON}"')
    x = sub1(x, 'SelectPortrait="Portrait_AlliedAntiVehicleVehicleTech1"', f'SelectPortrait="{PORTRAIT}"')
    x = sub1(x, 'Description="Desc:AlliedAntiVehicleVehicleTech1"', f'Description="Desc:{UNIT}"')
    x = sub1(x, 'TypeDescription="Type:AlliedAntiVehicleVehicleTech1"', f'TypeDescription="Type:{UNIT}"')
    x = sub1(x, 'CommandSet="AlliedAntiVehicleVehicleTech1CommandSet"', f'CommandSet="{COMMANDS}"')
    x = re.sub(r'(<BuildCost Account="=\$ACCOUNT_ORE" Amount=")\d+(")', r'\g<1>900\2', x)
    x = re.sub(r'\s*<GameDependency>\s*<NeededUpgrade>Upgrade_AlliedTech2</NeededUpgrade>\s*</GameDependency>', '', x)
    x = sub1(x, 'MaxHealth="480"', 'MaxHealth="300"')
    x = re.sub(r'(<LocomotorSet\b[^>]*Condition="NORMAL"[^>]*Speed=")80\.0(")', r'\g<1>100.0\2', x)
    x = sub1(x, '\t\t</Draws>', SHRINK_DRAW)
    x = sub1(x, '\t\t<Behaviors>', SHRINK_BEHAVIORS)
    assert 'Upgrade_AlliedTech2' not in x and 'Amount="900"' in x and 'Speed="100.0"' in x
    c26.ART, saved = SRC, c26.ART                    # image_assets reads the button / portrait from c26.ART
    try:
        images = c26.image_assets(BUTTON) + c26.image_assets(PORTRAIT)
    finally:
        c26.ART = saved
    x = sub1(x, '</AssetDeclaration>', images +
             f'\t<LogicCommand Type="UNIT_BUILD" id="Command_Construct{UNIT}">\n\t\t<Object>{UNIT}</Object>\n'
             f'\t</LogicCommand>\n\t<LogicCommandSet id="{COMMANDS}">\n'
             f'\t\t<Cmd>Command_AlliedSupportAircraftShrinkRay</Cmd>\n\t\t<Cmd>Command_AttackMove</Cmd>\n'
             f'\t\t<Cmd>Command_MoveToPositionAndCollect</Cmd>\n\t</LogicCommandSet>\n</AssetDeclaration>')
    with open(path, 'w', encoding='utf-8', newline='\r\n') as f:
        f.write(x.replace('\r\n', '\n'))
    print('model', MODEL, to_w3x.convert(SRC, MODEL, PIVOTS, c23.PARTS, scale=SCALE, level=30, retail_maps=True,
                                         **c24.AI_TONE), 'triangles')


_factory_xml = c26.factory_xml


def factory_xml():
    _factory_xml()                                   # CampNew26: retail list + 游隼
    path = os.path.join(c26.DATA, c26.FACTORY + '.xml')
    x = open(path, encoding='utf-8').read()
    x = sub1(x, f'\t\t<Cmd>Command_Construct{c26.UNIT}</Cmd>\n',
             f'\t\t<Cmd>Command_Construct{c26.UNIT}</Cmd>\n\t\t<Cmd>Command_Construct{UNIT}</Cmd>\n')
    x = sub1(x, '<Includes>', f'<Includes>\n\t\t<Include type="all" source="DATA:CNVUnits/Data/{UNIT}.xml" />')
    with open(path, 'w', encoding='utf-8', newline='\r\n') as f:
        f.write(x.replace('\r\n', '\n'))


c26.factory_xml = factory_xml
_generate = c6.edit


def generate(m):
    unit_xml()
    _generate(m)                                     # CampNew28's battle scene (factory, 游隼 x2, Cryocopter, Hammers)
    objs = next(n for _, n in m.walk() if n.name == 'ObjectsList')
    p1 = next(k for k in objs.kids if b'AlliedAntiVehicleVehicleTech1' in k.head[:60])
    pr, flags = newmap.typed_props_of(m, p1)
    objs.kids.append(newmap.object_node(m, pr, flags, UNIT, *SHRINK_AT, angle=math.pi / 2,
                                        uniqueID=f'{UNIT} {len(objs.kids)}'))


c6.edit = generate

if __name__ == '__main__':
    if c23.game_running():
        c2.OUT = c4.OUT = os.path.join(os.path.dirname(os.path.dirname(HERE)), 'work', 'staging', NAME)
        print('RA3 is running -> staging at', c4.OUT)
    c4.main()
