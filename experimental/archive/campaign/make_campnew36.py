"""苏军「阻塞气球车」机制验证 (CampNew36): a short anti-air "cable" zone that slows and hurts aircraft, no new model yet.

Design (docs/story/units.md, user 2026-10-20): Soviet T1 has no air force and its scouting rests on the Terror Drone. A
cheap truck lets up a tethered balloon: wide vision, and around the cable a zone that catches low aircraft (damage and
slow) -- against Vindicator / Twinblade ore raids. It cannot hit the ground; the zone is smaller than the Apollo's, the
IFV's and the Striker-VX's range, so they can shoot the balloon from outside.

Stand-in (this probe: the zone only; deploying is CampNew35's proven toggle, added later): a copy of the Bullfrog
(its turret already aims up) with the flak gun cut to CNV_BalloonCable (range 150, 10 a shot instead of 15, same
rate), an AttributeModifierAuraUpdate on enemy aircraft within 150 (SPEED 50 %, the frozen shader so the bench sees
who is caught), vision 600.

Scene: a Soviet ore truck with the balloon unit beside it, four of our Vindicators south of it; bench: box-select the
Vindicators, right-click the truck. CNV_NO_BALLOON=1: the truck alone (the control).

Bench (2026-10-21, with an airfield to fly home to): the control's four bomb the truck at ~7 s and all go home; with
the balloon they turn white (slowed) and smoke on the way in, one is shot down, three go home hurt, the truck is still
bombed. A raid costs a Vindicator; it does not stop the drop.
Deploy (CNV_SCENE=deploy): packed it drives up to two hovering Vindicators and holds fire; deployed it fires at once
(one turns white and falls) and ignores a move order. The raid scene's balloon is the enemy's: run it with
CNV_DEPLOY=0.

  python -I -X utf8 experimental/campaign/make_campnew36.py            -> Documents\\Red Alert 3\\Mods\\CampNew36
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
NAME = 'CampNew36'
c4.NAME = c2.NAME = NAME
c2.SRC_DIR = os.path.join(c2.SDK, 'Mods', NAME, 'data')
c2.BUILT = os.path.join(c2.SDK, 'BuiltMods', 'mods', NAME.lower(), 'data')
c2.OUT = c4.OUT = os.path.join(os.path.expanduser('~'), 'Documents', 'Red Alert 3', 'Mods', NAME)
c7.MAP_MOD = NAME + 'Map'

SAGE = os.path.join(c2.SDK, 'SageXML', 'Soviet', 'Units')
UNIT = 'CNV_BalloonProbe'
c7.EXTRA_TEMPLATES[UNIT] = {'file': f'DATA:CNVUnits/Data/{UNIT}.xml', 'EditorSorting': 'UNIT'}
c7.EXTRA_OWN += [b'AttributeModifier:AttributeModifier_CNV_Cable', b'WeaponTemplate:CNV_BalloonCable']

CABLE = int(os.environ.get('CNV_CABLE_RANGE', '150'))
CABLE_DAMAGE = os.environ.get('CNV_CABLE_DAMAGE', '10')
SLOW = os.environ.get('CNV_CABLE_SLOW', '50%')
VISION = os.environ.get('CNV_BALLOON_VISION', '600')
NO_BALLOON = os.environ.get('CNV_NO_BALLOON') == '1'
# 展开 (CNV_DEPLOY=1, default): the Guardian's whole painter toggle (its SpecialPower, command and button) on the
# Bullfrog. Packed: drives, no cable, normal vision. Deployed (GENERIC_TOGGLE_STATE): IMMOBILE, vision x2 (650), the
# cable gun and the slow aura on. CNV_DEPLOY=0: always up, speed 1 (the first probe)
DEPLOY = os.environ.get('CNV_DEPLOY', '1') == '1'
# CNV_SCENE: raid (default: the ore-truck raid, the balloon is the enemy's) | deploy (our balloon truck, two enemy
# Vindicators hovering 165 north: drive up packed -> no fire; deploy -> fire and slow; move order -> stays)
SCENE_KIND = os.environ.get('CNV_SCENE', 'raid')
TOGGLE = '''			<SpecialPower id="ModuleTag_CNV_BalloonTrigger" SpecialPowerTemplate="SpecialPower_ToggleTargetPainter"/>
			<ToggleStatusSpecialAbilityUpdate id="ModuleTag_CNV_BalloonToggle" Options="RECONSTITUTE_STORED_COMMAND"
				SpecialPowerTemplate="SpecialPower_ToggleTargetPainter">
				<ToggleState>
					<SkirmishAiInfo ToggleHint="TOGGLE_DEFAULT"/>
				</ToggleState>
				<ToggleState ObjectStatus="GENERIC_TOGGLE_STATE" AttributeModifier="AttributeModifier_CNV_BalloonUp">
					<SkirmishAiInfo ToggleHint="TOGGLE_DEFAULT"/>
				</ToggleState>
			</ToggleStatusSpecialAbilityUpdate>
'''
DEPLOY_DECL = '''	<AttributeModifier id="AttributeModifier_CNV_BalloonUp" Category="NONE" ObjectStatusToSet="IMMOBILE">
		<Modifier Type="VISION" Value="200%"/>
	</AttributeModifier>
	<LogicCommandSet id="CNV_BalloonCommandSet">
		<Cmd>Command_ToggleTargetPainter</Cmd>
		<Cmd>Command_AttackMove</Cmd>
	</LogicCommandSet>
'''
if DEPLOY:
    c7.EXTRA_OWN += [b'AttributeModifier:AttributeModifier_CNV_BalloonUp', b'LogicCommandSet:CNV_BalloonCommandSet']

DECL = f'''	<AttributeModifier id="AttributeModifier_CNV_Cable" Category="NONE" Duration="1s"
		Shader="ShaderOverride_ObjectsFrozen">
		<Modifier Type="SPEED" Value="{SLOW}"/>
	</AttributeModifier>
'''
AURA = f'''			<AttributeModifierAuraUpdate id="ModuleTag_CNV_CableAura" AttributeModifierName="AttributeModifier_CNV_Cable"
				RefreshDelay="0.5s" Range="{CABLE}" InitiallyActive="true">
				<ObjectFilter Rule="ANY" Relationship="ENEMIES" Include="AIRCRAFT"/>
			</AttributeModifierAuraUpdate>
'''


def sub1(x, old, new):
    assert x.count(old) == 1, (old[:60], x.count(old))
    return x.replace(old, new, 1)


def cable_weapon():
    """The Bullfrog's flak gun under our id: range CABLE, CABLE_DAMAGE a shot."""
    w = open(os.path.join(c2.SDK, 'SageXML', 'GlobalData', 'Weapon.xml'), encoding='utf-8').read()
    m = re.search(r'\t*<WeaponTemplate\s+id="SovietAntiAirShipFlakCannon".*?</WeaponTemplate>\n', w, re.S)
    x = m.group(0).replace('id="SovietAntiAirShipFlakCannon"', 'id="CNV_BalloonCable"')
    x = sub1(x, 'AttackRange="300.0"', f'AttackRange="{CABLE}.0"')
    return sub1(x, 'Damage="15.0"', f'Damage="{CABLE_DAMAGE}.0"')


