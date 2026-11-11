"""AttachNugget4: PREDICT1000001099/1001111099/1000001099/1000001099.

At6s each finite gun marks a1000HP passive Hammer for10UNRES (99%).
base has AttachUpdate but no nugget; high dispatches ModuleTag_Attach;
order forbids the target's NO_ATTACK status; removed filters INFANTRY.
The module has Range600/CloseEnoughRange1, ONE_ATTACH_PER_PARENT,
STICK_TO_PARENT and TELEPORT. It sets parent VEHICLE_ATTACHED and child
ENCLOSED/UNATTACKABLE; native ATTACHED is queried separately. GUESSED:
dispatch binds the caster to the victim; no autonomous attach before fire.
At9s the parent moves150 north. A14s area check verifies the child follows,
not just that two bits were set. No exact walking frame or geometry claim.
Packed=1e9*childAlive+1e7*attachedBeforeFire+1e6*attachedAfterFire+
1e5*parentStatusAfterFire+1e4*childAtMovedParent+1000*parentAlive+parentHP%.
The5s/8s/14s snapshots close after one script frame. Dead HP is cleared.
No parent death, damage leech, repair, detach, upgrades or projectile tested.
Empty single clips load1s; order6s; NO_ATTACK closes each window after4/15s.
First fixture incorrectly referenced a missing AttachModuleId in order:
capture stopped at4s, access violation recorded near firing, no hit data.
Correct that invalid control to a real module plus ForbiddenTargetObjectStatus;
do not treat missing samples as an attachment-rule failure.
MEASURED2026-11-10: corrected fixture PASS1000001099/1001111099/
1000001099/1000001099 (work/logs/c_attach_retry_bench.log). The preceding
corrected build could not start DirectX; unchanged --no-build retry passed.
Only direct zero-radius, teleport/stick/status subset is replayed. Complex
retail module handlers remain gaps; this is not whole-item bench promotion.
"""
import xml.etree.ElementTree as ET
from maps import probe_range
from model import status
from parts import Mission, Script, Test, square
from checks.engine_weaponfx import gun
from checks.engine_missile import target

CASES=('base','high','order','removed')


def _module_contract(unit):
    """This probe owns its modules in one XML; reject missing Poid providers before BAB/game."""
    nodes=list(ET.fromstring(unit.xml).iter())
    modules={e.attrib['id'] for e in nodes if e.tag.rsplit('}',1)[-1]=='AttachUpdate' and 'id' in e.attrib}
    refs={e.attrib.get('AttachModuleId','') for e in nodes if e.tag.rsplit('}',1)[-1]=='AttachNugget'}
    missing=refs-modules
    if missing:
        raise ValueError(f'{unit.id}: unpublished AttachModuleId {sorted(missing)}')


def mission():
    m=Mission(name='CampAttach',map=probe_range,units=[],facts={})
    for lane in CASES:
        kind='INFANTRY' if lane=='removed' else 'VEHICLE'
        forbidden=' ForbiddenTargetObjectStatus="NO_ATTACK"' if lane=='order' else ''
        nugget=(f'<AttachNugget AttachModuleId="ModuleTag_Attach"{forbidden}><SpecialObjectFilter '
                f'Rule="ANY" Include="{kind}"/></AttachNugget>' if lane!='base' else '')
        u=gun('CNV_Attach'+lane.title(),10,nugget)
        u.xml=u.xml.replace('DamageType="EXPLOSIVE"','DamageType="UNRESISTABLE"')
        u.xml=u.xml.replace('<Behaviors>','<Behaviors>'+
            '<AttachUpdate id="ModuleTag_Attach" Range="600" CloseEnoughRange="1" '
            'ParentStatus="VEHICLE_ATTACHED" AttachedObjectStatus="ENCLOSED UNATTACKABLE" '
            'Flags="ONE_ATTACH_PER_PARENT STICK_TO_PARENT TELEPORT"/>',1)
        _module_contract(u)
        v=target('CNV_AttachVictim'+lane.title(),health=1000)
        m.units.extend((u,v))
        m.put(u.id,lane+' gun',side='p1',angle=1.5708,name='Attach '+lane+' child')
        m.put(v.id,lane+' gun',0,450,side='s1',angle=4.7124,name='Attach '+lane+' parent')
        m.waypoint(lane+' goal','Attach goal '+lane,lane+' gun',0,600)
    return m


