"""SpecificSpecialPowerDelay variants on the successful aimicspon Hunt team: one delay line, nothing else differs
(no team delay, the same update/health/targets; the inherited manual warrior removed, only the automatic window read).

aidelay0 / aidelay999 (bench 2026-11-11): RUSH_ATTACK MaximumDelay 0 / 999, MinimumDelay 0. Prediction before bench:
zero lets both warriors charge together; 999 still lets the first charge, then samples a cooldown in 0..999 s, so
no second charge in the window (a sampled prediction, NOT a deterministic bound).
aidelaytype: the 999 line on PowerType AOE_ATTACK -- the warriors' RUSH_ATTACK is not delayed: predicted as zero.
aidelaymin: MinimumDelay 999, MaximumDelay 0 -- the program's draw (work/re/l4_toggle.md) is its upper end when the
range is empty or reversed, so 0: predicted as zero (a MinimumDelay taken as a floor would give 999).
aidelaytog / aidelaytogdef (TogglePowerSubType): the warriors give way to TOG_PK, a Peacekeeper whose two ToggleStates
both say TOGGLE_ALWAYS -- the program's TOGGLE heuristic then switches every micro round, target or not
(l4_toggle.md) -- built from a copied barracks; the line is TOGGLE 999 s on sub type TOGGLE_ALWAYS / TOGGLE_DEFAULT.
The program keys a TOGGLE cooldown by the hint of the state being switched to and keeps it per micro manager (the
team): predicted aidelaytog one shield up for good after the first switch, aidelaytogdef switching on and off.
"""
import dataclasses

from missions import aimicro_bench as am
from missions import aiskirm_bench as sk
from units import production

TOG_PK, TOG_BARRACKS = 'CNVTogPK', 'CNVTogBarracks'


def toggle_pk():
    pk = sk.new_pk(TOG_PK)
    x = pk.xml
    # MaxHealth x 100: the kept-up conscripts killed them by s41 in the simulator; a death reads as a switch back
    for old, new in [*((h, 'ToggleHint="TOGGLE_ALWAYS"') for h in ('ToggleHint="TOGGLE_DEFAULT"',
                                                                    'ToggleHint="TOGGLE_DEFENSE_SELF_ONLY"')),
                     ('MaxHealth="150.0"', 'MaxHealth="15000.0"')]:
        assert x.count(old) == 1, old
        x = x.replace(old, new)
    return dataclasses.replace(pk, xml=x, what='维和换 id，盾的两个状态都标 TOGGLE_ALWAYS（AI 每轮都切），血 ×100')


def mission(maximum, minimum=0, power='RUSH_ATTACK', name=None, sub=None):
    name = name or ('Long' if maximum else 'Zero')
    toggle = sub is not None
    unit = dict(unit=TOG_PK, factory=TOG_BARRACKS) if toggle else {}
    m = am.built('CampAD' + name, tactic='Hunt', foes=True, spow=True, **unit)
    if toggle:
        pk = toggle_pk()
        m.units += [pk, production.building('AlliedBarracks', [pk.id], TOG_BARRACKS)]
    filename, xml, asset = m.assets[0]
    tag = (f'<SpecificSpecialPowerDelay PowerType="{power}" '
           + (f'TogglePowerSubType="{sub}" ' if toggle else '')
           + f'MinimumDelay="{minimum}s" MaximumDelay="{maximum}s"/>')
    # SDK sequence: TargetBias*, SpecificSpecialPowerDelay*, RetreatBaseCriteria,
    # IgnoreTargets. Appending after IgnoreTargets fails BinaryAssetBuilder.
    anchor = '    <RetreatBaseCriteria'
    assert xml.count(anchor) == 1
    xml = xml.replace(anchor, '    ' + tag + '\n' + anchor)
    assert tag in xml
    m.assets[0] = filename, xml, asset
    m.facts['specific maximum'] = maximum
    # the draw: max when max <= min, else in [min, max]; a TOGGLE line holds only its own sub type
    own = 'TOGGLE' if toggle else 'RUSH_ATTACK'
    m.facts['delayed'] = power == own and sub in (None, 'TOGGLE_ALWAYS') and maximum > 0
    return m


