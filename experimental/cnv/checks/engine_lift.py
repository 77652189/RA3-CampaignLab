"""ActivateLiftObjectNugget6: PREDICT1099/10001099/1099/1099.

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
Expectations below preserve OBSERVATIONS for future diagnostics, not an
explanatory simulator model; neither run passed the original hypothesis.
"""
from maps import probe_range
from model import status
from parts import Mission, Script, Test
from checks.engine_weaponfx import gun
from checks.engine_missile import target

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
