"""Corrected placement PREDICT992002200/992002180/992002160/992002200.
First bench2002200 on every lane was not a valid firing comparison: three
guns were at y=-50 and no house-hit signal was shown. Translate the entire
rig450 north (relative positions unchanged) and pack houseHP*1e7 as well.
Marker30 on3000HP house ->99%; this now positively verifies each gun fired.
No nugget values changed. Original member-only prediction follows:
Four3000HP AM_Apartments_01 each receive two100HP Soviet conscripts at3s
with the existing INSTANTLY action. At6s one30UNRESISTABLE marker hits the
house (99% remains, far above ejection threshold33.3%). high additionally
DamageContainedNugget20UNRESISTABLE, MaxUnitsToDamage1, stock-style
DamageObjectFilter NONE INFANTRY ->passenger health sum180; order cap2
->160; removed cap2 but filterVEHICLE ->200. base has only marker ->200.
Every row=sum passengerHP% +1000*aliveCount +1000000*ENCLOSEDcount.
This checks actual entry, survival and cap without assuming which passenger
is picked first. Health is cleared before read to defeat dead-object freeze.
No radius/splash, no upgrades; selection priority, armor and buildings dying
are not asserted. Empty clips load1s, fire6s, NO_ATTACK6+4/15; four lines.
Before implementation the simulator read992002200 on every corrected row.
MEASURED 2026-11-10: corrected rig PASS992002200/992002180/992002160/992002200;
run_queue summary `1 run: PASS 1` (work/logs/w6_contained_fixed_bench.log).
Simulation replays the same four readings. Only direct, shot_clock hits with
a separate ordinary damage marker are benched; passenger priority GUESSED.
"""
from maps import probe_range
from model import status
from parts import Mission,Script,Test
from checks.engine_weaponfx import gun
HOUSE='AM_Apartments_01'
MAN='SovietAntiInfantryInfantry'
CASES=(('base',0,'INFANTRY'),('high',1,'INFANTRY'),('order',2,'INFANTRY'),('removed',2,'VEHICLE'))

def mission():
    m=Mission(name='CampContain',map=probe_range,units=[],facts={})
    for lane,cap,kind in CASES:
        extra=f'<DamageContainedNugget Damage="20" DamageType="UNRESISTABLE" DeathType="NORMAL" MaxUnitsToDamage="{cap}"><DamageObjectFilter Rule="NONE" Include="{kind}"/></DamageContainedNugget>' if cap else ''
        u=gun('CNV_Contained'+lane.title(),30,extra)
        u.xml=u.xml.replace('DamageType="EXPLOSIVE"','DamageType="UNRESISTABLE"')
        m.units.append(u)
        m.put(HOUSE,lane+' gun',0,450,side='civ',name='Contained '+lane+' house')
        m.put(u.id,lane+' gun',side='p1',angle=1.5708,name='Contained '+lane+' gun')
        for i in range(2):m.put(MAN,lane+' gun',-40+80*i,300,side='s1',name=f'Contained {lane} man{i}')
    return m

def check(m):
    t=Test();start=[('MAP_REVEAL_ALL_PERM',m.player('p1')),('SET_MILLISECOND_TIMER','Contained In',3.0),('SET_MILLISECOND_TIMER','Contained Fire',6.0),('SET_MILLISECOND_TIMER','Contained Stop',6+4/15)]
    enter=[];fire=[];stop=[]
    for lane,cap,kind in CASES:
        h='Contained '+lane+' house';g='Contained '+lane+' gun';c='CNV_Contained_'+lane
        start += [('UNIT_CHANGE_OBJECT_STATUS',v,'NO_ATTACK',1) for v in [h,g]+[f'Contained {lane} man{i}' for i in range(2)]]
        enter += [('NAMED_GARRISON_SPECIFIC_BUILDING_INSTANTLY',f'Contained {lane} man{i}',h) for i in range(2)]
        fire += [('UNIT_CHANGE_OBJECT_STATUS',g,'NO_ATTACK',0),('NAMED_ATTACK_NAMED',g,h)]
        stop += [('UNIT_CHANGE_OBJECT_STATUS',g,'NO_ATTACK',1)]
        t.counters.append((c,lane+' packed'))
        t.scripts.append(Script('Test - zero '+lane,[],[('SET_COUNTER',c+'HouseHP',0),('SET_UNIT_HEALTH_PERCENTAGE_TO_COUNTER',h,c+'HouseHP'),('COUNTER_MATH_VALUE',c+'HouseHP',2,10000000),('SET_COUNTER_TO_COUNTER',c,c+'HouseHP')],once=False))
        for i in range(2):
            v=f'Contained {lane} man{i}';tmp=c+'HP'+str(i)
            t.scripts += [Script(f'Test - hp {lane}{i}',[],[('SET_COUNTER',tmp,0),('SET_UNIT_HEALTH_PERCENTAGE_TO_COUNTER',v,tmp),('COUNTER_MATH_COUNTER',c,0,tmp)],once=False),
                          Script(f'Test - alive {lane}{i}',[('NAMED_NOT_DESTROYED',v)],[('INCREMENT_COUNTER',1000,c)],once=False),
                          Script(f'Test - inside {lane}{i}',[('UNIT_HAS_OBJECT_STATUS',v,status('ENCLOSED'))],[('INCREMENT_COUNTER',1000000,c)],once=False)]
    t.scripts.insert(0,Script('Test - start',[],start))
    t.scripts.insert(1,Script('Test - in',[('TIMER_EXPIRED','Contained In')],enter))
    t.scripts.insert(2,Script('Test - fire',[('TIMER_EXPIRED','Contained Fire')],fire))
    t.scripts.append(Script('Test - stop',[('TIMER_EXPIRED','Contained Stop')],stop))
    t.expect=[(label,14,'==',v,16) for (_,label),v in zip(t.counters,(992002200,992002180,992002160,992002200))]
    t.bench=[('bench_watch',dict(seconds=16.0,every=.5,sheet=False,lines=4))]
    return t
MISSION={'engine_contained':mission}
CHECKS={'engine_contained':{'a':check}}