LOCK_RA, LOCK_BARRACKS = 'CNVLockRA', 'CNVLockBarr'
FOES = {'2': 'SovietAntiAirShip', '1': 'SovietAntiAirShip', 'm': 'SovietMiner'}


def lock_ra():
    """The Rocket Angel (SDK Japan/Units/JapanAntiVehicleInfantryTech3.xml) under LOCK_RA: its retail TOGGLE_LOCKDOWN
    states untouched; cost 900 -> 200 (two inside the opener's deposit), MaxHealth x 100 (the Bullfrogs' flak), no
    tech 3 upgrade needed (bench 11-24 first run: with it none was built, game and simulator alike)."""
    import os
    import labpaths
    from parts import Unit
    x = open(os.path.join(labpaths.SDK3, 'SageXML', 'Japan', 'Units', 'JapanAntiVehicleInfantryTech3.xml'),
             encoding='utf-8').read()
    for old, new in [*((f'{k}="JapanAntiVehicleInfantryTech3"', f'{k}="{LOCK_RA}"') for k in ('id', 'EditorName')),
                     ('Amount="900"', 'Amount="200"'), ('MaxHealth="400"', 'MaxHealth="40000"'),
                     # its GameDependency: the Japanese barracks' tech 3, which the copied barracks never gets
                     ('<NeededUpgrade>Upgrade_JapanBarracksTech3</NeededUpgrade>', '')]:
        assert x.count(old) == 1, old
        x = x.replace(old, new)
    return Unit(LOCK_RA, x, what='火箭天使换 id（锁定枪两个状态照原版），造价 200，血 ×100')


def lock(team):
    """ailock2 / ailock1 / ailockm (TOGGLE_LOCKDOWN, work/re/l4_toggle.md hint 9): the aimicspon Hunt team takes
    LOCK_RA; no delay line. 2: two angels, two Bullfrogs (armed, their flak hits the angels) -- predicted one locks,
    never two at once (the switch marks TOGGLE used for the round; a target another locks is skipped). 1: the team
    takes one -- predicted never (a team of one never locks). m: two angels, two unarmed Ore Collectors -- predicted
    never (no enemy can attack)."""
    m = am.built('CampAL' + team, tactic='Hunt', foes=True, spow=True, unit=LOCK_RA, factory=LOCK_BARRACKS,
                 foe=FOES[team])
    ra = lock_ra()
    m.units += [ra, production.building('AlliedBarracks', [ra.id], LOCK_BARRACKS)]
    filename, xml, asset = m.assets[0]
    # the angel walks on AIR (its locomotor's Surfaces): the team template's LAND AMPHIBIOUS never took it
    for old, new in [('AllowedLocomotorTypes="LAND AMPHIBIOUS"', 'AllowedLocomotorTypes="LAND AMPHIBIOUS AIR"'),
                     *([('MinUnits="2" MaxUnits="2"', 'MinUnits="1" MaxUnits="1"')] if team == '1' else [])]:
        assert xml.count(old) == 1, old
        xml = xml.replace(old, new)
    m.assets[0] = filename, xml, asset
    m.facts['delayed'] = team == '2'        # toggled(): 'up once, never two' against 'never up'
    m.facts['lock team'] = 1.0 if team == '1' else 2.0
    return m


MISSION = {'ailock2': lambda: lock('2'), 'ailock1': lambda: lock('1'), 'ailockm': lambda: lock('m'),
           'aidelay0':lambda: mission(0), 'aidelay999': lambda: mission(999),
           'aidelaytype': lambda: mission(999, power='AOE_ATTACK', name='Type'),
           'aidelaymin': lambda: mission(0, minimum=999, name='Min'),
           'aidelaytog': lambda: mission(999, power='TOGGLE', name='Tog', sub='TOGGLE_ALWAYS'),
           'aidelaytogdef': lambda: mission(999, power='TOGGLE', name='TogDef', sub='TOGGLE_DEFAULT')}
