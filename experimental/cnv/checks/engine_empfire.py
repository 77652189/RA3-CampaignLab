"""PREDICT before bench: 901090/901100/901080/901090.

Two 1000HP V4 clones carry the same finite one-shot 100UNRES weapon.
At6s each receives a 100UNRES marker; only high also receives EMP4s.
At6.5s each is explicitly ordered to fire north at a passive 1000HP target;
NO_ATTACK closes that window after4/15s. Before10s the control should have
hit once (target90%) and the EMP gun never (target100%). At11s a second
identical order/window, after EMP expiry, should leave targets80%/90%.
Capture early at9s, late at14s; each packed row = gunHP%*10000 +
1000*gunAlive + targetHP%. Marker90% and survival positively verify the
EMP carrier was hit and remained alive. TargetHP is cleared before reading.
The marker and first attack are separated by0.5s, so neither same-frame
ordering nor the exact expiry frame is inferred. Movement, EMP stacking,
filters, other paralysis types and weapon cooldown during EMP untested.

First bench read891089/891100/891078/891089: EMP behavior separated, but
the fixture had not neutralized retail side/rear damage multipliers105/110.
Correct the fixture's two recipient armors to NoArmor (100% in all directions), leaving
damage, geometry and timers unchanged; do not fit EMP rules to those HPs.
MEASURED 2026-11-10, neutral fixture: PASS901090/901100/901080/901090
(work/logs/c_empfire_noarmor_bench.log). The first corrected-armor build
could not inherit a retail armor instance; NoArmor builds without that
extra asset. Only the two firing windows, not exact expiry or ongoing
reload behavior, are benched. Simulator before fix let both lanes fire;
after fix it replays all four readings.
"""
import re

from maps import probe_range
from parts import Mission, Script, Test
from checks.engine_weaponfx import gun
from checks.engine_missile import target


def neutral_direction_armor(u):
    """Only UNRESISTABLE is used here; NoArmor removes direction as a confound."""
    parent = re.search(r'<ArmorSet\s+Armor="([^"]+)"', u.xml).group(1)
    u.xml = u.xml.replace('Armor="'+parent+'"', 'Armor="NoArmor"')


def mission():
    m = Mission(name='CampEmpFire', map=probe_range, units=[], facts={})
    for lane in ('base', 'high'):
        extra = '<ParalyzeNugget DurationSeconds="4s" ParalyzeType="EMP"/>' if lane == 'high' else ''
        marker = gun('CNV_EmpFireMark' + lane.title(), 100, extra)
        shooter = gun('CNV_EmpFireGun' + lane.title(), 100)
        for u in (marker, shooter):
            u.xml = u.xml.replace('DamageType="EXPLOSIVE"', 'DamageType="UNRESISTABLE"')
        shooter.xml, n = re.subn(r'MaxHealth="[^"]+"', 'MaxHealth="1000"', shooter.xml)
        assert n == 1, n
        dummy = target('CNV_EmpFireTarget' + lane.title(), health=1000)
        neutral_direction_armor(shooter)
        neutral_direction_armor(dummy)
        m.units.extend((marker, shooter, dummy))
        m.put(marker.id, lane+' gun', -100, 0, side='p1', angle=1.5708, name='EmpFire '+lane+' marker')
        m.put(shooter.id, lane+' gun', 0, 450, side='s1', angle=1.5708, name='EmpFire '+lane+' gun')
        m.put(dummy.id, lane+' gun', 0, 900, side='p1', name='EmpFire '+lane+' target')
    return m


def check(m):
    t = Test()
    start = [('MAP_REVEAL_ALL_PERM', m.player('p1'))]
    for lane in ('base', 'high'):
        marker, shooter, dummy = ['EmpFire '+lane+' '+k for k in ('marker', 'gun', 'target')]
        start.extend(('UNIT_CHANGE_OBJECT_STATUS', v, 'NO_ATTACK', 1) for v in (marker, shooter, dummy))
        for tag, at, who, victim in (('mark', 6., marker, shooter), ('early', 6.5, shooter, dummy),
                                     ('late', 11., shooter, dummy)):
            timer = 'EmpFire '+lane+' '+tag
            start.extend((('SET_MILLISECOND_TIMER', timer, at),
                          ('SET_MILLISECOND_TIMER', timer+' stop', at+4/15)))
            t.scripts.extend((Script('Test - '+timer, [('TIMER_EXPIRED', timer)],
                                     [('UNIT_CHANGE_OBJECT_STATUS', who, 'NO_ATTACK', 0), ('NAMED_ATTACK_NAMED', who, victim)]),
                              Script('Test - '+timer+' stop', [('TIMER_EXPIRED', timer+' stop')],
                                     [('UNIT_CHANGE_OBJECT_STATUS', who, 'NO_ATTACK', 1)])))
    for phase, at in (('early', 9.), ('late', 14.)):
        timer = 'EmpFire read '+phase
        start.append(('SET_MILLISECOND_TIMER', timer, at))
        for lane in ('base', 'high'):
            c = 'CNV_EmpFire_'+phase+'_'+lane
            shooter, dummy = 'EmpFire '+lane+' gun', 'EmpFire '+lane+' target'
            t.counters.append((c, phase+' '+lane))
            t.scripts.extend((Script('Test - read '+c, [('TIMER_EXPIRED', timer)],
                                     [('SET_COUNTER', c, 0), ('SET_COUNTER', c+'HP', 0),
                                      ('SET_UNIT_HEALTH_PERCENTAGE_TO_COUNTER', shooter, c),
                                      ('COUNTER_MATH_VALUE', c, 2, 10000),
                                      ('SET_UNIT_HEALTH_PERCENTAGE_TO_COUNTER', dummy, c+'HP'),
                                      ('COUNTER_MATH_COUNTER', c, 0, c+'HP')]),
                              Script('Test - alive '+c, [('TIMER_EXPIRED', timer), ('NAMED_NOT_DESTROYED', shooter)],
                                     [('INCREMENT_COUNTER', 1000, c)])))
    t.scripts.insert(0, Script('Test - start', [], start))
    t.expect = [(label, 15, '==', value, 16) for (_, label), value in
                zip(t.counters, (901090, 901100, 901080, 901090))]
    t.bench = [('bench_watch', dict(seconds=16., every=.5, sheet=False, lines=4))]
    return t


MISSION = {'engine_empfire': mission}
CHECKS = {'engine_empfire': {'a': check}}
