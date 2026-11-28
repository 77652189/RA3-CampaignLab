"""Weapon impact checks and inline scenes."""
from functools import cache
from types import SimpleNamespace


@cache
def engine_attach():
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
    from benches.weapon.target_effects.checks import engine_weaponfx
    gun = engine_weaponfx()["shared"].gun
    from benches.weapon.firing.checks import engine_missile
    target = engine_missile()["shared"].target

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
        samples: the module never gives it (engine_attach_nocoll n). Native
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


    def check_child_death(m, *, delete=False):
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
        removal='NAMED_DELETE' if delete else 'NAMED_KILL'
        for phase,actions in (('Fire',fire),('Stop',stop),('Kill',[(removal,'Attach high child')])):
            t.scripts.append(Script('Test - child death '+phase,[('TIMER_EXPIRED','ChildDeath '+phase)],actions))
        t.expect=[(label,16,'==',value,18) for (_,label),value in zip(t.counters,(127,124))]
        t.bench=[('bench_watch',dict(seconds=18.,every=.5,sheet=False,lines=2))]
        return t


    def mission_child_delete():
        """Same established simple module; delete the linked child, keep its parent alive."""
        m=mission_child_death();m.name='CampAttachDel'
        return m


    def check_child_delete(m):
        """PREDICT127/124: links8s, NAMED_DELETE high child10s, live-parent status14s.

        Before120/120 independently proves ATTACHED/VEHICLE_ATTACHED/ENCLOSED/
        UNATTACKABLE. Late parentAlive4 + childAlive2 + parentStatus1 distinguishes
        removal from loss of the parent. No status read from the deleted child;
        parent deletion, retail modules and exact cleanup timing remain gaps.
        MEASURED2026-11-11: before120/120, late127/124, one run PASS;
        see work/re/c_attach_delete_report.md. No whole-item bench promotion.
        """
        t=check_child_death(m,delete=True)
        t.counters=[(name,label.replace('death','delete')) for name,label in t.counters]
        t.expect=[(label.replace('death','delete'),*rest) for label,*rest in t.expect]
        return t


    def mission_parent_delete():
        """Established simple module: live control versus directly deleted parent."""
        m=mission_child_death();m.name='CampAttachPD'
        return m


    def check_parent_delete(m):
        """PREDICT3871/3856: links8s, delete high parent10s, live-child bits14s.

        Before3840 = 32*(ATTACHED64 + parent VEHICLE_ATTACHED32 + ENCLOSED16
        + UNATTACKABLE8). Late: childAlive16,parentAlive8,ATTACHED4,ENCLOSED2,
        UNATTACKABLE1, each queried independently. No deleted-parent status read.
        MEASURED2026-11-11: before3840/3840, late3871/3856, one run PASS.
        See work/re/c_attach_parent_delete_report.md; no retail-module, collision,
        exact cleanup-frame or whole-item bench claim.
        """
        t=Test();start=[('MAP_REVEAL_ALL_PERM',m.player('p1'))];fire=[];stop=[]
        for phase,at in (('Fire',6.),('Stop',6+4/15),('Before',8.),('Delete',10.),('Late',14.)):
            start.append(('SET_MILLISECOND_TIMER','ParentDelete '+phase,at))
        for lane in ('base','high'):
            child,parent='Attach '+lane+' child','Attach '+lane+' parent'
            c='CNV_ParentDelete_'+lane;t.counters.append((c,lane+' parent delete'))
            start.extend(('UNIT_CHANGE_OBJECT_STATUS',v,'NO_ATTACK',1) for v in (child,parent))
            fire.extend((('UNIT_CHANGE_OBJECT_STATUS',child,'NO_ATTACK',0),('NAMED_ATTACK_NAMED',child,parent)))
            stop.append(('UNIT_CHANGE_OBJECT_STATUS',child,'NO_ATTACK',1))
            for phase,samples in (
                    ('Before',((2048,('UNIT_HAS_OBJECT_STATUS',child,status('ATTACHED'))),
                               (1024,('UNIT_HAS_OBJECT_STATUS',parent,status('VEHICLE_ATTACHED'))),
                               (512,('UNIT_HAS_OBJECT_STATUS',child,status('ENCLOSED'))),
                               (256,('UNIT_HAS_OBJECT_STATUS',child,status('UNATTACKABLE'))))),
                    ('Late',((16,('NAMED_NOT_DESTROYED',child)),(8,('NAMED_NOT_DESTROYED',parent)),
                             (4,('UNIT_HAS_OBJECT_STATUS',child,status('ATTACHED'))),
                             (2,('UNIT_HAS_OBJECT_STATUS',child,status('ENCLOSED'))),
                             (1,('UNIT_HAS_OBJECT_STATUS',child,status('UNATTACKABLE')))))):
                for weight,cond in samples:
                    t.scripts.append(Script(f'Test - parent delete {lane} {phase}{weight}',
                        [('TIMER_EXPIRED','ParentDelete '+phase),('FLAG','ParentDelete sampled '+phase,0),cond],
                        [('INCREMENT_COUNTER',weight,c)]))
        for phase in ('Before','Late'):
            t.scripts.append(Script('Test - parent delete close '+phase,[('TIMER_EXPIRED','ParentDelete '+phase)],
                                   [('SET_FLAG','ParentDelete sampled '+phase,1)]))
        t.scripts.insert(0,Script('Test - start',[],start))
        for phase,actions in (('Fire',fire),('Stop',stop),('Delete',[('NAMED_DELETE','Attach high parent')])):
            t.scripts.append(Script('Test - parent delete '+phase,[('TIMER_EXPIRED','ParentDelete '+phase)],actions))
        t.expect=[(label,16,'==',value,18) for (_,label),value in zip(t.counters,(3871,3856))]
        t.bench=[('bench_watch',dict(seconds=18.,every=.5,sheet=False,lines=2))]
        return t


    NOCOLL=('NO_COLLISIONS NON_AUTOACQUIRABLE','NO_COLLISIONS','NON_AUTOACQUIRABLE','NON_AUTOACQUIRABLE')


    def mission_nocoll():
        """Why engine_attach_parent's child reads NO_COLLISIONS 0: per lane the simple module's AttachedObjectStatus
        (NOCOLL) -- base the order swapped, high NO_COLLISIONS alone, order NON_AUTOACQUIRABLE with the script setting
        NO_COLLISIONS on the attached child at 9 s, removed the same set with no nugget (never attached: the control
        that this gun keeps a script-set bit; KNC a reads one on an infantry)."""
        m=mission();m.name='CampAttachNC'
        for lane,bits in zip(CASES,NOCOLL):
            u=next(u for u in m.units if u.id=='CNV_Attach'+lane.title())
            u.xml=re.sub(r'<AttachNugget\b.*?</AttachNugget>','',u.xml,flags=re.S)
            if lane!='removed':
                u.xml=u.xml.replace('</Nuggets>','<AttachNugget AttachModuleId="ModuleTag_Attach">'
                                    '<SpecialObjectFilter Rule="ANY" Include="VEHICLE"/></AttachNugget></Nuggets>')
            u.xml=u.xml.replace('AttachedObjectStatus="ENCLOSED UNATTACKABLE"',f'AttachedObjectStatus="{bits}"')
        return m


    def check_nocoll(m):
        """Child bits at 8 s (ATTACHED32 NON_AUTOACQUIRABLE16 NO_COLLISIONS8) and 12 s (4 2 1), each its own query.
        PREDICT 54/36/55/1: the module never gives NO_COLLISIONS (both orders), a script-set one stays on the child.
        Were it given as written: 63/45/55/1; were an attached child's NO_COLLISIONS cleared: 54/36/54/1."""
        t=Test();start=[('MAP_REVEAL_ALL_PERM',m.player('p1'))]
        for phase,at in (('Fire',6.),('Stop',6+4/15),('Before',8.),('Set',9.),('Late',12.)):
            start.append(('SET_MILLISECOND_TIMER','NoColl '+phase,at))
        acts={'Fire':[],'Stop':[],'Set':[]}
        for lane in CASES:
            child,parent='Attach '+lane+' child','Attach '+lane+' parent'
            c='CNV_NoColl_'+lane;t.counters.append((c,lane+' nocoll'))
            start.extend(('UNIT_CHANGE_OBJECT_STATUS',v,'NO_ATTACK',1) for v in (child,parent))
            acts['Fire']+=[('UNIT_CHANGE_OBJECT_STATUS',child,'NO_ATTACK',0),('NAMED_ATTACK_NAMED',child,parent)]
            acts['Stop'].append(('UNIT_CHANGE_OBJECT_STATUS',child,'NO_ATTACK',1))
            if lane in ('order','removed'):
                acts['Set'].append(('UNIT_CHANGE_OBJECT_STATUS',child,'NO_COLLISIONS',1))
            for phase,prefix in (('Before',8),('Late',1)):
                for weight,bit in ((4,'ATTACHED'),(2,'NON_AUTOACQUIRABLE'),(1,'NO_COLLISIONS')):
                    t.scripts.append(Script(f'Test - nocoll {lane} {phase}{weight}',
                        [('TIMER_EXPIRED','NoColl '+phase),('FLAG','NoColl sampled '+phase,0),
                         ('UNIT_HAS_OBJECT_STATUS',child,status(bit))],[('INCREMENT_COUNTER',prefix*weight,c)]))
        for phase in ('Before','Late'):
            t.scripts.append(Script('Test - nocoll close '+phase,[('TIMER_EXPIRED','NoColl '+phase)],
                                   [('SET_FLAG','NoColl sampled '+phase,1)]))
        t.scripts.insert(0,Script('Test - start',[],start))
        t.scripts+=[Script('Test - nocoll '+k,[('TIMER_EXPIRED','NoColl '+k)],v) for k,v in acts.items()]
        t.expect=[(label,13,'==',value,14) for (_,label),value in zip(t.counters,(54,36,55,1))]
        t.bench=[('bench_watch',dict(seconds=14.,every=.5,sheet=False,lines=4))]
        return t


    MISSION={'engine_attach':mission,'engine_attach_detach':mission_detach,'engine_attach_parent':mission_parent_death,
             'engine_attach_child':mission_child_death,'engine_attach_child_delete':mission_child_delete,
             'engine_attach_parent_delete':mission_parent_delete,'engine_attach_nocoll':mission_nocoll}
    CHECKS={'engine_attach':{'a':check},'engine_attach_detach':{'a':check_detach},'engine_attach_parent':{'a':check_parent_death},
            'engine_attach_child':{'a':check_child_death},'engine_attach_child_delete':{'a':check_child_delete},
            'engine_attach_parent_delete':{'a':check_parent_delete},'engine_attach_nocoll':{'n':check_nocoll}}
    return dict(MISSION=MISSION, CHECKS=CHECKS, shared=SimpleNamespace(
        _module_contract=_module_contract))


