"""New round PREDICT16051/31066/61096,hit1 after first-hit clock fix.
Scripts run before object updates. OrderF0 -> object hitF1 -> observedF2;
move6.5s rounds toF8; EMP1/2/4s endsF16/31/61, first movement there,
observed departureF17/32/62. Origin script omits orderF0 ->raw16/31/61.
Arrival raw counter omits move trigger ->43 moving frames +8/23/53 held
frames =51/66/96. Remaining1 after first-hit correction was ceil(a-b)
versus ceil(a)-ceil(b); move must independently round0.5s*15 up to8.
Sim now predicts the full packed tuple exactly, before rerunning bench.
Prior experiment, before the clock correction:
Bench FAIL raw16051/31066/61096, hit1. Scripts precede fire/move,
so add1 to raw arrival, departure and hit for trigger-relative observation:
arrival52/67/97, departure17/32/62, hit2. Sim hit raw2 vs bench1.
At that stage EMP was shelved without an implementation; reopened above.
Identical EMP clone at1/2/4s, damage1.5 UNRESISTABLE on150HP infantry.
Initially empty clip loads1s; fire6s, NO_ATTACK6+4/15; move6.5s.
Four displayed lines: each lane encodes1000*departure_frame + arrival_frames;
departure_frame is the first script frame outside a1-unit origin square,
from fire order. This observes first post-EMP movement, not an EMP status bit.
Fourth line records first damage observation from order (independent clock).
PREDICT: damage2, departure18/33/63 (damage2+duration15/30/60+one
script-observation frame), arrival54/69/99; packed18054/33069/63099.
Departure prediction is GUESSED: object update vs script phase is unverified.
Prior isolated2/4s arrival readings67/97 were2 below predictions69/99.
If the residual changes with duration STOP; if constant inspect departure
and hit timing, do not infer onset merely from damage or fit a2-frame fix.
"""
from maps import probe_range
from parts import Mission,Script,Test,square
from checks.engine_weaponfx import gun

RUN=16.0
CASES=(('base',1),('high',2),('order',4))

def mission():
    return Mission(name='CampEmp',map=probe_range,units=[],facts={})

def check(m):
    t=Test(); start=[('MAP_REVEAL_ALL_PERM',m.player('p1')),
        ('SET_MILLISECOND_TIMER','EMP Fire',6.0),
        ('SET_MILLISECOND_TIMER','EMP Stop',6.0+4/15),
        ('SET_MILLISECOND_TIMER','EMP Move',6.5)]
    fire=[]; stop=[]; move=[]
    for lane,seconds in CASES:
        u=gun('CNV_Emp'+lane.title(),1.5,
              f'<ParalyzeNugget DurationSeconds="{seconds}s" ParalyzeType="EMP"/>')
        u.xml=u.xml.replace('DamageType="EXPLOSIVE"','DamageType="UNRESISTABLE"')
        m.units.append(u)
        shooter='EMP '+lane+' gun'; victim='EMP '+lane+' man'
        m.put(u.id,lane+' gun',side='p1',angle=1.5708,name=shooter)
        m.put('AlliedAntiInfantryInfantry',lane+' gun',0,450,side='s1',name=victim)
        start += [('UNIT_CHANGE_OBJECT_STATUS',name,'NO_ATTACK',1) for name in (shooter,victim)]
        fire += [('UNIT_CHANGE_OBJECT_STATUS',shooter,'NO_ATTACK',0),('NAMED_ATTACK_NAMED',shooter,victim)]
        stop += [('UNIT_CHANGE_OBJECT_STATUS',shooter,'NO_ATTACK',1)]
        m.waypoint(lane+' goal','EMP Goal '+lane,lane+' gun',0,675)
        x,y=m.point(lane+' goal'); gate='EMP Gate '+lane; origin='EMP Origin '+lane
        t.areas[gate]=square(x,y-40,40)
        t.areas[origin]=square(x,y-225,1)
        c='CNV_EMP_'+lane; dep='EMP Departed '+lane; moving='EMP Moving '+lane
        t.counters.append((c,str(seconds)+'s packed'))
        move += [('MOVE_NAMED_UNIT_TO',victim,m.mark(lane+' goal')),('SET_FLAG',moving,1)]
        # Count origin frames directly in the thousands; no dependency on HUD sampling.
        t.scripts += [
            Script('Test - origin '+lane,[('FLAG','EMP Ordered',1),('FLAG',dep,0),('NAMED_INSIDE_AREA',victim,origin)], [('INCREMENT_COUNTER',1000,c)],once=False),
            Script('Test - depart '+lane,[('FLAG','EMP Ordered',1),('NAMED_OUTSIDE_AREA',victim,origin)], [('SET_FLAG',dep,1)]),
            Script('Test - arrive '+lane,[('NAMED_INSIDE_AREA',victim,gate)],[('NAMED_STOP',victim),('SET_FLAG',moving,0)]),
            Script('Test - frames '+lane,[('FLAG',moving,1)],[('INCREMENT_COUNTER',1,c)],once=False)]
    t.counters.append(('CNV_EMP_Hit','hit frame'))
    t.scripts += [Script('Test - hit frame',[('FLAG','EMP Ordered',1),('UNIT_HEALTH','EMP high man',2,100)],
                         [('INCREMENT_COUNTER',1,'CNV_EMP_Hit')],once=False)]
    t.scripts.insert(0,Script('Test - start',[],start))
    t.scripts += [Script('Test - fire',[('TIMER_EXPIRED','EMP Fire')],fire+[('SET_FLAG','EMP Ordered',1)]),
                  Script('Test - stop',[('TIMER_EXPIRED','EMP Stop')],stop),
                  Script('Test - move',[('TIMER_EXPIRED','EMP Move')],move)]
    t.expect=[(label,14,'==',v,16) for (_,label),v in zip(t.counters,(16051,31066,61096,1))]
    t.bench=[('bench_watch',dict(seconds=RUN,every=.5,sheet=False,lines=4))]
    return t
MISSION={'engine_emp':mission}
CHECKS={'engine_emp':{'phase':check}}
