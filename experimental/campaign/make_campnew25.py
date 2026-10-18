"""Light tank v1 and v2 side by side (CampNew25): v1 = CampNew23's CNV_LightTank / CNTankL, v2 = CNV_LightTank2 /
CNTankB from experimental/units/cnv_lighttank2.py (modelled after the AI concept; work/units/lighttank2), v2 just
south of v1, on CampNew24's layout and builder.

  python -I -X utf8 experimental/campaign/make_campnew25.py   -> Documents\\Red Alert 3\\Mods\\CampNew25
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(os.path.dirname(HERE), 'units'))
import make_campnew24 as c24                    # noqa: E402

c23, c7, c4, c2 = c24.c23, c24.c7, c24.c4, c24.c2
NAME = 'CampNew25'
c4.NAME = c2.NAME = NAME
c2.SRC_DIR = os.path.join(c2.SDK, 'Mods', NAME, 'data')
c2.BUILT = os.path.join(c2.SDK, 'BuiltMods', 'mods', NAME.lower(), 'data')
c2.OUT = c4.OUT = os.path.join(os.path.expanduser('~'), 'Documents', 'Red Alert 3', 'Mods', NAME)
c7.MAP_MOD = NAME + 'Map'
del c7.EXTRA_TEMPLATES[c24.AI_UNIT]
c24.AI_UNIT, c24.AI_MODEL = 'CNV_LightTank2', 'CNTankB'
# 游隼's model: v3 (experimental/units/cnv_lighttank3.py, rebuilt after the second concept) unless CNV_TANK=2
TANK = os.environ.get('CNV_TANK', '3')
c24.AI_SRC = os.path.join(os.path.dirname(os.path.dirname(HERE)), 'work', 'units', f'lighttank{TANK}')
c7.EXTRA_TEMPLATES[c24.AI_UNIT] = {'file': 'DATA:CNVUnits/Data/' + c24.AI_UNIT + '.xml', 'EditorSorting': 'UNIT'}
c4.c3.STRINGS['Name:' + c24.AI_UNIT] = 'CNV 轻型坦克 v2'
c24.AI_PARTS = dict(c23.PARTS)                  # HULL, TREADS, TURRET, BARREL like v1
c24.AI_PARTS.update(HULL_D='BODY', TURRET_D='Bone_Turret')                                # detail meshes
if TANK == '2':
    c24.AI_PARTS['BARREL_D'] = 'Bone_Turret_Pitch'
# zoomed next to a retail Guardian (CNV_CLOSEUP), 游隼 at v1's scale covered 1.6x its screen area and read 50 %
# brighter (mean 120 vs 78): a light tank smaller than the main battle tank, a darker diffuse
c24.AI_SCALE = c23.SCALE * 0.8
c24.AI_LEVEL = 50
c24.AI_RETAIL_MAPS = os.environ.get('CNV_RETAIL_MAPS', '1') == '1'
# TURRET_AT / PITCH_AT / MUZZLE_AT of cnv_lighttank2.py / cnv_lighttank3.py, and the sensor lens (FX_Laser)
T, P, M, LENS = {'2': ((1.5, 0.0, 9.6), (6.0, 0.0, 1.7), (24.2, 0.0, 0.0), (0.1, -2.4, 4.4)),
                 '3': ((0.5, 0.0, 8.6), (8.4, 0.0, 2.1), (17.6, 0.0, 0.0), (-10.4, -8.3, 3.4))}[TANK]
c24.ai_pivots = lambda: [
    ('BODY', None, (0, 0, 0)),
    ('Bone_Turret', None, T), ('Bone_Turret_Pitch', 'Bone_Turret', P),
    ('BONE_GUN_MUZZLE', 'Bone_Turret_Pitch', M), ('FXBone_Muzzle', 'Bone_Turret_Pitch', (M[0] + 0.7, 0, 0)),
    ('FX_Laser', 'Bone_Turret', LENS), ('FX_Damage01', None, (-10, 0, 10)),
    ('FXTracksL', None, (-17, 10.0, 0)), ('FXTracksR', None, (-17, -10.0, 0))] + \
    [(f'Bone_{kind}_{fr}_{side}', None, (9 if fr == 'Front' else -9, 10.0 if side == 'Left' else -10.0, 2.4))
     for kind in ('Tread', 'Tracks') for fr in ('Front', 'Rear') for side in ('Left', 'Right')]

# CNV_CLOSEUP=1: both tanks side by side at the screen centre of the start camera (testbench/calib.py), the Soviet
# tank far away, for zoomed-in looks (run_bench.ps1 -Actions wheel); the start camera zooms towards the centre
if os.environ.get('CNV_CLOSEUP') == '1':
    c23.TANK_AT = (1222.0, 2470.0)
    c24.AI_AT = (1222.0, 2425.0)
    c23.ENEMY_AT = (c23.TANK_AT[0] + 1500, c23.TANK_AT[1])
    _gen = c24.c6.edit

    def _with_guardian(m):                      # a retail Guardian just south, as the look to match
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
