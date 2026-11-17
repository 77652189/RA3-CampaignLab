"""Engine line A round 173 (Physics P5, work/re/a_physics_plan.md): how a plane shot down in the air falls.

Six retail templates set Physics GravityMultiplier (30 on the Apollo, the MiG, the Vindicator ...). But a plane
killed in the air does not fall itself: its DestroyDie removes it at once and its CreateObjectDie (RequiredStatus
AIRBORNE_TARGET) makes, from AUFighterAircraft_Dying_OCL (CHOOSE_ONE: AlliedFighterAircraft_Collapse, debris with no
Physics and no weapon, or AlliedFighterAircraft_Dying), another object LIKE_EXISTING INHERIT_VELOCITY (x 0.5). The
Dying one has a Physics of its own, all defaults but the tumble (GravityMultiplier 1, KillWhenRestingOnGround) and
FireWeaponWhenDead NormalAircraftDeathWeapon (150 EXPLOSIVE, radius 20): the crash's hit is where and when the wreck
comes to rest.

Two Apollo copies (CNV_CrashA / CNV_CrashB, ra3ext's CNVProbe on them) fly east from probe_air's flat ground and are
killed by script at the same frame; each one's air death makes only its own wreck copy, a probe on it too:
  plain  CNV_CrashADying: retail's AlliedFighterAircraft_Dying as it is (GravityMultiplier 1)
  gm30   CNV_CrashBDying: the same with GravityMultiplier 30 on its Physics -- the live Apollo's value
Prediction from the data (the knock-back g, 64/225 a frame squared x GravityMultiplier, handoff-c-archive): from
the Apollo's 175 (its locomotor's PreferredHeight), starting level, plain falls sqrt(2 x 175 / 0.284) ~ 35 frames,
gm30 ~ 6.4. The live plane's own GravityMultiplier never comes into the crash (it is gone the frame it dies).
Counters: each plane's death (NAMED_DESTROYED) and its wrecks on the map (1 while falling, 0 once it has crashed).

Bench 11-11 CampCFFall_mcp_1111_221320 (ra3ext.log; work/logs/a173_crash.log): both planes killed at frame 105 at
(2885, y, 387.44), 175 over the ground (212.5), flying east at 15 a frame. Each wreck gets a `shock` line (caller in
work/re, v =(7.5, 0.003, 0.0011): the inherited x 0.5) and a knock-back `build` -- the fall IS the knock curve:
  plain  land (3160, 1500, 212.5) a 0.0098 b 12.2286, N 30: probe frames 106..135, z 387.50 -> 212.50 (BENCH)
  gm30   land (2940, 2000, 212.5) a 0.0021 b 29.3680, N 8:  probe frames 106..113
So the wreck's OWN GravityMultiplier sets the fall (8 points against 30), and the live plane's 30 never comes in.
The numbers come from the free fall (simunits.meta_impact_fall): T = sqrt(2 d / g) (35.08 / 6.40 frames), landing =
start + 7.5 T rounded up to the 20 grid, n = ceil(distance / 7.5) (37 / 8), b = (7.5 n + 2a + d) / n.
"""
import math
import os

import labpaths
from maps import probe_air
from parts import Mission, Script, Test, Unit, counted
from checks.engine_suppress_probe import EVERY, LINES

PLANE, WRECK, OCL = 'AlliedFighterAircraft', 'AlliedFighterAircraft_Dying', 'AUFighterAircraft_Dying_OCL'
LANES = {'plain': ('CNV_CrashA', 1.0, 1500.0), 'gm30': ('CNV_CrashB', 30.0, 2000.0)}   # copy, wreck GM, y
START_X, GOAL_X = 1700.0, 4200.0
GO, KILL, RUN = 1.0, 7.0, 13.0                                 # mission seconds
# bench 11-11 CampCFFall_mcp_1111_221320: lane -> (the wreck's start, its v, the logged landing, N, its probe z
# from the frame after it was made, one a frame; plain's frame 107 line is missing, so its list starts at 108)
BENCH = {'plain': ((2885.0, 1500.47, 387.44), (7.5, 0.003, 0.0011), (3160.0, 1500.0, 212.5), 30,
                   [387.50, 387.41, 387.18, 386.77, 386.14, 385.25, 384.05, 382.50, 380.56, 378.18, 375.32, 371.95,
                    368.01, 363.47, 358.28, 352.39, 345.78, 338.39, 330.19, 321.12, 311.15, 300.23, 288.33, 275.40,
                    261.39, 246.26, 229.98, 212.50]),
         'gm30': ((2885.0, 2000.47, 387.44), (7.5, 0.003, 0.0011), (2940.0, 2000.0, 212.5), 8,
                  [383.64, 373.94, 355.00, 323.80, 277.31, 212.50])}


