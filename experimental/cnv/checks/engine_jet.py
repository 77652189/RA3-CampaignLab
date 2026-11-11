"""JetAIUpdate minimum ordinary-move probe, engine line E.

Retail Vindicator (AlliedAntiGroundAircraft), NORMAL speed 180, Wings locomotor,
AccelerationSeconds 1, MinSpeed 160%, CirclingRadius 60, CirclingSpeed 50%; JetAIUpdate has
NeedsRunway=false. No airfield, enemy, attack or ammo expenditure is involved.
JetAIUpdate dispatches the order; speed/turning/idle circles belong to locomotion,
JetSlowDeathBehavior to death. This check cannot establish those whole modules.

From festival's west field, fly 1200 east at Go=1s, into a square half-side 100.
Prediction: survive at 100% and reach the square. Constant-speed reference
(1200-100)/180*15 = 91.67 frames; takeoff/acceleration/turning are unmeasured,
so the exact first-entry frame is a measurement, not a predeclared speed fit.
Four rows: frames since Go until FIRST entry (latched), first-entry flag,
current presence in the goal square, health percent. Presence may change again
while circling: reaching is deliberately latched separately from staying.

Bench 2026-11-11, CampJetA_mcp_1111_050503: PASS; s1-s5 flight counter
30/42/57/72/88, then s6-s26 97/1/1/100. First-entry counter=97;
thereafter inside=1 and health=100 throughout the observed run. Do not derive
an absolute order-to-arrival time from screenshot seconds (their clock differs).
Model: 91/1/1/100; endpoint/survival replay passes, exact counter strict xfail
in tests/test_simjet.py. No claim about circling trajectory or whole module.

600-distance control b, CampJetB_mcp_1111_053444: s1=29/0/0/100,
s2=42/0/0/100, s3-s26=47/1/1/100. Engine distance delta 600 takes
50 frames, consistent with speed 180. Ideal constant-speed entry references
are 91.67 and 41.67; both measured counts exceed those by 5.33 frames.
This supports a common startup contribution, but cannot separate takeoff,
acceleration and initial circling. Model counts 91 and 39 have different
coarse movement-step phase errors; do not add a constant to fit either one.

Offline E40: shot_clock frame movement (same scripts and speed, no startup
model) gives 92/42. Coarse phase therefore accounts for 1 and 3 frames of the
respective 6/8-frame gaps, leaving 5 frames to each measured integer counter. Both
clocks retain strict xfails against 97/47. This does not identify the engine's
takeoff, acceleration or initial circling mechanism; no timing fit is applied.
"""
from maps import festival
from parts import Mission, Script, Test, counted, square

JET = 'AlliedAntiGroundAircraft'
NAME = 'UNIT - CNV Jet'
RUN = 25.0


def mission():
    m = Mission(name='CampJet', map=festival, units=[], facts={})
    m.put(JET, 'west field', -600.0, 0.0, angle=0.0, role='jet', name=NAME)
    return m


def ordinary_move(m, goal_dx=600.0, measured_frames=97):
    t = Test()
    jet = m.role('jet').name
    x, y = m.site('west field')[:2]
    t.waypoints['Jet Goal'] = (x + goal_dx, y)
    t.areas['Jet Goal'] = square(x + goal_dx, y, 100.0)
    t.scripts.append(Script('Jet - start', [], [
        ('MAP_REVEAL_ALL_PERM', m.player('p1')),
        ('UNIT_CHANGE_OBJECT_STATUS', jet, 'NO_ATTACK', 1),
        ('SET_MILLISECOND_TIMER', 'Jet Go', 1.0),
        ('SET_FLAG', 'Jet Arrived', 0),
    ]))
    t.scripts.append(Script('Jet - move', [('TIMER_EXPIRED', 'Jet Go')],
                            m.order('move', [jet], 'Jet Goal', 'p1', crew='Jet')
                            + [('SET_FLAG', 'Jet Going', 1)]))
    t.counters += [('CNV_Jet_Frames', '飞帧'), ('CNV_Jet_Arrived', '到达')]
    t.scripts.append(Script('Jet - first entry', [
        ('FLAG', 'Jet Going', 1), ('NAMED_INSIDE_AREA', jet, 'Jet Goal'),
    ], [('SET_FLAG', 'Jet Arrived', 1), ('SET_COUNTER', 'CNV_Jet_Arrived', 1)]))
    t.scripts.append(Script('Jet - flight frames', [
        ('FLAG', 'Jet Going', 1), ('FLAG', 'Jet Arrived', 0),
    ], [('INCREMENT_COUNTER', 1, 'CNV_Jet_Frames')], once=False))
    counted('CNV_Jet_Inside', '在场', t, named=jet, area='Jet Goal')
    counted('CNV_Jet_Health', '机血', t, health=jet)
    t.expect = [('到达', 0, 'ever==', 1, RUN), ('机血', 2, '==', 100, RUN),
                ('在场', 10, '==', 1, RUN)]
    t.expect.append(('飞帧', 10, '==', measured_frames, RUN))
    t.bench = [('bench_watch', dict(seconds=RUN, every=1, sheet=False, lines=4))]
    return t


def short_move(m):
    """600 distance control: same start/order/heading/goal size as a; bench counter 47."""
    return ordinary_move(m, goal_dx=0.0, measured_frames=47)


MISSION = {'engine_jet': mission}
CHECKS = {'engine_jet': {'a': ordinary_move, 'b': short_move}}
