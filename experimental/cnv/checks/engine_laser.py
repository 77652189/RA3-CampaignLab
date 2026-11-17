"""Bench PASS2/90/2/90 (new run); PREDICT before bench. Two1000HP Hammers each receive one100 EXPLOSIVE
(100% tank armor); high gun additionally activates LaserId201 for2s.
Both shooters carry retail Mirage's matching LaserDraw/LaserState201;
so this is not an absent-renderer no-op. Laser nugget's schema fields
Lifetime/LaserId/HitGroundFX/OverShootDistance contain no damage field;
independent DamageNugget accounts for all100 damage. First script hit2
frames, no HP change after laser expires. Finite clip loads1s, fire6s,
stop6+4/15. Only HP/timing isolated here, draw declarations matched statically; rendered pixels are not asserted.
"""
import re
from pathlib import Path
from maps import probe_range
from parts import Mission,Script,Test
from checks.engine_weaponfx import gun
from checks.engine_missile import SAGE,target,TARGET_ID

def mission():
    m=Mission(name='CampLaser',map=probe_range,units=[target(health=1000)],facts={})
    xml=Path(SAGE,'Allied','Units','AlliedAntiVehicleVehicleTech3.xml').read_text(encoding='utf8')
    draw=re.search(r'<LaserDraw\b.*?</LaserDraw>',xml,re.S).group(0)
    state=re.search(r'<LaserState\b.*?</LaserState>',xml,re.S).group(0)
    for lane in ('base','high'):
        extra='<ActivateLaserNugget LaserId="201" Lifetime="2s"/>' if lane=='high' else ''
        u=gun('CNV_Laser'+lane.title(),100,extra)
        u.xml=u.xml.replace('</Draws>',draw+'</Draws>').replace('</Behaviors>',state+'</Behaviors>')
        m.units.append(u)
        m.put(u.id,lane+' gun',side='p1',angle=1.5708,name='Laser '+lane+' gun')
        m.put(TARGET_ID,lane+' gun',0,450,side='s1',angle=4.7124,name='Laser '+lane+' target')
    return m

def check(m):
    t=Test();start=[('MAP_REVEAL_ALL_PERM',m.player('p1')),('SET_MILLISECOND_TIMER','Laser Fire',6.0),('SET_MILLISECOND_TIMER','Laser Stop',6+4/15)]
    fire=[];stop=[]
    for lane in ('base','high'):
        g='Laser '+lane+' gun';v='Laser '+lane+' target';c='CNV_Laser_'+lane
        start += [('UNIT_CHANGE_OBJECT_STATUS',name,'NO_ATTACK',1) for name in (g,v)]
        fire += [('UNIT_CHANGE_OBJECT_STATUS',g,'NO_ATTACK',0),('NAMED_ATTACK_NAMED',g,v)]
        stop += [('UNIT_CHANGE_OBJECT_STATUS',g,'NO_ATTACK',1)]
        t.counters.extend([(c,lane+' hit'),(c+'HP',lane+' HP')])
        t.scripts += [Script('Test - hit '+lane,[('FLAG','Laser Ordered',1),('UNIT_HEALTH',v,2,100)],[('INCREMENT_COUNTER',1,c)],once=False),
                      Script('Test - hp '+lane,[],[('SET_UNIT_HEALTH_PERCENTAGE_TO_COUNTER',v,c+'HP')],once=False)]
    t.scripts.insert(0,Script('Test - start',[],start))
    t.scripts.insert(1,Script('Test - fire',[('TIMER_EXPIRED','Laser Fire')],fire+[('SET_FLAG','Laser Ordered',1)]))
    t.scripts.append(Script('Test - stop',[('TIMER_EXPIRED','Laser Stop')],stop))
    t.expect=[(label,14,'==',v,16) for (_,label),v in zip(t.counters,(2,90,2,90))]
    t.bench=[('bench_watch',dict(seconds=16.0,every=.5,sheet=False,lines=4))]
    return t
MISSION={'engine_laser':mission}
CHECKS={'engine_laser':{'pair':check}}
