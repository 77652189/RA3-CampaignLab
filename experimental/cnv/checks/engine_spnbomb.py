"""SPN bombing consumer: prediction before bench.

A finite direct marker carries the retail SovietCommandoCallBombingRun SPN.
base keeps the retail OCLSpecialPower and OCLMonitorUpdate; high drops SPN;
order drops the OCL host; removed changes only the nugget filter to INFANTRY.
All casters keep their target order after the 4/15s firing window. A same-owner
retail construction yard provides the secondary location. The unedited retail
ParabolicCurve creates the bomber after 3.5s and approaches for 1.5s; its
99999 EXPLOSIVE bomb should kill the 1000HP target only in base. The other
three targets take the 10 UNRES marker only (99%). Packed = casterAlive*1000
+ victimAlive*100 + victimHP. This isolates dispatch through the original OCL
consumer, not the commando's full laser firing cycle or general OCL geometry.
MEASURED first diagnostic: CampSPNBombA_mcp_1111_201948, 141.7s FAIL.
All four lanes remain 1199 through s17; the marker fires, but the death
prediction is not met. Keep the original prediction as a diagnostic failure.
The marker-only replay in tests is not evidence of working bombing dispatch.
See work/re/c_spnbomb_report.md for the hypotheses and the native-host run.
"""
import re
from pathlib import Path
from checks.engine_spn import CASES
from checks.engine_weaponfx import gun
from checks.engine_missile import SAGE, target
from maps import probe_range
from parts import Mission, Script, Test, Unit

POWER = 'SpecialPowerBombingRun'
VALUES = (1000, 1199, 1199, 1199)


def retail_parts():
    root = Path(SAGE)
    xml = re.sub(r'<!--.*?-->', '', (root/'Soviet/Units/SovietCommandoTech1.xml').read_text(encoding='utf-8'), flags=re.S)
    host = re.search(r'<OCLSpecialPower\s+id="ModuleTag_BombingRun".*?</OCLSpecialPower>', xml, re.S).group()
    monitor = re.search(r'<OCLMonitorUpdate\s+id="ModuleTag_BombingRunMonitor".*?/>', xml, re.S).group()
    xml = re.sub(r'<!--.*?-->', '', (root/'GlobalData/Weapon.xml').read_text(encoding='utf-8'), flags=re.S)
    weapon = re.search(r'<WeaponTemplate\s+id="SovietCommandoCallBombingRun".*?</WeaponTemplate>', xml, re.S).group()
    nugget = re.search(r'<SpecialPowerNugget\b.*?</SpecialPowerNugget>', weapon, re.S).group()
    return host, monitor, nugget


def mission():
    m = Mission(name='CampSPNBomb', map=probe_range, units=[], facts={})
    host, monitor, nugget = retail_parts()
    for lane in CASES:
        extra = '' if lane == 'high' else nugget
        if lane == 'removed':
            extra = re.sub(r'<SpecialObjectFilter\b.*?/>', '<SpecialObjectFilter Rule="ANY" Include="INFANTRY"/>', extra, flags=re.S)
        caster = gun('CNV_SPBomb'+lane.title(), 10, extra)
        caster.xml = caster.xml.replace('DamageType="EXPLOSIVE"', 'DamageType="UNRESISTABLE"')
        if lane != 'order':
            caster.xml = caster.xml.replace('<Behaviors>', '<Behaviors>'+host+monitor, 1)
            caster.link += ['SpecialPowerTemplate:'+POWER, 'ObjectCreationList:OCL_SovietBombingRun']
        victim = target('CNV_SPBombTarget'+lane.title(), health=1000)
        m.units.extend((caster, victim))
        m.put(caster.id, lane+' gun', side='p1', angle=1.5708, name='SPB '+lane+' caster')
        m.put(victim.id, lane+' gun', 0, 250, side='s1', angle=4.7124, name='SPB '+lane+' victim')
    m.put('SovietConstructionYard', 'base gun', -400, -200, side='p1', name='SPB yard')
    m.spawns |= {'Soviet_BombingRun', 'SovietBombingRunBombProjectile'}
    return m


def check(m):
    t = Test()
    start = [('MAP_REVEAL_ALL_PERM', m.player('p1')), ('SET_MILLISECOND_TIMER', 'SPB fire', 6.),
             ('SET_MILLISECOND_TIMER', 'SPB stop', 6.+4/15)]
    fire, stop = [], []
    for lane in CASES:
        caster, victim = ['SPB '+lane+' '+role for role in ('caster', 'victim')]
        start += [('UNIT_CHANGE_OBJECT_STATUS', who, 'NO_ATTACK', 1) for who in (caster, victim)]
        start += [('UNIT_CHANGE_OBJECT_STATUS', who, 'IMMOBILE', 1) for who in (caster, victim)]
        fire += [('UNIT_CHANGE_OBJECT_STATUS', caster, 'NO_ATTACK', 0), ('NAMED_ATTACK_NAMED', caster, victim)]
        stop += [('UNIT_CHANGE_OBJECT_STATUS', caster, 'NO_ATTACK', 1)]
        counter = 'CNV_SPB_'+lane
        t.counters.append((counter, lane+' packed'))
        t.scripts += [Script('Test - hp '+lane, [], [('SET_COUNTER', counter, 0),
            ('SET_UNIT_HEALTH_PERCENTAGE_TO_COUNTER', victim, counter)], once=False),
            Script('Test - caster '+lane, [('NAMED_NOT_DESTROYED', caster)], [('INCREMENT_COUNTER', 1000, counter)], once=False),
            Script('Test - victim '+lane, [('NAMED_NOT_DESTROYED', victim)], [('INCREMENT_COUNTER', 100, counter)], once=False)]
    t.scripts.insert(0, Script('Test - start', [], start))
    t.scripts += [Script('Test - fire', [('TIMER_EXPIRED', 'SPB fire')], fire),
                  Script('Test - stop', [('TIMER_EXPIRED', 'SPB stop')], stop)]
    t.expect = [(label, 14, '==', value, 16) for (_, label), value in zip(t.counters, VALUES)]
    t.bench = [('bench_watch', dict(seconds=16., every=.5, sheet=False, lines=4))]
    return t


