"""Retail spy SPN consumer: prediction before bench.

DISGUISED is an SDK ModelState, not ObjectStatus. Four lanes keep the native
spy weapon/host, remove only SPN, remove only SpecialDisguiseUpdate, or remove
SPN and set the model condition by script as a query positive control.
All weapons add a 10 UNRES marker, latched on target HP below 100 percent.
At 6s release the spy's attack for 0.4s; targets are passive retail conscripts.
Packed = casterAlive*1000 + victimAlive*100 + markerSeen*10 + DISGUISED.
PREDICT final 1111/1110/1110/1111. The last bit is queried, never assumed from
KindOf or a damage marker. Script control validates only the read interface.
This measures dispatch/model condition only, not enemy acquisition or stealth.
MEASURED corrected marker: s1-4 1100/1100/1100/1100; s5-15
1111/1110/1110/1111, PASS. The first game used an inverted HP comparator:
its disguise bit was valid but its prelatched marker was not hit evidence.
The simulator replays the direct-hit DISGUISED bit and script positive control.
Identity/rendering/acquisition/retargeting/cancellation remain explicit gaps;
this is not whole-item coverage.
See work/re/c_spndisguise_report.md and c_spndisguise_measured.json.
"""
import re
from pathlib import Path

from checks.engine_missile import SAGE
from checks.engine_spn import CASES, mission as spn_mission
from parts import Mission, Script, Test, Unit

POWER = 'SpecialPower_InfantryDisguise'
VALUES = (1111, 1110, 1110, 1111)


def mission(cross_kind=False):
    root = Path(SAGE)
    spy = (root/'Allied/Units/AlliedInfiltrationInfantry.xml').read_text(encoding='utf-8')
    weapons = (root/'GlobalData/Weapon.xml').read_text(encoding='utf-8')
    weapon = re.search(r'<WeaponTemplate\s+id="AlliedInfiltrationInfantryDisguiser".*?</WeaponTemplate>', weapons, re.S).group()
    m = Mission(name='CampSPNSpyX' if cross_kind else 'CampSPNSpy', map=spn_mission().map, units=[], facts={})
    for lane in CASES:
        uid, wid = 'CNV_SPSpy'+lane.title(), 'CNV_SPSpyGun'+lane.title()
        xml = spy.replace('id="AlliedInfiltrationInfantry"', f'id="{uid}"', 1)
        xml = xml.replace('Template="AlliedInfiltrationInfantryDisguiser"', f'Template="{wid}"')
        w = weapon.replace('id="AlliedInfiltrationInfantryDisguiser"', f'id="{wid}"', 1)
        if lane in (('order', 'removed') if cross_kind else ('high', 'removed')):
            w = re.sub(r'<SpecialPowerNugget\b[^<>]*/>', '', w)
        if lane == 'order' and not cross_kind:
            xml = re.sub(r'<SpecialDisguiseUpdate\b[^<>]*/>', '', xml)
        w = w.replace('</Nuggets>', '<DamageNugget Damage="10" DamageType="UNRESISTABLE" DeathType="NORMAL"/></Nuggets>')
        xml = xml.replace('</AssetDeclaration>', w+'</AssetDeclaration>')
        m.units.append(Unit(uid, xml, link=['WeaponTemplate:'+wid]))
        m.put(uid, lane+' gun', side='p1', angle=1.5708, name='SPD '+lane+' caster')
        victim = 'SovietAntiInfantryVehicle' if cross_kind and lane != 'base' else 'SovietAntiInfantryInfantry'
        m.put(victim, lane+' gun', 0, 250, side='s1', angle=4.7124, name='SPD '+lane+' victim')
    return m


def check(m):
    t = Test()
    start = [('MAP_REVEAL_ALL_PERM', m.player('p1')),
             ('SET_MILLISECOND_TIMER', 'SPD fire', 6.),
             ('SET_MILLISECOND_TIMER', 'SPD stop', 6.4)]
    fire, stop = [], []
    for lane in CASES:
        caster, victim = ['SPD '+lane+' '+role for role in ('caster', 'victim')]
        for who in (caster, victim):
            start += [('UNIT_CHANGE_OBJECT_STATUS', who, 'NO_ATTACK', 1),
                      ('UNIT_CHANGE_OBJECT_STATUS', who, 'IMMOBILE_ALLOW_ROTATE', 1)]
        fire += [('UNIT_CHANGE_OBJECT_STATUS', caster, 'NO_ATTACK', 0),
                 ('NAMED_ATTACK_NAMED', caster, victim)]
        stop += [('UNIT_CHANGE_OBJECT_STATUS', caster, 'NO_ATTACK', 1)]
        counter, latch = 'CNV_SPD_'+lane, 'SPD marker '+lane
        t.counters.append((counter, lane+' packed'))
        t.scripts += [Script('Test - marker '+lane, [('UNIT_HEALTH', victim, 0, 100)], [('SET_COUNTER', latch, 10)]),
                      Script('Test - reset '+lane, [], [('SET_COUNTER', counter, 0), ('COUNTER_MATH_COUNTER', counter, 0, latch)], once=False),
                      Script('Test - caster '+lane, [('NAMED_NOT_DESTROYED', caster)], [('INCREMENT_COUNTER', 1000, counter)], once=False),
                      Script('Test - victim '+lane, [('NAMED_NOT_DESTROYED', victim)], [('INCREMENT_COUNTER', 100, counter)], once=False),
                      Script('Test - disguise '+lane, [('UNIT_HAS_MODELCONDITION', caster, 'DISGUISED')], [('INCREMENT_COUNTER', 1, counter)], once=False)]
    # Retail scripts use the generic action with a float duration (S02: 99999.).
    fire += [('UNIT_SET_MODELCONDITION_GENERIC', 'SPD removed caster', 'DISGUISED', 20.)]
    t.scripts.insert(0, Script('Test - start', [], start))
    t.scripts += [Script('Test - fire', [('TIMER_EXPIRED', 'SPD fire')], fire),
                  Script('Test - stop', [('TIMER_EXPIRED', 'SPD stop')], stop)]
    t.expect = [(label, 12, '==', value, 14) for (_, label), value in zip(t.counters, VALUES)]
    t.bench = [('bench_watch', dict(seconds=14., every=.5, sheet=False, lines=4))]
    return t


def cross_kind_mission():
    """Native spy INFANTRY filter: corrected prediction 1111/1110/1110/1111.

    Conscripts / Sickle / Sickle without SPN / scripted Sickle control.
    SpecialPower_InfantryDisguise declares Include=INFANTRY; the filter
    belongs to the power template, not the weapon or update module.
    Initial incomplete-data prediction wrongly allowed vehicles; see
    work/re/c_spnspyx_report.md for chronology and independent readings.
    Every lane must independently register a hit before it is evidence.
    Only DISGUISED is measured; identity and acquisition remain gaps.
    MEASURED 2026-11-13: one run, retry=0, PASS in 132.3s; s1-4 all1100,
    s5-15 1111/1110/1110/1111. All four hit markers latched independently.
    SovietScoutVehicle exclusion remains unmeasured.
    """
    return mission(cross_kind=True)


def cross_kind_check(m):
    t = check(m)
    t.expect = [(label, 12, '==', value, 14) for (_, label), value in
                zip(t.counters, (1111, 1110, 1110, 1111))]
    return t


MISSION = {'engine_spndisguise': mission, 'engine_spnspyx': cross_kind_mission}
CHECKS = {'engine_spndisguise': {'a': check}, 'engine_spnspyx': {'a': cross_kind_check}}
