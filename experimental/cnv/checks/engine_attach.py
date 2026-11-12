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
import os
import re
import xml.etree.ElementTree as ET
import labpaths
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


def mission(detach=False, lanes=CASES):
    m=Mission(name='CampAttachD' if detach else 'CampAttach',map=probe_range,units=[],facts={})
    for lane in lanes:
        kind='INFANTRY' if lane=='removed' and not detach else 'VEHICLE'
        forbidden=' ForbiddenTargetObjectStatus="NO_ATTACK"' if lane=='order' and not detach else ''
        nugget=(f'<AttachNugget AttachModuleId="ModuleTag_Attach"{forbidden}><SpecialObjectFilter '
                f'Rule="ANY" Include="{kind}"/></AttachNugget>'
                if (lane!='removed' if detach else lane!='base') else '')
        u=gun('CNV_Attach'+lane.title(),10,nugget)
        u.xml=u.xml.replace('DamageType="EXPLOSIVE"','DamageType="UNRESISTABLE"')
        flags=' MOVE_ORDER_FORCES_DETACH' if detach and lane!='base' else ''
        child_status='NON_AUTOACQUIRABLE NO_COLLISIONS' if detach else 'ENCLOSED UNATTACKABLE'
        u.xml=u.xml.replace('<Behaviors>','<Behaviors>'+
            '<AttachUpdate id="ModuleTag_Attach" Range="600" CloseEnoughRange="1" '
            f'ParentStatus="VEHICLE_ATTACHED" AttachedObjectStatus="{child_status}" '
            f'Flags="ONE_ATTACH_PER_PARENT STICK_TO_PARENT TELEPORT{flags}"/>',1)
        _module_contract(u)
        v=target('CNV_AttachVictim'+lane.title(),health=1000)
        m.units.extend((u,v))
        m.put(u.id,lane+' gun',0,600 if detach and lane=='removed' else 0,
              side='p1',angle=1.5708,name='Attach '+lane+' child')
        m.put(v.id,lane+' gun',0,450,side='s1',angle=4.7124,name='Attach '+lane+' parent')
        m.waypoint(lane+' goal','Attach goal '+lane,lane+' gun',0,600)
        if detach:
            m.waypoint(lane+' child goal','Attach child goal '+lane,lane+' gun',200,600)
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


def mission_detach():
    return mission(detach=True)


