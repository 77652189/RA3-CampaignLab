"""A small mission for the Cryocopter / shrink-ray vehicle / 游隼 combo (CampNew30), on CampNew29's units.

Player: two 游隼, the shrink-ray vehicle, a Cryocopter, the CNV War Factory and a power plant (build more).
Enemy: six named Hammers in two groups to the north. Objective: destroy them; a script marks it completed when
all six are destroyed, then sets the flag "Mission Won" to 1: that ends the mission (A03: a script on TIMER - Mission
Won does SET_FLAG("Mission Won", 1); completing every objective alone did not end it on the bench).

  python -I -X utf8 experimental/campaign/make_campnew30.py            -> Documents\\Red Alert 3\\Mods\\CampNew30
  CNV_EASY=1: one Hammer only, near the player, to check the objective and the end of the mission on the bench
"""
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import make_campnew29 as c29                    # noqa: E402

c28, c23 = c29.c28, c29.c23
c18, c7, c6, c4, c2 = c23.c18, c23.c7, c23.c6, c23.c4, c23.c2
newmap = c23.newmap
NAME = 'CampNew30'
c4.NAME = c2.NAME = NAME
c2.SRC_DIR = os.path.join(c2.SDK, 'Mods', NAME, 'data')
c2.BUILT = os.path.join(c2.SDK, 'BuiltMods', 'mods', NAME.lower(), 'data')
c2.OUT = c4.OUT = os.path.join(os.path.expanduser('~'), 'Documents', 'Red Alert 3', 'Mods', NAME)
c7.MAP_MOD = NAME + 'Map'

EASY = os.environ.get('CNV_EASY') == '1'
A = c28.A
GROUPS = [[(A[0] + dx, A[1] + 460) for dx in (-60, 0, 60)],
          [(A[0] + 320 + dx, A[1] + 700) for dx in (-60, 0, 60)]]
HAMMERS = [(A[0], A[1] + 230)] if EASY else [p for g in GROUPS for p in g]
NAMES = [f'UNIT - CNV03 Hammer {k + 1}' for k in range(len(HAMMERS))]
OBJ = c18.OBJ                                   # CampNew18's objective entry, retitled
c4.c3.STRINGS.update({
    c18.CAPTION: 'CNV03：先用冷冻直升机冰冻、收缩射线车缩小，再让游隼收割。',
    'MISSIONOBJ:CNV02_1': 'CNV03 目标：消灭北方的六辆铁锤坦克',
    'MISSIONOBJ:CNV02_1_DESC': '冷冻直升机冰冻、收缩射线车缩小、游隼高速收割或冲撞碾压。',
    'SCRIPT:CNV03_WIN': 'CNV03：苏军装甲部队已被全歼。',
})

_generate = c6.edit


def generate(m):
    _generate(m)                                 # CampNew29: factory, 游隼 x2, shrink vehicle, Cryocopter, Hammers
    objs = next(n for _, n in m.walk() if n.name == 'ObjectsList')
    head = lambda k: k.head[:60]                 # noqa: E731
    s1 = next(k for k in objs.kids if b'SovietAntiVehicleVehicleTech1' in head(k))
    objs.kids[:] = [k for k in objs.kids if b'SovietAntiVehicleVehicleTech1' not in head(k)]
    for (x, y), name in zip(HAMMERS, NAMES):
        pr, flags = newmap.typed_props_of(m, s1)
        objs.kids.append(newmap.object_node(m, pr, flags, 'SovietAntiVehicleVehicleTech1', x, y, angle=-math.pi / 2,
                                            objectName=name, uniqueID=f'Hammer {len(objs.kids)}'))
    win = m.new_script('CNV03 - Win', [m.new_content('Condition', 'NAMED_DESTROYED', n) for n in NAMES],
                       [m.new_content('ScriptAction', 'SET_MISSION_OBJECTIVE_STATUS', OBJ, 2),
                        m.new_content('ScriptAction', 'SHOW_MILITARY_CAPTION', 'SCRIPT:CNV03_WIN', 10.0),
                        m.new_content('ScriptAction', 'SET_FLAG', 'Mission Won', 1)])
    psl = next(n for _, n in m.walk() if n.name == 'PlayerScriptsList')
    psl.kids[2].kids.append(win)
    print('CNV03:', len(NAMES), 'Hammers', '(easy)' if EASY else '', '+ win script')


c6.edit = generate

if __name__ == '__main__':
    if c23.game_running():
        c2.OUT = c4.OUT = os.path.join(os.path.dirname(os.path.dirname(HERE)), 'work', 'staging', NAME)
        print('RA3 is running -> staging at', c4.OUT)
    c4.main()
