r"""A map from a real place (CampReal1): CampNew18's generated-map pipeline with the noise island replaced by
realmap.py's terrain and ground textures -- first place: the Golden Gate (realmap fetch goldengate 37.805 -122.465 7):
the Allies start in the city south of the strait, the Soviet tanks on the Marin hills north of it, the bridge is
the only land link.

  python -I -X utf8 experimental/campaign/realmap.py fetch goldengate 37.805 -122.465 7     (once; cached)
  python -I -X utf8 experimental/campaign/make_realmap.py      -> Documents\Red Alert 3\Mods\CampReal1
  python -I -X utf8 cnv.py map CampReal1                       -> work/maps/CampReal1.png

CNV_REAL=<place> picks another fetched place (START / ENEMY then need moving: pick them on the map picture).
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import make_campnew18 as c18                    # noqa: E402
import newmap                                   # noqa: E402
import realmap                                  # noqa: E402

c7, c4, c2 = c18.c7, c18.c4, c18.c2
NAME = 'CampReal1'                              # <= 15 characters, no underscore (skudef rule)
c4.NAME = c2.NAME = NAME
c2.SRC_DIR = os.path.join(c2.SDK, 'Mods', NAME, 'data')
c2.BUILT = os.path.join(c2.SDK, 'BuiltMods', 'mods', NAME.lower(), 'data')
c2.OUT = c4.OUT = os.path.join(os.path.expanduser('~'), 'Documents', 'Red Alert 3', 'Mods', NAME)
c7.MAP_MOD = NAME + 'Map'
PLACE = os.environ.get('CNV_REAL', 'goldengate')
c18.START = (3300.0, 1500.0)                    # the city (Presidio / Marina side), on land
c18.ENEMY = (800.0, 4500.0)                     # the Marin hills (west of the bridge head, on land)
c4.c3.STRINGS.update({c18.CAPTION: 'CNV 实景测试：地形、水域和道路取自真实地理数据（金门海峡）。',
                      'MISSIONOBJ:CNV02_1': '实景测试目标：消灭北岸山地的苏军坦克',
                      'MISSIONOBJ:CNV02_1_DESC': '地形来自公开高程数据，道路与城区来自 OpenStreetMap。'})

_real = realmap.Real(PLACE)
_cache = {}


def heights(hm, **_):
    _cache['h'] = _real.heights(hm)
    return _cache['h']


def paint(m, hm, tiles, seed=11):
    """newmap.paint_terrain's painting and blending, with realmap's textures instead of newmap.texture_for."""
    grid = _real.textures(hm, {(i, j): hm.get(i, j) for j in range(hm.height) for i in range(hm.width)})
    for (i, j), t in grid.items():
        tiles.set_bit(0, i, j, t == 'Rock_Yucatan01')
    return newmap.paint_grid(tiles, grid)


newmap.island_heights = heights
newmap.paint_terrain = paint

def game_running():            # make_campnew23's check (importing it would re-point the build at CampNew23)
    import subprocess
    out = subprocess.run(['tasklist'], capture_output=True, text=True, errors='replace').stdout.lower()
    return 'ra3_1.' in out or 'ra3.exe' in out or 'ra3ep1' in out      # Uprising too


if __name__ == '__main__':
    if game_running():
        c2.OUT = c4.OUT = os.path.join(os.path.dirname(os.path.dirname(HERE)), 'work', 'staging', NAME)
        print('RA3 is running -> staging at', c4.OUT)
    c4.main()
