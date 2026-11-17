"""Engine unit test: ToppleUpdate -- do the crushable props (lanterns, street lamps, fences, trees) fall when a vehicle
drives through them, and who can topple them (engine line C round 10; docs/engine/crush.md). Retail data (SDK SageXML):
OK_Lantern01 / SA_Fence09 inherit BaseSimulatedProp (prop body, CrusherInfo CrushableLevel 0, KindOf CRUSHABLE_OBSTACLE
...) with a topple module `KillWhenStartToppled=true` (ToppleFX FX_WoodCrush / FX_StreetLampCrush); trees (CS_Tree01,
BaseTree) have `KillWhenToppled=true` and a SlowDeath (SinkDelay 2 s, DestructionDelay 4 s). CrusherLevel of a Hammer is
20, of an Apocalypse 30, of a conscript 0. Questions: does the Hammer drive straight through (reach its goal) or go
round / stop; is the prop dead (NAMED_NOT_DESTROYED false) or dying (NAMED_DYING) afterwards, and when; can a conscript
(level 0, not strictly above the prop's 0) topple one; does the simulator's rule "a crusher strictly above the crushable
level kills it" (Sim.crush_along) apply to a prop at all.

On the festival map, west field, lanes along +x, 300 apart; every unit on HOLD_FIRE. Per lane the player's vehicle 200
west of the prop (the prop is neutral, 'civ'), ordered at 'Test Go' (1 s in) to a point 200 east of it:
  a  lane 1 Hammer -> OK_Lantern01   lane 2 Hammer -> CS_StreetLight   lane 3 Hammer -> SA_Fence09
  b  lane 1 Hammer -> CS_Tree01      lane 2 Conscript -> OK_Lantern01  lane 3 Apocalypse -> OK_Lantern01
Counters (four lines), counted from 'Test Go' on:
  帧数  frames since Go
  行k   (k = 1..3 the lanes) 1 x frames the prop is not destroyed + 1000 x frames it is dying + 1000000 x frames the
        vehicle is at its goal (a square of half-side 40)

Bench 2026-11-09 (every row's three parts read from the counter: arrival frame from the 1e6 part, destroyed = the frame
the 1x part stops, dying never counted): a -- the Hammer reaches its goal at frame ~91 in every lane (no stop, no detour);
lantern destroyed at frame 162, street lamp 118, fence 163. b -- Hammer: tree destroyed at 119; conscript (level 0): lantern
NEVER destroyed (still counting at frame 710), it walks to its goal at frame ~111; Apocalypse (level 30): lantern destroyed
at frame 170 (it reaches the goal at ~110). The NAMED_DYING part stays 0 everywhere: the props die at once (no dying
state), well AFTER the vehicle has passed (the vehicle crosses the prop at about frame 53).

Simulator comparison: tests/test_simbench_c.py::test_topple_the_five_props_disappear_at_the_bench_frames_without_ever_dying.
simtopple reads the inherited Geometry, ToppleUpdate and SlowDeath fields. KillWhenStartToppled starts the lantern /
fence's 8 s (120-frame) DestructionDelay at contact. The lamp / tree first fall and settle (20% initial velocity,
1% acceleration, 20% bounce), then wait their 4 s (60 frames). DynamicsDraw.Lifetime is visual debris, not this delay.
Paths through topple props move frame by frame, using the NORMAL LocomotorSet and AccelerationSeconds; the Hammer's
CampaignOverrides speed is 60, not its base 75. Simulated undestroyed counts: a 163 / 119 / 164, b 120 / still alive /
171 (each destruction 1 frame later than the bench); arrivals: a 91 / 91 / 91, b 91 / 110 / 111 (within 1 frame).
All dying counts are zero. This comparison covers these props and crossings, not general dynamics or debris physics.

  c  EnableDynamicsCollide (no fields; 137 retail campaign uses, nearly all through BaseSimulatedProp): three Hammers,
     lane 1 -> OK_Lantern01, lane 2 -> CNVLanternNoDyn (the lantern flattened -- BaseSimulatedProp's parts written in,
     no inheritFrom -- WITHOUT the module), lane 3 -> CNVLanternCopy (the same copy WITH it: the control for the copy).
     PREDICTED: the three alike (the module only lets the draw's debris collide). Bench 2026-11-10 (engine_topple_c,
     PASS): the three rows identical every second -- each Hammer at its goal at frame 91, each lantern gone at 162,
     never dying. Simulated: tests/test_simbench_c.py::test_enable_dynamics_collide_a_lantern_without_it_is_crushed_and_gone_at_the_same_frames.
"""
import os

import labpaths
from maps import festival
from parts import Mission, Script, Test, Unit, square

HAMMER, APOC, CONSCRIPT = 'SovietAntiVehicleVehicleTech1', 'SovietAntiVehicleVehicleTech3', 'SovietAntiInfantryInfantry'
LANTERN, LAMP, FENCE, TREE = 'OK_Lantern01', 'CS_StreetLight', 'SA_Fence09', 'CS_Tree01'
LANES = {'a': {1: (HAMMER, LANTERN, -300.0), 2: (HAMMER, LAMP, 0.0), 3: (HAMMER, FENCE, 300.0)},
         'b': {1: (HAMMER, TREE, -300.0), 2: (CONSCRIPT, LANTERN, 0.0), 3: (APOC, LANTERN, 300.0)},
         'c': {1: (HAMMER, LANTERN, -300.0), 2: (HAMMER, 'CNVLanternNoDyn', 0.0), 3: (HAMMER, 'CNVLanternCopy', 300.0)}}
