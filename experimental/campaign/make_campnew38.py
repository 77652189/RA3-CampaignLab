"""盟军招牌「自由号」空天航母机制验证 (CampNew38), slice 1: a slow hovering capital ship that launches drone bombers.

Design (docs/story/units.md 5.2): a huge hovering carrier; its deck launches drone bombers; its 超时空甲板 sends a
group of nearby ground units to any point in view every few minutes (slice 2); it flies slowly and fears anti-air;
the chrono deck runs on a power station (A7: the station dies, the deck goes dark). Story: FutureTech gives it to the
Allies, the hawk commander takes it in A7 (the player's boss), the player takes it back in A8.

Stand-in: a copy of the Kirov (retail: a slow hovering airship whose weapon slot works) with its bomb bay replaced by
CNV_LibertyDrones: the aircraft carrier's drone weapon (OCL_AlliedAttackDrones, 5 drones a clip, 10 s reload) at
range 600 instead of 1000; the turret's CheckVisionRange off (it would not launch beyond its own sight).
First tried on the SDK SampleMod's Harbinger gunship (CampNew16's): the copy flew to its target and never fired,
with the drones or with its own autocannon (bench 2026-10-21, _013526 / _013753), so the Kirov.
The catch on both: vision. The Kirov sees 150 and would neither launch nor close in on a Hammer 450 away (CampNew35's
lesson again; CheckVisionRange off did not help). At vision 650 (_020052): drones out from 6 s, the middle Hammer
dies at ~13 s, a second by 25 s; the carrier stays put. Open: the drones do not go home -- they gather in a line
beside the carrier (a dozen by 25 s).

Scene: our carrier south, three enemy Hammers 450 north. Bench: box-select the carrier, right-click a Hammer.

  python -I -X utf8 experimental/campaign/make_campnew38.py            -> Documents\\Red Alert 3\\Mods\\CampNew38
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
NAME = 'CampNew38'
c4.NAME = c2.NAME = NAME
c2.SRC_DIR = os.path.join(c2.SDK, 'Mods', NAME, 'data')
c2.BUILT = os.path.join(c2.SDK, 'BuiltMods', 'mods', NAME.lower(), 'data')
c2.OUT = c4.OUT = os.path.join(os.path.expanduser('~'), 'Documents', 'Red Alert 3', 'Mods', NAME)
c7.MAP_MOD = NAME + 'Map'

SAGE = os.path.join(c2.SDK, 'SageXML', 'Soviet', 'Units')
UNIT = 'CNV_LibertyProbe'
c7.EXTRA_TEMPLATES[UNIT] = {'file': f'DATA:CNVUnits/Data/{UNIT}.xml', 'EditorSorting': 'UNIT'}
c7.EXTRA_OWN += [b'WeaponTemplate:CNV_LibertyDrones']
DRONE_RANGE = 600


def sub1(x, old, new):
    assert x.count(old) == 1, (old[:60], x.count(old))
    return x.replace(old, new, 1)


def drone_weapon():
    """The Kirov's bomb weapon (fires from this host) with range 600, a 5-shot clip every 10 s and the aircraft
    carrier's drone OCL instead of the bomb. The carrier's own drone weapon was tried first: no launch either -- the
    cause was the Kirov's 150 vision (unit_xml), not the weapon."""
    w = open(os.path.join(c2.SDK, 'SageXML', 'GlobalData', 'Weapon.xml'), encoding='utf-8').read()
    m = re.search(r'\t*<WeaponTemplate\s+id="SovietBomberAircraftBombWeapon".*?</WeaponTemplate>\n', w, re.S)
    x = m.group(0).replace('id="SovietBomberAircraftBombWeapon"', 'id="CNV_LibertyDrones"')
    x = sub1(x, 'AttackRange="5.0"', f'AttackRange="{DRONE_RANGE}.0"')
    x = sub1(x, 'ClipSize="1"', 'ClipSize="5"\n\t\tAutoReloadsClip="AUTO"')
    x = sub1(x, 'MinSeconds="0.8s"\n\t\t\tMaxSeconds="1.0s"', 'MinSeconds="10.0s"\n\t\t\tMaxSeconds="10.0s"')
    x = sub1(x, 'MinSeconds=".1s"\n\t\t\tMaxSeconds=".1s"', 'MinSeconds="0.5s"\n\t\t\tMaxSeconds="0.5s"')
    x, n = re.subn(r'<ProjectileNugget.*?</ProjectileNugget>', '<WeaponOCLNugget WeaponOCL="OCL_AlliedAttackDrones"/>',
                   x, flags=re.S)
    assert n == 1
    return x


def unit_xml():
    x = open(os.path.join(SAGE, 'SovietBomberAircraft.xml'), encoding='utf-8').read()
    x = sub1(x, 'id="SovietBomberAircraft"', f'id="{UNIT}"')
    x = sub1(x, 'EditorName="SovietBomberAircraft"', f'EditorName="{UNIT}"')
    if os.environ.get('CNV_LIB_WEAPON') != 'kirov':      # the control: the Kirov's own bombs, same clicks
        x = sub1(x, 'Template="SovietBomberAircraftBombWeapon"', 'Template="CNV_LibertyDrones"')
    # the Kirov sees 150 (it bombs what is under it): nothing fired at 450 until it could see that far -- CampNew35's
    # lesson (CheckVisionRange off did not help)
    x = sub1(x, 'VisionRange="150"', 'VisionRange="650"')
    assert x.count('CheckVisionRange="true"') == 2           # the turret's and the AI's target choosers
    x = x.replace('CheckVisionRange="true"', 'CheckVisionRange="false"')
    x = sub1(x, '</AssetDeclaration>', drone_weapon() + '</AssetDeclaration>')
    with open(os.path.join(c26.DATA, UNIT + '.xml'), 'w', encoding='utf-8', newline='\r\n') as f:
        f.write(x.replace('\r\n', '\n'))


A = c28.A
SCENE = [(UNIT, (A[0], A[1] - 60), True)]
SCENE += [('SovietAntiVehicleVehicleTech1', (A[0] + dx, A[1] + 390), False) for dx in (-80, 0, 80)]

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
    print('CNV38: removed', len(gone), 'units;', len(SCENE), 'placed')


c6.edit = generate

if __name__ == '__main__':
    if c23.game_running():
        c2.OUT = c4.OUT = os.path.join(os.path.dirname(os.path.dirname(HERE)), 'work', 'staging', NAME)
        print('RA3 is running -> staging at', c4.OUT)
    c4.main()
