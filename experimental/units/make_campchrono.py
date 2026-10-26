r"""时滞炮车 sample (CampChrono1): make_campnew35.py's phase tank wearing its own model -- the first unit through the
art route of 2026-10-26 (GPT three-view sheet, concept_gpt.py -> Tripo multi-view model with parts -> Blender,
tripo_unit.py -> to_w3x.py) -- with its own button, portrait and name, built from CampNew26's CNV war factory.

The scene is CampNew35's: the phase tank 300 south of an enemy Apocalypse with two retail Guardians beside it (the
look and size to match). CNV_DEPLOY defaults to 0 here (always armed, so it fires without the deploy click).

  "C:\Program Files (x86)\Steam\steamapps\common\Blender\blender.exe" -b --factory-startup
      -P experimental/units/tripo_unit.py -- chronolag
  python -I -X utf8 experimental/units/button_icon.py compose button work/units/chronolag/game/icon.png
      work/units/chronolag/game/Button_CNV_PhaseProbe_on.tga                     (and portrait ... Portrait_CNV_PhaseProbe.tga)
  python -I -X utf8 experimental/units/make_campchrono.py          -> Documents\Red Alert 3\Mods\CampChrono1
(from a worktree set CNV_SDK to the shared SDK: labpaths finds it next to the repository)
"""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), 'campaign'))
os.environ.setdefault('CNV_DEPLOY', '0')
import make_campnew35 as c35                    # noqa: E402

c29, c26, c23, c7, c4, c2 = c35.c29, c35.c26, c35.c23, c35.c7, c35.c4, c35.c2
to_w3x = c23.to_w3x
NAME = 'CampChrono1'                            # <= 15 characters, no underscore
c4.NAME = c2.NAME = NAME
c2.SRC_DIR = os.path.join(c2.SDK, 'Mods', NAME, 'data')
c2.BUILT = os.path.join(c2.SDK, 'BuiltMods', 'mods', NAME.lower(), 'data')
c2.OUT = c4.OUT = os.path.join(os.path.expanduser('~'), 'Documents', 'Red Alert 3', 'Mods', NAME)
c7.MAP_MOD = NAME + 'Map'

UNIT, MODEL = c35.UNIT, 'CNChrono'
SRC = os.path.join(os.path.dirname(os.path.dirname(HERE)), 'work', 'units', 'chronolag', 'game')
BUTTON, PORTRAIT = f'Button_{UNIT}_on', f'Portrait_{UNIT}'
PARTS = {'HULL': 'BODY', 'TURRET': 'Bone_Turret', 'BARREL': 'Bone_Turret_Pitch'}
LEVEL = int(os.environ.get('CNV_CHRONO_LEVEL', 62))     # diffuse median (retail Allied vehicles 62..80)
c7.EXTRA_OWN += [b'LogicCommand:Command_Construct' + UNIT.encode()] + \
    [p + n.encode() for n in (BUTTON, PORTRAIT) for p in (b'PackedTextureImage:', b'Texture:')]
c4.c3.STRINGS.update({
    'Name:' + UNIT: '时滞炮车',
    'Type:' + UNIT: '时滞支援炮车',
    'Desc:' + UNIT: '不造成伤害：时滞弹把目标暂时推出时间，期间它不能移动、不能开火，也打不坏。',
})


def sub1(x, old, new):
    assert x.count(old) == 1, (old[:60], x.count(old))
    return x.replace(old, new, 1)


def pivots():
    with open(os.path.join(SRC, 'parts.json'), encoding='utf-8') as f:
        return [(n, p, tuple(at)) for n, p, at in json.load(f)['_pivots']]


_unit_xml = c35.unit_xml