def check_detach(m):
    """Retail JapanScoutInfantry's MOVE_ORDER_FORCES_DETACH, isolated from other handlers.

    Second-run PREDICT: 1133111099/1133100199/1133111099/1100000199.
    base: attached, no flag, child move; high: attached, flag, child move;
    order: attached, flag, parent move only; removed: flag, no nugget, child move.
    All parents move at9s; all but order children receive a plain move at16s.
    Bits at8s prove attachment;14s proves following;24s tests release and arrival.
    Packed=1e9*childAlive+1e8*parentAlive+2e7*everAttached+2e6*everParentStatus+
    1e7*attached8+1e6*parentStatus8+
    1e5*follow14+1e4*attached24+1e3*parentStatus24+100*childGoal24+parentHP%.
    Only the flag's direct, simple-module contract; no retail beam/projectile,
    geometry, alignment, leech, death or attack-move semantics claimed.

    MEASURED 2026-11-10 (two-run stop; no model rule inferred):
    First fixture, ENCLOSED UNATTACKABLE: 1111111099/1100000199/
    1100000099/1100000099 (c_attach_detach_bench.log). Flagged lanes had
    already cleared both statuses at8s, BEFORE the16s child move order.
    Second fixture substitutes retail NON_AUTOACQUIRABLE NO_COLLISIONS and
    latches ever-attached/ever-parent bits: 1133111099/1122000199/
    1122000099/1100000200 (c_attach_detach_native_status_bench.log).
    Both flagged lanes DID attach, then cleared before8s; neither followed
    the9s parent move. An explicit child move at16s cannot explain that.
    The removed control starts at y600 to shorten its walk: it faces away
    from the y450 target and shows no hit (HP100), then reaches its own
    goal. Orientation/command timing was not isolated; HP100 is not a rule.
    expect below preserves OBSERVATIONS for diagnosis, not the rejected
    prediction or whole-item evidence. Direct attack task/automatic move,
    NO_ATTACK interruption, and retail projectile dispatch remain unseparated.
    """
    t=Test();start=[('MAP_REVEAL_ALL_PERM',m.player('p1'))]
    for phase,at in (('Fire',6.),('Stop',6+4/15),('After',8.),('Move',9.),
                     ('Follow',14.),('ChildMove',16.),('Late',24.)):
        start.append(('SET_MILLISECOND_TIMER','Detach '+phase,at))
    fire=[];stop=[];move=[];child_move=[]
    for lane in CASES:
        child,parent='Attach '+lane+' child','Attach '+lane+' parent';c='CNV_Detach_'+lane
        start.extend(('UNIT_CHANGE_OBJECT_STATUS',v,'NO_ATTACK',1) for v in (child,parent))
        fire.extend((('UNIT_CHANGE_OBJECT_STATUS',child,'NO_ATTACK',0),('NAMED_ATTACK_NAMED',child,parent)))
        stop.append(('UNIT_CHANGE_OBJECT_STATUS',child,'NO_ATTACK',1))
        move.append(('MOVE_NAMED_UNIT_TO',parent,m.mark(lane+' goal')))
        if lane!='order':
            child_move.append(('MOVE_NAMED_UNIT_TO',child,m.mark(lane+' child goal')))
        parent_area,child_area='Detach parent '+lane,'Detach child '+lane
        t.areas[parent_area]=square(*m.point(lane+' goal'),60)
        t.areas[child_area]=square(*m.point(lane+' child goal'),60)
        t.counters.append((c,lane+' detach'))
        t.scripts.extend((Script('Test - detach hp '+lane,[],[('SET_COUNTER',c,0),
            ('SET_UNIT_HEALTH_PERCENTAGE_TO_COUNTER',parent,c),('COUNTER_MATH_COUNTER',c,0,c+'State')],once=False),
            Script('Test - detach parent alive '+lane,[('NAMED_NOT_DESTROYED',parent)],
                   [('INCREMENT_COUNTER',100000000,c)],once=False),
            Script('Test - detach child alive '+lane,[('NAMED_NOT_DESTROYED',child)],
                   [('INCREMENT_COUNTER',1000000000,c)],once=False)))
        t.scripts.extend((
            Script('Test - detach ever child '+lane,[('UNIT_HAS_OBJECT_STATUS',child,status('ATTACHED'))],
                   [('INCREMENT_COUNTER',20000000,c+'State')]),
            Script('Test - detach ever parent '+lane,[('UNIT_HAS_OBJECT_STATUS',parent,status('VEHICLE_ATTACHED'))],
                   [('INCREMENT_COUNTER',2000000,c+'State')])))
        snapshots=(('After',10000000,('UNIT_HAS_OBJECT_STATUS',child,status('ATTACHED'))),
                   ('After',1000000,('UNIT_HAS_OBJECT_STATUS',parent,status('VEHICLE_ATTACHED'))),
                   ('Follow',100000,('NAMED_INSIDE_AREA',child,parent_area)),
                   ('Late',10000,('UNIT_HAS_OBJECT_STATUS',child,status('ATTACHED'))),
                   ('Late',1000,('UNIT_HAS_OBJECT_STATUS',parent,status('VEHICLE_ATTACHED'))),
                   ('Late',100,('NAMED_INSIDE_AREA',child,child_area)))
        for i,(phase,weight,cond) in enumerate(snapshots):
            t.scripts.append(Script(f'Test - detach sample {lane}{i}',[('TIMER_EXPIRED','Detach '+phase),
                ('FLAG','Detach sampled '+phase,0),cond],[('INCREMENT_COUNTER',weight,c+'State')]))
    for phase in ('After','Follow','Late'):
        t.scripts.append(Script('Test - detach close '+phase,[('TIMER_EXPIRED','Detach '+phase)],
                               [('SET_FLAG','Detach sampled '+phase,1)]))
    t.scripts.insert(0,Script('Test - detach start',[],start))
    for phase,actions in (('Fire',fire),('Stop',stop),('Move',move),('ChildMove',child_move)):
        t.scripts.append(Script('Test - detach '+phase,[('TIMER_EXPIRED','Detach '+phase)],actions))
    t.expect=[(label,26,'==',v,28) for (_,label),v in zip(t.counters,
              (1133111099,1122000199,1122000099,1100000200))]
    t.bench=[('bench_watch',dict(seconds=28.,every=.5,sheet=False,lines=4))]
    return t