def _retail(*path):
    with open(os.path.join(labpaths.SDK3, 'SageXML', *path), encoding='utf-8') as f:
        return f.read()


def _probe(x, old, new):
    assert x.count(f'id="{old}"') == 1 and x.count('<Behaviors>') == 1, old
    x = x.replace(f'id="{old}"', f'id="{new}"', 1).replace(f'EditorName="{old}"', f'EditorName="{new}"')
    return x.replace('<Behaviors>', f'''<Behaviors>
			<DeletionUpdate id="ModuleTag_CNVProbe" MinFrames="{EVERY}" MaxFrames="{LINES}"/>''', 1)


def plane(lane):
    """[the Apollo copy, its wreck copy], probes on both; the plane's air death makes only that wreck."""
    uid, gm, _ = LANES[lane]
    wreck_id = uid + 'Dying'
    x = _probe(_retail('Allied', 'Units', PLANE + '.xml'), PLANE, uid)
    assert x.count(f'CreationList="{OCL}"') == 1
    x = x.replace(f'CreationList="{OCL}"', f'CreationList="{uid}OCL"')
    x = x.replace('</AssetDeclaration>', f'''	<ObjectCreationList id="{uid}OCL">
		<CreateObject Options="IGNORE_ALL_OBJECTS" Disposition="LIKE_EXISTING INHERIT_VELOCITY" Count="1"
			VelocityScale="0.5">
			<CreateObject>{wreck_id}</CreateObject>
		</CreateObject>
	</ObjectCreationList>
</AssetDeclaration>''', 1)
    w = _probe(_retail('Allied', 'Props', WRECK + '.xml'), WRECK, wreck_id)
    if gm != 1.0:
        assert w.count('id="ModuleTag_Physics"') == 1
        w = w.replace('id="ModuleTag_Physics"', f'id="ModuleTag_Physics" GravityMultiplier="{gm:g}"', 1)
    return [Unit(uid, x, link=[f'ObjectCreationList:{uid}OCL'], names=dict(unit=uid),
                 what='阿波罗的复制（探针）：空中打死只出自己的残骸复制',
                 params=dict(of=PLANE, every=EVERY, lines=LINES)),
            Unit(wreck_id, w, names=dict(unit=wreck_id),
                 what=f'阿波罗坠机残骸的复制（探针，GravityMultiplier {gm:g}）',
                 params=dict(of=WRECK, gm=gm, every=EVERY, lines=LINES))]


def name(lane):
    return f'UNIT - CNV Crash {lane}'


def mission():
    m = Mission(name='CampCF', map=probe_air, units=[u for k in LANES for u in plane(k)], facts={})
    m.ext = True                  # + the check's name: CampCFFall (<= 15)
    for lane, (uid, _, y) in LANES.items():
        m.put(uid, 'air flat S', 0.0, y - 1500.0, side='p1', angle=0.0, role=lane, name=name(lane))
    return m