@cache
def engine_attachc4():
    """Native Tanya C4: nugget retained/deleted x normal/EXPLOSIVES_ATTACHED parent.

    Preserve the native host, weapon selection and AttachUpdate. Only rename the
    host/attach weapon and remove AttachNugget in high/removed. Scripted parent
    EXPLOSIVES_ATTACHED in order/removed isolates ForbiddenParentStatus; it is
    not evidence of the native explosives lifecycle. No instant-shot substitute.
    Prediction before bench: base attaches, sets MARCH_OF_DEATH, detonates the
    10000HP Hammer and survives; deleted nugget and forbidden-parent lanes do
    not attach or detonate. Module-autonomous attachment is an alternative.
    Packed: parent HP% * 100 + child alive8 + parent alive16 + ever child
    ATTACHED1 + ever parent MARCH_OF_DEATH2 + ever parent EXPLOSIVES_ATTACHED4.
    Expect15/10024/10028/10028. Latches include the scripted bit from start.
    No claim of exact dispatch, detach, damage source or complete Attach cover.
    Measured a:11/10024/10030/10028. The forbidden parent gets MARCH_OF_DEATH
    without child ATTACHED. Original expectations are retained. b removes only
    ForbiddenParentStatus from the modules; predict11/10024/15/10028.
    Measured b confirms11/10024/15/10028; both retained-nugget parents die.
    The normal parent never latched EXPLOSIVES_ATTACHED before death in either
    run. These are diagnostic observations; native module replay remains a gap.
    """
    import re
    from pathlib import Path

    from benches.weapon.firing.checks import engine_missile
    missile = engine_missile()["shared"]
    SAGE = missile.SAGE
    target = missile.target
    from maps import probe_range
    from model import status
    from parts import Mission, Script, Test, Unit

    LANES = ('base', 'high', 'order', 'removed')
    VALUES = (15, 10024, 10028, 10028)


    def mission():
        root = Path(SAGE)
        native = (root / 'Allied/Units/AlliedCommandoTech1.xml').read_text(encoding='utf-8')
        source = 'AlliedCommandoAttachWeapon'
        weapons = (root / 'GlobalData/Weapon.xml').read_text(encoding='utf-8')
        weapon = re.search(r'<WeaponTemplate\s+id="' + source + r'".*?</WeaponTemplate>', weapons, re.S).group()
        m = Mission(name='CampAttC4', map=probe_range, units=[], facts={})
        m.ext = True
        for lane in LANES:
            uid, wid = 'CNV_AttC4' + lane.title(), 'CNV_AttC4Gun' + lane.title()
            xml = native.replace('id="AlliedCommandoTech1"', f'id="{uid}"', 1)
            xml = xml.replace(f'Template="{source}"', f'Template="{wid}"')
            w = weapon.replace(f'id="{source}"', f'id="{wid}"', 1)
            if lane in ('high', 'removed'):
                w, n = re.subn(r'<AttachNugget\b.*?</AttachNugget>', '', w, flags=re.S)
                assert n == 1
            xml = xml.replace('<Behaviors>', '<Behaviors><DeletionUpdate id="ModuleTag_CNVProbe" '
                              'MinFrames="15" MaxFrames="4000"/>', 1)
            xml = xml.replace('</AssetDeclaration>', w + '</AssetDeclaration>')
            victim = target('CNV_AttC4Parent' + lane.title(), health=10000)
            victim.xml = victim.xml.replace('<Behaviors>', '<Behaviors><DeletionUpdate id="ModuleTag_CNVProbe" '
                                            'MinFrames="15" MaxFrames="4000"/>', 1)
            m.units.extend((Unit(uid, xml, link=['WeaponTemplate:' + wid]), victim))
            m.put(uid, lane + ' gun', side='p1', angle=1.5708, name='C4 ' + lane + ' child')
            m.put(victim.id, lane + ' gun', 0, 120, side='s1', angle=4.7124, name='C4 ' + lane + ' parent')
        return m


    def check(m):
        t = Test()
        start = [('MAP_REVEAL_ALL_PERM', m.player('p1')), ('SET_MILLISECOND_TIMER', 'C4 Fire', 6.)]
        fire = []
        for lane in LANES:
            child, parent = ['C4 ' + lane + ' ' + role for role in ('child', 'parent')]
            c = 'CNV_AttC4_' + lane
            start.extend(('UNIT_CHANGE_OBJECT_STATUS', who, 'NO_ATTACK', 1) for who in (child, parent))
            if lane in ('order', 'removed'):
                start.append(('UNIT_CHANGE_OBJECT_STATUS', parent, 'EXPLOSIVES_ATTACHED', 1))
            fire.extend((('UNIT_CHANGE_OBJECT_STATUS', child, 'NO_ATTACK', 0), ('NAMED_ATTACK_NAMED', child, parent)))
            t.counters.append((c, lane + ' c4 packed'))
            for weight, who, bit in ((1, child, 'ATTACHED'), (2, parent, 'MARCH_OF_DEATH'),
                                      (4, parent, 'EXPLOSIVES_ATTACHED')):
                t.scripts.append(Script('Test - latch ' + lane + bit,
                    [('NAMED_NOT_DESTROYED', who), ('UNIT_HAS_OBJECT_STATUS', who, status(bit))],
                    [('INCREMENT_COUNTER', weight, c + ' ever')]))
            t.scripts.append(Script('Test - reset ' + lane, [], [('SET_COUNTER', c, 0)], once=False))
            t.scripts.append(Script('Test - hp ' + lane, [('NAMED_NOT_DESTROYED', parent)],
                [('SET_UNIT_HEALTH_PERCENTAGE_TO_COUNTER', parent, c), ('COUNTER_MATH_VALUE', c, 2, 100),
                 ('INCREMENT_COUNTER', 16, c)], once=False))
            t.scripts.append(Script('Test - child alive ' + lane, [('NAMED_NOT_DESTROYED', child)],
                [('INCREMENT_COUNTER', 8, c)], once=False))
            t.scripts.append(Script('Test - pack ' + lane, [],
                [('COUNTER_MATH_COUNTER', c, 0, c + ' ever')], once=False))
        t.scripts.insert(0, Script('Test - start', [], start))
        t.scripts.append(Script('Test - fire', [('TIMER_EXPIRED', 'C4 Fire')], fire))
        t.expect = [(label, 22, '==', value, 24) for (_, label), value in zip(t.counters, VALUES)]
        t.bench = [('bench_watch', dict(seconds=24., every=.5, sheet=False, lines=4))]
        return t


    def without_parent_gate(m):
        m.name = 'CampAttC4Gate'
        for u in m.units:
            if u.id.startswith('CNV_AttC4') and not u.id.startswith('CNV_AttC4Parent'):
                u.xml, n = re.subn(r'\s+ForbiddenParentStatus="EXPLOSIVES_ATTACHED"', '', u.xml)
                assert n == 1
        t = check(m)
        t.expect = [(label, 22, '==', value, 24) for (_, label), value in
                    zip(t.counters, (11, 10024, 15, 10028))]
        return t


    MISSION = {'engine_attachc4': mission}
    CHECKS = {'engine_attachc4': {'a': check, 'b': without_parent_gate}}
    return dict(MISSION=MISSION, CHECKS=CHECKS, shared=SimpleNamespace(
        LANES=LANES))


