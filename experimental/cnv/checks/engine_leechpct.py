"""New bench PASS1000025/1000025/1000030/1000020; PREDICT before bench.
Four10000HP shooters start20%=2000HP. Three sole, ungated
LeechPercentMaxHealthDamageNugget shots Damage999999UNRESISTABLE,
PercentMaxHealthToTake50%; one plain DamageNugget control. Victims:
base1000full, high1000half, order2000full, removed1000full control.
GUESSED healing source from field name: half VICTIM MAX health500/500/1000,
so caster25/25/30%; plain damage leaves20%. All victims die, shooters live.
Packed per lane=HP% +1000*victimAlive +1000000*shooterAlive, cleared each
frame before health read to defeat death-counter freeze. This separates
max-vs-current victim HP and victim-vs-caster maximum, with no cap saturation.
No retail RequiredUpgrade or filter in this core-field isolation; upgrade,
CRUSH-specific delivery and nonlethal healing are outside the first probe.
Empty clips load1s, order6s, NO_ATTACK6+4/15; four lines.
"""
import re
from maps import probe_range
from parts import Mission,Script,Test
from checks.engine_weaponfx import gun
from checks.engine_missile import target
CASES=(('base',1000,100.0,True),('high',1000,50.0,True),('order',2000,100.0,True),('removed',1000,100.0,False))

def mission():
    m=Mission(name='CampLPct',map=probe_range,units=[target('CNV_LPctT1',1000),target('CNV_LPctT2',2000)],facts={})
    for lane,hp,start,leech in CASES:
        u=gun('CNV_LPct'+lane.title(),999999)
        u.xml=u.xml.replace('DamageType="EXPLOSIVE"','DamageType="UNRESISTABLE"')
        u.xml,n=re.subn(r'\bMaxHealth="[^"]+"','MaxHealth="10000"',u.xml);assert n==1
        if leech:
            u.xml=u.xml.replace('<DamageNugget ','<LeechPercentMaxHealthDamageNugget PercentMaxHealthToTake="50%" ')
        m.units.append(u)
        m.put(u.id,lane+' gun',side='p1',angle=1.5708,name='LPct '+lane+' gun')
        m.put('CNV_LPctT2' if hp==2000 else 'CNV_LPctT1',lane+' gun',0,450,side='s1',angle=4.7124,name='LPct '+lane+' target')
    return m

def check(m):
    t=Test();start=[('MAP_REVEAL_ALL_PERM',m.player('p1')),('SET_MILLISECOND_TIMER','LPct Fire',6.0),('SET_MILLISECOND_TIMER','LPct Stop',6+4/15)]
    fire=[];stop=[]
    for lane,hp,health,leech in CASES:
        g='LPct '+lane+' gun';v='LPct '+lane+' target';c='CNV_LPct_'+lane
        start += [('UNIT_CHANGE_OBJECT_STATUS',name,'NO_ATTACK',1) for name in (g,v)]
        start += [('UNIT_SET_HEALTH',g,20.0),('UNIT_SET_HEALTH',v,float(health))]
        fire += [('UNIT_CHANGE_OBJECT_STATUS',g,'NO_ATTACK',0),('NAMED_ATTACK_NAMED',g,v)]
        stop += [('UNIT_CHANGE_OBJECT_STATUS',g,'NO_ATTACK',1)]
        t.counters.append((c,lane+' packed'))
        t.scripts += [Script('Test - hp '+lane,[],[('SET_COUNTER',c,0),('SET_UNIT_HEALTH_PERCENTAGE_TO_COUNTER',g,c)],once=False),
                      Script('Test - caster '+lane,[('NAMED_NOT_DESTROYED',g)],[('INCREMENT_COUNTER',1000000,c)],once=False),
                      Script('Test - victim '+lane,[('NAMED_NOT_DESTROYED',v)],[('INCREMENT_COUNTER',1000,c)],once=False)]
    t.scripts.insert(0,Script('Test - start',[],start))
    t.scripts.insert(1,Script('Test - fire',[('TIMER_EXPIRED','LPct Fire')],fire))
    t.scripts.append(Script('Test - stop',[('TIMER_EXPIRED','LPct Stop')],stop))
    t.expect=[(label,14,'==',v,16) for (_,label),v in zip(t.counters,(1000025,1000025,1000030,1000020))]
    t.bench=[('bench_watch',dict(seconds=16.0,every=.5,sheet=False,lines=4))]
    return t
MISSION={'engine_leechpct':mission}
CHECKS={'engine_leechpct':{'a':check}}