def check(m):
    t = Test()
    start = [('MAP_REVEAL_ALL_PERM', m.player('p1')), ('SET_MILLISECOND_TIMER', 'Crash Go', GO),
             ('SET_MILLISECOND_TIMER', 'Crash Kill', KILL)]
    start += [('UNIT_CHANGE_OBJECT_STATUS', name(k), 'NO_ATTACK', 1) for k in LANES]
    start += [('SET_COUNTER', f'CNV_Crash_{k}_dead', 0) for k in LANES]
    t.scripts.append(Script('Test - start', [], start))
    go = []
    for k, (_, _, y) in LANES.items():
        t.waypoints[f'Crash Goal {k}'] = (GOAL_X, y)
        go.append(('MOVE_NAMED_UNIT_TO', name(k), f'Crash Goal {k}'))
    t.scripts.append(Script('Test - go', [('TIMER_EXPIRED', 'Crash Go')], go))
    t.scripts.append(Script('Test - kill', [('TIMER_EXPIRED', 'Crash Kill')], [('NAMED_KILL', name(k)) for k in LANES]))
    for k, (uid, _, _) in LANES.items():
        c = f'CNV_Crash_{k}_dead'
        t.counters.append((c, f'{k} dead'))
        t.scripts.append(Script(f'Test - dead {k}', [('NAMED_DESTROYED', name(k))], [('SET_COUNTER', c, 1)]))
        counted(f'CNV_Crash_{k}_wreck', f'{k} wreck', t, template=uid + 'Dying')
    # alive and no wreck before the kill; dead, the wreck down (crashed) a second after it
    # bench 11-11: both dead from the counters' s6 (their clock runs ~1 s behind the mission's), the wreck count 0 at
    # every sample (a wreck lives 29 / 7 frames; why the 0.5 s samples never see one is not read) -- the fall itself
    # is read in ra3ext.log (BENCH)
    t.expect = [(f'{k} dead', KILL, '==', 1, RUN) for k in LANES]
    t.expect += [(f'{k} wreck', 1.0, '==', 0, RUN) for k in LANES]
    t.bench = [('bench_watch', dict(seconds=RUN, every=.5, sheet=False, lines=len(t.counters)))]
    return t


# ---- hit (engine line A round 180): where and when the crash hurts. Three Apollo copies whose air death makes only
# the retail wreck (plain): F flies east as in fall (killed at 7 s near x 2885, its wreck lands at (3160, 1500) 30
# frames later); H and G hover where they were placed (no order) over (3000, 2000) / (3000, 2900) and are killed at
# the same frame. Hammers under each landing: s1's at F's landing, s1's 40 east of it (out of the radius 20, centre
# to centre), s1's under H, the player's own under G (NormalAircraftDeathWeapon's DamageScalarDetails: allies 50 %).
# Prediction from the data (simunits.air_wrecks / crash_frames, Sim.air_crash): F's hit 30 frames after the kill at
# (3160, 1500); H / G fall from rest, 35 frames (g n (n + 1) / 2 >= 175, INFERRED); 150 EXPLOSIVE through the
# Hammer's armour, G's half that; the one 40 off untouched.
HIT_LANES = {'F': ('CNV_CrashF', (1700.0, 1500.0), True), 'H': ('CNV_CrashH', (3000.0, 2000.0), False),
             'G': ('CNV_CrashG', (3000.0, 2900.0), False)}         # copy, placed at, flies east
TANK = 'SovietAntiVehicleVehicleTech1'
HIT_TARGETS = {'in': ((3160.0, 1500.0), 's1'), 'out': ((3200.0, 1500.0), 's1'), 'H': ((3000.0, 2000.0), 's1'),
               'G': ((3000.0, 2900.0), 'p1')}
HIT_STEP = {'in': 1, 'H': 100, 'G': 10000, 'out': 1000000}       # 帧: frames after the kill each one was untouched
# Bench 11-12 CampCHHit_mcp_1112_111034 PASS (work/logs/a180_bench.log): 帧 150383830 at s15 -- in 30, H 38, G 38,
# out never hit (150: every frame); 血 in 70, H 72, G 86. ra3ext: F's wreck as fall's plain (2885, 1500.47) v 7.5 land
# 3160 b 12.2286; H / G's from (3000, y, 387.5) v (0.1, 0, 0) land (3000, y) a 0 b 4.8297 (n 37, 38 points). So a
# hovering plane drifts 0.2 a frame along its facing, n = ceil(T) + 1, the landing to the nearest 20 (simunits.
# meta_impact_fall); the hit is the wreck's last point (count = points); G's own tank takes half (86 vs 72).
# Not explained: F's tank 70, not 72 (H's, the same tank and weapon) -- the moving wreck takes ~15 more off it
# (a hypothesis: Physics collision damage on the way in; not read).
HIT_BENCH = {'frames': {'in': 30, 'H': 38, 'G': 38, 'out': None}, 'health': {'in': 70, 'H': 72, 'G': 86}}


def hit_plane(lane):
    return crash_plane(HIT_LANES[lane][0])


