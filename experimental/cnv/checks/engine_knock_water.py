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
from parts import Mission, Obj, Script, Test
from checks.engine_clip import ORDER
from checks.engine_knock_probe import PROBE_TANK, TANK, probe_tank, rocket_gun
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
# gate<A> = edge's layout pushed with amount A round the Hammer's ShockwaveResistance 90 (BaseVehicle; round 167's 60
# launched nobody, 130 all three): does the raw amount gate the knock (A > 90: all three fly, the dry one too though
# its falloff leaves 0.63 A; A < 90: no `shock` line at all), or the amount after falloff? Bench 11-11 (all PASS,
# read in ra3ext.log): 91 CampKWGate91_mcp_1111_205100 and 90 CampKWGate90_mcp_1111_205701 all three fly, landing
# 2750 / 2530 / 2670,3350, N 9 / 8 / 11; 89 CampKWGate89_mcp_1111_205321 no `shock` line. The raw amount, >= 90 flies.
GATES = (89, 90, 91)
CHECK_LANES.update({f'gate{a}': ('tank', (a, 250, 8.5)) for a in GATES})
SHIFT = {'edge': 40.0, **{f'gate{a}': 40.0 for a in GATES}}   # the lane's units moved east for that check
# what dies (bench 11-11): man lane nobody (the wet one lands on his own bank), tank lane the wet one
DEAD = {'man': 0, 'tank': 1, 'far': 0, 'ramp': 0, 'edge': 0, **{f'gate{a}': 0 for a in GATES}}
# farfire (Physics P4b): can a knocked man fire IN the air? far's push; the dry man's low flat flight (1940 -> 1560,
# 27 points, frames 173..199, ~22 over the flat bank) passes a retail Hammer (TANK, p1, NO_ATTACK) at (1730, 3350),
# 60 off his line: within his 150 (2-D, and 3-D at that height alike) over x 1593..1867, ~frames 177..196; his
# launch and landing both ~185+ off. He is ordered at ORDER + SHOOT (frame ~176, just after the lift): a hit by s14
# (his landing ~s13.3, out of range there) = he fires in the air; none until after his hold and a walk (~s17) = he
# does not (the simulator's INFERRED rule) -- 22 up, the 3-D range cannot be what stops him.
# Bench 11-11 CampKWFarfire_mcp_1111_212052 (ra3ext.log probe lines): shock at 175, N 25, he passes the Hammer at
# 20-22 up from frame ~182 to 196 within its 150 (2-D gap) -- the Hammer stays 100 to s15: NO fire in the air. He
# lies at (1560, 3280) (gap 152, out of reach) to frame 248, first step 249 = landing 199 + 50 (move orders: + 38,
# engine_knock_probe stand), walks 5 frames to (1575.8, 3274.7), gap 140.2 -- 10 inside his 150 -- and fires from
# there (first damage s16). farwalk tells the 12 extra frames apart: the same flight, the Hammer straight ahead of
# him, west of his landing and out of reach (gap ~169 at (1360, 3280)): first step at 237 = his turn to face the
# Hammer (here ~158 degrees, stand's 90), at 249 = the attack order's own wait. Bench 11-11
# CampKWFarwalk_mcp_1111_212626 PASS: still 249 (simunits.KNOCK_ATTACK_WAIT); he walks 11 frames west and stops at
# (1524.0, 3272.8), centre 164.2 off, gap 132.8 (farfire's 140.2: where the approach ends is unexplained).
CHECK_LANES['farfire'] = CHECK_LANES['farwalk'] = ('man', (285, 250, 8.5))
DEAD['farfire'] = DEAD['farwalk'] = 0
FIRE_AT = {'farfire': ('dry', (1730.0, 3350.0)),              # the shooter, the Hammer he is ordered on
           'farwalk': ('dry', (1360.0, 3280.0))}
