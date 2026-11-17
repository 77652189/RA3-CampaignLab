"""Retail painter consumer: PREDICT 1001084074/1011079069, repeated without SPN.

Four finite single-shot V4 shells carry the unedited retail painter Nuggets
and the two active retail PaintTarget SpecialPower modules. Only order/removed
drop SpecialPowerNugget. base/order casters belong to p1, high/removed to s1;
only s1 receives the retail PLAYER HighTechnology upgrade. No commented beam
handler is installed. A synthetic 10 UNRES marker proves launch in every lane.
At 6s mark a 1000HP Hammer 250 away, then a third party deals 100 EXPLOSIVE
at 6.5 and 9s. Retail AttributeModifierNugget supplies 150/200% damage taken
for 1.1s: early HP84/79, late74/69, independent of SpecialPowerNugget.
Packed: casterAlive*1e9 + victimAlive*1e6 + earlyHP*1000 + currentHP
+ casterUpgradeStatus*1e7. This is a finite retail-consumer slice, not the
guardian toggle/beam renderer or repeated firing/end-point timing.
MEASURED 2026-11-11: CampSPNRetA_mcp_1111_014512, one run PASS, 186.4s.
All packed values match; marker HP99, early84/79/84/79, late74/69/74/69.
Both sides live and the upgraded caster status is set in high/removed.
"""
import re
from pathlib import Path

from checks.engine_spn import CASES
from checks.engine_weaponfx import gun
from checks.engine_missile import SAGE, target
from maps import probe_range
from model import status
from parts import Mission, Script, Test

UPGRADE = 'Upgrade_AlliedHighTechnology'
PAINTER = 'AlliedAntiVehicleVehicleTech1TargetPainter'
VALUES = (1001084074, 1011079069, 1001084074, 1011079069)


def retail_parts():
    root = Path(SAGE)
    xml = re.sub(r'<!--.*?-->', '', (root / 'Allied/Units/AlliedAntiVehicleVehicleTech1.xml').read_text(encoding='utf-8'), flags=re.S)
    modules = re.findall(r'<SpecialPower\s+id="ModuleTag_PaintTarget(?:_HighTechnology)?".*?/>', xml, re.S)
    assert len(modules) == 2
    weapons = (root / 'GlobalData/Weapon.xml').read_text(encoding='utf-8')
    weapon = re.search(r'<WeaponTemplate\s+id="' + PAINTER + r'".*?</WeaponTemplate>', weapons, re.S).group()
    nuggets = re.search(r'<Nuggets>(.*?)</Nuggets>', weapon, re.S).group(1)
    return ''.join(modules), re.sub(r'<!--.*?-->', '', nuggets, flags=re.S)


def mission():
    m = Mission(name='CampSPNRet', map=probe_range, units=[], facts={})
    modules, nuggets = retail_parts()
    for lane in CASES:
        extra = nuggets if lane in ('base', 'high') else re.sub(r'<SpecialPowerNugget\b.*?</SpecialPowerNugget>', '', nuggets, flags=re.S)
        caster = gun('CNV_SPNRet' + lane.title(), 10, extra)
        caster.xml = caster.xml.replace('DamageType="EXPLOSIVE"', 'DamageType="UNRESISTABLE"')
        caster.xml = caster.xml.replace('<Behaviors>', '<Behaviors>' + modules +
            '<StatusBitsUpgrade id="ModuleTag_RetailProof" StatusToSet="WEAPON_UPGRADED_01">'
            f'<TriggeredBy>{UPGRADE}</TriggeredBy></StatusBitsUpgrade>', 1)
        caster.link += ['SpecialPowerTemplate:SpecialPower_PaintTargetTrigger',
                        'SpecialPowerTemplate:SpecialPower_PaintTargetTrigger_HighTechnology']
        victim = target('CNV_SPNRetVictim' + lane.title(), health=1000)
        hitter = gun('CNV_SPNRetHit' + lane.title(), 100)
        m.units.extend((caster, victim, hitter))
        upgraded = lane in ('high', 'removed')
        side, enemy = ('s1', 'p1') if upgraded else ('p1', 's1')
        for u, x, y, owner, role, angle in ((caster, 0, 0, side, 'caster', 1.5708),
                (victim, 0, 250, enemy, 'victim', 4.7124),
                (hitter, 100, 0, side, 'hitter', 1.5708)):
            m.put(u.id, lane + ' gun', x, y, side=owner, angle=angle, name='SPR ' + lane + ' ' + role)
    return m


