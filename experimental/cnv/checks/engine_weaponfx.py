"""Weapon round 1: PREDICTED before bench (2026-11-10).

attribute: two 10000HP Hammer lanes. At6s each takes100 EXPLOSIVE;
only high receives retail AttributeMod_TargetPainted (ARMOR150%,Duration1.1s).
At6.5s a1000 hit: base89%, high84%; at9s after expiry another1000:
base79%, high74%, both alive1. No fitted constants: the separate damage
weapon has EXPLOSIVE100% on BaseTankArmor, both guns face the target front.
Current simulator ignores the modifier nugget: predicts79/1/79/1.

line:1000 EXPLOSIVE, LineWidth5, UseDynamicLineLength true, Overshoot200.
10000HP Hammers at y450(target),350(before),550(after),x100/y450(outside).
PREDICTED health90/90/90/100. Current simulator only damages the named
victim:90/100/100/100. Geometry inclusion of full extents is INFERRED;
these centres are deliberately far from the boundaries. Bench first round: attribute PASS79/1/74/1 (early89/1/84/1),
line PASS90/90/90/100.
No broad promotion
from a limited probe; only explained fields may be registered.

All clones load their initially EMPTY clip in1s; order>=6s, stop each
one-shot burst after4/15s with NO_ATTACK. Float timers; at most4 lines.
"""
import re
from maps import probe_range
from parts import Mission, Script, Test, square
from checks.engine_clip import clip_v4
from checks.engine_missile import target, TARGET_ID

RUN = 16.0

def gun(uid, damage, extra=''):
    u = clip_v4('bare', uid=uid, hit=damage,
                spec=(0, 1/15, 1.0, 1, 'PRE_FIRE', (), RUN, 'weapon effect'))
    if extra:
        u.xml = u.xml.replace('</Nuggets>', extra + '</Nuggets>')
    return u


def mission():
    return Mission(name='CampWx', map=probe_range, units=[], facts={})


def check(m, which):
    t = Test()
    start = [('MAP_REVEAL_ALL_PERM', m.player('p1'))]
    def put(template, lane, x, y, side, name):
        m.put(template, lane+' gun', x, y, side=side, angle=1.5708 if side=='p1' else 4.7124, name=name)
        start.append(('UNIT_CHANGE_OBJECT_STATUS', name, 'NO_ATTACK', 1))
    def shoot(shooter, victim, at, suffix):
        fire, stop = 'Wfx Fire '+suffix, 'Wfx Stop '+suffix
        start.extend([('SET_MILLISECOND_TIMER', fire, float(at)),
                      ('SET_MILLISECOND_TIMER', stop, float(at+4/15))])
        t.scripts.extend([
            Script('Test - fire '+suffix, [('TIMER_EXPIRED',fire)],
                   [('UNIT_CHANGE_OBJECT_STATUS',shooter,'NO_ATTACK',0),('NAMED_ATTACK_NAMED',shooter,victim)]),
            Script('Test - stop '+suffix, [('TIMER_EXPIRED',stop)],
                   [('UNIT_CHANGE_OBJECT_STATUS',shooter,'NO_ATTACK',1)])])
    def hp(name, label):
        c='CNV_Wfx_'+label
        t.counters.append((c,label))
        t.scripts.append(Script('Test - hp '+label, [], [('SET_UNIT_HEALTH_PERCENTAGE_TO_COUNTER',name,c)], once=False))
    def alive(name, label):
        c='CNV_Wfx_'+label
        t.counters.append((c,label))
        t.scripts.extend([Script('Test - alive '+label, [], [('SET_COUNTER',c,1)],once=False),
                          Script('Test - dead '+label,[('NAMED_DESTROYED',name)],[('SET_COUNTER',c,0)],once=False)])
    if which == 'line':
        u=gun('CNV_WfxLine',1000)
        u.xml=u.xml.replace('<DamageNugget ', '<LineDamageNugget LineWidth="5" UseDynamicLineLength="true" OverShootDistance="200" ')
        m.units=[u,target()]
        put(u.id,'base',0,0,'p1','Wfx Gun')
        for i,(x,y) in enumerate(((0,450),(0,350),(0,550),(100,450))):
            name='Wfx Target '+str(i)
            put(TARGET_ID,'base',x,y,'s1',name)
            hp(name,'HP'+str(i))
        shoot('Wfx Gun','Wfx Target 0',6.0,'line')
        values=(90,90,90,100)
    else:
        m.units=[target()]
        for lane in ('base','high'):
            extra = '<AttributeModifierNugget AttributeModifierName="AttributeMod_TargetPainted"/>' if lane=='high' else ''
            mark=gun('CNV_Wfx'+lane.title(),100,extra)
            m.units.append(mark)
            victim='Wfx '+lane+' target'
            shooter='Wfx '+lane+' marker'
            put(mark.id,lane,0,0,'p1',shooter)
            put(TARGET_ID,lane,0,450,'s1',victim)
            shoot(shooter,victim,6.0,lane+' mark')
            hit=gun('CNV_WfxHit'+lane.title(),1000)
            m.units.append(hit)
            hitter='Wfx '+lane+' hit'
            put(hit.id,lane,100,0,'p1',hitter)
            shoot(hitter,victim,6.5,lane+' early')
            shoot(hitter,victim,9.0,lane+' late')
            hp(victim,lane+'HP'); alive(victim,lane+'Alive')
        values=(79,1,74,1)
    t.scripts.insert(0,Script('Test - start',[],start))
    t.expect=[(label,RUN-2,'==',value,RUN) for (_,label),value in zip(t.counters,values)]
    t.bench=[('bench_watch',dict(seconds=RUN,every=.5,sheet=False,lines=len(t.counters)))]
    return t

MISSION={'engine_weaponfx':mission}
CHECKS={'engine_weaponfx':{k:(lambda m,k=k:check(m,k)) for k in ('attribute','line')}}