def crash_plane(uid):
    x = _probe(_retail('Allied', 'Units', PLANE + '.xml'), PLANE, uid)
    x = x.replace(f'CreationList="{OCL}"', f'CreationList="{uid}OCL"')
    x = x.replace('</AssetDeclaration>', f'''	<ObjectCreationList id="{uid}OCL">
		<CreateObject Options="IGNORE_ALL_OBJECTS" Disposition="LIKE_EXISTING INHERIT_VELOCITY" Count="1"
			VelocityScale="0.5">
			<CreateObject>{uid}Dying</CreateObject>
		</CreateObject>
	</ObjectCreationList>
</AssetDeclaration>''', 1)
    w = _probe(_retail('Allied', 'Props', WRECK + '.xml'), WRECK, uid + 'Dying')
    return [Unit(uid, x, link=[f'ObjectCreationList:{uid}OCL'], names=dict(unit=uid),
                 what='阿波罗的复制（探针）：空中打死只出原版坠机残骸的复制', params=dict(of=PLANE, every=EVERY, lines=LINES)),
            Unit(uid + 'Dying', w, names=dict(unit=uid + 'Dying'), what='阿波罗坠机残骸的复制（探针，原版数值）',
                 params=dict(of=WRECK, every=EVERY, lines=LINES))]


def hit_name(k):
    return f'UNIT - CNV Crash Hit {k}'


def hit_mission():
    m = Mission(name='CampCH', map=probe_air, units=[u for k in HIT_LANES for u in hit_plane(k)], facts={})
    m.ext = True                  # CampCHHit
    for k, (uid, (x, y), _) in HIT_LANES.items():
        m.put(uid, 'air flat S', x - 1700.0, y - 1500.0, side='p1', angle=0.0, role=f'plane {k}', name=hit_name(k))
    for k, ((x, y), side) in HIT_TARGETS.items():
        m.put(TANK, 'air flat S', x - 1700.0, y - 1500.0, side=side, angle=0.0, role=f'tank {k}',
              name=hit_name('Tank ' + k))
    return m


def hit_check(m):
    t = Test()
    names = [hit_name(k) for k in HIT_LANES] + [hit_name('Tank ' + k) for k in HIT_TARGETS]
    t.scripts.append(Script('Test - start', [], [('MAP_REVEAL_ALL_PERM', m.player('p1')),
                                                 ('SET_MILLISECOND_TIMER', 'Crash Go', GO),
                                                 ('SET_MILLISECOND_TIMER', 'Crash Kill', KILL)]
                            + [('UNIT_CHANGE_OBJECT_STATUS', n, 'NO_ATTACK', 1) for n in names]
                            + [('SET_COUNTER', 'CNV_Crash_Frames', 0)]))
    t.waypoints['Crash Goal F'] = (GOAL_X, 1500.0)
    t.scripts.append(Script('Test - go', [('TIMER_EXPIRED', 'Crash Go')], [('MOVE_NAMED_UNIT_TO', hit_name('F'),
                                                                           'Crash Goal F')]))
    t.scripts.append(Script('Test - kill', [('TIMER_EXPIRED', 'Crash Kill')],
                            [('NAMED_KILL', hit_name(k)) for k in HIT_LANES] + [('SET_FLAG', 'Crash Killed', 1)]))
    t.counters.append(('CNV_Crash_Frames', '帧'))
    for k, step in HIT_STEP.items():
        t.scripts.append(Script(f'Test - untouched {k}', [('FLAG', 'Crash Killed', 1),
                                                          ('UNIT_HEALTH', hit_name('Tank ' + k), 3, 100)],
                                [('INCREMENT_COUNTER', step, 'CNV_Crash_Frames')], once=False))
    for k in ('in', 'H', 'G'):
        c = f'CNV_Crash_Health_{k}'
        t.counters.append((c, f'血{k}'))
        t.scripts.append(Script(f'Test - health {k}', [], [('SET_UNIT_HEALTH_PERCENTAGE_TO_COUNTER',
                                                           hit_name('Tank ' + k), c)], once=False))
    t.expect = [('血in', KILL + 4, '<', 100, RUN)]
    t.bench = [('bench_watch', dict(seconds=RUN, every=.5, sheet=False, lines=len(t.counters)))]
    return t


