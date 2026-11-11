"""PREDICT before bench:2/1090/2/1080 (two first-hit frames + alive/HP).
Retail DOTNugget (PlayerPowerIrradiateTargetWeapon) uses Damage, DamageInterval,
DamageDuration, RADIATION, RemoveIfHealed. Keep the damage type and use
400 damage every0.2s=3frames, durations1s=15frames and2s=30frames.
Targets1000HP BaseTankArmor RADIATION5% ->20HP (2%) per tick.
GUESSED initial tick at impact, expiry excluded: offsets0,3,...<15/30
give5/10 ticks, HP90/80. OrderF0, object impactF1, first script seesF2.
No separate DamageNugget: first-hit counters isolate DOT's initial phase.
Clock scripts run after the order and count while health100%, so direct
impact reads2. Final counters=1000*alive+HP%; four displayed lines.
If initial tick is delayed3frames first reads5; an inclusive end adds one
tick. These alternatives are distinguished without per-number fitting.
No healing, repeat hits, stacking, upgrades, splash, death or OCL asserted.
Before implementation simulator ignored DOT:151/1100/151/1100 at16s.
MEASURED first round:2/1088/2/1078 (FAIL of initial exclusive-end prediction).
Both first frames match; expiry INCLUSIVE gives offsets0,3,...,15/30,
6/11 ticks ->HP88/78. Same formula for both durations, no fitted constants.
Revised PREDICT before confirmation bench:2/1088/2/1078.
MEASURED confirmation PASS2/1088/2/1078; `1 run: PASS 1`
(work/logs/w6_dot_confirm_bench.log, 2026-11-10). Simulator replays both.
Empty clip loads1s; order6s; NO_ATTACK6+4/15; float timers.
"""
import re
from maps import probe_range
from parts import Mission,Script,Test
from checks.engine_weaponfx import gun
from checks.engine_missile import target,TARGET_ID
CASES=(('base',1),('high',2))

def mission():
    m=Mission(name='CampDot',map=probe_range,units=[target(health=1000)],facts={})
    for lane,seconds in CASES:
        u=gun('CNV_Dot'+lane.title(),0)
        nugget=(f'<DOTNugget Damage="400" DamageInterval="0.2s" DamageDuration="{seconds}s" '
                'DamageType="RADIATION" DamageFXType="RADIATION" DeathType="IRRADIATED" RemoveIfHealed="true"/>')
        u.xml,n=re.subn(r'<DamageNugget\b[^>]*/>',nugget,u.xml);assert n==1
        m.units.append(u)
        m.put(u.id,lane+' gun',side='p1',angle=1.5708,name='DOT '+lane+' gun')
        m.put(TARGET_ID,lane+' gun',0,450,side='s1',angle=4.7124,name='DOT '+lane+' target')
    return m

def check(m):
    t=Test();start=[('MAP_REVEAL_ALL_PERM',m.player('p1')),('SET_MILLISECOND_TIMER','DOT Fire',6.0),('SET_MILLISECOND_TIMER','DOT Stop',6+4/15)]
    fire=[];stop=[]
    for lane,seconds in CASES:
        g='DOT '+lane+' gun';v='DOT '+lane+' target';c='CNV_DOT_'+lane
        start += [('UNIT_CHANGE_OBJECT_STATUS',name,'NO_ATTACK',1) for name in (g,v)]
        fire += [('UNIT_CHANGE_OBJECT_STATUS',g,'NO_ATTACK',0),('NAMED_ATTACK_NAMED',g,v)]
        stop += [('UNIT_CHANGE_OBJECT_STATUS',g,'NO_ATTACK',1)]
        t.counters += [(c+'First',str(seconds)+'s first'),(c+'HP',str(seconds)+'s aliveHP')]
        t.scripts += [Script('Test - clock '+lane,[('FLAG','DOT Ordered',1),('UNIT_HEALTH',v,2,100)],
                             [('INCREMENT_COUNTER',1,c+'First')],once=False),
                      Script('Test - hp '+lane,[],[('SET_COUNTER',c+'HP',0),('SET_UNIT_HEALTH_PERCENTAGE_TO_COUNTER',v,c+'HP')],once=False),
                      Script('Test - alive '+lane,[('NAMED_NOT_DESTROYED',v)],[('INCREMENT_COUNTER',1000,c+'HP')],once=False)]
    t.scripts.insert(0,Script('Test - start',[],start))
    t.scripts.insert(1,Script('Test - fire',[('TIMER_EXPIRED','DOT Fire')],fire+[('SET_FLAG','DOT Ordered',1)]))
    t.scripts.append(Script('Test - stop',[('TIMER_EXPIRED','DOT Stop')],stop))
    t.expect=[(label,14,'==',value,16) for (_,label),value in zip(t.counters,(2,1088,2,1078))]
    t.bench=[('bench_watch',dict(seconds=16.0,every=.5,sheet=False,lines=4))]
    return t
MISSION={'engine_dot':mission}
CHECKS={'engine_dot':{'a':check}}
