"""Engine probe: the prop body -- what script damage, a script kill and a direct attack do to a placed map prop
(engine line E round 1). 1443 of the 2524 templates the retail campaign maps place have this body; 965 of them have
nothing else that acts (street segments, planters: no topple, no slow death, no crush), the rest fall over
(engine_topple) or sink. Retail data (SDK SageXML): the prop body has no fields at all (PropBodyModuleData extends
BodyModuleData with an empty sequence): no MaxHealth. BaseSimulatedProp's KindOf is IMMOBILE UNATTACKABLE
NOT_AUTOACQUIRABLE SIMPLE_OBJECT_PROP CLEARED_BY_BUILD; its SlowDeath only answers DeathTypes TOPPLED (8 s).

Questions: what health does the script read (SET_UNIT_HEALTH_PERCENTAGE_TO_COUNTER) on a body with no MaxHealth; does
NAMED_DAMAGE hurt or kill it; does NAMED_KILL destroy it, at once or through a dying state; does a tank told to
NAMED_ATTACK_NAMED a prop shoot it at all.

On the festival map, west field, three lanes 300 apart, each a neutral ('civ') prop:
  lane 1 AM_StreetSegment01 (the prop body only)   lane 2 CS_Tree01 (topple + slow death)   lane 3 OK_Lantern01
  (BaseSimulatedProp: topple, slow death, dynamics collide)
Variants, all at 'Test Go' (1 s in):
  a  NAMED_DAMAGE 10 on each prop
  b  NAMED_KILL on each prop
  c  a player Hammer 120 west of each prop (no hold-fire) is told NAMED_ATTACK_NAMED its prop
Counters (four lines at most), read every 0.5 s:
  a     血k (k = 1..3) the prop's health percent, written every frame; 存 = per frame from Go on, 1000^(k-1) for
        each lane k whose prop is not destroyed
  b, c  帧数 frames since Go; 行k 1 x frames the prop is not destroyed + 1000 x frames it is dying

PREDICTED (the simulator today, before the bench): it gives a body without MaxHealth 300 HP (Sim.add's default);
see the readings once run.
"""
from maps import festival
from parts import Mission, Script, Test

HAMMER = 'SovietAntiVehicleVehicleTech1'
PROPS = {1: ('AM_StreetSegment01', -300.0), 2: ('CS_Tree01', 0.0), 3: ('OK_Lantern01', 300.0)}
RUN = 20.0


def _n(part):
    return f'UNIT - CNV Prop {part}'


def mission(which='a'):
    m = Mission(name=f'CampPropBd{which.upper()}', map=festival, units=[], facts={})
    for k, (prop, dy) in PROPS.items():
        m.put(prop, 'west field', 0.0, dy, side='civ', role=f'prop {k}', name=_n(f'Prop {k}'))
        if which == 'c':
            m.put(HAMMER, 'west field', -120.0, dy, angle=0.0, role=f'gun {k}', name=_n(f'Gun {k}'))
    return m


def prop_test(m, which='a'):
    t = Test()
    start = [('MAP_REVEAL_ALL_PERM', m.player('p1')), ('SET_MILLISECOND_TIMER', 'Test Go', 1.0)]
    t.scripts.append(Script('Test - start', [], start))
    if which == 'a':
        go = [('NAMED_DAMAGE', _n(f'Prop {k}'), 10.0) for k in PROPS]
    elif which == 'b':
        go = [('NAMED_KILL', _n(f'Prop {k}')) for k in PROPS]
    else:
        go = [('NAMED_ATTACK_NAMED', _n(f'Gun {k}'), _n(f'Prop {k}')) for k in PROPS]
    t.scripts.append(Script('Test - go', [('TIMER_EXPIRED', 'Test Go')], go + [('SET_FLAG', 'Test Going', 1)]))
    going = ('FLAG', 'Test Going', 1)
    if which == 'a':                    # four lines at most: the three healths, then who is still there
        t.counters.append(('CNV_Prop_Left', '存'))
        for k in PROPS:
            prop = _n(f'Prop {k}')
            t.counters.insert(k - 1, (f'CNV_Prop_Health{k}', f'血{k}'))
            t.scripts.append(Script(f'Test - health {k}', [], [('SET_UNIT_HEALTH_PERCENTAGE_TO_COUNTER', prop,
                                                                 f'CNV_Prop_Health{k}')], once=False))
            t.scripts.append(Script(f'Test - left {k}', [going, ('NAMED_NOT_DESTROYED', prop)],
                                    [('INCREMENT_COUNTER', 1000 ** (k - 1), 'CNV_Prop_Left')], once=False))
    else:
        t.counters.append(('CNV_Prop_Frames', '帧数'))
        t.scripts.append(Script('Test - frames', [going], [('INCREMENT_COUNTER', 1, 'CNV_Prop_Frames')], once=False))
        for k in PROPS:
            prop = _n(f'Prop {k}')
            t.counters.append((f'CNV_Prop_Row{k}', f'行{k}'))
            for j, (cond, step) in enumerate([(('NAMED_NOT_DESTROYED', prop), 1), (('NAMED_DYING', prop), 1000)]):
                t.scripts.append(Script(f'Test - row {k} {j}', [going, cond],
                                        [('INCREMENT_COUNTER', step, f'CNV_Prop_Row{k}')], once=False))
    t.expect = [(t.counters[-1][1] if which == 'a' else '帧数', 0, 'ever>=', 1, RUN)]
    t.bench = [('bench_watch', dict(every=0.5, sheet=False, lines=len(t.counters), seconds=RUN))]
    return t


MISSION = {'engine_propbody': lambda: mission('a'), 'engine_propbody_b': lambda: mission('b'),
           'engine_propbody_c': lambda: mission('c')}
CHECKS = {'engine_propbody': {'a': lambda m: prop_test(m, 'a')},
          'engine_propbody_b': {'b': lambda m: prop_test(m, 'b')},
          'engine_propbody_c': {'c': lambda m: prop_test(m, 'c')}}