# ---- face (engine line A round 181): why hit's F tank (70) lost more than H's (72). The Hammer's armour
# (BaseTankArmor) takes Side 105 / Rear 110 by the angle from its facing to where its attacker is (docs/engine/
# weapons.md, engine_shot flank; the same place: front). 150 x 1.10 = 165 of 550 -> 70 exactly; 150 -> 72.7; 157.5 ->
# 71.4. Hypotheses: H1 the moving wreck's collision hurts on the way in, H2 the MetaImpact shock, H3 the flank scalar
# (F's wreck comes in from the west, behind the east-facing tank; H's rests where it started, no direction).
# Four F planes as hit's F (flying east, killed at 7 s near x 2885, wrecks land at x 3160) over Hammers facing east /
# north / west / south (four counter lines: no hovering lane; hit's H is the same-place case). Prediction H3: E 70,
# N 71, W 72, S 71; H1 / H2: the same whatever their facing (70).
FACE_LANES = {'E': (1500.0, 0.0), 'N': (1800.0, math.pi / 2), 'W': (2100.0, math.pi), 'S': (2400.0, -math.pi / 2)}
FACE_LAND_X = 3160.0
FACE_PREDICT = {'E': 70, 'N': 71, 'W': 72, 'S': 71}
# Bench 11-12 CampCKFace_mcp_1112_120614 PASS (work/logs/a181_bench.log): 血 E 70, N 71, W 71, S 70 from s8. H1 / H2
# out (not all 70): the flank scalar it is. All four wrecks logged the same (2885, y + 0.47) v 7.5 -> land (3160, y),
# last probe (3160.0, y) -- yet W is side, not front, and S rear: no one direction fits E rear and W side. A
# hypothesis (INFERRED, not read): the wreck rests a float hair off the tank's centre and the residue's main axis
# follows float32's step -- west under y 2048 (E rear, N side), north over it (W side, S rear). The hovering wrecks
# (hit's H / G, no move at all) rest exactly on: front (72 / 86).
FACE_BENCH = {'E': 70, 'N': 71, 'W': 71, 'S': 70}


def face_name(k):
    return f'UNIT - CNV Crash Face {k}'


def face_mission():
    units = [u for k in FACE_LANES for u in crash_plane(f'CNV_CrashK{k}')]
    m = Mission(name='CampCK', map=probe_air, units=units, facts={})
    m.ext = True                  # CampCKFace
    for k, (y, angle) in FACE_LANES.items():
        m.put(f'CNV_CrashK{k}', 'air flat S', 0.0, y - 1500.0, side='p1', angle=0.0, role=f'plane {k}',
              name=face_name(k))
        m.put(TANK, 'air flat S', FACE_LAND_X - 1700.0, y - 1500.0, side='s1', angle=angle, role=f'tank {k}',
              name=face_name('Tank ' + k))
    return m


def face_check(m):
    t = Test()
    keys = list(FACE_LANES)
    names = [face_name(k) for k in keys] + [face_name('Tank ' + k) for k in keys]
    t.scripts.append(Script('Test - start', [], [('MAP_REVEAL_ALL_PERM', m.player('p1')),
                                                 ('SET_MILLISECOND_TIMER', 'Crash Go', GO),
                                                 ('SET_MILLISECOND_TIMER', 'Crash Kill', KILL)]
                            + [('UNIT_CHANGE_OBJECT_STATUS', n, 'NO_ATTACK', 1) for n in names]))
    go = []
    for k, (y, _) in FACE_LANES.items():
        t.waypoints[f'Crash Goal {k}'] = (GOAL_X, y)
        go.append(('MOVE_NAMED_UNIT_TO', face_name(k), f'Crash Goal {k}'))
    t.scripts.append(Script('Test - go', [('TIMER_EXPIRED', 'Crash Go')], go))
    t.scripts.append(Script('Test - kill', [('TIMER_EXPIRED', 'Crash Kill')], [('NAMED_KILL', face_name(k))
                                                                              for k in keys]))
    for k in keys:
        c = f'CNV_Crash_Face_{k}'
        t.counters.append((c, f'血{k}'))
        t.scripts.append(Script(f'Test - health {k}', [], [('SET_UNIT_HEALTH_PERCENTAGE_TO_COUNTER',
                                                           face_name('Tank ' + k), c)], once=False))
    t.expect = [('血E', KILL + 4, '<', 100, RUN)]
    t.bench = [('bench_watch', dict(seconds=RUN, every=.5, sheet=False, lines=len(t.counters)))]
    return t


MISSION = {'engine_crash_fall': mission, 'engine_crash_hit': hit_mission, 'engine_crash_face': face_mission}
CHECKS = {'engine_crash_fall': {'fall': check}, 'engine_crash_hit': {'hit': hit_check},
          'engine_crash_face': {'face': face_check}}