RUN, HOLD_FIRE = 45.0, 3


def _sub1(x, old, new):
    assert x.count(old) == 1, (old[:60], x.count(old))
    return x.replace(old, new, 1)


def lantern_copy(dyn):
    """OK_Lantern01 flattened: BaseSimulatedProp's parts written into the copy (no inheritFrom), with or without its
    EnableDynamicsCollide -- a child cannot take an inherited module out, so both copies stand alone."""
    name = 'CNVLanternCopy' if dyn else 'CNVLanternNoDyn'
    x = open(os.path.join(labpaths.SDK3, 'SageXML', 'Civilian', 'Osaka_OK', 'Props', 'OK_Lantern01.xml'),
             encoding='utf-8').read()
    x = _sub1(x, 'id="OK_Lantern01"', f'id="{name}"')
    x = _sub1(x, 'EditorName="OK_Lantern01"', f'EditorName="{name}"')
    x = _sub1(x, 'inheritFrom="BaseSimulatedProp"', 'IsTrainable="false"')
    x = _sub1(x, 'source="DATA:BaseObjects/BaseSimulatedProp.xml"', 'source="DATA:GlobalData/GlobalDefines.xml"')
    x = _sub1(x, '<Draws>', '<DisplayName>Prop</DisplayName>\n    <ArmorSet Armor="NoArmor" />\n    <Draws>')
    base = ('\n\t\t\t<SlowDeath id="ModuleTag_SlowDeath" SinkDelay="0.0s" SinkRate="3.0" DestructionDelay="8s">'
            '\n\t\t\t\t<DieMuxData DeathTypes="TOPPLED" />\n\t\t\t</SlowDeath>')
    if dyn:
        base = '\n\t\t\t<EnableDynamicsCollide id="ModuleTag_EnableDynamics"/>' + base
    x = _sub1(x, '<Behaviors>', '<Behaviors>' + base)
    x = _sub1(x, '<Geometry', '<Body>\n      <PropBody id="DefaultBody"/>\n    </Body>\n    <Geometry')
    x = _sub1(x, '</Geometry>', '</Geometry>\n    <CrusherInfo id="id_CrusherInfo" CrushableLevel="0" />')
    return Unit(name, x, what='灯笼的扁平复制（' + ('保留' if dyn else '去掉') + ' EnableDynamicsCollide）')


def _n(part):
    return f'UNIT - CNV Topple {part}'


def mission(which='a'):
    units = [lantern_copy(False), lantern_copy(True)] if which == 'c' else []
    m = Mission(name=f'CampTopple{which.upper()}', map=festival, units=units, facts={})
    for k, (crusher, prop, dy) in LANES[which].items():
        m.put(crusher, 'west field', -200.0, dy, angle=0.0, role=f'crusher {k}', name=_n(f'Crusher {k}'))
        m.put(prop, 'west field', 0.0, dy, side='civ', role=f'prop {k}', name=_n(f'Prop {k}'))
    return m


def topple_test(m, which='a'):
    t = Test()
    p1 = m.player('p1')
    x, y = m.site('west field')[:2]
    for k, (_, _, dy) in LANES[which].items():
        t.waypoints[f'Test Goal {k}'] = (x + 200.0, y + dy)
        t.areas[f'Test Goal {k}'] = square(x + 200.0, y + dy, 40.0)
    start = [('MAP_REVEAL_ALL_PERM', p1), ('SET_MILLISECOND_TIMER', 'Test Go', 1.0)]
    start += [('UNIT_SET_STANCE', _n(f'Crusher {k}'), HOLD_FIRE) for k in LANES[which]]
    t.scripts.append(Script('Test - start', [], start))
    go = [('MOVE_NAMED_UNIT_TO', _n(f'Crusher {k}'), f'Test Goal {k}') for k in LANES[which]]
    t.scripts.append(Script('Test - go', [('TIMER_EXPIRED', 'Test Go')], go + [('SET_FLAG', 'Test Going', 1)]))
    going = ('FLAG', 'Test Going', 1)
    t.counters.append(('CNV_Topple_Frames', '帧数'))
    t.scripts.append(Script('Test - frames', [going], [('INCREMENT_COUNTER', 1, 'CNV_Topple_Frames')], once=False))
    for k in LANES[which]:
        prop, crusher = _n(f'Prop {k}'), _n(f'Crusher {k}')
        t.counters.append((f'CNV_Topple_Row{k}', f'行{k}'))
        for j, (cond, step) in enumerate([(('NAMED_NOT_DESTROYED', prop), 1), (('NAMED_DYING', prop), 1000),
                                          (('NAMED_INSIDE_AREA', crusher, f'Test Goal {k}'), 1000000)]):
            t.scripts.append(Script(f'Test - row {k} {j}', [going, cond],
                                    [('INCREMENT_COUNTER', step, f'CNV_Topple_Row{k}')], once=False))
    t.expect = [('帧数', 0, 'ever>=', 1, RUN)]
    t.bench = [('bench_watch', dict(every=1.0, sheet=False, lines=len(t.counters), seconds=RUN))]
    return t


MISSION = {'engine_topple': mission, 'engine_topple_b': lambda: mission('b'), 'engine_topple_c': lambda: mission('c')}
CHECKS = {'engine_topple': {'a': topple_test}, 'engine_topple_b': {'b': lambda m: topple_test(m, 'b')},
          'engine_topple_c': {'c': lambda m: topple_test(m, 'c')}}
