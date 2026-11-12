"""Engine line A round 163 (Physics P3, work/re/a_physics_plan.md): does a body knocked back into water die?

Generals' PhysicsBehavior kills a stunned (knocked-back) unit that comes to rest where it cannot be -- water for a
land unit, a cliff, off the map (PhysicsUpdate.cpp testStunnedUnitForDestruction). RA3's PhysicsBehavior.xsd keeps
the knock-back curve and the stun times; whether the rule is still there is what this reads.

On maps/probe_air's sea lane (y 3300: ground 340 ours, the water at 320, a trench x 2100..2500 with a floor at 250)
one rocket a lane (engine_knock_probe's retail V4 rocket, its warhead the 1.5 hit and a MetaImpactNugget of
ShockWaveAmount 200 -- retail's top -- radius 250, z mult 8.5) hits a target standing on the bank, its two
neighbours on either side of it: the one on the trench's side is pushed over the water, the other the same distance
onto dry ground (the control). Every unit is NO_ATTACK but the gun's one shot; the DamageNugget has Radius 0, so the
neighbours take no damage.

  man   Peacekeeper probes (engine_suppress_probe's CNV_SuppProbeMan), target at x 2000, neighbours 60 east / west
  tank  Hammer probes (engine_knock_probe's CNV_KnockHammer), target at x 2600 (the far bank), neighbours 80 west / east

Prediction from the data (simunits.meta_impact_velocity / _ground_launch on level ground): the man's wet neighbour
flies 17 frames and lands at x 2220 (trench floor, 70 under water), the dry one at x 1780; the Hammer's at 2380 /
2820. Generals' rule: the wet one dies, the dry one lives (no fall damage: engine_knock_probe land).
The two lanes are 600 apart (the shock's radius is 250), one check each (four counter lines at most).

Bench 11-11 (ra3ext.log `build ... land=` lines; work/logs/a163_water_*.log):
  man  CampKWMan_mcp_1111_151010: NOBODY dies. The wet man's own landing (2060 + 10.11 x 17 = 2232, in the trench) is
       moved by the engine to (2080, 3280) on his own bank (z 212.5, flat), N 5 points -- he never reaches the water;
       the dry one lands at (1760, 3280) as predicted. The target (direct hit, vertical) is flung to (2000, -1660),
       far off the map, and lives (health 99 to the end): no off-map kill.
  tank CampKWTank_mcp_1111_151445: PASS as written. The wet Hammer's own landing (2404, 3325) is moved to
       (2490, 3330, 203.1) -- the far bank's slope (rising 156 -> 212 over 2440..2500), 10-unit steps, not the
       20 grid -- and it is gone the frame it lands (178); the target, flung to (2490, 3530, 203.1), likewise (192).
       The dry one at (2830, 3330, 212.5) lives.
  So: RA3 keeps a knocked body out of water by moving the landing point (the end cell is tested
  for the body's locomotor; when it fails another cell is searched for -- work/re/asm/a163_*.txt, A handoff); what lands on
  the slope dies (Generals' cliff rule, INFERRED). far tells the two searches apart (along the line / nearest cell).
  far  CampKWFar_mcp_1111_151821: PASS. The wet man's own landing (2400, in the trench, 100 short of the far bank)
       is moved to (2500, 3280, 212.5) -- the FAR bank's flat top, the nearest standable cell, not back along the
       line -- and he lives. (The dry one lands at 1560, not the 1580 predicted: n 26-27, not 25 -- unexplained.)
  ramp CampKWRamp_mcp_1111_172522 (round 166, PASS as written): the tank lane on probe_air's dry table (y 800,
       amount 130). The wet Hammer lands where predicted, its own landing not moved: (2470, 810, 240.6) on the
       ramp's slope (the trench bank's 15 a cell, 65 ours above the water), and LIVES to the end (frame 375); the
       dry one (2730, 810) and the direct hit (2650, 890) on the table live too. So the slope does not kill: the
       tank lane's Hammer died for the water's nearness (its slope cell 5 over the water, the 20 cell round its
       +10 point reaching under it, INFERRED), not Generals' cliff rule.
  edge CampKWEdge_mcp_1111_174551 (round 167, PASS as written): the tank lane 40 east, amount 130. The wet Hammer's
       engine landing (`build` line) is (2510, 3310, 212.5) -- the far bank's flat top, right at the slope's edge,
       its cell [2510, 2520) 20 over the water, the 5-over slope cell 2490 within 20 of its +10 point -- and it LIVES
       to the end. So it is the landing cell itself that kills (2490: 5 over the water, dead; 2510: 20 over, alive;
       ramp 2470: 65 over, alive), not a footprint round it: the threshold lies between 5 and 20 (the men's
       stand test's 10, INFERRED). The landings are on the 20 grid +10 in both x and y (2510, 3310 / 2770, 3310 /
       the direct hit 2690, 3390). The first try (amount 60, the lane unshifted, CampKWEdge_mcp_1111_174217)
       launched nobody, not even the direct hit (v 34 up by the formula): below some shock amount no knock at all.
"""
from maps import probe_air
from parts import Mission, Script, Test
from checks.engine_clip import ORDER
from checks.engine_knock_probe import PROBE_TANK, probe_tank, rocket_gun
from checks.engine_suppress_probe import PROBE, probe_man

