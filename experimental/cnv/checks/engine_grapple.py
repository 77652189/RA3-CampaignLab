"""GrapplingHookNugget1 minimal consumer probe, prediction before bench.

Retail SovietAntiVehicleVehicleTech3Harpoon supplies Damage1 CANNON,
ForbiddenTargetObjectStatus UNDER_RUSH_ATTACK and VEHICLE/STRUCTURE filter.
Its caster GrapplingHookUpdate has PullRate40, GENERIC_TOGGLE_STATE validation
and crush/grind weapons. Here independent10UNRES marks a1000HP Hammer;
synthetic hook Damage0 attempts to isolate dispatch/pull, without crush/grind
or bounce; whether Damage0 itself prevents dispatch remains unresolved.
base: module/no nugget; high: module+VEHICLE; order: module+INFANTRY;
removed: VEHICLE nugget/no module. Synthetic module omits ObjectStatusValidation (V4 toggle selects an empty set).
At6s open one4/15s firing window, then NO_ATTACK again (known single-shot
fixture). GUESSED: accepted hook keeps pulling after this stop; at14s target
enters the150+-100 near area, controls stay450 away. PREDICT1099/11099/1099/1099.
Packed=10000*everNear+1000*targetAlive+targetHP%. No exact pull frame,
release rule, blocked collision, building pull, retail damage or grind claim.
The predicted consumer behavior is a hypothesis, not a replay assertion.
Initial fixture 1100/1100/1100/1100: toggle selected V4 empty weapon set;
corrected fixture removes both toggle action and module validation, no other change.
MEASURED corrected run:1099/1099/1099/1099; all markers hit, high neverNear.
This rejects the persistence/dispatch prediction, not proof that hooks do nothing.
Damage0 shortcut vs NO_ATTACK release vs missing host context are unseparated.
Keep the original prediction below for diagnosis; do not promote this check.
"""
from maps import probe_range
from parts import Mission, Script, Test, square
from checks.engine_weaponfx import gun
from checks.engine_missile import target

CASES = ('base', 'high', 'order', 'removed')


def mission():
    m = Mission(name='CampGrapple', map=probe_range, units=[], facts={})
    for lane in CASES:
        kind = 'INFANTRY' if lane == 'order' else 'VEHICLE'
        extra = (f'<GrapplingHookNugget Damage="0" DamageType="UNRESISTABLE" '
                 'ForbiddenTargetObjectStatus="UNDER_RUSH_ATTACK">'
                 f'<SpecialObjectFilter Rule="ANY" Include="{kind}"/>'
                 '</GrapplingHookNugget>' if lane != 'base' else '')
        u = gun('CNV_Grapple' + lane.title(), 10, extra)
        u.xml = u.xml.replace('DamageType="EXPLOSIVE"', 'DamageType="UNRESISTABLE"')
        if lane != 'removed':
            u.xml = u.xml.replace('<Behaviors>', '<Behaviors>'
                '<GrapplingHookUpdate id="ModuleTag_GrapplingHook" PullRate="40" '
                'MinBounceDelay="0.5s" MaxBounceDelay="1s" BouncePercentage="0%">'
                '<KeepAliveObjectFilter Rule="ANY" Include="VEHICLE STRUCTURE TIME_BOMB"/>'
                '</GrapplingHookUpdate>', 1)
        v = target('CNV_GrappleVictim' + lane.title(), health=1000)
        m.units.extend((u, v))
        m.put(u.id, lane+' gun', side='p1', angle=1.5708, name='Grapple '+lane+' gun')
        m.put(v.id, lane+' gun', 0, 450, side='s1', angle=4.7124, name='Grapple '+lane+' victim')
        m.waypoint(lane+' near', 'Grapple near '+lane, lane+' gun', 0, 150)
    return m


def check(m):
    t = Test()
    start = [('MAP_REVEAL_ALL_PERM', m.player('p1')),
             ('SET_MILLISECOND_TIMER', 'Grapple Fire', 6.),
             ('SET_MILLISECOND_TIMER', 'Grapple Stop', 6+4/15)]
    fire, stop = [], []
    for lane in CASES:
        g, v = 'Grapple '+lane+' gun', 'Grapple '+lane+' victim'
        c, area = 'CNV_Grapple_'+lane, 'Grapple near '+lane
        t.areas[area] = square(*m.point(lane+' near'), 100)
        start.extend(('UNIT_CHANGE_OBJECT_STATUS', n, 'NO_ATTACK', 1) for n in (g, v))
        fire.extend((('UNIT_CHANGE_OBJECT_STATUS', g, 'NO_ATTACK', 0), ('NAMED_ATTACK_NAMED', g, v)))
        stop.append(('UNIT_CHANGE_OBJECT_STATUS', g, 'NO_ATTACK', 1))
        t.counters.append((c, lane+' packed'))
        t.scripts.extend((
            Script('Test - hp '+lane, [], [('SET_COUNTER', c, 0),
                   ('SET_UNIT_HEALTH_PERCENTAGE_TO_COUNTER', v, c),
                   ('COUNTER_MATH_COUNTER', c, 0, c+'State')], once=False),
            Script('Test - alive '+lane, [('NAMED_NOT_DESTROYED', v)],
                   [('INCREMENT_COUNTER', 1000, c)], once=False),
            Script('Test - near '+lane, [('NAMED_INSIDE_AREA', v, area)],
                   [('INCREMENT_COUNTER', 10000, c+'State')]) ))
    t.scripts.insert(0, Script('Test - start', [], start))
    t.scripts.extend((Script('Test - fire', [('TIMER_EXPIRED', 'Grapple Fire')], fire),
                      Script('Test - stop', [('TIMER_EXPIRED', 'Grapple Stop')], stop)))
    t.expect = [(label, 16, '==', n, 18) for (_, label), n in zip(t.counters, (1099, 11099, 1099, 1099))]
    t.bench = [('bench_watch', dict(seconds=18., every=.5, sheet=False, lines=4))]
    return t


MISSION = {'engine_grapple': mission}
CHECKS = {'engine_grapple': {'a': check}}
