"""Real Sickle leap: retail ground-hit weapon versus only MetaImpact removed.

Two identical lanes jump 250 north, with enemy infantry 40 east and friendly
infantry 40 west of the landing waypoint. No KindOf or locomotion edits.
Prediction: both land and damage enemies equally; only a shocks enemy infantry.
Friendly infantry must not receive shock. Landing dispatch/time are measured,
not supplied by a V4. Native stunned-state lifecycle remains outside this slice.
c/d repeat NO_ATTACK from 7.4 s to isolate landing health from the machine gun;
the two retail DamageNuggets, armour and KindOf remain identical to a/b.
"""
import os
import re

import labpaths
from maps import probe_range
from model import Mission, Script, Test, Unit, square
from checks.engine_suppress_probe import probe_man, PROBE, EVERY, LINES

STOCK = 'SovietAntiInfantryVehicle'
LAND = STOCK + 'LandWeapon'
UID = 'CNV_SickleLanding'
WEAPON = UID + 'Weapon'
LANES = ('removed', 'switch')


def retail_weapon():
    with open(os.path.join(labpaths.SDK3, 'SageXML', 'GlobalData', 'Weapon.xml'), encoding='utf-8') as f:
        return re.search(r'<WeaponTemplate\s+id="' + LAND + r'".*?</WeaponTemplate>', f.read(), re.S).group(0)


def sickle(without_meta=False):
    with open(os.path.join(labpaths.SDK3, 'SageXML', 'Soviet', 'Units', STOCK + '.xml'), encoding='utf-8') as f:
        xml = f.read()
    xml = xml.replace('id="' + STOCK + '"', 'id="' + UID + '"', 1)
    xml = xml.replace('GroundHitWeapon="' + LAND + '"', 'GroundHitWeapon="' + WEAPON + '"')
    xml = xml.replace('<Behaviors>', '<Behaviors><DeletionUpdate id="ModuleTag_CNVProbe" '
                      f'MinFrames="{EVERY}" MaxFrames="{LINES}"/>', 1)
    weapon = retail_weapon().replace('id="' + LAND + '"', 'id="' + WEAPON + '"', 1)
    if without_meta:
        weapon, n = re.subn(r'<MetaImpactNugget\b.*?</MetaImpactNugget>', '', weapon, flags=re.S)
        assert n == 1
    xml = xml.replace('</AssetDeclaration>', weapon + '</AssetDeclaration>')
    return Unit(UID, xml, names=dict(unit=UID), link=['WeaponTemplate:' + WEAPON],
                what='原版镰刀跳跃落地对照，仅可删除落地武器 MetaImpact', params=dict(of=STOCK))


def name(lane, part):
    return 'Sickle ' + lane + ' ' + part


def mission():
    m = Mission(name='CampKSickle', map=probe_range, units=[sickle(), probe_man()], facts={})
    m.ext = True
    for lane in LANES:
        site = lane + ' gun'
        m.put(UID, site, side='p1', angle=1.5708, name=name(lane, 'gun'))
        m.put(PROBE, site, 40, 250, side='s1', name=name(lane, 'enemy'))
        m.put(PROBE, site, -40, 250, side='p1', name=name(lane, 'friend'))
        m.waypoint(lane, name(lane, 'land'), site, 0, 250)
    return m


def check(m, without_meta=False, hold_fire=False):
    m.units = [sickle(without_meta), probe_man()]
    t = Test()
    start = [('MAP_REVEAL_ALL_PERM', m.player('p1')),
             ('SET_MILLISECOND_TIMER', 'Sickle jump', 6.)]
    if hold_fire:
        # Before the observed f114 landing, and every script pass afterwards.
        # Leap can clear the initial NO_ATTACK; do not alter its retail weapon.
        start.append(('SET_MILLISECOND_TIMER', 'Sickle cease fire', 7.4))
    for lane in LANES:
        start += [('UNIT_CHANGE_OBJECT_STATUS', name(lane, part), 'NO_ATTACK', 1)
                  for part in ('gun', 'enemy', 'friend')]
        x, y = m.site(lane + ' gun')[:2]
        area = name(lane, 'area')
        t.areas[area] = square(x, y + 250, 20)
        hp, land = 'CNV_Sickle_' + lane + '_hp', 'CNV_Sickle_' + lane + '_land'
        t.counters += [(hp, lane + ' hp'), (land, lane + ' land')]
        t.scripts += [Script(name(lane, 'hp'), [], [
            ('SET_UNIT_HEALTH_PERCENTAGE_TO_COUNTER', name(lane, 'enemy'), hp)], once=False),
            Script(name(lane, 'reset'), [], [('SET_COUNTER', land, 0)], once=False),
            Script(name(lane, 'count'), [('NAMED_INSIDE_AREA', name(lane, 'gun'), area)],
                   [('SET_COUNTER', land, 1)], once=False)]
        t.expect += [(lane + ' land', 10, '==', 1, 16)]
        if hold_fire:
            t.expect += [(lane + ' hp', 10, '==', 100, 16)]
    t.scripts.insert(0, Script('Test - start', [], start))
    t.scripts.append(Script('Test - leap', [('TIMER_EXPIRED', 'Sickle jump')], [
        ('NAMED_USE_COMMANDBUTTON_ABILITY_AT_WAYPOINT', name(lane, 'gun'),
         'Command_ActivateLeapSpecialPower', m.mark(lane)) for lane in LANES]))
    if hold_fire:
        t.scripts.append(Script('Test - hold fire', [('TIMER_EXPIRED', 'Sickle cease fire')], [
            ('UNIT_CHANGE_OBJECT_STATUS', name(lane, 'gun'), 'NO_ATTACK', 1)
            for lane in LANES], once=False))
    t.bench = [('bench_watch', dict(seconds=16., every=.5, sheet=False, lines=4))]
    return t


MISSION = {'engine_knock_sickle': mission}
CHECKS = {'engine_knock_sickle': {
    'a': check, 'b': lambda m: check(m, True),
    'c': lambda m: check(m, hold_fire=True),
    'd': lambda m: check(m, True, hold_fire=True)}}
