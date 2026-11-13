"""Retail Sudden Transport SPN consumer; prediction before bench.

Native transport/weapon, SPN removed, SpecialDisguiseUpdate removed, and
SPN removed plus scripted DISGUISED positive control. Add only a 10 UNRES
marker to the retail weapon. Passive retail Sickles are vehicle targets.
Release attack at 6s for 0.4s, keep both bodies immobile with rotation.
Packed = casterAlive*1000 + victimAlive*100 + markerSeen*10 + DISGUISED.
PREDICT s12-14: 1111/1110/1110/1111; unpack takes retail 1s.
This tests direct-hit dispatch and the queried bit only. Identity, opacity,
acquisition, retargeting, cancellation and exact unpack timing remain gaps.
The script lane validates the read interface independently of native dispatch.
MEASURED 2026-11-13: s1-4 all1100; s5 1110/1110/1110/1111;
s6-15 1111/1110/1110/1111, PASS (128.5s, one run, retry=0).
See work/re/c_spntrans_report.md; exact unpack timing remains a gap.
"""
import re
from pathlib import Path

from checks.engine_missile import SAGE
from checks.engine_spn import CASES, mission as spn_mission
from parts import Mission, Script, Test, Unit

POWER = 'SpecialPower_JapanLightTransportVehicleDisguise'
VALUES = (1111, 1110, 1110, 1111)


def mission(target_filter=False):
    root = Path(SAGE)
    transport = (root/'Japan/Units/JapanLightTransportVehicle.xml').read_text(encoding='utf-8')
    weapons = (root/'GlobalData/Weapon.xml').read_text(encoding='utf-8')
    weapon = re.search(r'<WeaponTemplate\s+id="JapanLightTransportVehicleDisguiser".*?</WeaponTemplate>', weapons, re.S).group()
    m = Mission(name='CampSPNTrF' if target_filter else 'CampSPNTr',
                map=spn_mission().map, units=[], facts={})
    for lane in CASES:
        uid, wid = 'CNV_SPTr'+lane.title(), 'CNV_SPTrGun'+lane.title()
        xml = transport.replace('id="JapanLightTransportVehicle"', f'id="{uid}"', 1)
        xml = xml.replace('Template="JapanLightTransportVehicleDisguiser"', f'Template="{wid}"')
        w = weapon.replace('id="JapanLightTransportVehicleDisguiser"', f'id="{wid}"', 1)
        if lane in (('order', 'removed') if target_filter else ('high', 'removed')):
            w = re.sub(r'<SpecialPowerNugget\b[^<>]*/>', '', w)
        if lane == 'order' and not target_filter:
            xml = re.sub(r'<SpecialDisguiseUpdate\b[^<>]*/>', '', xml)
        w = w.replace('</Nuggets>', '<DamageNugget Damage="10" DamageType="UNRESISTABLE" DeathType="NORMAL"/></Nuggets>')
        xml = xml.replace('</AssetDeclaration>', w+'</AssetDeclaration>')
        m.units.append(Unit(uid, xml, link=['WeaponTemplate:'+wid]))
        m.put(uid, lane+' gun', side='p1', angle=1.5708, name='SPT '+lane+' caster')
        victim = 'AlliedAntiInfantryInfantry' if target_filter and lane != 'base' else 'SovietAntiInfantryVehicle'
        m.put(victim, lane+' gun', 0, 250, side='s1', angle=4.7124, name='SPT '+lane+' victim')
    return m


def check(m):
    t = Test()
    start = [('MAP_REVEAL_ALL_PERM', m.player('p1')),
             ('SET_MILLISECOND_TIMER', 'SPT fire', 6.),
             ('SET_MILLISECOND_TIMER', 'SPT stop', 6.4)]
    fire, stop = [], []
    for lane in CASES:
        caster, victim = ['SPT '+lane+' '+role for role in ('caster', 'victim')]
        for who in (caster, victim):
            start += [('UNIT_CHANGE_OBJECT_STATUS', who, 'NO_ATTACK', 1),
                      ('UNIT_CHANGE_OBJECT_STATUS', who, 'IMMOBILE_ALLOW_ROTATE', 1)]
        fire += [('UNIT_CHANGE_OBJECT_STATUS', caster, 'NO_ATTACK', 0),
                 ('NAMED_ATTACK_NAMED', caster, victim)]
        stop += [('UNIT_CHANGE_OBJECT_STATUS', caster, 'NO_ATTACK', 1)]
        counter, latch = 'CNV_SPT_'+lane, 'SPT marker '+lane
        t.counters.append((counter, lane+' packed'))
        t.scripts += [Script('Test - marker '+lane, [('UNIT_HEALTH', victim, 0, 100)], [('SET_COUNTER', latch, 10)]),
                      Script('Test - reset '+lane, [], [('SET_COUNTER', counter, 0), ('COUNTER_MATH_COUNTER', counter, 0, latch)], once=False),
                      Script('Test - caster '+lane, [('NAMED_NOT_DESTROYED', caster)], [('INCREMENT_COUNTER', 1000, counter)], once=False),
                      Script('Test - victim '+lane, [('NAMED_NOT_DESTROYED', victim)], [('INCREMENT_COUNTER', 100, counter)], once=False),
                      Script('Test - disguise '+lane, [('UNIT_HAS_MODELCONDITION', caster, 'DISGUISED')], [('INCREMENT_COUNTER', 1, counter)], once=False)]
    # Retail scripts use the generic action with a float duration (S02: 99999.).
    fire += [('UNIT_SET_MODELCONDITION_GENERIC', 'SPT removed caster', 'DISGUISED', 20.)]
    t.scripts.insert(0, Script('Test - start', [], start))
    t.scripts += [Script('Test - fire', [('TIMER_EXPIRED', 'SPT fire')], fire),
                  Script('Test - stop', [('TIMER_EXPIRED', 'SPT stop')], stop)]
    t.expect = [(label, 12, '==', value, 14) for (_, label), value in zip(t.counters, VALUES)]
    t.bench = [('bench_watch', dict(seconds=14., every=.5, sheet=False, lines=4))]
    return t


def filter_mission():
    """Retail VEHICLE filter: Sickle / Peacekeeper / no SPN / scripted bit.

    PREDICT settled 1111/1110/1110/1111, including independent hit markers
    in all four lanes. An unhit infantry lane cannot prove payload filtering.
    MEASURED 2026-11-13: s5 1110/1110/1110/1111, s6-15 as predicted.
    One run PASS, 135.4s, retry=0; work/re/c_spntrans_filter_report.md.
    """
    return mission(target_filter=True)


MISSION = {'engine_spntrans': mission, 'engine_spntrfilter': filter_mission}
CHECKS = {'engine_spntrans': {'a': check}, 'engine_spntrfilter': {'a': check}}