def unit_xml():
    x = open(os.path.join(SAGE, 'SovietAntiAirShip.xml'), encoding='utf-8').read()
    x = re.sub(r'\s*<GameObject\s+id="SovietAntiAirShip_Ground".*?</GameObject>', '', x, flags=re.S)
    x = sub1(x, 'id="SovietAntiAirShip"', f'id="{UNIT}"')
    x = sub1(x, 'EditorName="SovietAntiAirShip"', f'EditorName="{UNIT}"')
    x = sub1(x, 'Template="SovietAntiAirShipFlakCannon"', 'Template="CNV_BalloonCable"')
    if DEPLOY:
        x = sub1(x, 'Template="CNV_BalloonCable" />', 'Template="CNV_BalloonCable"\n\t\t\t\t\t\tObjectStatus="GENERIC_TOGGLE_STATE" />')
        x = sub1(x, 'CommandSet="SovietAntiAirShipCommandSet"', 'CommandSet="CNV_BalloonCommandSet"')
        x = sub1(x, '</Behaviors>', TOGGLE + AURA.replace('InitiallyActive="true"', 'InitiallyActive="true" '
                                                          'RequiredObjectStatusFlags="GENERIC_TOGGLE_STATE"')
                 + '\t\t</Behaviors>')
    else:
        x = sub1(x, 'VisionRange="325"', f'VisionRange="{VISION}"')
        # a balloon stays put: the first bench run's mobile Bullfrog drove at our parked Vindicators and shot them
        assert x.count('Condition="NORMAL"\n\t\t\tSpeed="100.0"') == 2
        x = x.replace('Condition="NORMAL"\n\t\t\tSpeed="100.0"', 'Condition="NORMAL"\n\t\t\tSpeed="1.0"')
        x = sub1(x, '</Behaviors>', AURA + '\t\t</Behaviors>')
    x = sub1(x, '</AssetDeclaration>', DECL + (DEPLOY_DECL if DEPLOY else '') + cable_weapon() + '</AssetDeclaration>')
    with open(os.path.join(c26.DATA, UNIT + '.xml'), 'w', encoding='utf-8', newline='\r\n') as f:
        f.write(x.replace('\r\n', '\n'))


TRUCK = (1180, 2635)                             # screen ~(558, 229) at the start camera
SCENE = [('SovietMiner', TRUCK, False)]
if not NO_BALLOON:
    SCENE.append((UNIT, (TRUCK[0] + 40, TRUCK[1] - 35), False))
# hovering: drawn around screen y 410, not at their ground point's 586 (box-select there)
SCENE += [('AlliedAntiGroundAircraft', (x, 2335), True) for x in (1105, 1155, 1205, 1255)]
# an airfield to fly home to after the drop, as in a real raid (without one they circled over the truck: first runs)
SCENE.append(('AlliedAirfield', (1180, 2060), True))
if SCENE_KIND == 'deploy':                       # ours: the balloon truck (screen ~(536, 586)); theirs: two Vindicators
    SCENE = [(UNIT, (1180, 2335), True)] + [('AlliedAntiGroundAircraft', (x, 2500), False) for x in (1150, 1210)]

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
    print('CNV36: removed', len(gone), 'units;', len(SCENE), 'placed', '(no balloon)' if NO_BALLOON else '')


c6.edit = generate

if __name__ == '__main__':
    if c23.game_running():
        c2.OUT = c4.OUT = os.path.join(os.path.dirname(os.path.dirname(HERE)), 'work', 'staging', NAME)
        print('RA3 is running -> staging at', c4.OUT)
    c4.main()