def engine_attachmine():
    """Native magnetic-mine AttachNugget, retained/deleted x normal/forbidden target.

    The native SovietMagneticBomb host fires the native attach weapon on creation;
    its one-second LifetimeUpdate, geometry and AttachUpdate are unchanged. Only
    rename host/weapon and delete AttachNugget in negative controls. Create at the
    parent waypoint at6s, after SPECIAL_ARMOR_ACTIVE is set in order/removed.
    PREDICT111/110/110/110: ever ATTACHED1 + ever child alive10 + parent alive100
    at10s. This isolates native mine dispatch and the target-status gate without
    claiming the Flak Trooper projectile/OCL path or explosion damage attribution.
    Raw evidence and unresolved alternatives: work/re/c_attachmine_report.md.
    MEASURED a111/110/111/110: the single SPECIAL_ARMOR_ACTIVE lane attached.
    b sets all three listed forbidden statuses and latches each bit independently
    (AIRBORNE_TARGET1000, VEHICLE_ATTACHED2000, SPECIAL_ARMOR_ACTIVE4000).
    PREDICT b111/110/7110/7110; this separates an unwritten status from mask/gate
    semantics. The original a prediction remains unchanged.
    MEASURED b111/110/7111/7110: all three parent bits latch, retained mine
    still attaches. Two runs exhausted; gate/dispatch cause remains a gap.
    """
    import re
    from pathlib import Path

    from benches.weapon.firing.checks import engine_missile
    missile = engine_missile()["shared"]
    SAGE = missile.SAGE
    target = missile.target
    from maps import probe_range
    from model import status
    from parts import Mission, Script, Test, Unit

    LANES = ('base', 'high', 'order', 'removed')
    VALUES = (111, 110, 110, 110)
    SOURCE = 'SovietAntiVehicleInfantryMagneticBombAttachWeapon'


    def mission():
        root = Path(SAGE)
        native = (root/'Soviet/Props/SovietMagneticBomb.xml').read_text(encoding='utf-8')
        weapons = (root/'GlobalData/Weapon.xml').read_text(encoding='utf-8')
        weapon = re.search(r'<WeaponTemplate\s+id="'+SOURCE+r'".*?</WeaponTemplate>', weapons, re.S).group()
        m = Mission(name='CampAttMine', map=probe_range, units=[], facts={})
        m.ext = True
        for lane in LANES:
            uid, wid = 'CNV_AttMine'+lane.title(), 'CNV_AttMineGun'+lane.title()
            xml = native.replace('id="SovietMagneticBomb"', f'id="{uid}"', 1)
            xml = xml.replace(f'WeaponName="{SOURCE}"', f'WeaponName="{wid}"')
            w = weapon.replace(f'id="{SOURCE}"', f'id="{wid}"', 1)
            if lane in ('high', 'removed'):
                w, count = re.subn(r'<AttachNugget\b.*?</AttachNugget>', '', w, flags=re.S)
                assert count == 1
            xml = xml.replace('</AssetDeclaration>', w+'</AssetDeclaration>')
            parent = target('CNV_AttMineParent'+lane.title(), health=100000)
            m.units.extend((Unit(uid, xml, link=['WeaponTemplate:'+wid]), parent))
            m.put(parent.id, lane+' gun', side='s1', name='Mine '+lane+' parent')
            m.waypoint(lane+' mine', 'Mine spawn '+lane, lane+' gun', 0, 0)
        return m


    def check(m):
        t = Test()
        start = [('MAP_REVEAL_ALL_PERM', m.player('p1')),
                 ('SET_MILLISECOND_TIMER', 'Mine Spawn', 6.),
                 ('SET_MILLISECOND_TIMER', 'Mine Sample', 10.)]
        spawn = []
        for lane in LANES:
            child, parent = ['Mine '+lane+' '+role for role in ('child', 'parent')]
            c = 'CNV_AttMine_'+lane
            t.counters.append((c, lane+' mine packed'))
            start.append(('UNIT_CHANGE_OBJECT_STATUS', parent, 'NO_ATTACK', 1))
            if lane in ('order', 'removed'):
                start.append(('UNIT_CHANGE_OBJECT_STATUS', parent, 'SPECIAL_ARMOR_ACTIVE', 1))
            spawn.append(('CREATE_NAMED_ON_TEAM_AT_WAYPOINT', child, 'CNV_AttMine'+lane.title(),
                          m.team('p1'), m.mark(lane+' mine')))
            for weight, suffix, conditions in (
                (10, 'born', [('NAMED_NOT_DESTROYED', child)]),
                (1, 'attached', [('NAMED_NOT_DESTROYED', child),
                                 ('UNIT_HAS_OBJECT_STATUS', child, status('ATTACHED'))]),
                (100, 'parent', [('TIMER_EXPIRED', 'Mine Sample'), ('NAMED_NOT_DESTROYED', parent)])):
                t.scripts.append(Script('Test - '+suffix+lane, conditions,
                                        [('INCREMENT_COUNTER', weight, c)]))
        t.scripts.insert(0, Script('Test - start', [], start))
        t.scripts.append(Script('Test - spawn', [('TIMER_EXPIRED', 'Mine Spawn')], spawn))
        t.expect = [(label, 12, '==', value, 14) for (_, label), value in zip(t.counters, VALUES)]
        t.bench = [('bench_watch', dict(seconds=14., every=.5, sheet=False, lines=4))]
        return t


    def all_forbidden(m):
        m.name = 'CampMineGate'
        t = check(m)
        for lane in ('order', 'removed'):
            parent = 'Mine '+lane+' parent'
            c = 'CNV_AttMine_'+lane
            for weight, bit in ((1000, 'AIRBORNE_TARGET'), (2000, 'VEHICLE_ATTACHED'),
                                (4000, 'SPECIAL_ARMOR_ACTIVE')):
                if bit != 'SPECIAL_ARMOR_ACTIVE':
                    t.scripts[0].do.append(('UNIT_CHANGE_OBJECT_STATUS', parent, bit, 1))
                t.scripts.append(Script('Test - gate '+lane+bit,
                    [('NAMED_NOT_DESTROYED', parent), ('UNIT_HAS_OBJECT_STATUS', parent, status(bit))],
                    [('INCREMENT_COUNTER', weight, c)]))
        t.expect = [(label, 12, '==', value, 14) for (_, label), value in
                    zip(t.counters, (111, 110, 7110, 7110))]
        return t


    MISSION = {'engine_attachmine': mission}
    CHECKS = {'engine_attachmine': {'a': check, 'b': all_forbidden}}
    return dict(MISSION=MISSION, CHECKS=CHECKS)