def check(m):
    t=Test();start=[('MAP_REVEAL_ALL_PERM',m.player('p1'))]
    for timer,at in (('Before',5.),('Fire',6.),('Stop',6+4/15),('After',8.),('Move',9.),('Follow',14.)):
        start.append(('SET_MILLISECOND_TIMER','Attach '+timer,at))
    fire=[];stop=[];move=[]
    for lane in CASES:
        child,parent='Attach '+lane+' child','Attach '+lane+' parent';c='CNV_Attach_'+lane
        start.extend(('UNIT_CHANGE_OBJECT_STATUS',v,'NO_ATTACK',1) for v in (child,parent))
        fire.extend((('UNIT_CHANGE_OBJECT_STATUS',child,'NO_ATTACK',0),('NAMED_ATTACK_NAMED',child,parent)))
        stop.append(('UNIT_CHANGE_OBJECT_STATUS',child,'NO_ATTACK',1))
        move.append(('MOVE_NAMED_UNIT_TO',parent,m.mark(lane+' goal')))
        x,y=m.point(lane+' goal');area='Attach area '+lane;t.areas[area]=square(x,y,60)
        t.counters.append((c,lane+' packed'))
        t.scripts.extend((Script('Test - hp '+lane,[],[('SET_COUNTER',c,0),
            ('SET_UNIT_HEALTH_PERCENTAGE_TO_COUNTER',parent,c),('COUNTER_MATH_COUNTER',c,0,c+'State')],once=False),
            Script('Test - parent alive '+lane,[('NAMED_NOT_DESTROYED',parent)],[('INCREMENT_COUNTER',1000,c)],once=False),
            Script('Test - child alive '+lane,[('NAMED_NOT_DESTROYED',child)],[('INCREMENT_COUNTER',1000000000,c)],once=False)))
        snapshots=(('Before',10000000,('UNIT_HAS_OBJECT_STATUS',child,status('ATTACHED'))),
                   ('After',1000000,('UNIT_HAS_OBJECT_STATUS',child,status('ATTACHED'))),
                   ('After',100000,('UNIT_HAS_OBJECT_STATUS',parent,status('VEHICLE_ATTACHED'))),
                   ('Follow',10000,('NAMED_INSIDE_AREA',child,area)))
        for i,(phase,weight,cond) in enumerate(snapshots):
            t.scripts.append(Script(f'Test - sample {lane}{i}',[('TIMER_EXPIRED','Attach '+phase),
                ('FLAG','Attach sampled '+phase,0),cond],[('INCREMENT_COUNTER',weight,c+'State')]))
    for phase in ('Before','After','Follow'):
        t.scripts.append(Script('Test - close '+phase,[('TIMER_EXPIRED','Attach '+phase)],
                               [('SET_FLAG','Attach sampled '+phase,1)]))
    t.scripts.insert(0,Script('Test - start',[],start))
    t.scripts.extend((Script('Test - fire',[('TIMER_EXPIRED','Attach Fire')],fire),
                      Script('Test - stop',[('TIMER_EXPIRED','Attach Stop')],stop),
                      Script('Test - move',[('TIMER_EXPIRED','Attach Move')],move)))
    t.expect=[(label,18,'==',v,20) for (_,label),v in zip(t.counters,(1000001099,1001111099,1000001099,1000001099))]
    t.bench=[('bench_watch',dict(seconds=20.,every=.5,sheet=False,lines=4))]
    return t


MISSION={'engine_attach':mission}
CHECKS={'engine_attach':{'a':check}}