def native_mission():
    """Second diagnostic: native vs synthetic hosts, both retain orders to 20s.

    base/high use the original commando and original calling weapon plus a
    10 UNRES marker; high drops SPN. order/removed use the finite gun with
    original OCL host/monitor; removed drops SPN. Latch the marker since the
    native calling weapon repeats. Prediction remains death only with SPN.
    MEASURED CampSPNBombA_mcp_1111_202415, 132.0s: s11..25 reads
    1010/1110/1110/1110. Only the original host kills. Synthetic extended
    host still does not kill: its death prediction remains FAIL. No claim
    about the precise native dispatch frame; see work/re/c_spnbomb_report.md.
    """
    m = mission()
    host, monitor, nugget = retail_parts()
    root = Path(SAGE)
    weapons = (root/'GlobalData/Weapon.xml').read_text(encoding='utf-8')
    weapon = re.search(r'<WeaponTemplate\s+id="SovietCommandoCallBombingRun".*?</WeaponTemplate>', weapons, re.S).group()
    for lane in CASES:
        uid = 'CNV_SPBomb'+lane.title()
        if lane in ('base', 'high'):
            xml = (root/'Soviet/Units/SovietCommandoTech1.xml').read_text(encoding='utf-8')
            xml = xml.replace('id="SovietCommandoTech1"', f'id="{uid}"', 1)
            xml = xml.replace('LOCAL_PILOT_SNIPE_TIMING', uid+'Timing')
            wid = uid+'Call'
            xml = xml.replace('Template="SovietCommandoCallBombingRun"', f'Template="{wid}"')
            w = weapon.replace('id="SovietCommandoCallBombingRun"', f'id="{wid}"', 1)
            if lane == 'high':
                w = re.sub(r'<SpecialPowerNugget\b.*?</SpecialPowerNugget>', '', w, flags=re.S)
            w = w.replace('</Nuggets>', '<DamageNugget Damage="10" DamageType="UNRESISTABLE" DeathType="NORMAL"/></Nuggets>')
            xml = xml.replace('</AssetDeclaration>', w+'</AssetDeclaration>')
            caster = Unit(uid, xml, link=['WeaponTemplate:'+wid])
        else:
            caster = gun(uid, 10, nugget if lane == 'order' else '')
            caster.xml = caster.xml.replace('DamageType="EXPLOSIVE"', 'DamageType="UNRESISTABLE"')
            caster.xml = caster.xml.replace('<Behaviors>', '<Behaviors>'+host+monitor, 1)
            caster.link += ['SpecialPowerTemplate:'+POWER, 'ObjectCreationList:OCL_SovietBombingRun']
        m.units = [caster if u.id == uid else u for u in m.units]
    return m


def native_check(m):
    t = check(m)
    start = t.scripts[0]
    start.do = [(a[0], a[1], 20.) if a[:2] == ('SET_MILLISECOND_TIMER', 'SPB stop') else a for a in start.do]
    start.do = [a for a in start.do if not (a[0] == 'UNIT_CHANGE_OBJECT_STATUS' and a[2] == 'IMMOBILE')]
    start.do += [('UNIT_CHANGE_OBJECT_STATUS', 'SPB '+lane+' '+role, 'IMMOBILE_ALLOW_ROTATE', 1)
                 for lane in CASES for role in ('caster', 'victim')]
    for lane in CASES:
        counter, latch = 'CNV_SPB_'+lane, 'SPB marker '+lane
        hp = next(s for s in t.scripts if s.name == 'Test - hp '+lane)
        hp.do = [('SET_COUNTER', counter, 0), ('COUNTER_MATH_COUNTER', counter, 0, latch)]
        t.scripts.append(Script('Test - marker '+lane, [('UNIT_HEALTH', 'SPB '+lane+' victim', 3, 100)],
                                [('SET_COUNTER', latch, 10)]))
    t.expect = [(label, 22, '==', value, 24) for (_, label), value in zip(t.counters, (1010, 1110, 1010, 1110))]
    t.bench = [('bench_watch', dict(seconds=24., every=.5, sheet=False, lines=4))]
    return t


MISSION = {'engine_spnbomb': mission, 'engine_spnbombnative': native_mission}
CHECKS = {'engine_spnbomb': {'a': check}, 'engine_spnbombnative': {'a': native_check}}
