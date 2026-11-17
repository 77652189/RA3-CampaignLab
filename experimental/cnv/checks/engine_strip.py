"""Bench exact PASS95/45/74 ->100095/100045/100074, alive3 (11-10).
PREDICT before bench: AmountToStrip acts on MAX health, not current.
10000HP Hammer, one1 UNRESISTABLE marker plus4%/4%/25% strip;
second lane starts at50%. UNRESISTABLE isolates armor. Predicted rounded
health96/46/75, all alive. Formula(10000*start -1 -10000*Amount)/100.
First bench maxhp read95/45/74: floor(95.99/45.99/74.99) is a
GUESSED counter-conversion explanation, not a new damage formula.
Second exact check changes marker1->100 (exactly1% of max10000),
predicts95/45/74 with integer health percentages, packed100095/100045/100074.
This removes floor-vs-round ambiguity without changing strip amounts.
GUESSED before bench: the percent amount is damage rather than reducing maxHP.
At10s SET_UNIT_HEALTH100% checks recovery ->100/100/100. This
is not an independent absolute-maxHP measurement; maxHP preservation
remains INFERRED from the damage-like percentage response.
Each displayed row HPbefore +1000*HPafter; fourth row alive count3.
Order6s after1s initial EMPTY clip load, NO_ATTACK stops6+4/15.
"""
from maps import probe_range
from parts import Mission,Script,Test
from checks.engine_weaponfx import gun
from checks.engine_missile import target,TARGET_ID

def mission():
    return Mission(name='CampStrip',map=probe_range,units=[target()],facts={})

def check(m, exact=False):
    t=Test(); start=[('MAP_REVEAL_ALL_PERM',m.player('p1')),
        ('SET_MILLISECOND_TIMER','Strip Fire',6.0),('SET_MILLISECOND_TIMER','Strip Stop',6.0+4/15),
        ('SET_MILLISECOND_TIMER','Strip Reset',10.0)]
    fire=[];stop=[];reset=[]
    for lane,amount,health in (('base',4,100.0),('high',4,50.0),('order',25,100.0)):
        u=gun('CNV_Strip'+lane.title(),100 if exact else 1,f'<StripMaxHealthPercentNugget AmountToStrip="{amount}%" DamageType="UNRESISTABLE"/>')
        u.xml=u.xml.replace('DamageType="EXPLOSIVE"','DamageType="UNRESISTABLE"');m.units.append(u)
        g='Strip '+lane+' gun'; v='Strip '+lane+' target'; c='CNV_Strip_'+lane
        m.put(u.id,lane+' gun',side='p1',angle=1.5708,name=g)
        m.put(TARGET_ID,lane+' gun',0,450,side='s1',angle=4.7124,name=v)
        start.extend([('UNIT_CHANGE_OBJECT_STATUS',name,'NO_ATTACK',1) for name in (g,v)])
        start.append(('UNIT_SET_HEALTH',v,health))
        fire += [('UNIT_CHANGE_OBJECT_STATUS',g,'NO_ATTACK',0),('NAMED_ATTACK_NAMED',g,v)]
        stop += [('UNIT_CHANGE_OBJECT_STATUS',g,'NO_ATTACK',1)]
        reset += [('UNIT_SET_HEALTH',v,100.0)]
        t.counters.append((c,lane+' HP packed'))
        temp='Strip HP '+lane
        t.scripts += [Script('Test - before '+lane,[('FLAG','Strip Reset Done',0)],[('SET_UNIT_HEALTH_PERCENTAGE_TO_COUNTER',v,c)],once=False),
          Script('Test - after '+lane,[('FLAG','Strip Reset Done',1)],[('SET_UNIT_HEALTH_PERCENTAGE_TO_COUNTER',v,temp),('COUNTER_MATH_VALUE',temp,2,1000),('COUNTER_MATH_COUNTER',c,0,temp)])]
    # Snapshot before reset, then add1000*restored health once on the following frame.
    t.counters.append(('CNV_Strip_Alive','alive'))
    t.scripts.append(Script('Test - alive',[('NAMED_NOT_DESTROYED','Strip '+lane+' target') for lane in ('base','high','order')],[('SET_COUNTER','CNV_Strip_Alive',3)],once=False))
    t.scripts.insert(0,Script('Test - start',[],start))
    t.scripts += [Script('Test - fire',[('TIMER_EXPIRED','Strip Fire')],fire),
        Script('Test - stop',[('TIMER_EXPIRED','Strip Stop')],stop),
        Script('Test - reset',[('TIMER_EXPIRED','Strip Reset')],reset+[('SET_FLAG','Strip Reset Done',1)])]
    t.expect=[(label,14,'==',v,16) for (_,label),v in zip(t.counters,(100095,100045,100074,3) if exact else (100096,100046,100075,3))]
    t.bench=[('bench_watch',dict(seconds=16.0,every=.5,sheet=False,lines=4))]
    return t
MISSION={'engine_strip':mission}
CHECKS={'engine_strip':{'maxhp':check,'exact':lambda m:check(m,True)}}