def check(m):
    t = Test()
    start = [('MAP_REVEAL_ALL_PERM', m.player('p1')),
             ('GIVE_PLAYER_UPGRADE', m.player('s1'), UPGRADE)]
    for lane in CASES:
        caster, victim, hitter = ['SPR ' + lane + ' ' + role for role in ('caster', 'victim', 'hitter')]
        start += [('UNIT_CHANGE_OBJECT_STATUS', who, 'NO_ATTACK', 1) for who in (caster, victim, hitter)]
        for phase, at, who in (('mark', 6., caster), ('early', 6.5, hitter), ('late', 9., hitter)):
            timer = 'SPR ' + lane + ' ' + phase
            start += [('SET_MILLISECOND_TIMER', timer, at), ('SET_MILLISECOND_TIMER', timer + ' stop', at + 4/15)]
            t.scripts += [Script('Test - ' + timer, [('TIMER_EXPIRED', timer)],
                [('UNIT_CHANGE_OBJECT_STATUS', who, 'NO_ATTACK', 0), ('NAMED_ATTACK_NAMED', who, victim)]),
                Script('Test - ' + timer + ' stop', [('TIMER_EXPIRED', timer + ' stop')],
                [('UNIT_CHANGE_OBJECT_STATUS', who, 'NO_ATTACK', 1)])]
        early, counter = 'SPR early ' + lane, 'CNV_SPR_' + lane
        start.append(('SET_MILLISECOND_TIMER', early + ' timer', 8.))
        t.scripts.append(Script('Test - snapshot ' + lane, [('TIMER_EXPIRED', early + ' timer')],
            [('SET_COUNTER', early, 0), ('SET_UNIT_HEALTH_PERCENTAGE_TO_COUNTER', victim, early)]))
        t.counters.append((counter, lane + ' packed'))
        t.scripts += [Script('Test - hp ' + lane, [], [('SET_COUNTER', counter, 0),
            ('SET_UNIT_HEALTH_PERCENTAGE_TO_COUNTER', victim, counter),
            ('SET_COUNTER', counter + ' tmp', 0), ('COUNTER_MATH_COUNTER', counter + ' tmp', 0, early),
            ('COUNTER_MATH_VALUE', counter + ' tmp', 2, 1000),
            ('COUNTER_MATH_COUNTER', counter, 0, counter + ' tmp')], once=False),
            Script('Test - caster ' + lane, [('NAMED_NOT_DESTROYED', caster)], [('INCREMENT_COUNTER', 1000000000, counter)], once=False),
            Script('Test - victim ' + lane, [('NAMED_NOT_DESTROYED', victim)], [('INCREMENT_COUNTER', 1000000, counter)], once=False),
            Script('Test - upgrade ' + lane, [('UNIT_HAS_OBJECT_STATUS', caster, status('WEAPON_UPGRADED_01'))],
                [('INCREMENT_COUNTER', 10000000, counter)], once=False)]
    t.scripts.insert(0, Script('Test - start', [], start))
    t.expect = [(label, 14, '==', value, 16) for (_, label), value in zip(t.counters, VALUES)]
    t.bench = [('bench_watch', dict(seconds=16., every=.5, sheet=False, lines=4))]
    return t


MISSION = {'engine_spnret': mission}
CHECKS = {'engine_spnret': {'a': check}}
