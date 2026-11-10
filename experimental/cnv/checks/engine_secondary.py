"""New bench PASS1099/0/1099/1; PREDICT before bench: packedHP+alive then frozen, control and high.
Two1000HP Hammer targets each take one10UNRESISTABLE marker. Only high
gets SecondaryDamageNugget Amount2000=MAX_SECONDARY_DAMAGE_SCALER200%
of1000. BaseVehicle fraction1.0 freezes; DissipateAmount25/UpdateDuration1s.
Even10s later cold>=2000-10*25=1750>1000, so frozen through final14..16s.
Marker UNRESISTABLE bypasses frozen armor, so both HP99 and alive1.
Single2000 dose deliberately exposes wrong continuous-DPS delivery: pre-fix
sim averaged2000 over17/15s clip, applies about0.5s before NO_ATTACK,
less than1000 cold, predicts1099/0/1099/0. Do not raise dose to hide this.
This validates secondary-vs-HP channel and single-hit delivery, NOT first
freeze phase, melt/recovery frames, splash or upgrades. Existing per-frame
melt approximation remains GUESSED. Empty clip loads1s, fire6s, stop6+4/15.
"""
from maps import probe_range
from model import status
from parts import Mission,Script,Test
from checks.engine_weaponfx import gun
from checks.engine_missile import target,TARGET_ID

def mission():
    m=Mission(name='CampSD',map=probe_range,units=[target(health=1000)],facts={})
    for lane in ('base','high'):
        effect='<SecondaryDamageNugget Amount="2000"/>' if lane=='high' else ''
        u=gun('CNV_SD'+lane.title(),10,effect)
        u.xml=u.xml.replace('DamageType="EXPLOSIVE"','DamageType="UNRESISTABLE"')
        m.units.append(u)
        m.put(u.id,lane+' gun',side='p1',angle=1.5708,name='SD '+lane+' gun')
        m.put(TARGET_ID,lane+' gun',0,450,side='s1',angle=4.7124,name='SD '+lane+' tank')
    return m

def check(m):
    t=Test();start=[('MAP_REVEAL_ALL_PERM',m.player('p1')),('SET_MILLISECOND_TIMER','SD Fire',6.0),('SET_MILLISECOND_TIMER','SD Stop',6.0+4/15)]
    fire=[];stop=[]
    for lane in ('base','high'):
        g='SD '+lane+' gun';v='SD '+lane+' tank';hp='CNV_SD_'+lane+'HP';cold='CNV_SD_'+lane+'Frozen'
        start += [('UNIT_CHANGE_OBJECT_STATUS',name,'NO_ATTACK',1) for name in (g,v)]
        fire += [('UNIT_CHANGE_OBJECT_STATUS',g,'NO_ATTACK',0),('NAMED_ATTACK_NAMED',g,v)]
        stop += [('UNIT_CHANGE_OBJECT_STATUS',g,'NO_ATTACK',1)]
        t.counters.extend([(hp,lane+' aliveHP'),(cold,lane+' frozen')])
        t.scripts += [Script('Test - hp '+lane,[],[('SET_COUNTER',hp,0),('SET_UNIT_HEALTH_PERCENTAGE_TO_COUNTER',v,hp),('SET_COUNTER',cold,0)],once=False),
                      Script('Test - alive '+lane,[('NAMED_NOT_DESTROYED',v)],[('INCREMENT_COUNTER',1000,hp)],once=False),
                      Script('Test - frozen '+lane,[('UNIT_HAS_OBJECT_STATUS',v,status('UNDER_FROZEN'))],[('SET_COUNTER',cold,1)],once=False)]
    t.scripts.insert(0,Script('Test - start',[],start))
    t.scripts.insert(1,Script('Test - fire',[('TIMER_EXPIRED','SD Fire')],fire))
    t.scripts.append(Script('Test - stop',[('TIMER_EXPIRED','SD Stop')],stop))
    t.expect=[(label,14,'==',v,16) for (_,label),v in zip(t.counters,(1099,0,1099,1))]
    t.bench=[('bench_watch',dict(seconds=16.0,every=.5,sheet=False,lines=4))]
    return t
MISSION={'engine_secondary':mission}
CHECKS={'engine_secondary':{'single':check}}