def engine_attachterror():
    """Native Terror Drone AttachNugget: retained/deleted nugget x live/killed parent.

    PREDICT before14s 127/127/3/3, late20s 127007/127000/3006/3002.
    Before packed bits: child ATTACHED64, parent VEHICLE_ATTACHED32,
    parent BOOBY_TRAPPED16, child ENCLOSED8/UNATTACKABLE4, childAlive2,
    parentAlive1. Late adds parentAlive4/childAlive2/live-parent attached1;
    before is multiplied by1000. Dead objects' status is never queried late.
    Parent NAMED_KILL at16s distinguishes native DIE_WHEN_PARENT_DIES_FROM_NOT_ME
    from the simple module's surviving child. Normal damage and exact death frame
    remain gaps. The native host, melee weapon and AttachUpdate are preserved;
    only the negative controls remove AttachNugget. Target HP is100000 to keep
    native internal damage from killing it before the scripted comparison.
    MEASURED2026-11-15: retained/deleted x live/killed reads127/127/3/3
    at14s; final127007/127000/3006/3002, PASS. First launch stopped in
    mode selection (no samples); unchanged --no-build restart reached the map.
    See work/re/c_attachterror_report.md. These snapshots do not publish the
    first dispatch position/frame, damage source or parent-death notification;
    complex filter and module handling remain gaps, not whole-item promotion.
    """
    import re
    from pathlib import Path

    from benches.weapon.firing.checks import engine_missile
    missile = engine_missile()["shared"]
    SAGE = missile.SAGE
    target = missile.target
    from maps import probe_range
    from model import status
    from parts import Mission, Script, Test, Unit

    LANES = ('base', 'high', 'order', 'removed')
    VALUES = (127007, 127000, 3006, 3002)


    def mission():
        root = Path(SAGE)
        native = (root/'Soviet/Units/SovietScoutVehicle.xml').read_text(encoding='utf-8')
        source = 'SovietScoutVehicleMeleeAttachWeapon'
        weapons = (root/'GlobalData/Weapon.xml').read_text(encoding='utf-8')
        weapon = re.search(r'<WeaponTemplate\s+id="'+source+r'".*?</WeaponTemplate>', weapons, re.S).group()
        m = Mission(name='CampAttTerror', map=probe_range, units=[], facts={})
        for lane in LANES:
            uid, wid = 'CNV_AttTerror'+lane.title(), 'CNV_AttTerrorGun'+lane.title()
            xml = native.replace('id="SovietScoutVehicle"', f'id="{uid}"', 1)
            xml = xml.replace(f'Template="{source}"', f'Template="{wid}"')
            w = weapon.replace(f'id="{source}"', f'id="{wid}"', 1)
            if lane in ('order', 'removed'):
                w, n = re.subn(r'<AttachNugget\b.*?</AttachNugget>', '', w, flags=re.S)
                assert n == 1
            xml = xml.replace('</AssetDeclaration>', w+'</AssetDeclaration>')
            victim = target('CNV_AttTerrorParent'+lane.title(), health=100000)
            m.units.extend((Unit(uid, xml, link=['WeaponTemplate:'+wid]), victim))
            m.put(uid, lane+' gun', side='p1', angle=1.5708, name='Terror '+lane+' child')
            m.put(victim.id, lane+' gun', 0, 120, side='s1', angle=4.7124,
                  name='Terror '+lane+' parent')
        return m


    def check(m):
        t = Test()
        start = [('MAP_REVEAL_ALL_PERM', m.player('p1'))]
        for phase, at in (('Fire', 6.), ('Before', 14.), ('Kill', 16.), ('Late', 20.)):
            start.append(('SET_MILLISECOND_TIMER', 'AttTerror '+phase, at))
        fire = []
        for lane in LANES:
            child, parent = ['Terror '+lane+' '+role for role in ('child', 'parent')]
            c = 'CNV_AttTerror_'+lane
            t.counters.append((c, lane+' terror packed'))
            start.extend(('UNIT_CHANGE_OBJECT_STATUS', who, 'NO_ATTACK', 1) for who in (child, parent))
            fire.extend((('UNIT_CHANGE_OBJECT_STATUS', child, 'NO_ATTACK', 0),
                         ('NAMED_ATTACK_NAMED', child, parent)))
            before = ((64, child, 'ATTACHED'), (32, parent, 'VEHICLE_ATTACHED'),
                      (16, parent, 'BOOBY_TRAPPED'), (8, child, 'ENCLOSED'),
                      (4, child, 'UNATTACKABLE'))
            for weight, who, bit in before:
                t.scripts.append(Script('Test - before '+lane+bit,
                    [('TIMER_EXPIRED', 'AttTerror Before'), ('FLAG', 'AttTerror sampled Before', 0),
                     ('NAMED_NOT_DESTROYED', who), ('UNIT_HAS_OBJECT_STATUS', who, status(bit))],
                    [('INCREMENT_COUNTER', 1000*weight, c)]))
            for phase, multiplier, lives in (('Before', 1000, ((2, child), (1, parent))),
                                              ('Late', 1, ((2, child), (4, parent)))):
                for weight, who in lives:
                    t.scripts.append(Script('Test - alive '+phase+who,
                        [('TIMER_EXPIRED', 'AttTerror '+phase), ('FLAG', 'AttTerror sampled '+phase, 0),
                         ('NAMED_NOT_DESTROYED', who)], [('INCREMENT_COUNTER', multiplier*weight, c)]))
            t.scripts.append(Script('Test - late parent '+lane,
                [('TIMER_EXPIRED', 'AttTerror Late'), ('FLAG', 'AttTerror sampled Late', 0),
                 ('NAMED_NOT_DESTROYED', parent), ('UNIT_HAS_OBJECT_STATUS', parent, status('VEHICLE_ATTACHED'))],
                [('INCREMENT_COUNTER', 1, c)]))
        for phase in ('Before', 'Late'):
            t.scripts.append(Script('Test - close '+phase, [('TIMER_EXPIRED', 'AttTerror '+phase)],
                                   [('SET_FLAG', 'AttTerror sampled '+phase, 1)]))
        t.scripts.insert(0, Script('Test - start', [], start))
        t.scripts.extend((Script('Test - fire', [('TIMER_EXPIRED', 'AttTerror Fire')], fire),
                          Script('Test - kill', [('TIMER_EXPIRED', 'AttTerror Kill')],
                                 [('NAMED_KILL', 'Terror '+lane+' parent') for lane in ('high', 'removed')])))
        t.expect = [(label, 22, '==', value, 24) for (_, label), value in zip(t.counters, VALUES)]
        t.bench = [('bench_watch', dict(seconds=24., every=.5, sheet=False, lines=4))]
        return t


    def forbidden(plan):
        """A420: DIE_WHEN_PARENT_HAS_FORBIDDEN_STATUS (UNDERGOING_REPAIR, ignored under UNDER_IRON_CURTAIN). plan:
        {lane: ((second, role, bit), ...)} set by script. Packed per lane: 100 child alive when the 16 s bit goes on
        (meant as a frame count; the script runs once) + at 20 s parent alive 1 / VEHICLE_ATTACHED 2 / BOOBY_TRAPPED
        4, child alive 8 / ATTACHED 16, +32 child ATTACHED at 14 s. MEASURED 11-27 (CampAttTerrorF/G_mcp_1127_1915 /
        _1914): f 133 / 133 / 109 / 109 -- the repair bit kills the drone, its parent's bits go with it, the parent's
        curtain does not spare it (predicted it would); g 163 / 163 / 109 / 109 -- the drone's own curtain does."""
        def check(m):
            t = Test()
            start = [('MAP_REVEAL_ALL_PERM', m.player('p1'))]
            for phase, at in (('Fire', 6.), ('Before', 14.), ('Curtain', 15.), ('Kill', 16.), ('Late', 20.)):
                start.append(('SET_MILLISECOND_TIMER', 'AttTerror '+phase, at))
            fire, sets = [], {}
            for lane in LANES:
                child, parent = ['Terror '+lane+' '+role for role in ('child', 'parent')]
                c = 'CNV_AttTerror_'+lane
                t.counters.append((c, lane+' terror packed'))
                start.extend(('UNIT_CHANGE_OBJECT_STATUS', who, 'NO_ATTACK', 1) for who in (child, parent))
                fire.extend((('UNIT_CHANGE_OBJECT_STATUS', child, 'NO_ATTACK', 0), ('NAMED_ATTACK_NAMED', child, parent)))
                for at, role, bit in plan.get(lane, ()):
                    who = 'Terror '+lane+' '+role
                    sets.setdefault('Curtain' if at == 15 else 'Kill', []).append(
                        ('UNIT_CHANGE_OBJECT_STATUS', who, status(bit), 1))
                t.scripts.append(Script('Test - frames '+lane,
                    [('TIMER_EXPIRED', 'AttTerror Kill'), ('FLAG', 'AttTerror sampled Late', 0),
                     ('NAMED_NOT_DESTROYED', child)], [('INCREMENT_COUNTER', 100, c)]))
                for phase, weight, who, bit in (('Before', 32, child, 'ATTACHED'), ('Late', 1, parent, None),
                                                ('Late', 2, parent, 'VEHICLE_ATTACHED'), ('Late', 4, parent, 'BOOBY_TRAPPED'),
                                                ('Late', 8, child, None), ('Late', 16, child, 'ATTACHED')):
                    t.scripts.append(Script(f'Test - {phase} {lane} {weight}',
                        [('TIMER_EXPIRED', 'AttTerror '+phase), ('FLAG', 'AttTerror sampled '+phase, 0),
                         ('NAMED_NOT_DESTROYED', who)] + ([('UNIT_HAS_OBJECT_STATUS', who, status(bit))] if bit else []),
                        [('INCREMENT_COUNTER', weight, c)]))
            for phase in ('Before', 'Late'):
                t.scripts.append(Script('Test - close '+phase, [('TIMER_EXPIRED', 'AttTerror '+phase)],
                                        [('SET_FLAG', 'AttTerror sampled '+phase, 1)]))
            t.scripts.insert(0, Script('Test - start', [], start))
            t.scripts.append(Script('Test - fire', [('TIMER_EXPIRED', 'AttTerror Fire')], fire))
            for phase, acts in sets.items():
                t.scripts.append(Script('Test - set '+phase, [('TIMER_EXPIRED', 'AttTerror '+phase)], acts))
            t.bench = [('bench_watch', dict(seconds=24., every=.5, sheet=False, lines=4))]
            return t
        return check

    REPAIR, CURTAIN = (16, 'parent', 'UNDERGOING_REPAIR'), (15, 'parent', 'UNDER_IRON_CURTAIN')
    MISSION = {'engine_attachterror': mission}
    CHECKS = {'engine_attachterror': {'a': check,
        'f': forbidden({'base': (REPAIR,), 'high': (CURTAIN, REPAIR), 'order': (REPAIR,)}),
        'g': forbidden({'base': ((15, 'child', 'UNDER_IRON_CURTAIN'), REPAIR), 'high': (CURTAIN,)})}}
    return dict(MISSION=MISSION, CHECKS=CHECKS)


