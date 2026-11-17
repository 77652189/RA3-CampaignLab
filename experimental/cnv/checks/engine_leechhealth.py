"""New bench PASS1001095045/1001090050/1001090045/1001090040; initial prediction.
Four1000HP casters start40%=400HP; each1000HP target starts full.
base: LeechHealthDamageNugget Damage100 GUN, tank armor50% ->target95%;
GUESSED healing after armor:100% of50 ->caster45%.
high:100UNRESISTABLE bypasses armor ->target90%, heal100 ->caster50%.
order: same UNRESISTABLE, PercentDamageToHeal50% ->caster45%, target90%.
removed: plain100UNRESISTABLE ->caster40%, target90%.
Packed=1e9*targetAlive+1e6*casterAlive+1000*targetHP%+casterHP%.
If healing is before armor, base instead reads1001095050; the other lanes
separate heal percentage from ordinary damage/autoheal. No health cap reached.
Core unfiltered, ungated direct nugget; death/upgrade/beam weapon theft not
asserted. Empty clips load1s; order6s, NO_ATTACK6+4/15; four lines.
"""
import re
from maps import probe_range
from parts import Mission,Script,Test
from checks.engine_weaponfx import gun
from checks.engine_missile import target,TARGET_ID
CASES=(('base','GUN',100),('high','UNRESISTABLE',100),('order','UNRESISTABLE',50),('removed','UNRESISTABLE',None))

def mission():
    m=Mission(name='CampLH',map=probe_range,units=[target(health=1000)],facts={})
    for lane,kind,pct in CASES:
        u=gun('CNV_LHealth'+lane.title(),100)
        u.xml=u.xml.replace('DamageType="EXPLOSIVE"',f'DamageType="{kind}"')
        u.xml,n=re.subn(r'\bMaxHealth="[^"]+"','MaxHealth="1000"',u.xml);assert n==1
        if pct is not None:u.xml=u.xml.replace('<DamageNugget ',f'<LeechHealthDamageNugget PercentDamageToHeal="{pct}%" ')
        m.units.append(u)
        m.put(u.id,lane+' gun',side='p1',angle=1.5708,name='LH '+lane+' gun')
        m.put(TARGET_ID,lane+' gun',0,450,side='s1',angle=4.7124,name='LH '+lane+' target')
    return m

def check(m):
    t=Test();start=[('MAP_REVEAL_ALL_PERM',m.player('p1')),('SET_MILLISECOND_TIMER','LH Fire',6.0),('SET_MILLISECOND_TIMER','LH Stop',6+4/15)]
    fire=[];stop=[]
    for lane,kind,pct in CASES:
        g='LH '+lane+' gun';v='LH '+lane+' target';c='CNV_LH_'+lane;tmp=c+'VictimHP'
        start += [('UNIT_CHANGE_OBJECT_STATUS',name,'NO_ATTACK',1) for name in (g,v)]
        start.append(('UNIT_SET_HEALTH',g,40.0))
        fire += [('UNIT_CHANGE_OBJECT_STATUS',g,'NO_ATTACK',0),('NAMED_ATTACK_NAMED',g,v)]
        stop += [('UNIT_CHANGE_OBJECT_STATUS',g,'NO_ATTACK',1)]
        t.counters.append((c,lane+' packed'))
        t.scripts += [Script('Test - hp '+lane,[],[('SET_COUNTER',c,0),('SET_COUNTER',tmp,0),
            ('SET_UNIT_HEALTH_PERCENTAGE_TO_COUNTER',g,c),('SET_UNIT_HEALTH_PERCENTAGE_TO_COUNTER',v,tmp),
            ('COUNTER_MATH_VALUE',tmp,2,1000),('COUNTER_MATH_COUNTER',c,0,tmp)],once=False),
            Script('Test - caster '+lane,[('NAMED_NOT_DESTROYED',g)],[('INCREMENT_COUNTER',1000000,c)],once=False),
            Script('Test - victim '+lane,[('NAMED_NOT_DESTROYED',v)],[('INCREMENT_COUNTER',1000000000,c)],once=False)]
    t.scripts.insert(0,Script('Test - start',[],start))
    t.scripts.insert(1,Script('Test - fire',[('TIMER_EXPIRED','LH Fire')],fire))
    t.scripts.append(Script('Test - stop',[('TIMER_EXPIRED','LH Stop')],stop))
    t.expect=[(label,14,'==',v,16) for (_,label),v in zip(t.counters,(1001095045,1001090050,1001090045,1001090040))]
    t.bench=[('bench_watch',dict(seconds=16.0,every=.5,sheet=False,lines=4))]
    return t
MISSION={'engine_leechhealth':mission}
CHECKS={'engine_leechhealth':{'a':check}}