def mission_parent_death():
    """Simple/native module x live/killed parent; direct dispatch, not retail projectile.

    base/high use the established simple module; order/removed use the complete
    JapanScoutInfantry AttachUpdate unchanged. All children use its two status
    bits. Parent kill at10s follows the8s attachment snapshot; late sample14s.
    PREDICT simple live1023, simple kill992 (survive, clear all bits).
    Native lanes may detach before8s: then death semantics remain a gap.
    Before bits: ATTACHED512,parent256,NON_AUTOACQUIRABLE128,NO_COLLISIONS64.
    Late bits: childAlive32,parentAlive16,ATTACHED8,parent4,NON2,COLL1.
    No death HP read or delete involved. First run's combined child-bit query
    was low; independent bits distinguish missing flags from an AND-query gap.
    MEASURED2026-11-11: 958/928/48/32 (c_attach_parent_split_bench.log).
    Simple NON_AUTOACQUIRABLE reads high; NO_COLLISIONS reads low at both
    samples. Do not infer a reason or silently clear it in the model. Native
    lanes have no8s link, so their death boundary remains unmeasured. See
    work/re/c_attach_parent_report.md; full replay is a strict xfail.
    """
    m=mission();m.name='CampAttachP'
    path=os.path.join(labpaths.SDK3,'SageXML','Japan','Units','JapanScoutInfantry.xml')
    with open(path,encoding='utf-8') as f:
        native=re.findall(r'<AttachUpdate\b.*?</AttachUpdate>',f.read(),re.S)
    assert len(native)==1, 'native AttachUpdate provider changed'
    for lane in CASES:
        u=next(u for u in m.units if u.id=='CNV_Attach'+lane.title())
        # All four lanes dispatch a valid nugget to a vehicle; no old filters.
        u.xml=re.sub(r'<AttachNugget\b.*?</AttachNugget>','',u.xml,flags=re.S)
        u.xml=u.xml.replace('</Nuggets>','<AttachNugget AttachModuleId="ModuleTag_Attach">'
                            '<SpecialObjectFilter Rule="ANY" Include="VEHICLE"/></AttachNugget></Nuggets>')
        u.xml=u.xml.replace('AttachedObjectStatus="ENCLOSED UNATTACKABLE"',
                            'AttachedObjectStatus="NON_AUTOACQUIRABLE NO_COLLISIONS"')
        if lane in ('order','removed'):
            u.xml,n=re.subn(r'<AttachUpdate\b[^>]*/>',lambda _:native[0],u.xml)
            assert n==1, 'simple AttachUpdate provider changed'
        _module_contract(u)
    return m


def check_parent_death(m):
    t=Test();start=[('MAP_REVEAL_ALL_PERM',m.player('p1'))]
    for phase,at in (('Fire',6.),('Stop',6+4/15),('Before',8.),('Kill',10.),('Late',14.)):
        start.append(('SET_MILLISECOND_TIMER','ParentDeath '+phase,at))
    fire=[];stop=[]
    for lane in CASES:
        child,parent='Attach '+lane+' child','Attach '+lane+' parent'
        c='CNV_ParentDeath_'+lane;t.counters.append((c,lane+' parent death'))
        start.extend(('UNIT_CHANGE_OBJECT_STATUS',v,'NO_ATTACK',1) for v in (child,parent))
        fire.extend((('UNIT_CHANGE_OBJECT_STATUS',child,'NO_ATTACK',0),('NAMED_ATTACK_NAMED',child,parent)))
        stop.append(('UNIT_CHANGE_OBJECT_STATUS',child,'NO_ATTACK',1))
        for phase,prefix in (('Before',64),('Late',1)):
            samples=((8,[('UNIT_HAS_OBJECT_STATUS',child,status('ATTACHED'))]),
                     (4,[('UNIT_HAS_OBJECT_STATUS',parent,status('VEHICLE_ATTACHED'))]),
                     (2,[('UNIT_HAS_OBJECT_STATUS',child,status('NON_AUTOACQUIRABLE'))]),
                     (1,[('UNIT_HAS_OBJECT_STATUS',child,status('NO_COLLISIONS'))]))
            if phase=='Late':
                samples+=((32,[('NAMED_NOT_DESTROYED',child)]),(16,[('NAMED_NOT_DESTROYED',parent)]))
            for weight,conditions in samples:
                t.scripts.append(Script(f'Test - parent death {lane} {phase}{weight}',
                    [('TIMER_EXPIRED','ParentDeath '+phase),('FLAG','ParentDeath sampled '+phase,0)]+conditions,
                    [('INCREMENT_COUNTER',prefix*weight,c)]))
    for phase in ('Before','Late'):
        t.scripts.append(Script('Test - parent death close '+phase,[('TIMER_EXPIRED','ParentDeath '+phase)],
                               [('SET_FLAG','ParentDeath sampled '+phase,1)]))
    t.scripts.insert(0,Script('Test - start',[],start))
    for phase,actions in (('Fire',fire),('Stop',stop),('Kill',[
            ('NAMED_KILL','Attach '+lane+' parent') for lane in ('high','removed')])):
        t.scripts.append(Script('Test - parent death '+phase,[('TIMER_EXPIRED','ParentDeath '+phase)],actions))
    t.expect=[(label,16,'==',value,18) for (_,label),value in zip(t.counters,(958,928,48,32))]
    t.bench=[('bench_watch',dict(seconds=18.,every=.5,sheet=False,lines=4))]
    return t


