"""Retail scrambler consumer, prediction before bench.

base/high: retail Nuggets with/without SpecialPowerNugget. order/removed:
remove AttributeModifierNugget, retain/drop SpecialPowerNugget. Unedited
retail filters, power module (including TriggerFX=None) and retail modifier.
Finite immobile V4 shells, idle acquisition disabled, 10 UNRES marker,
victim 100 UNRES single shots; synthetic victim directional scalars100%,
sink faces the victim so all damage uses100%.
Caster 250 away, victim range0..150; sink100 east, initially UNATTACKABLE.
Release victim NO_ATTACK at5s, mark6s, expose/order sink6.5s without clearing
victim NO_ATTACK (would confound the modifier). Stop6.5+4/15; rearm9s.
1s NO_ATTACK predicts sink early100/100/90/90, late90/90/80/80;
victim99% throughout, all three alive. Packed aliveCount*1e8 +
victimHP*10000 + earlySinkHP*100 + lateSinkHP. No exact expiry phase,
repeated beams, naval toggling or general filter boundary claim.
MEASURED 2026-11-11: fixed-static CampSPNScrA_mcp_1111_021038,
135.2s FAIL. All four victims99%, all three bodies alive. Unjammed
order/removed sink reaches90 earlier; base/high reaches90 later, before
the8s snapshot; final sink80 in all four lanes, packed300999080.
Thus AttributeModifier delays fire independently of SPN, but the final HP
cannot discriminate it. Expiry clearing a script-added NO_ATTACK versus
queued attack resumption is unresolved. Predictions below intentionally
remain diagnostic FAIL; do not register this check as a passing replay.
Earlier runs had minimum-range/geometry and possible idle-pursuit confounders;
evidence and hypothesis table live in the private C handoff.
"""
import re
from pathlib import Path
from checks.engine_spn import CASES
from checks.engine_weaponfx import gun
from checks.engine_missile import SAGE, target
from maps import probe_range
from parts import Mission, Script, Test

VALUES = (301000090, 301000090, 300999080, 300999080)
POWER = 'SpecialPower_WeaponScrambler'


def retail_parts():
    root = Path(SAGE)
    xml = re.sub(r'<!--.*?-->', '', (root/'Allied/Units/AlliedAntiAirShip.xml').read_text(encoding='utf-8'), flags=re.S)
    module = re.search(r'<SpecialPower\s+id="ModuleTag_WeaponScrambler".*?/>', xml, re.S).group()
    xml = (root/'GlobalData/Weapon.xml').read_text(encoding='utf-8')
    weapon = re.search(r'<WeaponTemplate\s+id="AlliedAntiAirShipWeaponScrambler".*?</WeaponTemplate>', xml, re.S).group()
    nuggets = re.search(r'<Nuggets>(.*?)</Nuggets>', weapon, re.S).group(1)
    return module, re.sub(r'<!--.*?-->', '', nuggets, flags=re.S)


def mission():
    m = Mission(name='CampSPNScr', map=probe_range, units=[], facts={})
    module, nuggets = retail_parts()
    for lane in CASES:
        extra = nuggets
        if lane in ('high', 'removed'):
            extra = re.sub(r'<SpecialPowerNugget\b.*?</SpecialPowerNugget>', '', extra, flags=re.S)
        if lane in ('order', 'removed'):
            extra = re.sub(r'<AttributeModifierNugget\b.*?</AttributeModifierNugget>', '', extra, flags=re.S)
        caster = gun('CNV_Scr'+lane.title(), 10, extra)
        caster.xml = caster.xml.replace('DamageType="EXPLOSIVE"', 'DamageType="UNRESISTABLE"')
        caster.xml = caster.xml.replace('<Behaviors>', '<Behaviors>'+module, 1)
        caster.link.append('SpecialPowerTemplate:'+POWER)
        victim = gun('CNV_ScrVictim'+lane.title(), 100)
        victim.xml = victim.xml.replace('DamageType="EXPLOSIVE"', 'DamageType="UNRESISTABLE"')
        victim.xml, n = re.subn(r'\bAttackRange="[^"]+"', 'AttackRange="150"', victim.xml)
        assert n == 1
        victim.xml, n = re.subn(r'MinimumAttackRange="[^"]+"', 'MinimumAttackRange="0"', victim.xml)
        assert n == 1
        victim.xml, n = re.subn(r'MaxHealth="[^"]+"', 'MaxHealth="1000"', victim.xml)
        assert n == 1
        # Normalize only the synthetic shell's directional armor, not retail nuggets.
        armor = victim.id+'Armor'
        victim.xml = victim.xml.replace('Armor="SovietAntiStructureVehicleArmor"', 'Armor="'+armor+'"')
        victim.xml = victim.xml.replace('</AssetDeclaration>',
            '<ArmorTemplate id="'+armor+'" Default="100" '
            'SideDamageScalar="100" RearDamageScalar="100"/></AssetDeclaration>')
        victim.link.append('ArmorTemplate:'+armor)
        for actor in (caster, victim):
            actor.xml = actor.xml.replace('AutoAcquireEnemiesWhenIdle="YES"', 'AutoAcquireEnemiesWhenIdle="NO"')
        sink = target('CNV_ScrSink'+lane.title(), health=1000)
        m.units.extend((caster, victim, sink))
        for u,x,y,side,role,angle in ((caster,0,0,'p1','caster',1.5708),
                (victim,0,250,'s1','victim',0.), (sink,100,250,'p1','sink',3.14159265)):
            m.put(u.id,lane+' gun',x,y,side=side,angle=angle,name='SCR '+lane+' '+role)
    return m


