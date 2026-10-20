r"""Tripo probe (CampTripo1, 2026-10-20): a tank made by Tripo Studio from 游隼 v3's concept picture
(work/units/lighttank_ai/concept_v3.png -> H2.5 model -> Tripo retopology to 5000 triangles, free tier), converted by
ai_lighttank_blend.py keep=1 (its own atlas and colour kept; our team mask, normals, pivots), in CampNew24's AI slot.
Laid out like CampNew25 CNV_CLOSEUP: the v1 parametric tank, the Tripo tank and a retail Guardian in a column at the
start camera's centre, so bench shots compare with CampNew25's close-ups of 游隼 v3.

  "C:\Program Files (x86)\Steam\steamapps\common\Blender\blender.exe" -b --factory-startup
      -P experimental/units/ai_lighttank_blend.py -- work/units/tripo/tank_retopo5k.glb work/units/tripo/blend5k
      keep=1 voxel=0 smooth=0 tris=6000
  python -I -X utf8 experimental/campaign/make_camptripo.py      -> Documents\Red Alert 3\Mods\CampTripo1
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import make_campnew24 as c24                    # noqa: E402

c23, c7, c4, c2 = c24.c23, c24.c7, c24.c4, c24.c2
NAME = 'CampTripo1'                             # <= 15 characters, no underscore (skudef rule)
c4.NAME = c2.NAME = NAME
c2.SRC_DIR = os.path.join(c2.SDK, 'Mods', NAME, 'data')
c2.BUILT = os.path.join(c2.SDK, 'BuiltMods', 'mods', NAME.lower(), 'data')
c2.OUT = c4.OUT = os.path.join(os.path.expanduser('~'), 'Documents', 'Red Alert 3', 'Mods', NAME)
c7.MAP_MOD = NAME + 'Map'
c24.AI_SRC = os.path.join(os.path.dirname(os.path.dirname(HERE)), 'work', 'units', 'tripo',
                          os.environ.get('CNV_TRIPO', 'blend5k'))
c4.c3.STRINGS['Name:' + c24.AI_UNIT] = 'CNV 轻型坦克（Tripo）'
c24.AI_SCALE = c23.SCALE * 0.8                  # 游隼's close-up scale (CampNew25)
c24.AI_LEVEL = int(os.environ.get('CNV_TRIPO_LEVEL', 50))
if os.environ.get('CNV_TRIPO_TONE') == '1':     # 游隼 v3's tone (CampNew25 CNV_TONE): edges, plate / body specular
    c24.AI_TONE = dict(edge_gain=1.8, edge_spec=200, plate_spec=70, plate_share=30, body_spec=18, contrast=1.6)
c24.AI_RETAIL_MAPS = True
c23.TANK_AT = (1222.0, 2470.0)
c24.AI_AT = (1222.0, 2425.0)
c23.ENEMY_AT = (c23.TANK_AT[0] + 1500, c23.TANK_AT[1])
_gen = c24.c6.edit


def _with_guardian(m):                          # CampNew25's retail Guardian just south, as the look to match
    _gen(m)
    objs = next(n for _, n in m.walk() if n.name == 'ObjectsList')
    p1 = next(k for k in objs.kids if b'AlliedAntiVehicleVehicleTech1' in k.head[:60])
    pr, flags = c24.newmap.typed_props_of(m, p1)
    objs.kids.append(c24.newmap.object_node(m, pr, flags, 'AlliedAntiVehicleVehicleTech1', 1222.0, 2380.0,
                                            angle=0.0, uniqueID=f'Guardian closeup {len(objs.kids)}'))


c24.c6.edit = _with_guardian

if __name__ == '__main__':
    if c23.game_running():
        c2.OUT = c4.OUT = os.path.join(os.path.dirname(os.path.dirname(HERE)), 'work', 'staging', NAME)
        print('RA3 is running -> staging at', c4.OUT)
    c4.main()