def engine_cryo():
    """Engine unit test: the freeze (SecondaryDamageTracker, ADR 0019 layer 3; engine line C round 7) -- how fast a cryo
    beam freezes a tank, how long it stays frozen once the beam is gone. The simulator's rule (Damage.chill, INFERRED from the
    SDK data, never benched): the cryocopter's beam adds 75 cold a second, the tracker melts 25 a second (BaseVehicle:
    DissipateAmount 25 per UpdateDuration, cap 200 % of max health), the highest step reached by Fraction of max health
    applies its modifier, 1.0 = UNDER_FROZEN (stopped, silent, armour CryoBeamFrozenArmor). For a Hammer (550 health):
    frozen after 550 / (75 - 25) = 11 s of beam; kept to 200 % = 1100 cold, so after the beam ends it melts 25 a second.

    On the Niagara map's west field (as engine_heal; the sim has no ground for probe_range): retail's cryocopter (AlliedSupportAircraft) and a retail Hammer (SovietAntiVehicleVehicleTech1,
    the enemy's, NO_ATTACK so it only stands), ordered at ORDER to be attacked. The copter is deleted by script at STOP
    (a beam that has run `STOP - ORDER` seconds). Variants (one a check; the idle copters are deleted at the start):
      one   one copter
      two   two copters (twice the beam)

    Counters: 先冻 = frames from the order until UNDER_FROZEN is first seen; 冻住 = frames UNDER_FROZEN is set in all;
    化冰 = of those, the frames after the copter was deleted (the melt time). The reading is the frame count the script
    saw (docs/engine/weapons.md 1: one more than the frame it happened).

    Bench 11-09 (round 7, first built on probe_range; work/bench_results/engine_cryo__<variant>.json keeps the latest run):
      one  先冻 139, 冻住 705, 化冰 334     two  先冻 79, 冻住 765, 化冰 334
    -> frozen until 844 frames after the order whatever the beam (STOP + melt), melting 334 frames = (1100 - 550) / 25 a
    second: the 200 % cap and the 25 a second are right. The simulator (Niagara) reads one 189 / 652 / 331, two 90 / 751 /
    331: the same ending, a slower copter flight. tests/test_simbench.py::test_cryo_*.

    Sim's answer (before the bench): one: 先冻 ~ 165 + the copter's flight (11 s of beam), then it melts (1100 - 550)/25 =
    22 s when the beam ran long enough to fill the cap; two: 先冻 ~ 90 (550 / 125 = 4.4 s of beam).
    """
    import resources
    from maps import niagara
    from model import status
    from parts import Mission, Script, Test

    COPTER, TANK = 'AlliedSupportAircraft', 'SovietAntiVehicleVehicleTech1'
    ORDER, STOP, RUN = 6.0, 40.0, 90.0
    VARIANTS = {'one': 1, 'two': 2}


    def mission():
        m = Mission(name='CampCryo', map=resources.measured(niagara), units=[], facts={})
        m.put(TANK, 'west field', -120.0, 560.0, side='s1', role='cryo tank', name='UNIT - CNV Cryo Tank')
        for k in range(2):
            m.put(COPTER, 'west field', -180.0 + 120.0 * k, 160.0, side='p1', role=f'cryo copter {k}',
                  name=f'UNIT - CNV Cryo Copter {k}')
        return m


    def cryo_test(m, k):
        n = VARIANTS[k]
        t = Test()
        tank = m.role('cryo tank').name
        copters = [m.role(f'cryo copter {i}').name for i in range(2)]
        frozen = ('UNIT_HAS_OBJECT_STATUS', tank, status('UNDER_FROZEN'))
        start = [('MAP_REVEAL_ALL_PERM', m.player('p1')), ('UNIT_CHANGE_OBJECT_STATUS', tank, 'NO_ATTACK', 1)]
        start += [('NAMED_DELETE', c) for c in copters[n:]]
        start += [('SET_MILLISECOND_TIMER', 'Test Order', ORDER), ('SET_MILLISECOND_TIMER', 'Test Stop', STOP)]
        t.scripts.append(Script('Test - start', [], start))
        t.scripts.append(Script('Test - order', [('TIMER_EXPIRED', 'Test Order')],
                                [('NAMED_ATTACK_NAMED', c, tank) for c in copters[:n]] + [('SET_FLAG', 'Test Ordered', 1)]))
        t.scripts.append(Script('Test - stop', [('TIMER_EXPIRED', 'Test Stop')],
                                [('NAMED_DELETE', c) for c in copters[:n]] + [('SET_FLAG', 'Test Stopped', 1)]))
        t.scripts.append(Script('Test - seen', [frozen], [('SET_FLAG', 'Test Seen', 1)]))
        rows = [('CNV_Cryo_First', '先冻', [('FLAG', 'Test Ordered', 1), ('FLAG', 'Test Seen', 0)]),
                ('CNV_Cryo_Held', '冻住', [frozen]),
                ('CNV_Cryo_Melt', '化冰', [('FLAG', 'Test Stopped', 1), frozen])]
        for c, label, cond in rows:
            t.counters.append((c, label))
            t.scripts.append(Script(f'Test - {c}', cond, [('INCREMENT_COUNTER', 1, c)], once=False))
        t.expect = [('冻住', 0, 'ever>=', 1, RUN - 1)]
        t.bench = [('bench_watch', dict(seconds=RUN, every=1, sheet=False, lines=len(t.counters)))]
        return t


    MISSION = {'engine_cryo': mission}
    CHECKS = {'engine_cryo': {k: (lambda m, k=k: cryo_test(m, k)) for k in VARIANTS}}
    return dict(MISSION=MISSION, CHECKS=CHECKS)