def mission_child_death():
    """Established simple ENCLOSED/UNATTACKABLE module, live versus script-killed child."""
    m=mission(lanes=('base','high'));m.name='CampAttachC'
    u=next(u for u in m.units if u.id=='CNV_AttachBase')
    u.xml=u.xml.replace('</Nuggets>','<AttachNugget AttachModuleId="ModuleTag_Attach">'
                        '<SpecialObjectFilter Rule="ANY" Include="VEHICLE"/></AttachNugget></Nuggets>')
    _module_contract(u)
    return m


def check_child_death(m):
    """PREDICT127/124: confirm links at8s, kill high child10s, read live parents14s.

    Before: child ATTACHED64, parent VEHICLE_ATTACHED32, child ENCLOSED16,
    child UNATTACKABLE8. Late: parentAlive4, childAlive2, parent status1.
    Dead-child status is deliberately not queried. No direct-delete, lethal
    damage, original-module or exact cleanup-frame claim.
    MEASURED2026-11-11: 120/120 before;127/124 late, one run PASS.
    The killed child's living parent clears VEHICLE_ATTACHED. Evidence:
    work/re/c_attach_child_report.md; no whole-item bench promotion.
    """
    t=Test();start=[('MAP_REVEAL_ALL_PERM',m.player('p1'))];fire=[];stop=[]
    for phase,at in (('Fire',6.),('Stop',6+4/15),('Before',8.),('Kill',10.),('Late',14.)):
        start.append(('SET_MILLISECOND_TIMER','ChildDeath '+phase,at))
    for lane in ('base','high'):
        child,parent='Attach '+lane+' child','Attach '+lane+' parent'
        c='CNV_ChildDeath_'+lane;t.counters.append((c,lane+' child death'))
        start.extend(('UNIT_CHANGE_OBJECT_STATUS',v,'NO_ATTACK',1) for v in (child,parent))
        fire.extend((('UNIT_CHANGE_OBJECT_STATUS',child,'NO_ATTACK',0),('NAMED_ATTACK_NAMED',child,parent)))
        stop.append(('UNIT_CHANGE_OBJECT_STATUS',child,'NO_ATTACK',1))
        for phase,samples in (
                ('Before',((64,('UNIT_HAS_OBJECT_STATUS',child,status('ATTACHED'))),
                           (32,('UNIT_HAS_OBJECT_STATUS',parent,status('VEHICLE_ATTACHED'))),
                           (16,('UNIT_HAS_OBJECT_STATUS',child,status('ENCLOSED'))),
                           (8,('UNIT_HAS_OBJECT_STATUS',child,status('UNATTACKABLE'))))),
                ('Late',((4,('NAMED_NOT_DESTROYED',parent)),(2,('NAMED_NOT_DESTROYED',child)),
                         (1,('UNIT_HAS_OBJECT_STATUS',parent,status('VEHICLE_ATTACHED')))))):
            for weight,cond in samples:
                t.scripts.append(Script(f'Test - child death {lane} {phase}{weight}',
                    [('TIMER_EXPIRED','ChildDeath '+phase),('FLAG','ChildDeath sampled '+phase,0),cond],
                    [('INCREMENT_COUNTER',weight,c)]))
    for phase in ('Before','Late'):
        t.scripts.append(Script('Test - child death close '+phase,[('TIMER_EXPIRED','ChildDeath '+phase)],
                               [('SET_FLAG','ChildDeath sampled '+phase,1)]))
    t.scripts.insert(0,Script('Test - start',[],start))
    for phase,actions in (('Fire',fire),('Stop',stop),('Kill',[('NAMED_KILL','Attach high child')])):
        t.scripts.append(Script('Test - child death '+phase,[('TIMER_EXPIRED','ChildDeath '+phase)],actions))
    t.expect=[(label,16,'==',value,18) for (_,label),value in zip(t.counters,(127,124))]
    t.bench=[('bench_watch',dict(seconds=18.,every=.5,sheet=False,lines=2))]
    return t


MISSION={'engine_attach':mission,'engine_attach_detach':mission_detach,'engine_attach_parent':mission_parent_death,
         'engine_attach_child':mission_child_death}
CHECKS={'engine_attach':{'a':check},'engine_attach_detach':{'a':check_detach},'engine_attach_parent':{'a':check_parent_death},
        'engine_attach_child':{'a':check_child_death}}
