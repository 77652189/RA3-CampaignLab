"""Bench PASS7/95/11/95 (new finite burst, 11-10); PREDICT before bench: retail Hammer straight projectile MuzzleVelocity50
units/frame at250/450 distance. ProjectileNugget resolves500 EXPLOSIVE
warhead on10000HP Hammer (100% armor), 95% after one hit. Object fires
atF1, script observes atF2; flight adds floor(distance/50)=5/9 frames.
Collision/launch phase formula is INFERRED from prior engine_shot evidence;
this new finite-burst probe rechecks it. Current sim has no flight:2/95/2/95.
Only stationary targets, no splash, no scatter. Empty clip loads1s;
order6s, NO_ATTACK6+4/15 stops before second clip. Four counters.
"""
from maps import probe_range
from parts import Mission,Script,Test
from checks.engine_shot import shell_v4,SHELL
from checks.engine_missile import target,TARGET_ID

def mission():
    u=shell_v4('CNV_Proj',reload=1.0)
    u.xml=u.xml.replace('ProjectileTemplate="CNV_ProjProjectile"',f'ProjectileTemplate="{SHELL}"')
    u.files={};u.also=[]
    m=Mission(name='CampProj',map=probe_range,units=[u,target()],facts={})
    for lane,d in (('base',250),('high',450)):
        m.put(u.id,lane+' gun',side='p1',angle=1.5708,name='Proj '+lane+' gun')
        m.put(TARGET_ID,lane+' gun',0,d,side='s1',angle=4.7124,name='Proj '+lane+' target')
    return m

def check(m):
    t=Test();start=[('MAP_REVEAL_ALL_PERM',m.player('p1')),('SET_MILLISECOND_TIMER','Proj Fire',6.0),('SET_MILLISECOND_TIMER','Proj Stop',6.0+4/15)]
    fire=[];stop=[]
    for lane in ('base','high'):
        g='Proj '+lane+' gun';v='Proj '+lane+' target';c='CNV_Proj_'+lane
        start += [('UNIT_CHANGE_OBJECT_STATUS',name,'NO_ATTACK',1) for name in (g,v)]
        fire += [('UNIT_CHANGE_OBJECT_STATUS',g,'NO_ATTACK',0),('NAMED_ATTACK_NAMED',g,v)]
        stop += [('UNIT_CHANGE_OBJECT_STATUS',g,'NO_ATTACK',1)]
        t.counters.extend([(c,lane+' hit'),(c+'HP',lane+' HP')])
        t.scripts += [Script('Test - frame '+lane,[('FLAG','Proj Ordered',1),('UNIT_HEALTH',v,2,100)],[('INCREMENT_COUNTER',1,c)],once=False),
                      Script('Test - hp '+lane,[],[('SET_UNIT_HEALTH_PERCENTAGE_TO_COUNTER',v,c+'HP')],once=False)]
    t.scripts.insert(0,Script('Test - start',[],start))
    t.scripts.insert(1,Script('Test - fire',[('TIMER_EXPIRED','Proj Fire')],fire+[('SET_FLAG','Proj Ordered',1)]))
    t.scripts.append(Script('Test - stop',[('TIMER_EXPIRED','Proj Stop')],stop))
    t.expect=[(label,14,'==',v,16) for (_,label),v in zip(t.counters,(7,95,11,95))]
    t.bench=[('bench_watch',dict(seconds=16.0,every=.5,sheet=False,lines=4))]
    return t
MISSION={'engine_projectile':mission}
CHECKS={'engine_projectile':{'flight':check}}
