"""Six native Lift weapons through Yuriko and occupied IFV/turret hosts.

PREDICT ground/air: ever LIFTED +10 alive +100 crew ENCLOSED gives
11/111/111/10. Negative is native Yuriko with only the selected Lift
nugget removed; no substituted damage, filters, module or firing cadence.
Crew enters at2s, attack8s, stop9s, final16s. These latch observations
cover activation only: landing cleanup, full filters and flight stay gaps.
Ground targets are passive100000HP Hammers; air targets native Twinblades.
No scripted lift bits, forced weapon slots or manual upgrades.
MEASURED2026-11-16 ground PASS11/111/111/10; air0/100/100/10:
all three native air targets died without a latched LIFTED bit; deleted
nugget target survived. Preserve the original air hypothesis in t.expect;
replay tests assert the actual air readings, not the rejected hypothesis.
Air crash/death dispatch and landing cleanup remain gaps. Evidence:
work/re/c_liftretail_report.md. No whole-consumer promotion.
"""
import re
from pathlib import Path

from checks.engine_missile import SAGE, target
from maps import probe_range
from model import status
from parts import Mission, Script, Test, Unit

LANES = ('base', 'high', 'order', 'removed')
GROUND = ('JapanCommandoTech1PsyonicCrush',
          'AAAVT1_JapanCommandoTech1PsyonicCrush', 'ABD_JapanCommandoTech1PsyonicCrush')
AIR = ('JapanCommandoTech1AirborneKiller',
       'AAAVT1_JapanCommandoTech1PsyonicAntiAirCrush', 'ABD_JapanCommandoTech1PsyonicAntiAirCrush')
VALUES = (11, 111, 111, 10)


def mission(air=False):
    m = Mission(name='CampLiftAir' if air else 'CampLiftGnd', map=probe_range, units=[], facts={})
    root = Path(SAGE)
    selected = (AIR if air else GROUND)[0]
    native = (root/'Japan/Units/JapanCommandoTech1.xml').read_text(encoding='utf-8')
    weapons = (root/'GlobalData/Weapon.xml').read_text(encoding='utf-8')
    weapon = re.search(r'<WeaponTemplate\s+id="'+selected+r'".*?</WeaponTemplate>', weapons, re.S).group()
    weapon, count = re.subn(r'<ActivateLiftObjectNugget\b.*?</ActivateLiftObjectNugget>', '', weapon, flags=re.S)
    assert count == 1
    weapon = weapon.replace('id="'+selected+'"', 'id="CNV_LiftNegativeWeapon"', 1)
    native = native.replace('id="JapanCommandoTech1"', 'id="CNV_LiftNegative"', 1)
    native = native.replace('Template="'+selected+'"', 'Template="CNV_LiftNegativeWeapon"')
    native = native.replace('</AssetDeclaration>', weapon+'</AssetDeclaration>')
    m.units.append(Unit('CNV_LiftNegative', native, link=['WeaponTemplate:CNV_LiftNegativeWeapon']))
    hosts = ('JapanCommandoTech1', 'AlliedAntiAirVehicleTech1', 'AlliedBaseDefense', 'CNV_LiftNegative')
    for lane, host in zip(LANES, hosts):
        m.put(host, lane+' gun', side='p1', angle=1.5708, name='RetailLift '+lane+' gun')
        if lane in ('high', 'order'):
            m.put('JapanCommandoTech1', lane+' gun', 40, 0, side='p1', name='RetailLift '+lane+' crew')
        if air:
            victim = 'SovietAntiGroundAircraft'
        else:
            unit = target('CNV_RetailLiftVictim'+lane.title(), health=100000)
            m.units.append(unit)
            victim = unit.id
        m.put(victim, lane+' gun', 0, 100, side='s1', angle=4.7124, name='RetailLift '+lane+' victim')
    m.put('AlliedPowerPlant', 'order gun', -200, 0, side='p1', name='RetailLift power')
    return m


def check(m):
    t = Test()
    start = [('MAP_REVEAL_ALL_PERM', m.player('p1'))]
    for phase, seconds in (('Enter', 2.), ('Fire', 8.), ('Stop', 9.), ('Sample', 16.)):
        start.append(('SET_MILLISECOND_TIMER', 'RetailLift '+phase, seconds))
    enter, fire, stop = [], [], []
    for lane in LANES:
        g, v = ['RetailLift '+lane+' '+role for role in ('gun', 'victim')]
        c = 'CNV_RetailLift_'+lane
        t.counters.append((c, lane+' native lift'))
        start += [('UNIT_CHANGE_OBJECT_STATUS', who, 'NO_ATTACK', 1) for who in (g, v)]
        if lane in ('high', 'order'):
            crew = 'RetailLift '+lane+' crew'
            start.append(('UNIT_CHANGE_OBJECT_STATUS', crew, 'NO_ATTACK', 1))
            enter.append(('NAMED_GARRISON_SPECIFIC_BUILDING_INSTANTLY', crew, g))
            t.scripts.append(Script('Test - crew '+lane,
                [('TIMER_EXPIRED', 'RetailLift Sample'), ('UNIT_HAS_OBJECT_STATUS', crew, status('ENCLOSED'))],
                [('INCREMENT_COUNTER', 100, c)]))
        fire += [('UNIT_CHANGE_OBJECT_STATUS', g, 'NO_ATTACK', 0), ('NAMED_ATTACK_NAMED', g, v)]
        stop.append(('UNIT_CHANGE_OBJECT_STATUS', g, 'NO_ATTACK', 1))
        t.scripts += [
            Script('Test - ever lifted '+lane,
                [('NAMED_NOT_DESTROYED', v), ('UNIT_HAS_OBJECT_STATUS', v, status('LIFTED_INTO_AIR'))],
                [('INCREMENT_COUNTER', 1, c)]),
            Script('Test - alive '+lane,
                [('TIMER_EXPIRED', 'RetailLift Sample'), ('NAMED_NOT_DESTROYED', v)],
                [('INCREMENT_COUNTER', 10, c)])]
    t.scripts.insert(0, Script('Test - start', [], start))
    for phase, actions in (('Enter', enter), ('Fire', fire), ('Stop', stop)):
        t.scripts.append(Script('Test - '+phase, [('TIMER_EXPIRED', 'RetailLift '+phase)], actions))
    t.expect = [(label, 17, '==', value, 19) for (_, label), value in zip(t.counters, VALUES)]
    t.bench = [('bench_watch', dict(seconds=19., every=.5, sheet=False, lines=4))]
    return t


MISSION = {'engine_liftground': mission, 'engine_liftair': lambda: mission(air=True)}
CHECKS = {name: {'a': check} for name in MISSION}
