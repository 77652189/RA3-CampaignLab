"""SpecialPowerNugget: PREDICT1001099080/1001099075/1001099080/1001099080.

Four 1000HP casters fire one10UNRES marker at a1000HP passive victim6s.
high also dispatches a named power present on the caster. Its SpecialPower
module applies AttributeMod_TargetPainted to SELF (ARMOR150%,1.1s).
The caster takes100EXPLOSIVE from the front at6.5s and9s: control80%,
high75% (150 early,100 late). order omits the matching module; removed
has it but the nugget filters INFANTRY while the target is a VEHICLE.
All four victims99%. Packed=1e9*casterAlive+1e6*victimAlive+
1000*victimHP%+casterHP%; each HP cleared first to prevent stale readings.
This distinguishes real ability execution from an empty notification or
the marker alone. GUESSED dispatch receiver is caster, not victim; no
claim about OCL/disguise/bombing powers, upgrades, radius or projectiles.
Initially empty single clips reload1s; every window ends after4/15s.
MEASURED2026-11-10: all four predicted packed values PASS
(work/logs/c_spn_bench.log,151.6s). high caster85% after early hit,75%
after late hit; other casters90%/80%. Thus execution, caster receiver,
matching module and target filtering are distinguished. The simulator's
old all80% result fails; the direct self-ARMOR dispatch now replays PASS.
Retail combat cache v18 retains the raw power references; unsupported
handlers report gaps instead of inheriting this self-buff behavior.
"""
import re

from maps import probe_range
from parts import Mission, Script, Test
from checks.engine_weaponfx import gun
from checks.engine_missile import target

CASES=('base','high','order','removed')


def mission():
    m=Mission(name='CampSPN',map=probe_range,units=[],facts={})
    for lane in CASES:
        power='CNV_SPNPower'+lane.title()
        filt='<SpecialObjectFilter Rule="ANY" Include="INFANTRY"/>' if lane=='removed' else ''
        nugget=(f'<SpecialPowerNugget SpecialPowerTemplate="{power}">{filt}</SpecialPowerNugget>'
                if lane!='base' else '')
        caster=gun('CNV_SPNCaster'+lane.title(),10,nugget)
        caster.xml=caster.xml.replace('DamageType="EXPLOSIVE"','DamageType="UNRESISTABLE"')
        caster.xml,n=re.subn(r'\bMaxHealth="[^"]+"','MaxHealth="1000"',caster.xml)
        assert n==1
        if lane!='order':
            caster.xml=caster.xml.replace('<Behaviors>', '<Behaviors>'+
                f'<SpecialPower id="ModuleTag_SPN" SpecialPowerTemplate="{power}" '
                'AttributeModifier="AttributeMod_TargetPainted" AttributeModifierAffectsSelf="true"/>',1)
        caster.xml=caster.xml.replace('</AssetDeclaration>',
            f'<SpecialPowerTemplate id="{power}" ReloadTime="0s" TargetType="OBJECT" '
            'MaxCastRange="1000"/></AssetDeclaration>')
        caster.link.append('SpecialPowerTemplate:'+power)
        victim=target('CNV_SPNVictim'+lane.title(),health=1000)
        hitter=gun('CNV_SPNHit'+lane.title(),100)
        m.units.extend((caster,victim,hitter))
        m.put(caster.id,lane+' gun',side='p1',angle=1.5708,name='SPN '+lane+' caster')
        m.put(victim.id,lane+' gun',0,450,side='s1',angle=4.7124,name='SPN '+lane+' victim')
        m.put(hitter.id,lane+' gun',100,450,side='s1',angle=4.7124,name='SPN '+lane+' hitter')
    return m


def check(m):
    t=Test();start=[('MAP_REVEAL_ALL_PERM',m.player('p1'))]
    for lane in CASES:
        caster,victim,hitter=['SPN '+lane+' '+x for x in ('caster','victim','hitter')]
        start.extend(('UNIT_CHANGE_OBJECT_STATUS',v,'NO_ATTACK',1) for v in (caster,victim,hitter))
        for phase,at,who,to in (('mark',6.,caster,victim),('early',6.5,hitter,caster),('late',9.,hitter,caster)):
            timer='SPN '+lane+' '+phase
            start.extend((('SET_MILLISECOND_TIMER',timer,at),('SET_MILLISECOND_TIMER',timer+' stop',at+4/15)))
            t.scripts.extend((Script('Test - '+timer,[('TIMER_EXPIRED',timer)],
                [('UNIT_CHANGE_OBJECT_STATUS',who,'NO_ATTACK',0),('NAMED_ATTACK_NAMED',who,to)]),
                Script('Test - '+timer+' stop',[('TIMER_EXPIRED',timer+' stop')],
                [('UNIT_CHANGE_OBJECT_STATUS',who,'NO_ATTACK',1)])))
        c='CNV_SPN_'+lane;tmp=c+'HP'
        t.counters.append((c,lane+' packed'))
        t.scripts.extend((Script('Test - hp '+lane,[],[
            ('SET_COUNTER',c,0),('SET_COUNTER',tmp,0),
            ('SET_UNIT_HEALTH_PERCENTAGE_TO_COUNTER',caster,c),
            ('SET_UNIT_HEALTH_PERCENTAGE_TO_COUNTER',victim,tmp),('COUNTER_MATH_VALUE',tmp,2,1000),
            ('COUNTER_MATH_COUNTER',c,0,tmp)],once=False),
            Script('Test - caster '+lane,[('NAMED_NOT_DESTROYED',caster)],[('INCREMENT_COUNTER',1000000000,c)],once=False),
            Script('Test - victim '+lane,[('NAMED_NOT_DESTROYED',victim)],[('INCREMENT_COUNTER',1000000,c)],once=False)))
    t.scripts.insert(0,Script('Test - start',[],start))
    t.expect=[(label,14,'==',v,16) for (_,label),v in zip(t.counters,(1001099080,1001099075,1001099080,1001099080))]
    t.bench=[('bench_watch',dict(seconds=16.,every=.5,sheet=False,lines=4))]
    return t


MISSION={'engine_spn':mission}
CHECKS={'engine_spn':{'a':check}}