def engine_lift():
    """ActivateLiftObjectNugget: historical four-lane release diagnostics.

    One10UNRES marker at6s hits each1000HP passive Hammer (99%, alive).
    base has no lift; high Lifetime2s; order Lifetime.2s; removed Lifetime2s
    but no caster LiftObjectUpdate. All eligible VEHICLE targets, same geometry.
    The caster module uses LiftVelocity4, elevation cap60, TimeIncrement.5s,
    MaxTimeLifted8s; no SoftLandingWeapon or AirplaneCrashWeapon. Only caster
    module presence and nugget lifetime differ. GUESSED: activation is owned
    by the caster, LIFTED_INTO_AIR remains set during the lift lease, clears
    after release/fall. Snapshot at7s separates long and short leases;18s is
    past both leases AND the module's8s cap. Snapshot bits packed early*1e7+
    late*1e6+alive*1000+HP%. Do not infer a vertical trajectory from these bits.
    No force movement/landing damage/air targets/structures/range boundaries.
    Each gun loads an empty single clip in1s; fire6s, NO_ATTACK6+4/15.
    First bench a:1099/11001099/11001099/1099. Both durations set and
    retain the bit through18s without SoftLandingWeapon. The stock landing
    weapon applies a0.1s LIFTED_INTO_AIR modifier; landing adds ONLY that
    stock module field, no damage/geometry/timer changes, and retests the
    original snapshot hypothesis. No expiry model is fitted to the first run.
    Second bench landing:1099/10001099/10001099/1099. Landing clears the
    late bit, but short Lifetime still does not clear by7s. STOP: activation
    and landing prerequisite are observed, lifetime/renewal rule unresolved.
    Expectations below preserve OBSERVATIONS; neither run passed the original
    hypothesis. D50 (work/re/d50_lift_release.md) now explains the timer:
    TimeIncrement .5s gives 7 frames per hit, renewal caps at 120 frames;
    Lifetime is not used and release does not clear LIFTED. Thus a replays
    without a landing model. Landing clear remains INFERRED and unimplemented;
    its replay is a strict xfail. These snapshots do not measure timer frames.
    """
    from maps import probe_range
    from model import status
    from parts import Mission, Script, Test
    from benches.weapon.target_effects.checks import engine_weaponfx
    gun = engine_weaponfx()["shared"].gun
    from benches.weapon.firing.checks import engine_missile
    target = engine_missile()["shared"].target

    CASES=(('base',0,True),('high',2,True),('order',.2,True),('removed',2,False))


    def mission():
        m=Mission(name='CampLift',map=probe_range,units=[],facts={})
        for lane,seconds,module in CASES:
            extra=(f'<ActivateLiftObjectNugget Lifetime="{seconds:g}s">'
                   '<SpecialObjectFilter Rule="ANY" Include="VEHICLE"/></ActivateLiftObjectNugget>'
                   if seconds else '')
            u=gun('CNV_Lift'+lane.title(),10,extra)
            u.xml=u.xml.replace('DamageType="EXPLOSIVE"','DamageType="UNRESISTABLE"')
            if module:
                u.xml=u.xml.replace('<Behaviors>','<Behaviors>'+
                    '<LiftObjectUpdate id="ModuleTag_Lift" CrusherModifiesVelocity="false" '
                    'LiftVelocity="4" MaxElevationFromGround="60" TimeIncrement="0.5s" MaxTimeLifted="8s"/>',1)
            v=target('CNV_LiftVictim'+lane.title(),health=1000)
            m.units.extend((u,v))
            m.put(u.id,lane+' gun',side='p1',angle=1.5708,name='Lift '+lane+' gun')
            m.put(v.id,lane+' gun',0,450,side='s1',angle=4.7124,name='Lift '+lane+' victim')
        return m


    def check(m,landing=False):
        if landing:
            for u in m.units:
                if '<LiftObjectUpdate' in u.xml:
                    u.xml=u.xml.replace('MaxTimeLifted="8s"/>',
                        'MaxTimeLifted="8s" SoftLandingWeapon="JapanCommandoSoftLanding"/>')
        t=Test();start=[('MAP_REVEAL_ALL_PERM',m.player('p1')),
            ('SET_MILLISECOND_TIMER','Lift Fire',6.),('SET_MILLISECOND_TIMER','Lift Stop',6+4/15),
            ('SET_MILLISECOND_TIMER','Lift Early',7.),('SET_MILLISECOND_TIMER','Lift Late',18.)]
        fire=[];stop=[]
        for lane,_,_ in CASES:
            g,v='Lift '+lane+' gun','Lift '+lane+' victim';c='CNV_Lift_'+lane
            start.extend(('UNIT_CHANGE_OBJECT_STATUS',n,'NO_ATTACK',1) for n in (g,v))
            fire.extend((('UNIT_CHANGE_OBJECT_STATUS',g,'NO_ATTACK',0),('NAMED_ATTACK_NAMED',g,v)))
            stop.append(('UNIT_CHANGE_OBJECT_STATUS',g,'NO_ATTACK',1))
            t.counters.append((c,lane+' packed'))
            t.scripts.extend((Script('Test - hp '+lane,[],[
                ('SET_COUNTER',c,0),('SET_UNIT_HEALTH_PERCENTAGE_TO_COUNTER',v,c),
                ('COUNTER_MATH_COUNTER',c,0,c+'State')],once=False),
                Script('Test - alive '+lane,[('NAMED_NOT_DESTROYED',v)],[('INCREMENT_COUNTER',1000,c)],once=False)))
            for phase,weight in (('Early',10000000),('Late',1000000)):
                t.scripts.append(Script('Test - '+phase+' '+lane,
                    [('TIMER_EXPIRED','Lift '+phase),('FLAG','Lift sampled '+phase,0),
                     ('UNIT_HAS_OBJECT_STATUS',v,status('LIFTED_INTO_AIR'))],
                    [('INCREMENT_COUNTER',weight,c+'State')]))
        for phase in ('Early','Late'):
            t.scripts.append(Script('Test - close sample '+phase,[('TIMER_EXPIRED','Lift '+phase)],
                                   [('SET_FLAG','Lift sampled '+phase,1)]))
        t.scripts.insert(0,Script('Test - start',[],start))
        t.scripts.extend((Script('Test - fire',[('TIMER_EXPIRED','Lift Fire')],fire),
                          Script('Test - stop',[('TIMER_EXPIRED','Lift Stop')],stop)))
        observed=(1099,10001099,10001099,1099) if landing else (1099,11001099,11001099,1099)
        t.expect=[(label,20,'==',n,22) for (_,label),n in zip(t.counters,observed)]
        t.bench=[('bench_watch',dict(seconds=22.,every=.5,sheet=False,lines=4))]
        return t


    MISSION={'engine_lift':mission}
    CHECKS={'engine_lift':{'a':check,'landing':lambda m:check(m,landing=True)}}
    return dict(MISSION=MISSION, CHECKS=CHECKS)