GUN = 'CNV_KnockShore'
SHOCK = (200, 250, 8.5)                                       # amount, radius, z mult
# check -> (its lane, the gun's shock). far = the man lane pushed harder: the wet one's own landing at x 2400 in the
# trench, 100 short of the far bank (amount 285: v 14.35/frame, n 25, 2060 + 359 = 2419 -> 2400) -- does the engine
# put him back on his own bank (along the line) or on the nearer far bank (nearest standable cell)?
# ramp = the tank lane's layout on probe_air's dry table (y 800), pushed softer (amount 130: the wet Hammer's own
# landing 2520 - 5.4 x 9 = 2471 -> the 20 grid's +10 point 2470, on the ramp's slope, z 385 ours, 65 above the
# water) -- the trench's slope without the water: dies = the slope kills (Generals' cliff rule), lives = the water's
# nearness killed the tank lane's one
# edge = the tank lane 40 east (SHIFT: target 2640, the wet Hammer 2560) pushed as ramp (amount 130: ramp's wet one
# moved 49, so 2560 - 49 = 2511 -> the +10 point 2510): the far bank's flat top, its cell [2510, 2520) 20 over the
# water, the slope cell 2490 (5 over) 10..20 away -- lives = only the landing cell's own nearness to the water kills,
# dies = the body's footprint round it does. (Round 167's first try, amount 60 unshifted, launched nobody, not even
# the direct hit: CampKWEdge_mcp_1111_174217, no `build` line, all three at their spots to frame 345.)
CHECK_LANES = {'man': ('man', SHOCK), 'tank': ('tank', SHOCK), 'far': ('man', (285, 250, 8.5)),
               'ramp': ('ramp', (130, 250, 8.5)), 'edge': ('tank', (130, 250, 8.5))}
SHIFT = {'edge': 40.0}                                        # the lane's units moved east for that check
# what dies (bench 11-11): man lane nobody (the wet one lands on his own bank), tank lane the wet one
DEAD = {'man': 0, 'tank': 1, 'far': 0, 'ramp': 0, 'edge': 0}
# lane: (target template, its site, target's x on site..E, the wet neighbour's x offset)
LANES = {'man': (PROBE, 'air sea S', 300.0, 60.0), 'tank': (PROBE_TANK, 'air sea S', 900.0, -80.0),
         'ramp': (PROBE_TANK, 'air ramp S', 900.0, -80.0)}     # sea S (1700, 3300), ramp S (1700, 800)
RANGE = 450.0                                                 # the gun south of its target
STOP = 2.0                                                    # retail's 0.5 s pre-attack, reload 4.5 s: one rocket
RUN = ORDER + 14.0
PARTS = ('man', 'wet', 'dry')


def name(lane, part):
    return f'UNIT - CNV Shore {lane} {part}'


def units(shock=SHOCK):
    return [rocket_gun(GUN, shock), probe_man(), probe_tank()]


def mission():
    m = Mission(name='CampKW', map=probe_air, units=units(), facts={})
    m.ext = True                  # + the check's name: CampKWMan (<= 15)
    for lane, (target, site, x, wet) in LANES.items():
        m.put(GUN, site, x, -RANGE, side='p1', angle=1.5708, name=name(lane, 'gun'))
        m.put(target, site, x, 0.0, side='s1', role=lane, name=name(lane, 'man'))
        m.put(target, site, x + wet, 0.0, side='s1', name=name(lane, 'wet'))
        m.put(target, site, x - wet, 0.0, side='s1', name=name(lane, 'dry'))
    return m


def check(m, which):
    lane, shock = CHECK_LANES[which]
    m.units = units(shock)
    moved = {name(lane, p) for p in ('gun',) + PARTS}
    for o in m.objects:
        if o.name in moved:
            o.x += SHIFT.get(which, 0.0)
    t = Test()
    start = [('MAP_REVEAL_ALL_PERM', m.player('p1'))]
    start += [('UNIT_CHANGE_OBJECT_STATUS', name(k, p), 'NO_ATTACK', 1) for k in LANES for p in ('gun',) + PARTS]
    start += [('SET_MILLISECOND_TIMER', 'Shore Fire', float(ORDER)),
              ('SET_MILLISECOND_TIMER', 'Shore Stop', ORDER + STOP)]
    start += [('SET_COUNTER', f'CNV_Shore_{p}_dead', 0) for p in ('wet', 'dry')]
    t.scripts.append(Script('Test - start', [], start))
    t.scripts.append(Script('Test - fire', [('TIMER_EXPIRED', 'Shore Fire')],
                            [('UNIT_CHANGE_OBJECT_STATUS', name(lane, 'gun'), 'NO_ATTACK', 0),
                             ('NAMED_ATTACK_NAMED', name(lane, 'gun'), name(lane, 'man'))]))
    t.scripts.append(Script('Test - stop', [('TIMER_EXPIRED', 'Shore Stop')],
                            [('UNIT_CHANGE_OBJECT_STATUS', name(lane, 'gun'), 'NO_ATTACK', 1)]))
    expect = {}
    for p, hp in (('man', 99), ('dry', 100)):
        c = f'CNV_Shore_{p}'
        t.counters.append((c, f'{p} health'))
        t.scripts.append(Script(f'Test - health {p}', [],
                                [('SET_UNIT_HEALTH_PERCENTAGE_TO_COUNTER', name(lane, p), c)], once=False))
        expect[f'{p} health'] = hp
    for p, dead in (('wet', DEAD[which]), ('dry', 0)):
        c = f'CNV_Shore_{p}_dead'
        t.counters.append((c, f'{p} dead'))
        t.scripts.append(Script(f'Test - dead {p}', [('NAMED_DESTROYED', name(lane, p))], [('SET_COUNTER', c, 1)]))
        expect[f'{p} dead'] = dead
    t.expect = [(label, RUN - 2, '==', expect[label], RUN) for _, label in t.counters]
    t.bench = [('bench_watch', dict(seconds=RUN, every=.5, sheet=False, lines=len(t.counters)))]
    return t


MISSION = {'engine_knock_water': mission}
CHECKS = {'engine_knock_water': {k: (lambda m, k=k: check(m, k)) for k in CHECK_LANES}}