def check(m):
    t = Test()
    start = [('MAP_REVEAL_ALL_PERM', m.player('p1'))]
    for lane in CASES:
        caster,victim,sink = ['SCR '+lane+' '+r for r in ('caster','victim','sink')]
        start += [('UNIT_CHANGE_OBJECT_STATUS', who, 'NO_ATTACK', 1) for who in (caster,victim,sink)]
        start += [('UNIT_CHANGE_OBJECT_STATUS',who,'IMMOBILE',1) for who in (caster,victim,sink)]
        start += [('UNIT_CHANGE_OBJECT_STATUS',sink,'UNATTACKABLE',1)]
        def event(label,at,actions):
            timer = 'SCR '+lane+' '+label
            start.append(('SET_MILLISECOND_TIMER',timer,float(at)))
            t.scripts.append(Script('Test - '+timer,[('TIMER_EXPIRED',timer)],actions))
        event('release',5,[('UNIT_CHANGE_OBJECT_STATUS',victim,'NO_ATTACK',0)])
        event('mark',6,[('UNIT_CHANGE_OBJECT_STATUS',caster,'NO_ATTACK',0),('NAMED_ATTACK_NAMED',caster,victim)])
        event('mark stop',6+4/15,[('UNIT_CHANGE_OBJECT_STATUS',caster,'NO_ATTACK',1)])
        event('early',6.5,[('UNIT_CHANGE_OBJECT_STATUS',sink,'UNATTACKABLE',0),('NAMED_ATTACK_NAMED',victim,sink)])
        event('early stop',6.5+4/15,[('UNIT_CHANGE_OBJECT_STATUS',victim,'NO_ATTACK',1)])
        early = 'SCR snapshot '+lane
        event('snapshot',8,[('SET_COUNTER',early,0),('SET_UNIT_HEALTH_PERCENTAGE_TO_COUNTER',sink,early)])
        event('late',9,[('UNIT_CHANGE_OBJECT_STATUS',victim,'NO_ATTACK',0),('NAMED_ATTACK_NAMED',victim,sink)])
        event('late stop',9+4/15,[('UNIT_CHANGE_OBJECT_STATUS',victim,'NO_ATTACK',1)])
        c = 'CNV_SCR_'+lane
        t.counters.append((c,lane+' packed'))
        t.scripts.append(Script('Test - pack '+lane,[],[
            ('SET_COUNTER',c,0),('SET_UNIT_HEALTH_PERCENTAGE_TO_COUNTER',victim,c),
            ('COUNTER_MATH_VALUE',c,2,10000),('SET_COUNTER',c+' tmp',0),
            ('COUNTER_MATH_COUNTER',c+' tmp',0,early),('COUNTER_MATH_VALUE',c+' tmp',2,100),
            ('COUNTER_MATH_COUNTER',c,0,c+' tmp'),('SET_COUNTER',c+' hp',0),
            ('SET_UNIT_HEALTH_PERCENTAGE_TO_COUNTER',sink,c+' hp'),('COUNTER_MATH_COUNTER',c,0,c+' hp')],once=False))
        for role,who in (('caster',caster),('victim',victim),('sink',sink)):
            t.scripts.append(Script('Test - alive '+lane+' '+role,[('NAMED_NOT_DESTROYED',who)],
                [('INCREMENT_COUNTER',100000000,c)],once=False))
    t.scripts.insert(0,Script('Test - start',[],start))
    t.expect = [(label,14,'==',value,16) for (_,label),value in zip(t.counters,VALUES)]
    t.bench = [('bench_watch',dict(seconds=16.,every=.5,sheet=False,lines=4))]
    return t


MISSION = {'engine_spnscr': mission}
CHECKS = {'engine_spnscr': {'a': check}}