def engine_lift_probe():
    """Engine line A round 169 (for C's ActivateLiftObjectNugget, work/re/handoff-c.md): a lifted body's height frame by
    frame and the frame it lands.

    engine_lift's counters are two snapshots (7 s / 18 s) of LIFTED_INTO_AIR: they cannot give the lift's height or the
    landing frame. Here every victim is engine_lift's 1000-health Hammer carrying ra3ext's CNVProbe (the same
    DeletionUpdate tag as engine_knock_probe's CNV_KnockHammer), so the run folder's ra3ext.log has its x / y / z; and a
    script counts, every frame, whether the victim has LIFTED_INTO_AIR (one counter a lane: the frames it was set).

    Four lanes (probe_range's base / high / order / removed sites), engine_lift's gun (one 10 UNRESISTABLE shot at 6 s,
    the ActivateLiftObjectNugget Lifetime 2 s -- unused, D50) and caster module (LiftVelocity 4, MaxTimeLifted 8 s);
    each check sets TimeIncrement, MaxElevationFromGround and SoftLandingWeapon (JapanCommandoSoftLanding) a lane:
      fall    base: no nugget, no module (control) / soft 0.5 s / bare 0.5 s without SoftLandingWeapon / long 1 s
      height  lowlong 1 s capped at 28 / long 1 s (on soft's old site) / mid 0.7 s / soft 0.5 s (on long's old site)
    Prediction from the data (D50 / D52, work/re/d50_lift_release.md): a hit lifts trunc(TimeIncrement x 15) frames --
    soft / bare 7, long 15 -- z + 4 a frame while under the cap (soft / bare 28 up, long 60), then the physics drops it;
    on touching down the SoftLandingWeapon puts a 0.1 s LIFTED_INTO_AIR modifier whose expiry clears the bit (landing
    + 1..2 frames). Without it (bare) the bit stays. The fall is not in the data (knock-back's 64 / 15^2 a frame^2 would
    take 14 frames from 28, 21 from 60).

    Bench 11-11 fall CampLPFall_mcp_1111_202526 PASS as written (work/logs/a169_liftfall.log): the hit at frame 93 (90 +
    3; both releases 7 / 15 frames after it). Release = a shock with zero velocity through knock-back's own curve (the
    `shock ... v=0` line from the lift's release, then a second from the physics the same frame): soft from z 240.5
    (212.5 + 28 = 7 x 4) at frame 100, `build land=2310,850,212.5 a=0 b=1.75` (the +10 on the 20 grid, as knock-back),
    N 20; long from 272.5 (+60, the cap: 15 x 4) at frame 108, b 2.6087, N 26 then 25. The probe writes no line while
    the body is lifted or falling; its first line after is at the landing spot, soft frame 120 (= 100 + 20), long 133
    (= 108 + 25), x moved 10. Counters: soft lifted 28 frames (93 .. 120: cleared one frame after it lands); bare and
    long never cleared (150 frames at the end) -- long has the SoftLandingWeapon (the shock line carries it) but kept
    the bit, against D52. height asks why.
    """
    from maps import probe_range
    from model import status
    from parts import Mission, Script, Test
    from benches.weapon.target_effects.checks import engine_weaponfx
    gun = engine_weaponfx()["shared"].gun
    from benches.weapon.firing.checks import engine_missile
    target = engine_missile()["shared"].target
    from benches.weapon.target_effects.checks import engine_suppress_probe
    suppress_probe = engine_suppress_probe()["shared"]
    EVERY = suppress_probe.EVERY
    LINES = suppress_probe.LINES

    FIRE, RUN = 6.0, 13.0
    SITES = ('base', 'high', 'order', 'removed')       # probe_range lanes, one caster + victim each
    # check -> {site: (label, TimeIncrement s or None = no nugget and no module, SoftLandingWeapon, MaxElevationFromGround)}
    CONFIGS = {
        'fall': {'base': ('base', None, False, 60), 'high': ('soft', 0.5, True, 60),
                 'order': ('bare', 0.5, False, 60), 'removed': ('long', 1.0, True, 60)},
        # why long (60 up) kept the bit: lowlong lifts as long as long but no higher than soft; mid 40 up; long moved
        # to soft's site and soft to long's (the site ruled out)
        'height': {'base': ('lowlong', 1.0, True, 28), 'high': ('long', 1.0, True, 60),
                   'order': ('mid', 0.7, True, 60), 'removed': ('soft', 0.5, True, 60)},
    }
    # from RUN - 1 s. fall: as first written (passed). height: the prediction if the fall's height decides
    EXPECT = {'fall': [('base lifted frames', RUN - 1, '==', 0), ('soft lifted frames', RUN - 1, '>=', 7),
                       ('long lifted frames', RUN - 1, '>=', 15), ('bare lifted frames', RUN - 1, '>=', 60)],
              'height': [('lowlong lifted frames', RUN - 1, '<=', 40), ('long lifted frames', RUN - 1, '>=', 60),
                         ('soft lifted frames', RUN - 1, '==', 28)]}


    def victim(uid):
        v = target(uid, health=1000)
        v.xml = v.xml.replace('<Behaviors>', (
            f'<Behaviors>\n'
            f'\t\t\t<DeletionUpdate id="ModuleTag_CNVProbe" MinFrames="{EVERY}" MaxFrames="{LINES}"/>'
        ), 1)
        v.what += '；多一个 ra3ext 的 CNVProbe 模块，逐帧记位置'
        return v


    def caster(site, config):
        _, inc, soft, cap = config[site]
        extra = ('<ActivateLiftObjectNugget Lifetime="2s"><SpecialObjectFilter Rule="ANY" Include="VEHICLE"/>'
                 '</ActivateLiftObjectNugget>' if inc else '')
        u = gun('CNV_LiftP' + site.title(), 10, extra)
        u.xml = u.xml.replace('DamageType="EXPLOSIVE"', 'DamageType="UNRESISTABLE"')
        if inc:
            landing = ' SoftLandingWeapon="JapanCommandoSoftLanding"' if soft else ''
            u.xml = u.xml.replace('<Behaviors>', '<Behaviors><LiftObjectUpdate id="ModuleTag_Lift" '
                                  f'CrusherModifiesVelocity="false" LiftVelocity="4" MaxElevationFromGround="{cap:g}" '
                                  f'TimeIncrement="{inc:g}s" MaxTimeLifted="8s"{landing}/>', 1)
        return u


    def name(site, part):
        return f'Lift probe {site} {part}'


    def mission():
        m = Mission(name='CampLP', map=probe_range, units=[], facts={})
        m.ext = True                  # + the check's name: CampLPFall / CampLPHeight (<= 15)
        for site in SITES:
            u, v = caster(site, CONFIGS['fall']), victim('CNV_LiftPVictim' + site.title())
            m.units.extend((u, v))
            m.put(u.id, site + ' gun', side='p1', angle=1.5708, name=name(site, 'gun'))
            m.put(v.id, site + ' gun', 0, 450, side='s1', angle=4.7124, name=name(site, 'victim'))
        return m


    def check(m, which):
        config = CONFIGS[which]
        for i, site in enumerate(SITES):   # this check's casters (the mission is built with fall's); same ids
            m.units[2 * i] = caster(site, config)
        t = Test()
        start = [('MAP_REVEAL_ALL_PERM', m.player('p1')), ('SET_MILLISECOND_TIMER', 'Lift probe fire', FIRE),
                 ('SET_MILLISECOND_TIMER', 'Lift probe stop', FIRE + 4 / 15)]
        fire, stop = [], []
        for site in SITES:
            g, v, c = name(site, 'gun'), name(site, 'victim'), 'CNV_LiftP_' + site
            start.extend(('UNIT_CHANGE_OBJECT_STATUS', n, 'NO_ATTACK', 1) for n in (g, v))
            fire.extend((('UNIT_CHANGE_OBJECT_STATUS', g, 'NO_ATTACK', 0), ('NAMED_ATTACK_NAMED', g, v)))
            stop.append(('UNIT_CHANGE_OBJECT_STATUS', g, 'NO_ATTACK', 1))
            t.counters.append((c, config[site][0] + ' lifted frames'))
            t.scripts.append(Script('Test - lifted ' + site, [('UNIT_HAS_OBJECT_STATUS', v, status('LIFTED_INTO_AIR'))],
                                    [('INCREMENT_COUNTER', 1, c)], once=False))
        t.scripts.insert(0, Script('Test - start', [], start))
        t.scripts.extend((Script('Test - fire', [('TIMER_EXPIRED', 'Lift probe fire')], fire),
                          Script('Test - stop', [('TIMER_EXPIRED', 'Lift probe stop')], stop)))
        t.expect = EXPECT[which]
        t.bench = [('bench_watch', dict(seconds=RUN, every=.5, sheet=False, lines=4))]
        return t


    MISSION = {'engine_lift_probe': mission}
    CHECKS = {'engine_lift_probe': {k: (lambda m, k=k: check(m, k)) for k in CONFIGS}}
    return dict(MISSION=MISSION, CHECKS=CHECKS)