SHOOT = 5.7                                                   # after ORDER: frame ~176 (the lift is 173)
AIR_BY = 14.0                                                 # his landing ~13.3 s: hit before = in the air
# climb (Physics, the curve up to higher ground): ramp's layout moved 560 east, so the wet Hammer stands on the flat
# east of the table's east ramp (3000..3060) and the burst pushes it west, up onto the table. From the data (burst
# ~10.7 west of the target, as ramp / edge) its level-ground landing is ~2920, the +10 grid 2930 on the table top
# (268.75, 56 over its launch); man and dry land on the flat east. Bench 11-11 CampKWClimb_mcp_1111_214128 PASS (all
# live): the wet one's `build` land=(2930, 850, 268.75) a 9.49, N 18, its own landing not moved; the curve climbs
# over the ramp (no dip into it) to an apex 275.00 at frame 185 and comes down onto the top at 190 -- both controls
# at the landing + 1.3 a (281.09, the probe points fitted to 0.005; simunits.meta_impact_trajectory). The direct hit
# lands (3290, 1030) N 21, the dry one (3350, 830) N 14.
CHECK_LANES['climb'] = ('ramp', SHOCK)
SHIFT['climb'] = 560.0
DEAD['climb'] = 0
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
    expect, run, healths = {}, RUN, (('man', 99), ('dry', 100))
    if which in FIRE_AT:            # four counter lines at most: the shooter's health and death give way
        shooter, (x, y) = FIRE_AT[which]
        run, healths = ORDER + 18.0, (('man', 99),)
        m.objects.append(Obj(TANK, x, y, side='p1', name=name(lane, 'target'), site=LANES[lane][1]))
        t.scripts[0].do += [('UNIT_CHANGE_OBJECT_STATUS', name(lane, 'target'), 'NO_ATTACK', 1),
                            ('SET_MILLISECOND_TIMER', 'Shore Shoot', ORDER + SHOOT)]
        t.scripts.append(Script('Test - shoot', [('TIMER_EXPIRED', 'Shore Shoot')],
                                [('UNIT_CHANGE_OBJECT_STATUS', name(lane, shooter), 'NO_ATTACK', 0),
                                 ('NAMED_ATTACK_NAMED', name(lane, shooter), name(lane, 'target'))]))
    for p, hp in healths:
        c = f'CNV_Shore_{p}'
        t.counters.append((c, f'{p} health'))
        t.scripts.append(Script(f'Test - health {p}', [],
                                [('SET_UNIT_HEALTH_PERCENTAGE_TO_COUNTER', name(lane, p), c)], once=False))
        expect[f'{p} health'] = hp
    for p, dead in (('wet', DEAD[which]),) + ((('dry', 0),) if which not in FIRE_AT else ()):
        c = f'CNV_Shore_{p}_dead'
        t.counters.append((c, f'{p} dead'))
        t.scripts.append(Script(f'Test - dead {p}', [('NAMED_DESTROYED', name(lane, p))], [('SET_COUNTER', c, 1)]))
        expect[f'{p} dead'] = dead
    t.expect = [(label, run - 2, '==', expect[label], run) for _, label in t.counters]
    if which in FIRE_AT:
        c = 'CNV_Shore_target'
        t.counters.append((c, 'target health'))
        t.scripts.append(Script('Test - health target', [],
                                [('SET_UNIT_HEALTH_PERCENTAGE_TO_COUNTER', name(lane, 'target'), c)], once=False))
        # untouched while he flies (prediction: no fire in the air), hit by the end (he walks in and fires)
        t.expect += [('target health', AIR_BY - 2, '==', 100, AIR_BY + 1), ('target health', run - 2, '<', 100, run)]
    t.bench = [('bench_watch', dict(seconds=run, every=.5, sheet=False, lines=len(t.counters)))]
    return t


MISSION = {'engine_knock_water': mission}
CHECKS = {'engine_knock_water': {k: (lambda m, k=k: check(m, k)) for k in CHECK_LANES}}