def unit_xml():
    _unit_xml()                                 # CampNew35: the Guardian with the phase shell
    path = os.path.join(c26.DATA, UNIT + '.xml')
    x = open(path, encoding='utf-8').read()
    # our model (make_campnew23.unit_xml's swap): every model, our still idle animation, no tread scrolling
    x = re.sub(r'(<Model\s+Name=")[^"]*(")', lambda m: m.group(1) + MODEL.upper() + m.group(2), x)
    x = re.sub(r'AnimationName="[^"]*"', f'AnimationName="{MODEL.upper()}_IDLE"', x)
    x = re.sub(r'\s*<TreadScrollingMap\b[^>]*/>', '', x)
    x = sub1(x, '<Includes>', f'<Includes>\n\t\t<Include type="all" source="ART:{MODEL}.w3x" />'
                              f'\n\t\t<Include type="all" source="ART:{MODEL}_IDLE.w3x" />')
    # its own button, portrait, texts; buildable without the armor facility (as 游隼, make_campnew26)
    x = sub1(x, 'ButtonImage="Button_AlliedAntiVehicleVehicleTech1_on"', f'ButtonImage="{BUTTON}"')
    x = sub1(x, 'SelectPortrait="Portrait_AlliedAntiVehicleVehicleTech1"', f'SelectPortrait="{PORTRAIT}"')
    x = sub1(x, 'Description="Desc:AlliedAntiVehicleVehicleTech1"', f'Description="Desc:{UNIT}"')
    x = sub1(x, 'TypeDescription="Type:AlliedAntiVehicleVehicleTech1"', f'TypeDescription="Type:{UNIT}"')
    x = sub1(x, '>Name:AlliedAntiVehicleVehicleTech1<', f'>Name:{UNIT}<')
    x = re.sub(r'\s*<GameDependency>\s*<NeededUpgrade>Upgrade_AlliedTech2</NeededUpgrade>\s*</GameDependency>', '', x)
    c26.ART, saved = SRC, c26.ART               # image_assets reads the button / portrait from c26.ART
    try:
        images = c26.image_assets(BUTTON) + c26.image_assets(PORTRAIT)
    finally:
        c26.ART = saved
    x = sub1(x, '</AssetDeclaration>', images + f'\t<LogicCommand Type="UNIT_BUILD" id="Command_Construct{UNIT}">\n'
                                                f'\t\t<Object>{UNIT}</Object>\n\t</LogicCommand>\n</AssetDeclaration>')
    assert 'Upgrade_AlliedTech2' not in x
    assert set(re.findall(r'<Model\s+Name="([^"]*)"', x)) == {MODEL.upper()}, re.findall(r'<Model\s+Name="([^"]*)"', x)
    with open(path, 'w', encoding='utf-8', newline='\r\n') as f:
        f.write(x.replace('\r\n', '\n'))
    print('model', MODEL, to_w3x.convert(SRC, MODEL, pivots(), PARTS, src_name=MODEL, level=LEVEL,
                                         retail_maps=True), 'triangles')


c35.unit_xml = unit_xml
_factory_xml = c26.factory_xml


def factory_xml():
    _factory_xml()                              # CampNew29: retail list + 游隼 + the shrink-ray car
    path = os.path.join(c26.DATA, c26.FACTORY + '.xml')
    x = open(path, encoding='utf-8').read()
    x = sub1(x, f'\t\t<Cmd>Command_Construct{c29.UNIT}</Cmd>\n',
             f'\t\t<Cmd>Command_Construct{c29.UNIT}</Cmd>\n\t\t<Cmd>Command_Construct{UNIT}</Cmd>\n')
    x = sub1(x, '<Includes>', f'<Includes>\n\t\t<Include type="all" source="DATA:CNVUnits/Data/{UNIT}.xml" />')
    with open(path, 'w', encoding='utf-8', newline='\r\n') as f:
        f.write(x.replace('\r\n', '\n'))


c26.factory_xml = factory_xml

if __name__ == '__main__':
    if c23.game_running():
        c2.OUT = c4.OUT = os.path.join(os.path.dirname(os.path.dirname(HERE)), 'work', 'staging', NAME)
        print('RA3 is running -> staging at', c4.OUT)
    c4.main()