def engine_liftretail():
    """Six native Lift weapons through Yuriko and occupied IFV/turret hosts.

    PREDICT ground/air: ever LIFTED +10 alive +100 crew ENCLOSED gives
    11/111/111/10. Negative is native Yuriko with only the selected Lift
    nugget removed; no substituted damage, filters, module or firing cadence.
    Crew enters at2s, attack8s, stop9s, final16s. These latch observations
    cover activation only: landing cleanup, full filters and flight stay gaps.
    Ground targets are passive100000HP Hammers; air targets native Twinblades.
    No scripted lift bits, forced weapon slots or manual upgrades.
    MEASURED2026-11-16 ground PASS11/111/111/10; air0/100/100/10:
    all three native air targets died without a latched LIFTED bit; deleted
    nugget target survived. Preserve the original air hypothesis in t.expect;
    replay tests assert the actual air readings, not the rejected hypothesis.
    Air crash/death dispatch and landing cleanup remain gaps. Evidence:
    work/re/c_liftretail_report.md. No whole-consumer promotion.
    """
    import re
    from pathlib import Path

    from benches.weapon.firing.checks import engine_missile
    missile = engine_missile()["shared"]
    SAGE = missile.SAGE
    target = missile.target
    from maps import probe_range
    from model import status
    from parts import Mission, Script, Test, Unit

    LANES = ('base', 'high', 'order', 'removed')
    GROUND = ('JapanCommandoTech1PsyonicCrush',
              'AAAVT1_JapanCommandoTech1PsyonicCrush', 'ABD_JapanCommandoTech1PsyonicCrush')
    AIR = ('JapanCommandoTech1AirborneKiller',
           'AAAVT1_JapanCommandoTech1PsyonicAntiAirCrush', 'ABD_JapanCommandoTech1PsyonicAntiAirCrush')
    VALUES = (11, 111, 111, 10)


    def mission(air=False):
        m = Mission(name='CampLiftAir' if air else 'CampLiftGnd', map=probe_range, units=[], facts={})
        root = Path(SAGE)
        selected = (AIR if air else GROUND)[0]
        native = (root/'Japan/Units/JapanCommandoTech1.xml').read_text(encoding='utf-8')
        weapons = (root/'GlobalData/Weapon.xml').read_text(encoding='utf-8')
        weapon = re.search(r'<WeaponTemplate\s+id="'+selected+r'".*?</WeaponTemplate>', weapons, re.S).group()
        weapon, count = re.subn(r'<ActivateLiftObjectNugget\b.*?</ActivateLiftObjectNugget>', '', weapon, flags=re.S)
        assert count == 1
        weapon = weapon.replace('id="'+selected+'"', 'id="CNV_LiftNegativeWeapon"', 1)
        native = native.replace('id="JapanCommandoTech1"', 'id="CNV_LiftNegative"', 1)
        native = native.replace('Template="'+selected+'"', 'Template="CNV_LiftNegativeWeapon"')
        native = native.replace('</AssetDeclaration>', weapon+'</AssetDeclaration>')
        m.units.append(Unit('CNV_LiftNegative', native, link=['WeaponTemplate:CNV_LiftNegativeWeapon']))
        hosts = ('JapanCommandoTech1', 'AlliedAntiAirVehicleTech1', 'AlliedBaseDefense', 'CNV_LiftNegative')
        for lane, host in zip(LANES, hosts):
            m.put(host, lane+' gun', side='p1', angle=1.5708, name='RetailLift '+lane+' gun')
            if lane in ('high', 'order'):
                m.put('JapanCommandoTech1', lane+' gun', 40, 0, side='p1', name='RetailLift '+lane+' crew')
            if air:
                victim = 'SovietAntiGroundAircraft'
            else:
                unit = target('CNV_RetailLiftVictim'+lane.title(), health=100000)
                m.units.append(unit)
                victim = unit.id
            m.put(victim, lane+' gun', 0, 100, side='s1', angle=4.7124, name='RetailLift '+lane+' victim')
        m.put('AlliedPowerPlant', 'order gun', -200, 0, side='p1', name='RetailLift power')
        return m


    def check(m):
        t = Test()
        start = [('MAP_REVEAL_ALL_PERM', m.player('p1'))]
        for phase, seconds in (('Enter', 2.), ('Fire', 8.), ('Stop', 9.), ('Sample', 16.)):
            start.append(('SET_MILLISECOND_TIMER', 'RetailLift '+phase, seconds))
        enter, fire, stop = [], [], []
        for lane in LANES:
            g, v = ['RetailLift '+lane+' '+role for role in ('gun', 'victim')]
            c = 'CNV_RetailLift_'+lane
            t.counters.append((c, lane+' native lift'))
            start += [('UNIT_CHANGE_OBJECT_STATUS', who, 'NO_ATTACK', 1) for who in (g, v)]
            if lane in ('high', 'order'):
                crew = 'RetailLift '+lane+' crew'
                start.append(('UNIT_CHANGE_OBJECT_STATUS', crew, 'NO_ATTACK', 1))
                enter.append(('NAMED_GARRISON_SPECIFIC_BUILDING_INSTANTLY', crew, g))
                t.scripts.append(Script('Test - crew '+lane,
                    [('TIMER_EXPIRED', 'RetailLift Sample'), ('UNIT_HAS_OBJECT_STATUS', crew, status('ENCLOSED'))],
                    [('INCREMENT_COUNTER', 100, c)]))
            fire += [('UNIT_CHANGE_OBJECT_STATUS', g, 'NO_ATTACK', 0), ('NAMED_ATTACK_NAMED', g, v)]
            stop.append(('UNIT_CHANGE_OBJECT_STATUS', g, 'NO_ATTACK', 1))
            t.scripts += [
                Script('Test - ever lifted '+lane,
                    [('NAMED_NOT_DESTROYED', v), ('UNIT_HAS_OBJECT_STATUS', v, status('LIFTED_INTO_AIR'))],
                    [('INCREMENT_COUNTER', 1, c)]),
                Script('Test - alive '+lane,
                    [('TIMER_EXPIRED', 'RetailLift Sample'), ('NAMED_NOT_DESTROYED', v)],
                    [('INCREMENT_COUNTER', 10, c)])]
        t.scripts.insert(0, Script('Test - start', [], start))
        for phase, actions in (('Enter', enter), ('Fire', fire), ('Stop', stop)):
            t.scripts.append(Script('Test - '+phase, [('TIMER_EXPIRED', 'RetailLift '+phase)], actions))
        t.expect = [(label, 17, '==', value, 19) for (_, label), value in zip(t.counters, VALUES)]
        t.bench = [('bench_watch', dict(seconds=19., every=.5, sheet=False, lines=4))]
        return t


    MISSION = {'engine_liftground': mission, 'engine_liftair': lambda: mission(air=True)}
    CHECKS = {name: {'a': check} for name in MISSION}
    return dict(MISSION=MISSION, CHECKS=CHECKS)


BENCHES = (
    engine_attach, engine_attachc4, engine_attachmine, engine_attachterror,
    engine_cryo, engine_lift, engine_lift_probe, engine_liftretail,
)
