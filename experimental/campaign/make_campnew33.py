"""A small mission for 帝国「鸣神」(CampNew33, CNV04), on CampNew32's unit and overrides.

Player: two 鸣神, six Imperial Warriors (retail, with the 复仇 death module), a Tsunami tank, the Empire war factory
CNV_JWarFactory (鸣神 buildable) and a power plant. Enemy: two named Soviet groups to the north -- three Hammers
(CNV03's first group's place) and two Hammers with a Sickle further north-east (off the start camera). Objective:
destroy them; the win script completes the objective and sets "Mission Won" (as CNV03, make_campnew30.py).
Intended play: deploy 鸣神 behind the warriors, send the warriors in; their deaths in the zone hand 复仇 to the
tanks, then retract (dash) and finish.

  python -I -X utf8 experimental/campaign/make_campnew33.py            -> Documents\\Red Alert 3\\Mods\\CampNew33
"""
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import make_campnew32 as c32                    # noqa: E402

c31, c28, c23 = c32.c31, c32.c28, c32.c23
c18, c7, c6, c4, c2 = c23.c18, c23.c7, c23.c6, c23.c4, c23.c2
newmap = c23.newmap
NAME = 'CampNew33'
c4.NAME = c2.NAME = NAME
c2.SRC_DIR = os.path.join(c2.SDK, 'Mods', NAME, 'data')
c2.BUILT = os.path.join(c2.SDK, 'BuiltMods', 'mods', NAME.lower(), 'data')
c2.OUT = c4.OUT = os.path.join(os.path.expanduser('~'), 'Documents', 'Red Alert 3', 'Mods', NAME)
c7.MAP_MOD = NAME + 'Map'

A = c28.A
PLAYER = [(c32.UNIT, (A[0] - 60, A[1] + 40)), (c32.UNIT, (A[0] + 60, A[1] + 40)),
          ('JapanAntiVehicleVehicleTech1', (A[0], A[1] + 90))] + \
    [('JapanAntiInfantryInfantry', (A[0] - 125 + 50 * k, A[1] + 170)) for k in range(6)]
ENEMY = [('SovietAntiVehicleVehicleTech1', (A[0] + dx, A[1] + 460)) for dx in (-60, 0, 60)] + \
    [('SovietAntiVehicleVehicleTech1', (A[0] + 320 + dx, A[1] + 700)) for dx in (-50, 50)] + \
    [('SovietAntiInfantryVehicle', (A[0] + 320, A[1] + 760))]
NAMES = [f'UNIT - CNV04 Enemy {k + 1}' for k in range(len(ENEMY))]
OBJ = c18.OBJ
c4.c3.STRINGS.update({
    c18.CAPTION: 'CNV04：鸣神展开信号区，帝国武士的牺牲会化作复仇意志。',
    'MISSIONOBJ:CNV02_1': 'CNV04 目标：消灭北方的苏军装甲部队',
    'MISSIONOBJ:CNV02_1_DESC': '鸣神在武士身后展开信号形态；武士在信号区内阵亡，周围帝国单位获得复仇（伤害、速度提升，'
                               '可叠三层，脚下光纹显示层数）。雷鼓每一刻只传一道信号，让武士一个接一个冲锋，别挤成一团被一炮带走。'
                               '收回形态时冲刺。',
    'SCRIPT:CNV04_WIN': 'CNV04：苏军装甲部队已被全歼。',
})

_generate = c6.edit


def generate(m):
    _generate(m)                                 # CampNew32: 鸣神, overrides, Empire factory, its test scene
    objs = next(n for _, n in m.walk() if n.name == 'ObjectsList')
    head = lambda k: k.head[:60]                 # noqa: E731
    p1 = next(k for k in objs.kids if b'CNV_Narukami' in head(k))
    s1 = next(k for k in objs.kids if b'SovietAntiVehicleVehicleTech1' in head(k))
    drop = (b'CNV_Narukami', b'JapanAntiVehicleVehicleTech1', b'JapanAntiInfantryInfantry',
            b'SovietAntiVehicleVehicleTech1', b'SovietAntiInfantryVehicle')
    objs.kids[:] = [k for k in objs.kids if not any(u in head(k) for u in drop)]
    for template, (x, y) in PLAYER:
        pr, flags = newmap.typed_props_of(m, p1)
        objs.kids.append(newmap.object_node(m, pr, flags, template, x, y, angle=math.pi / 2,
                                            uniqueID=f'{template} {len(objs.kids)}'))
    for (template, (x, y)), name in zip(ENEMY, NAMES):
        pr, flags = newmap.typed_props_of(m, s1)
        objs.kids.append(newmap.object_node(m, pr, flags, template, x, y, angle=-math.pi / 2, objectName=name,
                                            uniqueID=f'Enemy {len(objs.kids)}'))
    win = m.new_script('CNV04 - Win', [m.new_content('Condition', 'NAMED_DESTROYED', n) for n in NAMES],
                       [m.new_content('ScriptAction', 'SET_MISSION_OBJECTIVE_STATUS', OBJ, 2),
                        m.new_content('ScriptAction', 'SHOW_MILITARY_CAPTION', 'SCRIPT:CNV04_WIN', 10.0),
                        m.new_content('ScriptAction', 'SET_FLAG', 'Mission Won', 1)])
    psl = next(n for _, n in m.walk() if n.name == 'PlayerScriptsList')
    psl.kids[2].kids.append(win)
    print('CNV04:', len(PLAYER), 'player units,', len(NAMES), 'enemies + win script')


c6.edit = generate

if __name__ == '__main__':
    if c23.game_running():
        c2.OUT = c4.OUT = os.path.join(os.path.dirname(os.path.dirname(HERE)), 'work', 'staging', NAME)
        print('RA3 is running -> staging at', c4.OUT)
    c4.main()
