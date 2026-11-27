"""Body state and death bench checks."""


import math


LANES = {'plain': ('CNV_CrashA', 1.0, 1500.0), 'gm30': ('CNV_CrashB', 30.0, 2000.0)}   # copy, wreck GM, y

# bench 11-11 CampCFFall_mcp_1111_221320: lane -> (the wreck's start, its v, the logged landing, N, its probe z
# from the frame after it was made, one a frame; plain's frame 107 line is missing, so its list starts at 108)
BENCH = {'plain': ((2885.0, 1500.47, 387.44), (7.5, 0.003, 0.0011), (3160.0, 1500.0, 212.5), 30,
                   [387.50, 387.41, 387.18, 386.77, 386.14, 385.25, 384.05, 382.50, 380.56, 378.18, 375.32, 371.95,
                    368.01, 363.47, 358.28, 352.39, 345.78, 338.39, 330.19, 321.12, 311.15, 300.23, 288.33, 275.40,
                    261.39, 246.26, 229.98, 212.50]),
         'gm30': ((2885.0, 2000.47, 387.44), (7.5, 0.003, 0.0011), (2940.0, 2000.0, 212.5), 8,
                  [383.64, 373.94, 355.00, 323.80, 277.31, 212.50])}

HIT_STEP = {'in': 1, 'H': 100, 'G': 10000, 'out': 1000000}       # 帧: frames after the kill each one was untouched

# Bench 11-12 CampCHHit_mcp_1112_111034 PASS (work/logs/a180_bench.log): 帧 150383830 at s15 -- in 30, H 38, G 38,
# out never hit (150: every frame); 血 in 70, H 72, G 86. ra3ext: F's wreck as fall's plain (2885, 1500.47) v 7.5 land
# 3160 b 12.2286; H / G's from (3000, y, 387.5) v (0.1, 0, 0) land (3000, y) a 0 b 4.8297 (n 37, 38 points). So a
# hovering plane drifts 0.2 a frame along its facing, n = ceil(T) + 1, the landing to the nearest 20 (simunits.
# meta_impact_fall); the hit is the wreck's last point (count = points); G's own tank takes half (86 vs 72).
# Not explained: F's tank 70, not 72 (H's, the same tank and weapon) -- the moving wreck takes ~15 more off it
# (a hypothesis: Physics collision damage on the way in; not read).
HIT_BENCH = {'frames': {'in': 30, 'H': 38, 'G': 38, 'out': None}, 'health': {'in': 70, 'H': 72, 'G': 86}}

# ---- face (engine line A round 181): why hit's F tank (70) lost more than H's (72). The Hammer's armour
# (BaseTankArmor) takes Side 105 / Rear 110 by the angle from its facing to where its attacker is (docs/engine/
# weapons.md, engine_shot flank; the same place: front). 150 x 1.10 = 165 of 550 -> 70 exactly; 150 -> 72.7; 157.5 ->
# 71.4. Hypotheses: H1 the moving wreck's collision hurts on the way in, H2 the MetaImpact shock, H3 the flank scalar
# (F's wreck comes in from the west, behind the east-facing tank; H's rests where it started, no direction).
# Four F planes as hit's F (flying east, killed at 7 s near x 2885, wrecks land at x 3160) over Hammers facing east /
# north / west / south (four counter lines: no hovering lane; hit's H is the same-place case). Prediction H3: E 70,
# N 71, W 72, S 71; H1 / H2: the same whatever their facing (70).
FACE_LANES = {'E': (1500.0, 0.0), 'N': (1800.0, math.pi / 2), 'W': (2100.0, math.pi), 'S': (2400.0, -math.pi / 2)}

# Bench 11-12 CampCKFace_mcp_1112_120614 PASS (work/logs/a181_bench.log): 血 E 70, N 71, W 71, S 70 from s8. H1 / H2
# out (not all 70): the flank scalar it is. All four wrecks logged the same (2885, y + 0.47) v 7.5 -> land (3160, y),
# last probe (3160.0, y) -- yet W is side, not front, and S rear: no one direction fits E rear and W side. A
# hypothesis (INFERRED, not read): the wreck rests a float hair off the tank's centre and the residue's main axis
# follows float32's step -- west under y 2048 (E rear, N side), north over it (W side, S rear). The hovering wrecks
# (hit's H / G, no move at all) rest exactly on: front (72 / 86).
FACE_BENCH = {'E': 70, 'N': 71, 'W': 71, 'S': 70}

def face_name(k):
    return f'UNIT - CNV Crash Face {k}'

CREATION = tuple('Upgrade_CreationVeterancy_' + x for x in ('VETERAN', 'ELITE', 'HEROIC'))

SHROUD_LANES = ('base', 'high', 'order', 'removed')


def engine_crash_fall():
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
    from benches.weapon.target_effects.checks import engine_suppress_probe
    suppress_probe = engine_suppress_probe()["shared"]
    EVERY = suppress_probe.EVERY
    LINES = suppress_probe.LINES

    PLANE, WRECK, OCL = 'AlliedFighterAircraft', 'AlliedFighterAircraft_Dying', 'AUFighterAircraft_Dying_OCL'
    START_X, GOAL_X = 1700.0, 4200.0
    GO, KILL, RUN = 1.0, 7.0, 13.0                                 # mission seconds


    def _retail(*path):
        with open(os.path.join(labpaths.SDK3, 'SageXML', *path), encoding='utf-8') as f:
            return f.read()


    def _probe(x, old, new):
        assert x.count(f'id="{old}"') == 1 and x.count('<Behaviors>') == 1, old
        x = x.replace(f'id="{old}"', f'id="{new}"', 1).replace(f'EditorName="{old}"', f'EditorName="{new}"')
        return x.replace('<Behaviors>', (
            f'<Behaviors>\n'
            f'\t\t\t<DeletionUpdate id="ModuleTag_CNVProbe" MinFrames="{EVERY}" MaxFrames="{LINES}"/>'
        ), 1)


    def plane(lane):
        """[the Apollo copy, its wreck copy], probes on both; the plane's air death makes only that wreck."""
        uid, gm, _ = LANES[lane]
        wreck_id = uid + 'Dying'
        x = _probe(_retail('Allied', 'Units', PLANE + '.xml'), PLANE, uid)
        assert x.count(f'CreationList="{OCL}"') == 1
        x = x.replace(f'CreationList="{OCL}"', f'CreationList="{uid}OCL"')
        x = x.replace('</AssetDeclaration>', (
            f'\t<ObjectCreationList id="{uid}OCL">\n'
            f'\t\t<CreateObject Options="IGNORE_ALL_OBJECTS" Disposition="LIKE_EXISTING INHERIT_VELOCITY" Count="1"\n'
            f'\t\t\tVelocityScale="0.5">\n'
            f'\t\t\t<CreateObject>{wreck_id}</CreateObject>\n'
            f'\t\t</CreateObject>\n'
            f'\t</ObjectCreationList>\n'
            f'</AssetDeclaration>'
        ), 1)
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
    # Prediction from the data (simunits.air_wrecks / crash_frames, Life.air_crash): F's hit 30 frames after the kill at
    # (3160, 1500); H / G fall from rest, 35 frames (g n (n + 1) / 2 >= 175, INFERRED); 150 EXPLOSIVE through the
    # Hammer's armour, G's half that; the one 40 off untouched.
    HIT_LANES = {'F': ('CNV_CrashF', (1700.0, 1500.0), True), 'H': ('CNV_CrashH', (3000.0, 2000.0), False),
                 'G': ('CNV_CrashG', (3000.0, 2900.0), False)}         # copy, placed at, flies east
    TANK = 'SovietAntiVehicleVehicleTech1'
    HIT_TARGETS = {'in': ((3160.0, 1500.0), 's1'), 'out': ((3200.0, 1500.0), 's1'), 'H': ((3000.0, 2000.0), 's1'),
                   'G': ((3000.0, 2900.0), 'p1')}


    def hit_plane(lane):
        return crash_plane(HIT_LANES[lane][0])


    def crash_plane(uid):
        x = _probe(_retail('Allied', 'Units', PLANE + '.xml'), PLANE, uid)
        x = x.replace(f'CreationList="{OCL}"', f'CreationList="{uid}OCL"')
        x = x.replace('</AssetDeclaration>', (
            f'\t<ObjectCreationList id="{uid}OCL">\n'
            f'\t\t<CreateObject Options="IGNORE_ALL_OBJECTS" Disposition="LIKE_EXISTING INHERIT_VELOCITY" Count="1"\n'
            f'\t\t\tVelocityScale="0.5">\n'
            f'\t\t\t<CreateObject>{uid}Dying</CreateObject>\n'
            f'\t\t</CreateObject>\n'
            f'\t</ObjectCreationList>\n'
            f'</AssetDeclaration>'
        ), 1)
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


    FACE_LAND_X = 3160.0
    FACE_PREDICT = {'E': 70, 'N': 71, 'W': 72, 'S': 71}




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
    return dict(MISSION=MISSION, CHECKS=CHECKS)


def engine_crush():
    """Engine unit test: 物理碰撞 (ADR 0019 layer 2; CrusherInfo, DestroyDie + the collapse OCL) -- two questions only:
    can a unit drive over another (and which), and does a destroyed building take time to go.

    Retail data (SDK SageXML): CrusherInfo CrusherLevel / CrushableLevel -- infantry crushable 10, vehicles 20, Soviet
    structures 40; the Hammer (SovietAntiVehicleVehicleTech1) inherits crusher 10 from BaseVehicle and sets its own 20;
    the Apocalypse (SovietAntiVehicleVehicleTech3) crusher 30. Generals rule: crushed when crusher > crushable.
    A structure (AlliedPowerPlant) has DestroyDie and a CreateObjectDie whose OCL makes AlliedPowerPlant_Collapse
    (NO_COLLIDE UNATTACKABLE DEBRIS; LifetimeUpdate 10-30 s, then SlowDeath 10 s).

    On the festival map, west field, three lanes along +x, 300 apart; every unit on HOLD_FIRE (no shots: a death is a
    crush). In each lane the player's tank 200 west of an enemy unit, ordered at 'Test Go' (one second in) to a point 200
    east of it (straight through):
      lane 1  Hammer -> enemy conscript (10)          lane 2  Hammer -> enemy guardian (20)
      lane 3  Apocalypse -> enemy guardian (20)
    and an enemy power plant 600 north, NAMED_KILL at 'Test Go'.

    Counters (four lines), every one counted from 'Test Go' on:
      帧数  frames since Go
      步兵  1 x frames the conscript is not destroyed + 1000 x frames it is dying + 1000000 x frames it is in its own spot
           (a square of half-side 30: did it step aside?)
      坦克  1 x frames lane 2's guardian is not destroyed + 1000 x frames lane 3's guardian is not destroyed
           + 1000000 x frames lane 2's Hammer is at its goal (half-side 40)
      建筑  1 x frames the plant is not destroyed + 1000 x frames it is dying + 1000000 x frames the enemy has a collapse
           object in the plant's square (half-side 150)

    Bench 11-06 (B round 5; one run each):
      all CampCrushAll_mcp_1106_042112 (s46): 步兵 170127043 -- crushed at frame 43, never left its spot, lay dead 127
        frames (8.5 s, its SlowDeath); 坦克 605069701 -- lane 2's guardian alive throughout (the Hammer went round, at
        its goal from 96), lane 3's crushed at 69; 建筑 1000 -- the plant dying the kill frame only, gone the next; the
        collapse object never counted as the enemy's.
      b CampCrushBTwo_mcp_1106_042416 (s21): 镰刀 216000329 -- the Sickle (30) never crushed by the Apocalypse (30):
        strictly greater it is; the Apocalypse went round, at its goal from 113; 到点 238238 -- the free lane and the lane
        through the killed plant both at the goal from frame 91 (the wreck does not block); 电厂 1000 as above.
    docs/engine/crush.md.
    """
    from maps import festival
    from parts import Mission, Script, Test, square

    HAMMER, APOC = 'SovietAntiVehicleVehicleTech1', 'SovietAntiVehicleVehicleTech3'
    CONSCRIPT, GUARDIAN = 'SovietAntiInfantryInfantry', 'AlliedAntiVehicleVehicleTech1'
    PLANT, COLLAPSE = 'AlliedPowerPlant', 'AlliedPowerPlant_Collapse'
    LANES = {1: (HAMMER, CONSCRIPT, -300.0), 2: (HAMMER, GUARDIAN, 0.0), 3: (APOC, GUARDIAN, 300.0)}
    PLANT_DY = 600.0
    RUN = 45.0
    HOLD_FIRE = 3


    def _n(part):
        return f'UNIT - CNV Crush {part}'


    def mission():
        m = Mission(name='CampCrush', map=festival, units=[], facts={})
        m.spawns |= {COLLAPSE}
        for k, (tank, target, dy) in LANES.items():
            m.put(tank, 'west field', -200.0, dy, angle=0.0, role=f'tank {k}', name=_n(f'Tank {k}'))
            m.put(target, 'west field', 0.0, dy, angle=180.0, side='s1', role=f'target {k}', name=_n(f'Target {k}'))
        m.put(PLANT, 'west field', 0.0, PLANT_DY, side='s1', role='plant', name=_n('Plant'))
        return m


    def crush_test(m):
        t = Test()
        p1, s1 = m.player('p1'), m.player('s1')
        x, y = m.site('west field')[:2]
        for k, (_, _, dy) in LANES.items():
            t.waypoints[f'Test Goal {k}'] = (x + 200.0, y + dy)
        t.areas['Test Spot 1'] = square(x, y + LANES[1][2], 30.0)
        t.areas['Test Goal 2'] = square(x + 200.0, y + LANES[2][2], 40.0)
        t.areas['Test Plant'] = square(x, y + PLANT_DY, 150.0)
        names = [_n(f'Tank {k}') for k in LANES] + [_n(f'Target {k}') for k in LANES]
        start = [('MAP_REVEAL_ALL_PERM', p1), ('SET_MILLISECOND_TIMER', 'Test Go', 1.0)]
        start += [('UNIT_SET_STANCE', n, HOLD_FIRE) for n in names]
        t.scripts.append(Script('Test - start', [], start))
        go = [('MOVE_NAMED_UNIT_TO', _n(f'Tank {k}'), f'Test Goal {k}') for k in LANES] + [('NAMED_KILL', _n('Plant'))]
        t.scripts.append(Script('Test - go', [('TIMER_EXPIRED', 'Test Go')], go + [('SET_FLAG', 'Test Going', 1)]))
        going = ('FLAG', 'Test Going', 1)

        t.counters.append(('CNV_Crush_Frames', '帧数'))
        t.scripts.append(Script('Test - frames', [going], [('INCREMENT_COUNTER', 1, 'CNV_Crush_Frames')], once=False))
        man, g2, g3, plant = _n('Target 1'), _n('Target 2'), _n('Target 3'), _n('Plant')
        rows = {
            2: ('步兵', [(('NAMED_NOT_DESTROYED', man), 1), (('NAMED_DYING', man), 1000),
                        (('NAMED_INSIDE_AREA', man, 'Test Spot 1'), 1000000)]),
            3: ('坦克', [(('NAMED_NOT_DESTROYED', g2), 1), (('NAMED_NOT_DESTROYED', g3), 1000),
                        (('NAMED_INSIDE_AREA', _n('Tank 2'), 'Test Goal 2'), 1000000)]),
            4: ('建筑', [(('NAMED_NOT_DESTROYED', plant), 1), (('NAMED_DYING', plant), 1000),
                        (('PLAYER_HAS_COMPARISON_UNIT_TYPE_IN_TRIGGER_AREA', s1, 3, 1, COLLAPSE, 'Test Plant'), 1000000)]),
        }
        for k, (label, conds) in rows.items():
            t.counters.append((f'CNV_Crush_Row{k}', label))
            for j, (cond, step) in enumerate(conds):
                t.scripts.append(Script(f'Test - row {k} {j}', [going, cond],
                                        [('INCREMENT_COUNTER', step, f'CNV_Crush_Row{k}')], once=False))
        t.expect = [('帧数', 0, 'ever>=', 1, RUN)]
        t.bench = [('bench_watch', dict(every=1.0, sheet=False, lines=len(t.counters), seconds=RUN))]
        return t


    SICKLE = 'SovietScoutVehicle'                     # crushable 30, against the Apocalypse's crusher 30
    LANES_B = {1: (APOC, SICKLE, -300.0), 2: (HAMMER, None, 0.0), 3: (HAMMER, PLANT, 300.0)}


    def mission_b():
        m = Mission(name='CampCrushB', map=festival, units=[], facts={})
        for k, (tank, target, dy) in LANES_B.items():
            m.put(tank, 'west field', -200.0, dy, angle=0.0, role=f'tank {k}', name=_n(f'Tank {k}'))
            if target:
                m.put(target, 'west field', 0.0, dy, angle=180.0, side='s1', role=f'target {k}', name=_n(f'Target {k}'))
        return m


    def crush_b(m):
        """Lane 1 Apocalypse -> enemy Sickle (30 against 30: is an equal level crushed?); lane 2 a Hammer on an empty
        lane (the free drive, 400); lane 3 a Hammer through an enemy power plant killed at Go (does the wreck block?)."""
        t = Test()
        p1 = m.player('p1')
        x, y = m.site('west field')[:2]
        for k, (_, _, dy) in LANES_B.items():
            t.waypoints[f'Test Goal {k}'] = (x + 200.0, y + dy)
            t.areas[f'Test Goal {k}'] = square(x + 200.0, y + dy, 40.0)
        names = [_n(f'Tank {k}') for k in LANES_B] + [_n('Target 1')]
        start = [('MAP_REVEAL_ALL_PERM', p1), ('SET_MILLISECOND_TIMER', 'Test Go', 1.0)]
        start += [('UNIT_SET_STANCE', n, HOLD_FIRE) for n in names]
        t.scripts.append(Script('Test - start', [], start))
        go = [('MOVE_NAMED_UNIT_TO', _n(f'Tank {k}'), f'Test Goal {k}') for k in LANES_B] + [('NAMED_KILL', _n('Target 3'))]
        t.scripts.append(Script('Test - go', [('TIMER_EXPIRED', 'Test Go')], go + [('SET_FLAG', 'Test Going', 1)]))
        going = ('FLAG', 'Test Going', 1)
        t.counters.append(('CNV_Crush_Frames', '帧数'))
        t.scripts.append(Script('Test - frames', [going], [('INCREMENT_COUNTER', 1, 'CNV_Crush_Frames')], once=False))
        sickle, plant = _n('Target 1'), _n('Target 3')
        at = lambda k: ('NAMED_INSIDE_AREA', _n(f'Tank {k}'), f'Test Goal {k}')  # noqa: E731
        rows = {
            2: ('镰刀', [(('NAMED_NOT_DESTROYED', sickle), 1), (('NAMED_DYING', sickle), 1000), (at(1), 1000000)]),
            3: ('到点', [(at(2), 1), (at(3), 1000)]),
            4: ('电厂', [(('NAMED_NOT_DESTROYED', plant), 1), (('NAMED_DYING', plant), 1000)]),
        }
        for k, (label, conds) in rows.items():
            t.counters.append((f'CNV_Crush_Row{k}', label))
            for j, (cond, step) in enumerate(conds):
                t.scripts.append(Script(f'Test - row {k} {j}', [going, cond],
                                        [('INCREMENT_COUNTER', step, f'CNV_Crush_Row{k}')], once=False))
        t.expect = [('帧数', 0, 'ever>=', 1, 20.0)]
        t.bench = [('bench_watch', dict(every=1.0, sheet=False, lines=len(t.counters), seconds=20.0))]
        return t


    MISSION = {'engine_crush': mission, 'engine_crush_b': mission_b}
    CHECKS = {'engine_crush': {'all': crush_test}, 'engine_crush_b': {'two': crush_b}}
    return dict(MISSION=MISSION, CHECKS=CHECKS)


def engine_drain():
    """LoseHealthUpdate on its retail host: three Dreadnoughts (SovietAntiStructureShip, 1500 HP; ModuleTag_RapidLaunchHealthDrain
    HealthTrigger 101 %, DamagePerSecond 50, RequiredStatus GENERIC_TOGGLE_STATE, ForbiddenStatus UNDER_IRON_CURTAIN), the
    player's, in the sea west of the island, holding fire. Its ToggleState names the drain (`<Module ModuleId=...>`), as the
    Kirov's names its own (engine_acts11 KV: drained 200 a second while on).
      P  Command_ToggleRapidLaunchSpecialPower pressed at 3 s and again at 15 s.   [100 -> 60 at 15 s, held]
      C  pressed at 3 s, UNDER_IRON_CURTAIN given by script at 8 s.                [100 -> 83 at 8 s, held]
      S  GENERIC_TOGGLE_STATE given by script at 3 s, no press (E146's script bit, on the retail host this time). [100]
    Counters: 血P, 血C, 血S (health %); 态 = P GENERIC + 10 C GENERIC + 100 S GENERIC + 1000 C UNDER_IRON_CURTAIN
    [0 -> 111 (3 s) -> 1111 (8 s) -> 1110 (15 s)].
    """
    from maps import island
    from parts import Mission, Script, Test, status
    from checks import engine_scripts8 as s8

    SHIPS = {'P': 2200.0, 'C': 2500.0, 'S': 2800.0}
    PRESS = 'Command_ToggleRapidLaunchSpecialPower'


    def _n(row):
        return 'CNV Drain ' + row


    def mission():
        m = Mission(name='CampDrain', map=island, units=[], facts={})
        for row, y in SHIPS.items():
            m.put('SovietAntiStructureShip', 'start', 400.0 - 1250.0, y - 2500.0, angle=0.0, name=_n(row), role=row)
        return m


    def check(m):
        t = Test()
        s8.at(t, 'hold', 0.1, [('UNIT_CHANGE_OBJECT_STATUS', _n(r), status('NO_ATTACK'), 1) for r in SHIPS] +
              [('MAP_REVEAL_ALL_PERM', m.player('p1'))])
        s8.at(t, 'press', 3.0, [('NAMED_USE_COMMANDBUTTON_ABILITY', _n(r), PRESS) for r in 'PC'] +
              [('UNIT_CHANGE_OBJECT_STATUS', _n('S'), status('GENERIC_TOGGLE_STATE'), 1)])
        s8.at(t, 'curtain', 8.0, [('UNIT_CHANGE_OBJECT_STATUS', _n('C'), status('UNDER_IRON_CURTAIN'), 1)])
        s8.at(t, 'back', 15.0, [('NAMED_USE_COMMANDBUTTON_ABILITY', _n('P'), PRESS)])
        bit = lambda row, b: ('UNIT_HAS_OBJECT_STATUS', _n(row), status(b))  # noqa: E731
        for row in SHIPS:
            t.counters.append(('CNV_Drain_' + row, '血' + row))
            t.scripts.append(Script('Test - Drain hp ' + row, [],
                                    [('SET_UNIT_HEALTH_PERCENTAGE_TO_COUNTER', _n(row), 'CNV_Drain_' + row)], once=False))
        s8.total(t, 'CNV_Drain_State', '态', [(1, bit('P', 'GENERIC_TOGGLE_STATE')), (10, bit('C', 'GENERIC_TOGGLE_STATE')),
                                              (100, bit('S', 'GENERIC_TOGGLE_STATE')),
                                              (1000, bit('C', 'UNDER_IRON_CURTAIN'))])
        s8.watch(t, 22.0)
        return t


    MISSION = {'engine_drain': mission}
    CHECKS = {'engine_drain': {'a': check}}
    return dict(MISSION=MISSION, CHECKS=CHECKS)


def engine_immortal():
    """Engine probe: damage floor and explicit removal of a retail dummy body.

    BENCHED 2026-11-09 (engine line C round 14; the readings are at the end of this docstring). The prediction below held on
    everything but one thing: after the delete the health counter stays 1, it is not written 0 (a dead object's counter freezes).
    Retail CPDummyTarget is placeable (EditorName / EditorSorting SYSTEM), immobile,
    selectable with a health bar, NoArmor and MaxHealth=100. Unlike BaseRock it is
    not UNATTACKABLE; its invisible in-game model does not affect named script reads.
    Source data: work/downloads/ra3sdk_v3/sdk3/XMLFiles/Civilian/Props/CPDummyTarget.xml.

    Two lanes (check variants, the same object and damage in each):
      a: Test Go at 1 s applies NAMED_DAMAGE 200 (= twice retail MaxHealth).
         Read health through a counter throughout the next 10 s; bench_watch every 0.5 s.
      b: as a, then NAMED_KILL at Go+10 s, NAMED_DELETE at Go+11 s.
         The gone counter becomes 1 when NAMED_DESTROYED observes the deletion.

    PREDICTED readings (health / gone): before Go 100 / 0; after the hit 1 / 0
    at every half-second observation for 10 s. In b, KILL leaves 1 / 0; after
    DELETE the gone counter is 1 and health is 0: the reader runs later in that
    same frame and writes 0 for a dead object; subsequent reads retain that 0.
    Only the gone counter establishes removal. Run a for 12 s, b for 14 s.

    Rule, not a fit: the Generals reference body's internalChangeHealth clamps
    changes to leave at least 1 HP, so 100 - 200 becomes 1 HP = 1 percent.
    ScriptActions::doNamedKill calls Object::kill (MaxHealth unresistable damage),
    which is clamped too. doNamedDelete calls GameLogic::destroyObject directly;
    it bypasses health changes. RA3 behavior remains a prediction pending line C.

    Bench 2026-11-09 (the ImmortalBody module of CPDummyTarget; lanes a, b, c = the kill alone, no delete, 14 s):
      a: health 1 (percent), gone 0, from the hit at 1 s to the end (s1-s13) -- the 200 hit leaves 1 %, the dummy lives on.
      c: the same 1 / 0 through s15 after the NAMED_KILL at 11 s -- a script kill does not remove it either (floor of 1).
      b: 1 / 0 to s10, then 1 / 1 from s11 (the bench clock labels run about a second behind the mission's): the delete
         removes it; the health counter keeps 1 beside gone 1 (it froze), the predicted 0 was wrong.
    """
    import resources
    from maps import niagara
    from parts import Mission, Script, Test

    TEMPLATE = 'CPDummyTarget'
    UNIT = 'UNIT - CNV Immortal Dummy'
    MAX_HEALTH = 100                 # retail CPDummyTarget.xml, not a probe override
    GO, OBSERVE = 1.0, 10.0


    def mission():
        m = Mission(name='CampImmortal', map=resources.measured(niagara), units=[], facts={})
        m.put(TEMPLATE, 'west field', -120.0, 260.0, side='p1', role='dummy', name=UNIT)
        return m


    def build_test(m, which='a'):
        t = Test()
        t.counters = [('CNV_Immortal_Health', '血量'), ('CNV_Immortal_Gone', '消失')]
        t.scripts.append(Script('Test - start', [], [
            ('MAP_REVEAL_ALL_PERM', m.player('p1')),
            ('SET_MILLISECOND_TIMER', 'Test Go', GO)]))
        t.scripts.append(Script('Test - go', [('TIMER_EXPIRED', 'Test Go')], [
            ('NAMED_DAMAGE', UNIT, 2 * MAX_HEALTH),
            ('SET_MILLISECOND_TIMER', 'Test Kill', OBSERVE)]))
        if which in 'bc':                   # c: the kill alone, no delete (bench 11-09 b: gone at s11.1, before the delete)
            t.scripts.append(Script('Test - kill', [('TIMER_EXPIRED', 'Test Kill')], [
                ('NAMED_KILL', UNIT)] + ([('SET_MILLISECOND_TIMER', 'Test Delete', 1.0)] if which == 'b' else [])))
        if which == 'b':
            t.scripts.append(Script('Test - delete', [('TIMER_EXPIRED', 'Test Delete')], [('NAMED_DELETE', UNIT)]))
        t.scripts += [
            Script('Test - health', [], [('SET_UNIT_HEALTH_PERCENTAGE_TO_COUNTER', UNIT,
                                         'CNV_Immortal_Health')], once=False),
            Script('Test - gone', [('NAMED_DESTROYED', UNIT)], [('SET_COUNTER', 'CNV_Immortal_Gone', 1)])]
        run = 12.0 if which == 'a' else 14.0
        t.expect = [('血量', 0, 'ever<=', 1, run)]
        if which == 'b':
            t.expect.append(('消失', 0, 'ever>=', 1, run))
        t.bench = [('bench_watch', dict(every=0.5, sheet=False, lines=len(t.counters), seconds=run))]
        return t


    MISSION = {'engine_immortal': mission}
    CHECKS = {'engine_immortal': {w: (lambda m, w=w: build_test(m, w)) for w in 'abc'}}
    return dict(MISSION=MISSION, CHECKS=CHECKS)


def engine_invuln():
    """Engine unit test: does an upgrade's INVULNERABLE 100% attribute modifier keep a building from losing health, and does
    taking the upgrade away make it hurt-able again (docs/engine/upgrades.md 4; what A9's tower ball, units/tower_ball.py,
    relies on: dark = INVULNERABLE through an AttributeModifierUpgrade, lit = none).

    The probe's own target (ADR 0016 G5: built here, not from units/): retail's Soviet bunker under CNV_InvulnBox, its
    garrison, aura, stealth and build dependency dropped, MaxHealth HEALTH, with two OBJECT upgrades like the ball's: Dark =
    INVULNERABLE 100% (no Duration), Lit = no modifier. On the range probe map (maps/probe_range.py) each lane's gun is the
    player's and its one target stands neutral until SHOW, when it is handed to the enemy, so every gun meets its target
    already in the lane's state. Guns: retail's sentry gun (benches/weapon/firing engine_range gun: GUN damage, 100 % on structures); the
    two lanes whose target stands 450 out get their gun's High (RANGE x2 and VISION x2) at s0.

      base     250  no upgrade                                         (control: hurt)
      low      250  Dark at s0, kept                                   (hurt?)
      removed  250  Dark at s0, removed at SWAP                        (hurt?)
      order    450  Dark at s0, removed at SWAP, granted again at BACK (hurt?)
      switch   250  Dark at s0, removed at LATE (12 s after SHOW)      (hurt only from LATE?)
      high     450  the rhythm device's steps while being shot: Dark at s0; LATE: Dark off, Lit on; REDARK: Lit off, Dark on
                    (does the health stop falling again at REDARK?)

    Counters (the bench reads the first three lines):
      invuln A: base hurt = 1, low hurt = 10, removed hurt = 100, order hurt = 1000
      invuln B: switch hurt = 1, high hurt = 10
      invuln C: high below 90 / 75 / 60 / 45 / 30 % = 1 / 10 / 100 / 1000 / 10000 (when each appears: from the watch)

    The kinds round (engine_invuln_kinds, KINDS): the same steps (removed / order keep their Dark), each lane's box another
    way of being dark: base no upgrade but retail's A09 Iron Curtain aura object beside it; low / switch / high Dark =
    INVULNERABLE + ObjectStatusToSet "NO_BRIBE UNDER_IRON_CURTAIN" (retail Iron Curtain's bits); removed Dark = ARMOR 1%;
    order Dark = retail's AttributeModifier_IronCurtain itself (Duration 20 s).

    Read (测, 2026-11-04, docs/engine/upgrades.md 4):
      engine_invuln / engine_invuln_enemy (plain INVULNERABLE, targets neutral then enemy / enemy throughout): every
        lane hurt from s7, the kept-dark ones too; high's health falls at one pace through dark, lit, dark again
        (<90 s15, <75 s23, <60 s33, <45 s43). The modifier alone does nothing.
      engine_invuln_kinds: A 100 from s7, 1100 from s19; B 11 from s19; C 1 from s25, then nothing to s49 -- the aura box
        and the kept status box never hurt; the armor box hurt at once (1 % still scratches); the retail-modifier box
        whole for 20 s, then hurt (its Duration runs out under the upgrade too); the status box hurt once its Dark is
        removed (switch), and high hurt while lit (s20-s28) then holds again once dark.
    """
    import os
    import re

    import labpaths
    from benches.weapon.firing.checks import engine_range
    range_bench = engine_range()["shared"]
    from maps import probe_range
    from parts import Mission, Script, Test, Unit

    RETAIL = 'SovietBunker'
    BOX = 'CNV_InvulnBox'
    GUN = 'CNV_InvulnGun'
    HEALTH = 4000
    SWAP, BACK, SHOW = 3.0, 5.0, 8.0
    LATE, REDARK, RUN = SHOW + 12.0, SHOW + 20.0, SHOW + 40.0
    LANES = {'base': 250, 'low': 250, 'removed': 250, 'order': 450, 'switch': 250, 'high': 450}
    FAR = ('order', 'high')
    STEPS = (90, 75, 60, 45, 30)


    def _sub1(x, old, new):
        assert x.count(old) == 1, (old[:60], x.count(old))
        return x.replace(old, new, 1)


    RETAIL_IC = 'AttributeModifier_IronCurtain'     # GlobalData/AttributeModifier.xml: INVULNERABLE + UNDER_IRON_CURTAIN, 20 s
    DARK = {    # what the Dark upgrade does, per kind of box
        'plain': '<Modifier Type="INVULNERABLE" Value="100%"/>',                     # the ball's own (units/tower_ball.py)
        'status': '<Modifier Type="INVULNERABLE" Value="100%"/>',                    # + retail Iron Curtain's status bits
        'armor': '<Modifier Type="ARMOR" Value="1%"/>',                              # does the upgrade take at all?
        'retail': None,                                                               # retail's Iron Curtain modifier itself
    }


    def box(id=BOX, health=HEALTH, kind='plain'):
        """retail's bunker as a plain building with the ball's two upgrades (names on = Lit, off = Dark); kind: what
        Dark does (DARK)."""
        x = open(os.path.join(labpaths.SDK3, 'SageXML', 'Soviet', 'Structures', f'{RETAIL}.xml'), encoding='utf-8').read()
        x = _sub1(x, f'id="{RETAIL}"', f'id="{id}"')
        x = _sub1(x, f'EditorName="{RETAIL}"', f'EditorName="{id}"')
        x = _sub1(x, 'KindOf="+GARRISON +FS_FACTORY +AUTO_RALLYPOINT +IGNORE_FOR_VICTORY', 'KindOf="+IGNORE_FOR_VICTORY')
        x = _sub1(x, ' +GARRISONABLE_UNTIL_DESTROYED"', '"')
        x = re.sub(r'\s*<GameDependency>.*?</GameDependency>', '', x, count=1, flags=re.S)
        for module, tag in (('GarrisonContain', 'ModuleTag_Garrison'),
                            ('AttributeModifierAuraUpdate', 'ModuleTag_AttributeModifierAura')):
            x, n = re.subn(rf'\s*<{module}\s+id="{tag}".*?</{module}>', '', x, count=1, flags=re.S)
            assert n == 1, module
        x, n = re.subn(r'\s*<InvisibilityBehavior\s+id="ModuleTag_Invisibility"[^>]*/>', '', x, count=1)
        assert n == 1, 'InvisibilityBehavior'
        x = _sub1(x, 'MaxHealth="1500"', f'MaxHealth="{health}"')
        up_on, up_off = f'Upgrade_{id}_Lit', f'Upgrade_{id}_Dark'
        mod_off = RETAIL_IC if kind == 'retail' else f'AttributeModifier_{id}_Dark'
        x = _sub1(x, '<Behaviors>', (
            f'<Behaviors>\n'
            f'\t\t\t<AttributeModifierUpgrade id="ModuleTag_CNV_InvulnDark" AttributeModifier="{mod_off}">\n'
            f'\t\t\t\t<TriggeredBy>{up_off}</TriggeredBy>\n'
            f'\t\t\t</AttributeModifierUpgrade>'
        ))
        status = ' ObjectStatusToSet="NO_BRIBE UNDER_IRON_CURTAIN"' if kind == 'status' else ''
        own = '' if kind == 'retail' else (
            f'\n'
            f'\t<AttributeModifier id="{mod_off}" Category="NONE"{status}>\n'
            f'\t\t{DARK[kind]}\n'
            f'\t</AttributeModifier>'
        )
        x = _sub1(x, '</AssetDeclaration>', (
            f'\t<UpgradeTemplate id="{up_on}" Type="OBJECT"/>\n'
            f'\t<UpgradeTemplate id="{up_off}" Type="OBJECT"/>{own}\n'
            f'</AssetDeclaration>'
        ))
        link = [f'UpgradeTemplate:{up_on}', f'UpgradeTemplate:{up_off}'] + ([] if kind == 'retail' else
                                                                           [f'AttributeModifier:{mod_off}'])
        return Unit(id, x, link=link, names={'on': up_on, 'off': up_off},
                    what=f'引擎探针：原版地堡当靶子，暗 = {kind} 修正升级，亮 = 无修正', params=dict(health=health, kind=kind))


    def _key(lane):
        return lane.title()


    AURA = 'A09_IronCurtainEffect'      # retail campaign A09's lasting Iron Curtain: an aura object (Range 750, 0.75 s)
    KINDS = {'base': 'plain', 'low': 'status', 'removed': 'armor', 'order': 'retail', 'switch': 'status', 'high': 'status'}


    def mission(owner='neutral', kinds=None):
        """owner: who holds the targets from s0 -- 'neutral' (handed to the enemy at SHOW) or 's1' (the enemy throughout:
        the gun does not pick a building itself, so it waits for its order at SHOW either way). kinds: {lane: box kind}
        (KINDS: the second round, all lanes' Dark kept from s0 but switch / high, as in invuln; base gets no upgrade but
        retail's Iron Curtain aura object on its target); None: every lane the ball's own plain box."""
        name = 'CampInvK' if kinds else 'CampInv' if owner == 'neutral' else 'CampInvE'
        lanes = kinds or {lane: 'plain' for lane in LANES}
        units = [box(f'{BOX}_{k.title()}', kind=k) for k in dict.fromkeys(lanes.values())]
        m = Mission(name=name, map=probe_range, units=units + [range_bench.gun(GUN, vision=2.0)], facts={})
        for lane, d in LANES.items():
            m.put(GUN, f'{lane} gun', role=f'{lane} gun', name=f'UNIT - CNV Invuln {_key(lane)} Gun')
            m.put(f'{BOX}_{lanes[lane].title()}', f'{lane} at {d:g}', side=owner, role=f'{lane} target',
                  name=f'UNIT - CNV Invuln {_key(lane)} Target')
        if kinds:
            m.put(AURA, f'base at {LANES["base"]:g}', side=owner, dy=-60.0)
        for k in range(3):
            m.put('SovietPowerPlant', f'power {k + 1}', role=f'power {k + 1}', name=f'UNIT - CNV Invuln Power {k + 1}')
        return m


    def invuln(m):
        t = Test()
        high = next(u for u in m.units if u.id == GUN).names['on']
        kept = m.name == 'CampInvK'         # the kinds round: removed / order keep their Dark (does it take at all?)

        def tg(lane):
            return m.role(f'{lane} target').name

        def up(lane, which):
            return next(u for u in m.units if u.id == m.role(f'{lane} target').template).names[which]

        timers = (('Swap', SWAP), ('Back', BACK), ('Show', SHOW), ('Late', LATE), ('Redark', REDARK))
        start = [('MAP_REVEAL_ALL_PERM', m.player('p1'))]
        start += [('SET_MILLISECOND_TIMER', f'Test {k}', s) for k, s in timers]
        start += [('NAMED_RECEIVE_UPGRADE', high, m.role(f'{lane} gun').name) for lane in FAR]
        start += [('NAMED_RECEIVE_UPGRADE', up(lane, 'off'), tg(lane)) for lane in LANES if lane != 'base']
        swap = [] if kept else [('NAMED_REMOVE_UPGRADE', up(lane, 'off'), tg(lane)) for lane in ('removed', 'order')]
        back = [] if kept else [('NAMED_RECEIVE_UPGRADE', up('order', 'off'), tg('order'))]
        s1 = m.player('s1')
        # the sentry gun does not pick a building itself (bench 2026-11-04: nothing hurt, the control neither): every gun is
        # told to attack its target at SHOW and again after each switch (a gun might give up on a target it cannot hurt)
        attack = [('NAMED_ATTACK_NAMED', m.role(f'{lane} gun').name, tg(lane)) for lane in LANES]
        neutral = m.name == 'CampInv'
        show = [('NAMED_TRANSFER_OWNERSHIP_PLAYER', tg(lane), s1) for lane in LANES if neutral] + attack
        late = [('NAMED_REMOVE_UPGRADE', up('switch', 'off'), tg('switch')),
                ('NAMED_REMOVE_UPGRADE', up('high', 'off'), tg('high')),
                ('NAMED_RECEIVE_UPGRADE', up('high', 'on'), tg('high'))] + attack
        redark = [('NAMED_REMOVE_UPGRADE', up('high', 'on'), tg('high')),
                  ('NAMED_RECEIVE_UPGRADE', up('high', 'off'), tg('high'))] + attack
        t.scripts += [Script('Test - start', [], start)]
        t.scripts += [Script(f'Test - {k.lower()}', [('TIMER_EXPIRED', f'Test {k}')], acts)
                      for k, acts in (('Swap', swap), ('Back', back), ('Show', show), ('Late', late), ('Redark', redark))]
        rows = (('CNV_Invuln_A', '无敌甲', [(lane, 100) for lane in ('base', 'low', 'removed', 'order')]),
                ('CNV_Invuln_B', '无敌乙', [(lane, 100) for lane in ('switch', 'high')]),
                ('CNV_Invuln_C', '无敌丙', [('high', p) for p in STEPS]))
        for counter, label, marks in rows:
            t.counters.append((counter, label))
            t.scripts.append(Script(f'Test - {counter} zero', [], [('SET_COUNTER', counter, 0)]))
            for k, (lane, pct) in enumerate(marks):
                name, key = tg(lane), f'{_key(lane)} {pct}'
                flag = f'Test Invuln {key}'
                t.scripts += [Script(f'Test - hurt {key}', [('UNIT_HEALTH', name, 0, pct)], [('SET_FLAG', flag, 1)]),
                              Script(f'Test - dead {key}', [('NAMED_DESTROYED', name)], [('SET_FLAG', flag, 1)]),
                              Script(f'Test - hit {key}', [('FLAG', flag, 1)], [('INCREMENT_COUNTER', 10 ** k, counter)])]
        # only the control is judged (the rest is what the test is for): the plain box gets hurt; in the kinds round (base
        # under the aura) the switch box, its Dark gone at LATE, does
        t.expect = [('无敌乙', 0, 'ever>', 0, RUN)] if kept else [('无敌甲', 0, 'ever>', 0, RUN)]
        t.bench = [('bench_watch', dict(seconds=RUN, every=2, sheet=False, lines=3))]
        return t


    # the builds this module makes and their checks (cnv/registry.py)
    MISSION = {'engine_invuln': mission, 'engine_invuln_enemy': lambda: mission(owner='s1'),
               'engine_invuln_kinds': lambda: mission(owner='s1', kinds=KINDS)}
    CHECKS = {'engine_invuln': {'invuln': invuln}, 'engine_invuln_enemy': {'invuln': invuln},
              'engine_invuln_kinds': {'invuln': invuln}}
    return dict(MISSION=MISSION, CHECKS=CHECKS)


def engine_kill():
    """Engine unit test: the kill chain (ADR 0019 layer 3; docs/engine/weapons.md; engine line C round 6) -- what a shooter
    does between a kill and its next shot. engine_clip read the weapon's own rhythm (the coil: a shot every 48 frames, so
    a 480-health tank dies to two shots in 96 frames); the powerdef bench shows one tank per ~125 frames, ~29 frames more
    per KILL. This probe measures them: one shooter (engine_clip's V4 copy, instant, damage KILL = more than any target's
    health) and four 10 000-health Hammers in a row, NO_ATTACK so they only stand; each shot kills one.

    Variants (ca coil+auto, co coil+ordered, ba bare+auto, bo bare+ordered, c3 clip3+auto, pa pre-only+auto; id suffix: timers (pre-attack s, firing s, reload s, clip, ReAcquireDetailType), how the next target comes):
      auto   the order names target 1 only; targets 2-4 are taken by the shooter itself (auto-acquire)
      order  every target is ordered by script the frame the one before is destroyed
      clip3  the 3-shot clip (no pre-attack, firing 0.3, reload 2.0), auto: does the clip go on across a kill?
      bare   no pre-attack, firing 0, reload 0.1, auto: the shortest cycle, the kill gap with nothing to hide behind
    (each in a 'coil' (pre 2.5, firing 0.5, reload 0.1) and a 'bare' timer set where it makes sense; see VARIANTS).

    Counters (one line a target): the frames in which that target is still alive and the one before is gone (target 1:
    from the order). A kill shows as the counter standing still; the spans are the shooter's frames to the kill, and
    span(k) - first-shot-frames is the kill chain's extra. The reading is the frame count the script saw, one more than the
    frame the damage landed (docs/engine/weapons.md 1).

    Bench 11-09 (round 6; work/bench_results/engine_kill__<variant>.json; pa not run). Counter per target = frames between
    the kill before and this one (target 1: from the order); one kill = one shot:
      co (coil, ordered each kill)  40 / 48 / 48 / 48   -> the weapon's own cycle, NO extra between kills
      ca (coil, auto-acquire)       40 / 96 (then 4th 96; 3rd read 0 = it died out of order) -> auto adds one more
                                    full cycle (+48) before the next shot
      bo (bare, ordered)            2 / 2 / 2 / 2
      ba (bare, auto)               2 / 5 / - / 4      -> auto adds +3 (about the gap + 1)
      c3 (clip3 0 / 0.3 / 2.0, auto)  2 / 10 / - / 8   (gap inside the clip is 5; ordered not run)
    So the ~29 frames a kill the powerdef coil loses are the AUTO-acquire's: a shooter that picks its next target itself
    waits (coil: +48 after a one-shot kill; in powerdef the kill is the 2nd shot and the loss is ~29, so it is not simply
    one cycle -- not fitted). An ORDERED next target costs nothing. Next: ordered vs auto with a 2-shot kill (the
    powerdef case), 3 / 4 shot kills, and the 3rd-target order (which of the idle targets the shooter takes).
    """
    from maps import probe_range
    from parts import Mission, Script, Test
    from benches.weapon.firing.checks import engine_clip
    clip_v4 = engine_clip()["shared"].clip_v4
    from benches.weapon.firing.checks import engine_missile
    missile = engine_missile()["shared"]
    FAR = missile.FAR
    TARGET_ID = missile.TARGET_ID
    target = missile.target

    ORDER = 6.0
    KILL = 50000.0                          # more than the target's 10 000 whatever its armour
    N = 4
    SPOTS = [(0, FAR), (90, FAR), (-90, FAR), (180, FAR)]

    # id suffix: (timers = (pre, firing, reload, clip, ReAcquireDetailType, spans, run, label), ordered by script?)
    VARIANTS = {
        'ca':    ((2.5, 0.5, 0.1, 1, 'PRE_FIRE', (), 0, '线圈时序'), False, 45, '线圈时序，自动索敌'),
        'co':   ((2.5, 0.5, 0.1, 1, 'PRE_FIRE', (), 0, '线圈时序'), True, 45, '线圈时序，脚本逐个下令'),
        'ba':    ((0.0, 0.0, 0.1, 1, 'PRE_FIRE', (), 0, '无前摇'), False, 25, '无前摇，自动索敌'),
        'bo':   ((0.0, 0.0, 0.1, 1, 'PRE_FIRE', (), 0, '无前摇'), True, 25, '无前摇，脚本逐个下令'),
        'c3':   ((0.0, 0.3, 2.0, 3, 'PRE_FIRE', (), 0, '三发夹'), False, 45, '三发夹，自动索敌'),
        'pa':     ((2.5, 0.0, 0.1, 1, 'PRE_FIRE', (), 0, '只有前摇'), False, 45, '只有前摇，自动索敌'),
    }


    def _uid(k):
        return 'CNV_Kill' + k.title()


    def _tid(i):
        return f'{TARGET_ID}K{i}'


    def mission():
        units = [clip_v4(k, hit=KILL, spec=v[0], uid=_uid(k)) for k, v in VARIANTS.items()]
        units += [target(id=_tid(i)) for i in range(N)]
        m = Mission(name='CampKill', map=probe_range, units=units, facts={})
        for k in VARIANTS:
            m.put(_uid(k), 'base gun', side='p1', role=f'kill {k}', name=f'UNIT - CNV Kill {k.title()}')
        for i, (dx, dy) in enumerate(SPOTS):
            m.put(_tid(i), 'base gun', dx, dy, side='s1', role=f'kill target {i}', name=f'UNIT - CNV Kill Target {i}')
        return m


    def kill_test(m, k):
        timers, by_script, run, label = VARIANTS[k]
        t = Test()
        shooter = m.role(f'kill {k}').name
        tg = [m.role(f'kill target {i}').name for i in range(N)]
        idle = [m.role(f'kill {i}').name for i in VARIANTS if i != k]
        start = [('MAP_REVEAL_ALL_PERM', m.player('p1'))]
        start += [('NAMED_DELETE', x) for x in idle]
        start += [('UNIT_CHANGE_OBJECT_STATUS', x, 'NO_ATTACK', 1) for x in [shooter] + tg]
        start += [('SET_MILLISECOND_TIMER', 'Test Order', ORDER)]
        t.scripts.append(Script('Test - start', [], start))
        t.scripts.append(Script('Test - order', [('TIMER_EXPIRED', 'Test Order')],
                                [('UNIT_CHANGE_OBJECT_STATUS', shooter, 'NO_ATTACK', 0),
                                 ('NAMED_ATTACK_NAMED', shooter, tg[0]), ('SET_FLAG', 'Test Ordered', 1)]))
        for i in range(N):
            c = f'CNV_Kill_T{i}'
            t.counters.append((c, f'靶{i + 1}'))
            cond = [('FLAG', 'Test Ordered', 1), ('NAMED_NOT_DESTROYED', tg[i])] + \
                   ([('NAMED_DESTROYED', tg[i - 1])] if i else [])
            t.scripts.append(Script(f'Test - {c}', cond, [('INCREMENT_COUNTER', 1, c)], once=False))
            if by_script and i:
                t.scripts.append(Script(f'Test - next {i}', [('NAMED_DESTROYED', tg[i - 1]), ('NAMED_NOT_DESTROYED', tg[i])],
                                        [('NAMED_ATTACK_NAMED', shooter, tg[i])], once=False))
        t.expect = [(f'靶{N}', 0, 'ever>=', 1, run - 1)]
        t.bench = [('bench_watch', dict(seconds=run, every=1, sheet=False, lines=len(t.counters)))]
        return t


    MISSION = {'engine_kill': mission}
    CHECKS = {'engine_kill': {k: (lambda m, k=k: kill_test(m, k)) for k in VARIANTS}}
    return dict(MISSION=MISSION, CHECKS=CHECKS)


def engine_levelup():
    """Creation-veterancy upgrades each add one level (retail BaseVehicle), capped at 4.

    PREDICT: one HEROIC creation grant does not itself make a heroic unit; three
    distinct creation upgrades do. Repeating an already-held upgrade adds no level.
    Read the mirage's heroic WEAPON_UPGRADED_01 bit, with no combat or experience.
    Bench 2026-11-10 PASS: s1-s4 0/0/1/0, s5-s13 0/1/1/0.
    These are heroic-state booleans, not numeric rank readings.
    """
    from maps import probe_range
    from parts import Mission, Script, Test, status, counted, square



    def mission():
        m = Mission(name='CampLevel', map=probe_range, units=[])
        for lane in ('base', 'high', 'order', 'removed'):
            m.put('AlliedAntiVehicleVehicleTech3', lane + ' gun', role=lane,
                  name='Level ' + lane)
        return m


    def check(m):
        t = Test()
        grant = lambda lane, up: ('NAMED_RECEIVE_UPGRADE', up, m.role(lane).name)
        t.scripts = [Script('Test - start', [], [
            ('MAP_REVEAL_ALL_PERM', m.player('p1')),
            ('SET_MILLISECOND_TIMER', 'Level late', 6.0),
            grant('high', CREATION[2]),
            *[grant('order', up) for up in CREATION],
            *[grant('removed', CREATION[0]) for _ in range(3)]]),
            Script('Test - late', [('TIMER_EXPIRED', 'Level late')], [
                grant('high', CREATION[0]), grant('high', CREATION[1])])]
        for lane in ('base', 'high', 'order', 'removed'):
            c = 'Level ' + lane
            t.counters.append((c, lane + ' rank'))
            t.scripts += [
                Script('Test - zero ' + lane, [], [('SET_COUNTER', c, 0)], once=False),
                Script('Test - heroic ' + lane,
                       [('UNIT_HAS_OBJECT_STATUS', m.role(lane).name, status('WEAPON_UPGRADED_01'))],
                       [('SET_COUNTER', c, 1)], once=False)]
        t.expect = [('base rank', 2, '==', 0, 12), ('high rank', 2, '==', 0, 4),
                    ('high rank', 8, '==', 1, 12), ('order rank', 2, '==', 1, 12),
                    ('removed rank', 2, '==', 0, 12)]
        t.bench = [('bench_watch', dict(seconds=12.0, every=.5, sheet=False, lines=4))]
        return t


    MISSION = {'engine_levelup': mission}
    CHECKS = {'engine_levelup': {'a': check}}


    def regrant_check(m):
        """PREDICT: removing creation grants keeps rank; regrant adds another level.

        Retail BaseVehicle's three modules each gain one level, cap four, and use
        UpgradeModuleData's Permanent=false default. This is a prediction from data,
        not from the simulator's existing first-activation-only approximation.
        Lanes: one veteran grant; veteran removed/regranted twice; veteran+elite
        then veteran removed/regranted; all three grants then all three removed.
        Heroic bits: 0/0/0/1 initially and after removal, 0/0/1/1 after the first
        regrant, 0/1/1/1 after the second. No enemies, attacks or combat XP.
        Stable windows allow dispatch; exact activation frames remain INFERRED.
        Bench 2026-11-11 PASS: 0/0/0/1 -> 0/0/1/1 -> 0/1/1/1.
        """
        t = Test()
        lanes = ('base', 'high', 'order', 'removed')
        action = lambda kind, lane, up: ('NAMED_' + kind + '_UPGRADE', up, m.role(lane).name)
        start = [('MAP_REVEAL_ALL_PERM', m.player('p1'))]
        for sec, timer in ((6, 'remove'), (12, 'regrant'), (18, 'remove again'), (24, 'regrant again')):
            start.append(('SET_MILLISECOND_TIMER', 'Level ' + timer, float(sec)))
        for lane, count in zip(lanes, (1, 1, 2, 3)):
            start.append(('UNIT_CHANGE_OBJECT_STATUS', m.role(lane).name, 'NO_ATTACK', 1))
            start += [action('RECEIVE', lane, up) for up in CREATION[:count]]
        steps = [
            ('remove', [action('REMOVE', lane, CREATION[0]) for lane in ('high', 'order')]
             + [action('REMOVE', 'removed', up) for up in CREATION]),
            ('regrant', [action('RECEIVE', lane, CREATION[0]) for lane in ('high', 'order')]),
            ('remove again', [action('REMOVE', 'high', CREATION[0])]),
            ('regrant again', [action('RECEIVE', 'high', CREATION[0])])]
        t.scripts = [Script('Test - start', [], start)] + [
            Script('Test - ' + timer, [('TIMER_EXPIRED', 'Level ' + timer)], actions)
            for timer, actions in steps]
        for lane in lanes:
            counter = 'Level regrant ' + lane
            t.counters.append((counter, lane + ' heroic'))
            t.scripts += [
                Script('Test - zero ' + lane, [], [('SET_COUNTER', counter, 0)], once=False),
                Script('Test - heroic ' + lane,
                       [('UNIT_HAS_OBJECT_STATUS', m.role(lane).name, status('WEAPON_UPGRADED_01'))],
                       [('SET_COUNTER', counter, 1)], once=False)]
        for first, last, values in ((2, 4, (0, 0, 0, 1)), (8, 10, (0, 0, 0, 1)),
                                    (14, 16, (0, 0, 1, 1)), (20, 22, (0, 0, 1, 1)),
                                    (26, 28, (0, 1, 1, 1))):
            t.expect += [(lane + ' heroic', first, '==', value, last)
                         for lane, value in zip(lanes, values)]
        t.bench = [('bench_watch', dict(seconds=28.0, every=.5, sheet=False, lines=4))]
        return t


    CHECKS['engine_levelup']['b'] = regrant_check


    def elite_heroic_regrant_check(m):
        """PREDICT: elite and heroic creation grants each rearm after removal.

        Retail BaseVehicle has gain=1, cap=4 for each of the three triggers;
        Permanent defaults to false. Each tested lane starts with only one grant,
        so neither the initial grant nor first regrant should set the heroic bit.
        The second regrant should. Keep the all-grants-removed control heroic.
        Stable windows only: exact dispatch frames remain INFERRED.
        Bench 2026-11-11 PASS: 0/0/0/1 through first regrant, then 0/1/1/1.
        """
        t = Test()
        lanes = ('base', 'high', 'order', 'removed')
        triggers = {'high': CREATION[1], 'order': CREATION[2]}
        action = lambda kind, lane, up: ('NAMED_' + kind + '_UPGRADE', up, m.role(lane).name)
        start = [('MAP_REVEAL_ALL_PERM', m.player('p1'))]
        for sec, timer in ((6, 'remove'), (12, 'regrant'), (18, 'remove again'), (24, 'regrant again')):
            start.append(('SET_MILLISECOND_TIMER', 'Level ' + timer, float(sec)))
        for lane in lanes:
            start.append(('UNIT_CHANGE_OBJECT_STATUS', m.role(lane).name, 'NO_ATTACK', 1))
            grants = CREATION if lane == 'removed' else (triggers.get(lane, CREATION[0]),)
            start += [action('RECEIVE', lane, up) for up in grants]
        steps = []
        for timer, kind in (('remove', 'REMOVE'), ('regrant', 'RECEIVE'),
                            ('remove again', 'REMOVE'), ('regrant again', 'RECEIVE')):
            actions = [action(kind, lane, up) for lane, up in triggers.items()]
            if timer == 'remove':
                actions += [action('REMOVE', 'removed', up) for up in CREATION]
            steps.append(Script('Test - ' + timer, [('TIMER_EXPIRED', 'Level ' + timer)], actions))
        t.scripts = [Script('Test - start', [], start)] + steps
        for lane in lanes:
            counter = 'Level regrant ' + lane
            t.counters.append((counter, lane + ' heroic'))
            t.scripts += [
                Script('Test - zero ' + lane, [], [('SET_COUNTER', counter, 0)], once=False),
                Script('Test - heroic ' + lane,
                       [('UNIT_HAS_OBJECT_STATUS', m.role(lane).name, status('WEAPON_UPGRADED_01'))],
                       [('SET_COUNTER', counter, 1)], once=False)]
        for first, last, values in ((2, 4, (0, 0, 0, 1)), (8, 10, (0, 0, 0, 1)),
                                    (14, 16, (0, 0, 0, 1)), (20, 22, (0, 0, 0, 1)),
                                    (26, 28, (0, 1, 1, 1))):
            t.expect += [(lane + ' heroic', first, '==', value, last)
                         for lane, value in zip(lanes, values)]
        t.bench = [('bench_watch', dict(seconds=28.0, every=.5, sheet=False, lines=4))]
        return t


    CHECKS['engine_levelup']['c'] = elite_heroic_regrant_check


    def damage_mission():
        m = mission()
        m.name = 'CampLevelD'
        for lane in ('base', 'high', 'order', 'removed'):
            m.put('JapanAntiVehicleVehicleTech1', lane + ' gun', 0, 100,
                  side='s1', role=lane + ' target', name='Level target ' + lane)
        return m


    def damage_check(m):
        """PREDICT: one shot, 200/250/250/312.5 damage into 380 HP, 100% armor.

        Creation grants add the veteran DAMAGE_MULT125 as well as the heroic gun.
        Direct veterancy upgrades (engine_statusbits a) only selected the gun.
        Bench 11-10 PASS: s5-s15 47/34/34/17, with no Tsunami healing.
        """
        t = Test()
        lanes = ('base', 'high', 'order', 'removed')
        start = [('MAP_REVEAL_ALL_PERM', m.player('p1')),
                 ('SET_MILLISECOND_TIMER', 'Level fire', 6.0),
                 ('SET_MILLISECOND_TIMER', 'Level stop', 6 + 4 / 15)]
        fire, stop = [], []
        for n, lane in enumerate(lanes):
            gun, target = m.role(lane).name, m.role(lane + ' target').name
            start += [('UNIT_CHANGE_OBJECT_STATUS', name, 'NO_ATTACK', 1) for name in (gun, target)]
            start += [('NAMED_RECEIVE_UPGRADE', up, gun) for up in CREATION[:n]]
            fire += [('UNIT_CHANGE_OBJECT_STATUS', gun, 'NO_ATTACK', 0), ('NAMED_ATTACK_NAMED', gun, target)]
            stop += [('UNIT_CHANGE_OBJECT_STATUS', gun, 'NO_ATTACK', 1)]
            counted('Level hp ' + lane, lane + ' HP', t, health=target)
        t.scripts[:0] = [Script('Test - start', [], start),
                         Script('Test - fire', [('TIMER_EXPIRED', 'Level fire')], fire),
                         Script('Test - stop', [('TIMER_EXPIRED', 'Level stop')], stop)]
        t.expect = [(lane + ' HP', 10, '==', hp, 14) for lane, hp in zip(lanes, (47, 34, 34, 17))]
        t.bench = [('bench_watch', dict(seconds=14.0, every=.5, sheet=False, lines=4))]
        return t


    MISSION['engine_leveldamage'] = damage_mission
    CHECKS['engine_leveldamage'] = {'a': damage_check}


    def health_mission():
        m = mission()
        m.name = 'CampLevelH'
        return m


    def health_check(m):
        """PREDICT: 500/500/625/625 max HP leaves 80/80/84/84% after NAMED_DAMAGE 100.

        Freeze each reading immediately after script damage in the same script, before
        heroic AutoHeal can tick. No enemy, weapon, armor or combat experience involved.
        This check measures promotion from full health; check b covers injured promotion.
        Bench 2026-11-10 PASS: frozen counters s4-s14 80/80/84/84.
        """
        t = Test()
        start = [('MAP_REVEAL_ALL_PERM', m.player('p1')),
                 ('SET_MILLISECOND_TIMER', 'Level hurt', 6.0)]
        hurt = []
        for n, lane in enumerate(('base', 'high', 'order', 'removed')):
            name, counter = m.role(lane).name, 'Level frozen ' + lane
            start += [('UNIT_CHANGE_OBJECT_STATUS', name, 'NO_ATTACK', 1)]
            start += [('NAMED_RECEIVE_UPGRADE', up, name) for up in CREATION[:n]]
            start += [('SET_COUNTER', counter, -1)]
            hurt += [('NAMED_DAMAGE', name, 100),
                     ('SET_UNIT_HEALTH_PERCENTAGE_TO_COUNTER', name, counter)]
            t.counters.append((counter, lane + ' frozen HP'))
        t.scripts = [Script('Test - start', [], start),
                     Script('Test - freeze damage', [('TIMER_EXPIRED', 'Level hurt')], hurt)]
        t.expect = [(lane + ' frozen HP', 8, '==', hp, 12)
                    for lane, hp in zip(('base', 'high', 'order', 'removed'), (80, 80, 84, 84))]
        t.bench = [('bench_watch', dict(seconds=12.0, every=.5, sheet=False, lines=4))]
        return t


    MISSION['engine_levelhealth'] = health_mission
    CHECKS['engine_levelhealth'] = {'a': health_check}


    def injured_health_check(m):
        """PREDICT: injured elite promotion preserves health fraction: 50/80/50/20.

        Base is an unpromoted half-health control. The other lanes start at
        400/250/100 of 500 HP, then gain veteran and elite at six seconds.
        HEALTH_MULT125 predicts 500/312.5/125 of 625 HP. Keeping absolute HP
        would read 64/40/16; adding the max-HP delta would read 84/60/36.
        No heroic grant, healing, enemy, combat experience or player input.
        Freeze at eight seconds to allow upgrade dispatch to finish. At twelve
        seconds deal another 100 damage and freeze again: 30/64/34/4. This second
        reading proves max HP increased; unchanged percentages alone cannot.
        Bench 2026-11-11 PASS: 50/80/50/20 before the hit, 30/64/34/4 after.
        """
        t = Test()
        start = [('MAP_REVEAL_ALL_PERM', m.player('p1')),
                 ('SET_MILLISECOND_TIMER', 'Level promote injured', 6.0),
                 ('SET_MILLISECOND_TIMER', 'Level freeze injured', 8.0),
                 ('SET_MILLISECOND_TIMER', 'Level verify injured', 12.0)]
        promote, freeze, verify = [], [], []
        lanes = ('base', 'high', 'order', 'removed')
        for lane, damage in zip(lanes, (250, 100, 250, 400)):
            name, counter = m.role(lane).name, 'Level injured ' + lane
            start += [('UNIT_CHANGE_OBJECT_STATUS', name, 'NO_ATTACK', 1),
                      ('NAMED_DAMAGE', name, damage), ('SET_COUNTER', counter, -1)]
            if lane != 'base':
                promote += [('NAMED_RECEIVE_UPGRADE', up, name) for up in CREATION[:2]]
            freeze += [('SET_UNIT_HEALTH_PERCENTAGE_TO_COUNTER', name, counter)]
            verify += [('NAMED_DAMAGE', name, 100),
                       ('SET_UNIT_HEALTH_PERCENTAGE_TO_COUNTER', name, counter)]
            t.counters.append((counter, lane + ' injured HP'))
        t.scripts = [Script('Test - start', [], start),
                     Script('Test - promote injured', [('TIMER_EXPIRED', 'Level promote injured')], promote),
                     Script('Test - freeze injured', [('TIMER_EXPIRED', 'Level freeze injured')], freeze),
                     Script('Test - verify injured', [('TIMER_EXPIRED', 'Level verify injured')], verify)]
        t.expect = [(lane + ' injured HP', 9, '==', hp, 10)
                    for lane, hp in zip(lanes, (50, 80, 50, 20))]
        t.expect += [(lane + ' injured HP', 14, '==', hp, 16)
                     for lane, hp in zip(lanes, (30, 64, 34, 4))]
        t.bench = [('bench_watch', dict(seconds=16.0, every=.5, sheet=False, lines=4))]
        return t


    CHECKS['engine_levelhealth']['b'] = injured_health_check


    def range_mission():
        m = mission()
        m.name = 'CampLevelR'
        for lane, distance in zip(('base', 'high', 'order', 'removed'), (220, 220, 260, 260)):
            m.put('JapanAntiVehicleVehicleTech1', lane + ' gun', 0, distance,
                  side='s1', role=lane + ' target', name='Level range target ' + lane)
            m.waypoint(lane + ' target', 'Level range mark ' + lane, lane + ' gun', 0, distance)
        return m


    def range_check(m):
        """PREDICT: normal/heroic at 220, normal/heroic at 260: only heroic 220 hits.

        Retail normal/heroic guns have AttackRange 125/150; Unit_Heroic RANGE125%
        makes the latter 187.5. Bounding radii total 49.01, so even the heroic gun
        without the modifier cannot reach 220 (limit 199.01); with it 260 is out.
        All objects IMMOBILE, shooters HOLD_FIRE; only named orders may shoot.
        Four-frame fire window, no kills or XP. Counter = target HP percent +
        10000*heroic + 1000*ever-gun-moved + 100000*ever-target-moved. Movement
        means leaving a 2-unit square, latched throughout; margins exceed 20 units.
        Stable prediction: 100/10100/100/10100 -> 100/10017/100/10100.
        Bench 2026-11-11 PASS: s1-s4 initial, s5-s16 final, no movement flags.
        Exact activation/shot frames and the precise range boundary remain INFERRED.
        """
        t = Test()
        start = [('MAP_REVEAL_ALL_PERM', m.player('p1')),
                 ('PLAYER_SET_MONEY', m.player('s1'), 0),
                 ('SET_MILLISECOND_TIMER', 'Level range fire', 6.0),
                 ('SET_MILLISECOND_TIMER', 'Level range stop', 6 + 4 / 15)]
        fire, stop = [], []
        for lane in ('base', 'high', 'order', 'removed'):
            gun, target = m.role(lane).name, m.role(lane + ' target').name
            start += [('UNIT_CHANGE_OBJECT_STATUS', n, bit, 1)
                      for n in (gun, target) for bit in ('NO_ATTACK', 'IMMOBILE')]
            start.append(('UNIT_SET_STANCE', gun, 3))  # HOLD_FIRE, explicit orders still fire
            if lane in ('high', 'removed'):
                start += [('NAMED_RECEIVE_UPGRADE', up, gun) for up in CREATION]
            fire += [('UNIT_CHANGE_OBJECT_STATUS', gun, 'NO_ATTACK', 0), ('NAMED_ATTACK_NAMED', gun, target)]
            stop.append(('UNIT_CHANGE_OBJECT_STATUS', gun, 'NO_ATTACK', 1))
            counter = 'Level range ' + lane
            t.counters.append((counter, lane + ' range'))
            for name, point in ((gun, m.site(lane + ' gun')[:2]),
                                (target, m.point(lane + ' target'))):
                area = 'Level range pad ' + name
                flag = area + ' moved'
                t.areas[area] = square(*point, 2.0)
                t.scripts.append(Script('Test - latch ' + name, [('NAMED_OUTSIDE_AREA', name, area)],
                                        [('SET_FLAG', flag, 1)]))
            t.scripts.append(Script('Test - range HP ' + lane, [],
                                    [('SET_UNIT_HEALTH_PERCENTAGE_TO_COUNTER', target, counter)], once=False))
            for name, weight in ((gun, 1000), (target, 100000)):
                t.scripts.append(Script('Test - range moved ' + name,
                                        [('FLAG', 'Level range pad ' + name + ' moved', 1)],
                                        [('INCREMENT_COUNTER', weight, counter)], once=False))
            t.scripts.append(Script('Test - range heroic ' + lane,
                                    [('UNIT_HAS_OBJECT_STATUS', gun, status('WEAPON_UPGRADED_01'))],
                                    [('INCREMENT_COUNTER', 10000, counter)], once=False))
        t.scripts[:0] = [Script('Test - start', [], start),
                         Script('Test - range fire', [('TIMER_EXPIRED', 'Level range fire')], fire),
                         Script('Test - range stop', [('TIMER_EXPIRED', 'Level range stop')], stop)]
        for first, last, values in ((2, 4, (100, 10100, 100, 10100)),
                                    (10, 14, (100, 10017, 100, 10100))):
            t.expect += [(lane + ' range', first, '==', value, last)
                         for lane, value in zip(('base', 'high', 'order', 'removed'), values)]
        t.bench = [('bench_watch', dict(seconds=14.0, every=.5, sheet=False, lines=4))]
        return t


    MISSION['engine_levelrange'] = range_mission
    CHECKS['engine_levelrange'] = {'a': range_check}


    def rate_mission():
        m = mission()
        m.name = 'CampLevelRate'
        for lane in ('base', 'high', 'order', 'removed'):
            m.put('SovietConstructionYard', lane + ' gun', 0, 150,
                  side='s1', role=lane + ' target', name='Level rate target ' + lane)
        return m


    def rate_check(m):
        """Four retail Mirage guns: normal, direct heroic upgrade, rank4, rank3.

        PREDICT: both retail guns fire1.5/reload0.1 = 23+2 = 25 frames.
        Initial ceil-parts candidate21 predicted four heroic hits, but the first
        run read68% (five). Its reversed span conditions made intervals unreadable.
        Corrected run distinguishes effective20 (five hits) from21 (four hits).
        Bench2026-11-11 at x1 PASS:252525/252525/202020/252525, then84/80/68/80.
        This only distinguishes the effective cycle, not individual timing parts.
        Counter packs three successive inter-hit spans as a + 100*b + 10000*c;
        after second14 switches to final target HP (84/80/68/80). Four/five shots,
        no kill/XP, repair or target healing; order6, stop11.5, both IMMOBILE.
        Exact first-hit timing is outside this probe's claim.
        """
        t = Test()
        start = [('MAP_REVEAL_ALL_PERM', m.player('p1')),
                 ('PLAYER_SET_MONEY', m.player('s1'), 0),
                 ('SET_MILLISECOND_TIMER', 'Level rate fire', 6.0),
                 ('SET_MILLISECOND_TIMER', 'Level rate stop', 11.5),
                 ('SET_MILLISECOND_TIMER', 'Level rate hp', 14.0)]
        fire, stop = [], []
        for lane, grants, loss in zip(('base', 'high', 'order', 'removed'),
                                      ((), ('Upgrade_Veterancy_HEROIC',), CREATION, CREATION[:2]),
                                      (4, 5, 6.25, 5)):
            gun, target = m.role(lane).name, m.role(lane + ' target').name
            start += [('UNIT_CHANGE_OBJECT_STATUS', n, bit, 1)
                      for n in (gun, target) for bit in ('NO_ATTACK', 'IMMOBILE')]
            start.append(('UNIT_SET_STANCE', gun, 3))
            start += [('NAMED_RECEIVE_UPGRADE', up, gun) for up in grants]
            fire += [('UNIT_CHANGE_OBJECT_STATUS', gun, 'NO_ATTACK', 0), ('NAMED_ATTACK_NAMED', gun, target)]
            stop.append(('UNIT_CHANGE_OBJECT_STATUS', gun, 'NO_ATTACK', 1))
            counter = 'Level rate ' + lane
            t.counters.append((counter, lane + ' timing'))
            # Integer-percent plateaux uniquely identify shots1..3; unlike total
            # damage this holds all three intervals independently to the readings.
            for shot, weight in ((1, 1), (2, 100), (3, 10000)):
                upper = int(100 - shot * loss)
                lower = int(100 - (shot + 1) * loss)
                t.scripts.append(Script('Test - rate span ' + lane + str(shot),
                                        [('UNIT_HEALTH', target, 0, upper + 1),
                                         ('UNIT_HEALTH', target, 4, lower)],
                                        [('INCREMENT_COUNTER', weight, counter)], once=False))
            t.scripts.append(Script('Test - rate final HP ' + lane,
                                    [('TIMER_EXPIRED', 'Level rate hp')],
                                    [('SET_UNIT_HEALTH_PERCENTAGE_TO_COUNTER', target, counter)], once=False))
        t.scripts[:0] = [Script('Test - start', [], start),
                         Script('Test - rate fire', [('TIMER_EXPIRED', 'Level rate fire')], fire),
                         Script('Test - rate stop', [('TIMER_EXPIRED', 'Level rate stop')], stop)]
        for first, last, values in ((12, 13, (252525, 252525, 202020, 252525)),
                                    (15, 17, (84, 80, 68, 80))):
            t.expect += [(lane + ' timing', first, '==', value, last)
                         for lane, value in zip(('base', 'high', 'order', 'removed'), values)]
        t.bench = [('bench_watch', dict(seconds=17.0, every=.5, sheet=False, lines=4))]
        return t


    MISSION['engine_levelrate'] = rate_mission
    CHECKS['engine_levelrate'] = {'a': rate_check}




    def shroud_mission():
        m = mission()
        m.name = 'CampLevelFog'
        for lane, distance in zip(SHROUD_LANES, (580, 580, 750, 750)):
            for tag, dy in (('target', distance), ('near', 200)):
                m.put('JapanAntiVehicleVehicleTech1', lane + ' gun', 0, dy,
                      side='s1', role=lane + ' ' + tag, name='Level fog ' + lane + ' ' + tag)
        return m


    def shroud_check(m):
        """PREDICT: retail Mirage shroud500 -> heroic625; baseline VisionRange200.

        Normal/heroic at580, normal/heroic at750; an enemy at200 is the positive
        visibility control in each lane. Creation grants at6s, no attack/reveal.
        Counter=near discovered +10*target discovered +100*heroic status,
        +1000*ever moved (any of the lane's three objects). All IMMOBILE/NO_ATTACK.
        Lanes1500 apart, flat ground; even combined bounding radii (<60) cannot
        bridge the normal580 or heroic750 gaps. Precise fog cell edges and heroic
        VISION/auto-acquire are unmeasured; discovery cannot establish their values.
        Stable windows2-4:1/1/1/1;18-22:1/111/1/101. No discovery latch.
        Bench2026-11-11 x1 PASS: s1-s4 1/1/1/1; s5-s23 1/111/1/101.
        """
        t = Test()
        start = [('PLAYER_SET_MONEY', m.player('s1'), 0),
                 ('SET_MILLISECOND_TIMER', 'Level fog promote', 6.0)]
        promote = []
        for lane in SHROUD_LANES:
            gun = m.role(lane).name
            if lane in ('high', 'removed'):
                promote += [('NAMED_RECEIVE_UPGRADE', up, gun) for up in CREATION]
            c, moved = 'Level fog ' + lane, 'Level fog moved ' + lane
            t.counters.append((c, lane + ' fog'))
            for role in (lane, lane + ' target', lane + ' near'):
                obj = m.role(role)
                start += [('UNIT_CHANGE_OBJECT_STATUS', obj.name, bit, 1) for bit in ('IMMOBILE', 'NO_ATTACK')]
                placed = next(o for o in m.objects if o.name == obj.name)
                t.areas[obj.name] = square(placed.x, placed.y, 2.0)
                t.scripts.append(Script('Test - fog latch ' + role, [('NAMED_OUTSIDE_AREA', obj.name, obj.name)],
                                        [('SET_FLAG', moved, 1)]))
            t.scripts.append(Script('Test - fog reset ' + lane, [], [('SET_COUNTER', c, 0)], once=False))
            for tag, weight in (('near', 1), ('target', 10)):
                t.scripts.append(Script('Test - fog see ' + lane + tag,
                                        [('NAMED_DISCOVERED', m.player('p1'), m.role(lane + ' ' + tag).name)],
                                        [('INCREMENT_COUNTER', weight, c)], once=False))
            t.scripts.append(Script('Test - fog heroic ' + lane,
                                    [('UNIT_HAS_OBJECT_STATUS', gun, status('WEAPON_UPGRADED_01'))],
                                    [('INCREMENT_COUNTER', 100, c)], once=False))
            t.scripts.append(Script('Test - fog moved ' + lane, [('FLAG', moved, 1)],
                                    [('INCREMENT_COUNTER', 1000, c)], once=False))
        t.scripts[:0] = [Script('Test - start', [], start),
                         Script('Test - fog promote', [('TIMER_EXPIRED', 'Level fog promote')], promote)]
        for first, last, values in ((2, 4, (1, 1, 1, 1)), (18, 22, (1, 111, 1, 101))):
            t.expect += [(lane + ' fog', first, '==', value, last) for lane, value in zip(SHROUD_LANES, values)]
        t.bench = [('bench_watch', dict(seconds=22.0, every=1, sheet=False, lines=4))]
        return t


    MISSION['engine_levelshroud'] = shroud_mission
    CHECKS['engine_levelshroud'] = {'a': shroud_check}


    def vision_mission():
        m = mission()
        m.name = 'CampLevelEye'
        for lane, distance in zip(SHROUD_LANES, (240, 240, 310, 310)):
            for tag, dy in (('target', distance), ('near', 100)):
                m.put('SovietEngineer', lane + ' gun', 0, dy,
                      side='s1', role=lane + ' ' + tag, name='Level eye ' + lane + ' ' + tag)
        return m


    def vision_check(m):
        """Retail Mirage VisionRange200, Unit_Heroic VISION125 (no percent sign).

        First bench310/430 with Tsunami targets rejected additive325 and raw125x:
        neither heroic viewer sighted an enemy. This refined probe uses engineers
        (radius5; Mirage24.41): ordinary200 cannot reach240 even with both radii,
        percent250 reaches240 but not310; fixed125/no change reaches neither.
        All lanes1500 apart; ENEMY_SIGHTED aggregates any enemy, so
        positive controls100 away are deleted at6s, before promotion at12s.
        Four counters: sighted +10*near alive +100*heroic +1000*ever moved.
        All objects IMMOBILE/NO_ATTACK; no attacks, reveals or discovery query.
        Nonempty windows2-4 positive,8-10 isolated baseline,20-24 promoted.
        Prediction11/11/11/11 ->0/0/0/0 ->0/101/0/100 (percent candidate).
        Precise boundaries and automatic acquisition are outside this probe.
        Bench2026-11-11 x1 PASS: s1-s4 11/11/11/11; s5-s10 0/0/0/0;
        s11-s25 0/101/0/100, all12 window assertions passed, no movement bits.
        """
        t = Test()
        start = [('PLAYER_SET_MONEY', m.player('s1'), 0),
                 ('SET_MILLISECOND_TIMER', 'Level eye remove', 6.0),
                 ('SET_MILLISECOND_TIMER', 'Level eye promote', 12.0)]
        remove, promote = [], []
        for lane in SHROUD_LANES:
            gun, near = m.role(lane).name, m.role(lane + ' near').name
            remove.append(('NAMED_DELETE', near))
            if lane in ('high', 'removed'):
                promote += [('NAMED_RECEIVE_UPGRADE', up, gun) for up in CREATION]
            c, moved = 'Level eye ' + lane, 'Level eye moved ' + lane
            t.counters.append((c, lane + ' eye'))
            for role in (lane, lane + ' target', lane + ' near'):
                obj = m.role(role)
                start += [('UNIT_CHANGE_OBJECT_STATUS', obj.name, bit, 1) for bit in ('IMMOBILE', 'NO_ATTACK')]
                placed = next(o for o in m.objects if o.name == obj.name)
                t.areas[obj.name] = square(placed.x, placed.y, 2.0)
                t.scripts.append(Script('Test - eye latch ' + role,
                                        [('NAMED_NOT_DESTROYED', obj.name), ('NAMED_OUTSIDE_AREA', obj.name, obj.name)],
                                        [('SET_FLAG', moved, 1)]))
            t.scripts.append(Script('Test - eye reset ' + lane, [], [('SET_COUNTER', c, 0)], once=False))
            for tag, conditions, weight in (
                    ('sighted', [('ENEMY_SIGHTED', gun, 'Enemy', m.player('s1'))], 1),
                    ('near', [('NAMED_NOT_DESTROYED', near)], 10),
                    ('heroic', [('UNIT_HAS_OBJECT_STATUS', gun, status('WEAPON_UPGRADED_01'))], 100),
                    ('moved', [('FLAG', moved, 1)], 1000)):
                t.scripts.append(Script('Test - eye ' + tag + lane, conditions,
                                        [('INCREMENT_COUNTER', weight, c)], once=False))
        t.scripts[:0] = [Script('Test - start', [], start),
                         Script('Test - eye remove', [('TIMER_EXPIRED', 'Level eye remove')], remove),
                         Script('Test - eye promote', [('TIMER_EXPIRED', 'Level eye promote')], promote)]
        for first, last, values in ((2, 4, (11, 11, 11, 11)), (8, 10, (0, 0, 0, 0)),
                                    (20, 24, (0, 101, 0, 100))):
            t.expect += [(lane + ' eye', first, '==', value, last) for lane, value in zip(SHROUD_LANES, values)]
        t.bench = [('bench_watch', dict(seconds=24.0, every=1, sheet=False, lines=4))]
        return t


    MISSION['engine_levelvision'] = vision_mission
    CHECKS['engine_levelvision'] = {'a': vision_check}
    return dict(MISSION=MISSION, CHECKS=CHECKS)


def engine_life():
    """Engine probe: how many frames an object with a LifetimeUpdate lives, and how long an ice engineer's power takes to
    leave a wall (benches/body_death/state/scenes.py#engine_life; rules R1 and R5 of docs/story/sim-vs-bench-a4.md: the A4 bench read an ice
    wall standing ~28 s of its 30, and a wall ~9 s after the order).

    Frame 1 a script creates the named wall at A and the ice core at B; at ORDER s the two engineers are told to freeze
    C and D (NAMED_FIRE_SPECIAL_POWER_AT_WAYPOINT; his power reloads 20 s, so it is ready). Each frame (15 a second):
      墙A  1 x frames the named wall is not destroyed  + 1000 x frames a wall stands in the square round A
      墙B  1 x frames a wall stands in the square round B + 1000 x frames the named core is not destroyed
      冰C  from the order: 1 x frames nothing of his stands at C yet + 1000 x frames his core stands there
      冰D  the same at D (engineer 2 walks 400 first)
    So 墙A's units digits are the wall's life in frames, its thousands how long its body stands in the area; 墙B's
    thousands the core's life, its units the wall it left. 冰C / 冰D: the order to the core (units), the core to the
    wall (thousands). Read at the end only (the run outlasts all).
    bench 2026-11-07 (frames, R1): 墙A 451451, 墙B 83450 -- a 30 s wall 450 frames, a 5.5 s core 82, its wall at once.
    """
    from parts import Script, Test, square

    RUN, ORDER = 52.0, 21.0


    def frames(m):
        t = Test()
        p1 = m.player('p1')
        wall_a, core_b = 'UNIT - CNV Life Wall A', 'UNIT - CNV Life Core B'
        t.scripts += [Script('Test - start', [], [('MAP_REVEAL_ALL_PERM', p1),
                                                  ('CREATE_NAMED_ON_TEAM_AT_WAYPOINT', wall_a, 'CNV_LifeWall', m.team('p1'),
                                                   m.mark('life A')),
                                                  ('CREATE_NAMED_ON_TEAM_AT_WAYPOINT', core_b, 'CNV_LifeSeed', m.team('p1'),
                                                   m.mark('life B')),
                                                  ('SET_FLAG', 'Test Made', 1),
                                                  ('SET_MILLISECOND_TIMER', 'Test Order', ORDER)]),
                      Script('Test - order', [('TIMER_EXPIRED', 'Test Order')],
                             [('NAMED_FIRE_SPECIAL_POWER_AT_WAYPOINT', m.role(f'engineer {k}').name,
                               m.ability(f'engineer {k}', 'freeze'), m.mark(f'life {s}')) for k, s in ((1, 'C'), (2, 'D'))]
                             + [('SET_FLAG', 'Test Ordered', 1)])]
        for k in 'ABCD':
            t.areas[f'Test Life {k}'] = square(*m.point(f'life {k}'), 100.0)

        def there(template, k, n=1):
            return ('PLAYER_HAS_COMPARISON_UNIT_TYPE_IN_TRIGGER_AREA', p1, 3 if n else 2, n, template, f'Test Life {k}')

        made, ordered = [('FLAG', 'Test Made', 1)], [('FLAG', 'Test Ordered', 1)]
        t.scripts += [
            Script('Test - wall A alive', made + [('NAMED_NOT_DESTROYED', wall_a)],
                   [('INCREMENT_COUNTER', 1, 'CNV_Life_A')], once=False),
            Script('Test - wall A there', made + [there('CNV_LifeWall', 'A')],
                   [('INCREMENT_COUNTER', 1000, 'CNV_Life_A')], once=False),
            Script('Test - wall B there', made + [there('CNV_LifeWall', 'B')],
                   [('INCREMENT_COUNTER', 1, 'CNV_Life_B')], once=False),
            Script('Test - core B alive', made + [('NAMED_NOT_DESTROYED', core_b)],
                   [('INCREMENT_COUNTER', 1000, 'CNV_Life_B')], once=False)]
        for k in 'CD':
            t.scripts += [
                Script(f'Test - nothing at {k}', ordered + [there('CNV_LifeSeed', k, 0), there('CNV_LifeWall', k, 0)],
                       [('INCREMENT_COUNTER', 1, f'CNV_Life_{k}')], once=False),
                Script(f'Test - core at {k}', ordered + [there('CNV_LifeSeed', k)],
                       [('INCREMENT_COUNTER', 1000, f'CNV_Life_{k}')], once=False)]
        t.counters += [('CNV_Life_A', '墙A'), ('CNV_Life_B', '墙B'), ('CNV_Life_C', '冰C'), ('CNV_Life_D', '冰D')]
        life = m.facts['life'] * 15
        t.expect += [('墙A', RUN - 2, 'ever>=', life - 60),         # it stood about its lifetime (frames) ...
                     ('墙B', RUN - 2, 'ever>=', 1000),               # ... and the core lived and left a wall
                     ('冰C', RUN - 2, 'ever>=', 1000),               # each engineer's core came
                     ('冰D', RUN - 2, 'ever>=', 1000)]
        t.bench = [('bench_watch', dict(seconds=RUN, every=4, sheet=False, lines=len(t.counters)))]
        return t


    CHECKS = {'engine_life': {'frames': frames}}
    return dict(CHECKS=CHECKS)


def engine_managerbody():
    """ManagerBody: retail HB_Bridge_02 whole-bridge proxy, untouched / script damage.

    Use Niagara's two 270-unit bridges with their original adjacent start/end flags,
    on same-height banks over water. No empty bridge proxy is placed on dry land.
    HB_Bridge_02 -> BaseBridge -> BaseObject; BaseBridge's ManagerBody has
    InitialHealth=MaxHealth=1. Schema inherits ImmortalBody. PREDICTION (not proof):
    both named start proxies read 100 percent and survive NAMED_DAMAGE 200.
    The two state rows are 1 for named survival + 10 for a retail HB_Bridge_02
    remaining in that bridge's area. Missing names cannot pass via frozen HP.
    Damage at mission second 10 leaves a baseline despite loading time.
    Only whole-proxy script damage is tested: generated pieces, shared health,
    repair, killing/deleting, other templates and exact timing remain unmeasured.

    BENCH 2026-11-11 a: s1-s8 100/100/11/11; s9-s25 100/80/11/11.
    The XML-1HP prediction above was falsified: proxy health is a runtime value.
    b: s1-s8 100/100/11/11; s9-s18 80/80/11/11; s19-s35 1/1/11/11.
    270/700 bridges both lose 20 percentage points to 200 damage; 20000 more leaves
    both alive at a displayed 1%. Effective internal HP/floor remain INFERRED.
    No generated piece is named or hit, so shared/piece health is not verified.
    """
    from types import SimpleNamespace

    import platmap
    from maps import island, niagara
    from parts import Mission, Script, Test, square


    def mission(which='a'):
        # Keep the proven map geometry; replace only the first two pairs with names.
        probe_map = SimpleNamespace(**vars(niagara))
        probe_map.PLAYERS = {**niagara.PLAYERS, **island.NEUTRAL}
        probe_map.OBJECTS = niagara.OBJECTS[4:] if which == 'a' else niagara.OBJECTS[2:4] + niagara.OBJECTS[6:]
        m = Mission(name='CampManager', map=probe_map, units=[], facts={'diagnostic': which == 'b'})
        origin = m.site('front')
        pairs = niagara.BRIDGES[:2] if which == 'a' else [niagara.BRIDGES[0], niagara.BRIDGES[2]]
        for role, (p, q) in zip(('control', 'hit'), pairs):
            for k, (x, y, angle, flags) in enumerate(platmap.bridge(p, q)):
                part = role if k == 0 else role + ' end'
                m.put('HB_Bridge_02', 'front', x - origin[0], y - origin[1],
                      side='neutral', angle=angle, flags=flags, role=part,
                      name='Manager ' + part)
            m.areas['Manager ' + role] = square((p[0] + q[0]) / 2, p[1], (q[0] - p[0]) / 2 + 10)
        return m


    def check(m):
        t = Test()
        diagnostic = m.facts['diagnostic']
        t.counters = [('Manager HP ' + role, label)
                      for role, label in (('control', '原血'), ('hit', '伤血'))]
        t.counters += [('Manager state ' + role, label)
                       for role, label in (('control', '原存'), ('hit', '伤存'))]
        t.scripts = [Script('Manager start', [], [
            ('MAP_REVEAL_ALL_PERM', m.player('p1')),
            ('SET_MILLISECOND_TIMER', 'Manager damage', 10.0)]),
            Script('Manager damage', [('TIMER_EXPIRED', 'Manager damage')], [
                ('NAMED_DAMAGE', m.role('hit').name, 200)] + ([
                ('NAMED_DAMAGE', m.role('control').name, 200),
                ('SET_MILLISECOND_TIMER', 'Manager lethal', 10.0)] if diagnostic else []))]
        if diagnostic:
            t.scripts.append(Script('Manager lethal', [('TIMER_EXPIRED', 'Manager lethal')], [
                ('NAMED_DAMAGE', m.role(role).name, 20000) for role in ('control', 'hit')]))
        for role in ('control', 'hit'):
            name, state = m.role(role).name, 'Manager state ' + role
            t.scripts += [
                Script('Manager read ' + role, [], [
                    ('SET_UNIT_HEALTH_PERCENTAGE_TO_COUNTER', name, 'Manager HP ' + role),
                    ('SET_COUNTER', state, 0)], once=False),
                Script('Manager alive ' + role, [('NAMED_NOT_DESTROYED', name)], [
                    ('INCREMENT_COUNTER', 1, state)], once=False),
                Script('Manager retail ' + role, [
                    ('PLAYER_HAS_COMPARISON_UNIT_TYPE_IN_TRIGGER_AREA', m.player('neutral'),
                     3, 1, m.role(role).template, 'Manager ' + role)], [
                    ('INCREMENT_COUNTER', 10, state)], once=False)]
        if diagnostic:
            t.expect = [(label, 2, '==', 11, 33) for label in ('原存', '伤存')]
            t.expect += [(label, start, '==', hp, end) for label in ('原血', '伤血')
                         for start, end, hp in ((2, 7, 100), (14, 17, 80), (24, 33, 1))]
        else:
            t.expect = [('原血', 2, '==', 100, 23), ('伤血', 2, '==', 100, 7),
                        ('伤血', 15, '==', 80, 23),
                        ('原存', 2, '==', 11, 23), ('伤存', 2, '==', 11, 23)]
        t.bench = [('bench_watch', dict(every=0.5, sheet=False, lines=4, seconds=34 if diagnostic else 24))]
        return t


    MISSION = {'engine_managerbody': mission, 'engine_managerbody_b': lambda: mission('b')}
    CHECKS = {'engine_managerbody': {'a': check}, 'engine_managerbody_b': {'b': check}}
    return dict(MISSION=MISSION, CHECKS=CHECKS)


def engine_maxhealth():
    """NAMED_SET_MAX_HEALTH(object, max, full) on the bench (engine line A round 147): what happens to the current health.

    RA3 1.13 (work/re ra3-script-reference, action 551): the body's setMaxHealth is called with
    (max, 0) and, when `full` is set, setHealth 1.0 (slot 0x80). In Generals the 0 is MaxHealthChangeType
    SAME_CURRENTHEALTH: the hit points stay, only the ceiling moves (clamped down to a lower ceiling). The argument types
    are retail's (script_catalog: object, INT, BOOLEAN) -- the 11-05 engine_missile try passed 10000.0, a REAL, in the
    INT slot, so its "keeps the current health" reading is not this action's (the try was never committed).

    Four of the player's Guardians (480 health) on maps/probe_border.py, rows 500 apart, nobody near: NAMED_DAMAGE
    (an INT, no armour: engine_scripts7 panel) at 1 s / 3 s, the set at 2 s; each one's health percent read every frame.
      甲 A  240 off at 1 s, max 960 full 0 at 2 s     SAME_CURRENTHEALTH 25 (the ratio kept would be 50)
      乙 B  240 off at 1 s, max 960 full 1            100
      丙 D  max 9600 full 1, 480 off at 3 s           95 (the max not taken: dead, 0)
      丁 E  max 240 full 0, 120 off at 3 s            50 (clamped to 240, then half; not clamped 100 -> 75)
    """
    from maps import probe_border
    from parts import Mission, Script, Test
    import checks.engine_scripts8 as s8

    TANK = 'AlliedAntiVehicleVehicleTech1'          # MaxHealth 480
    O = (1300.0, 4300.0)                            # probe_border's 'stop row'
    LANES = {'A': (240, (960, 0), 0), 'B': (240, (960, 1), 0), 'D': (0, (9600, 1), 480),
             'E': (0, (240, 0), 120)}               # lane: (damage at 1 s, (max, full) at 2 s, damage at 3 s)
    LABELS = dict(zip(LANES, '甲乙丙丁'))
    BENCH = {'A': 25, 'B': 100, 'D': 95, 'E': 50}     # predicted from the decompile; the bench decides
    RUN = 10.0


    def _n(k):
        return f'UNIT - CNV MH {k}'


    def mission():
        m = Mission(name='CampMaxHp', map=probe_border, units=[], facts={})
        m.spawns |= {TANK}
        for i, k in enumerate(LANES):
            m.put(TANK, 'stop row', 1000.0 - O[0], 1000.0 + 500.0 * i - O[1], angle=0.0, name=_n(k), role=f'{k} tank')
        return m


    def mh(m, expect=BENCH):
        t = Test()
        first = [('NAMED_DAMAGE', m.role(f'{k} tank').name, d) for k, (d, _, _) in LANES.items() if d]
        sets = [('NAMED_SET_MAX_HEALTH', m.role(f'{k} tank').name, mx, full) for k, (_, (mx, full), _) in LANES.items()]
        then = [('NAMED_DAMAGE', m.role(f'{k} tank').name, d) for k, (_, _, d) in LANES.items() if d]
        s8.at(t, 'hurt', 1.0, first)
        s8.at(t, 'max', 2.0, sets)
        s8.at(t, 'then', 3.0, then)
        for k in LANES:
            counter = f'CNV_MH_{k}'
            t.counters.append((counter, LABELS[k]))
            t.scripts.append(Script(f'Test - {counter}', [], [('SET_UNIT_HEALTH_PERCENTAGE_TO_COUNTER',
                                                               m.role(f'{k} tank').name, counter)], once=False))
        t.expect += [(LABELS[k], 6, '==', v) for k, v in expect.items()]
        s8.watch(t, RUN)
        return t


    MISSION = {'engine_maxhealth': mission}
    CHECKS = {'engine_maxhealth': {'mh': mh}}
    return dict(MISSION=MISSION, CHECKS=CHECKS)


def engine_playerkill():
    """PLAYER_KILL ownership contrast; evidence: work/re/c_playerkill_report.md.

    Prediction before bench: at 5s kill Soviet_4, leaving Player_1/Soviet_5
    units and buildings alive (masks 7 -> 5). Kill empty Soviet_6 at 3s;
    repeat Soviet_4 at 9s. Four displayed counters: unit alive mask,
    building alive mask, dying mask (units bits 1/2/4, buildings 8/16/32),
    logic frame. No player defeat condition exists in script_catalog.json;
    object death is the measured slice, player elimination remains a gap.
    MEASURED A: f45/61/75 7/7/0/frame; f83/152/287 5/5/0/frame.
    """
    from maps import probe_border
    from parts import Mission, Script, Test, status
    from checks import engine_scripts8 as s8

    SIDES = ('p1', 's4', 's5')


    def mission():
        m = Mission(name='CampPlayerKill', map=probe_border, units=[], facts={})
        for k, side in enumerate(SIDES):
            for kind, template, dx in (('unit', 'AlliedAntiVehicleVehicleTech1', 0.),
                                       ('plant', 'SovietPowerPlant', 300.)):
                role = side+' '+kind
                m.put(template, 'stop row', -500.+k*1500.+dx, -2300., side=side,
                      role=role, name='CNV PlayerKill '+role)
        return m


    def check(m):
        t = Test()
        t.scripts.append(Script('Test - PlayerKill hold', [], [
            ('UNIT_CHANGE_OBJECT_STATUS', m.role(side+' '+kind).name, status('NO_ATTACK'), 1)
            for side in SIDES for kind in ('unit', 'plant')]))
        s8.at(t, 'kill empty player', 3., [('PLAYER_KILL', m.player('s6'))])
        s8.at(t, 'kill target player', 5., [('PLAYER_KILL', m.player('s4'))])
        s8.at(t, 'kill target again', 9., [('PLAYER_KILL', m.player('s4'))])
        for kind, label in (('unit', '单位位'), ('plant', '建筑位')):
            s8.total(t, 'CNV_PK_'+kind, label, [
                (2**k, ('NAMED_NOT_DESTROYED', m.role(side+' '+kind).name))
                for k, side in enumerate(SIDES)])
        s8.total(t, 'CNV_PK_Dying', '死亡位', [
            (2**(k+3*j), ('NAMED_DYING', m.role(side+' '+kind).name))
            for j, kind in enumerate(('unit', 'plant')) for k, side in enumerate(SIDES)])
        s8.frames(t, 'CNV_PK_Frame', '逻辑帧', [])
        s8.watch(t, 16., .5)
        return t


    PK = 'alliedantiinfantryinfantry'     # the Peacekeeper an Allied structure's death leaves (REQUIRES_LIVE_PLAYER)


    def allied():
        """Review xx #2: s4's and s5's plants are Allied (their BuildingDestruction list leaves a Peacekeeper only while
        the owner is a live player). s4 is cleared by PLAYER_KILL at 5 s and 9 s, s5's plant by NAMED_KILL at 5 s (does a
        script death leave one at all); p1's Soviet plant stays."""
        m = Mission(name='CampPKAllied', map=probe_border, units=[], facts={})
        for k, (side, template) in enumerate((('p1', 'SovietPowerPlant'), ('s4', 'AlliedPowerPlant'),
                                              ('s5', 'AlliedPowerPlant'))):
            m.put(template, 'stop row', -200.+k*1500., -2300., side=side, role=side, name='CNV PKAllied '+side)
        m.spawns |= {PK}
        return m


    def check_allied(m):
        t = Test()
        s8.at(t, 'kill player', 5., [('PLAYER_KILL', m.player('s4')), ('NAMED_KILL', m.role('s5').name)])
        s8.at(t, 'kill again', 9., [('PLAYER_KILL', m.player('s4'))])
        s8.total(t, 'CNV_PKA_Plant', '电厂位', [(2**k, ('NAMED_NOT_DESTROYED', m.role(side).name))
                                             for k, side in enumerate(('p1', 's4', 's5'))])
        for side in ('s4', 's5'):           # counted with the dying (PLAYER_HAS_OBJECT_COMPARISON), up to 2
            s8.total(t, 'CNV_PKA_'+side, side+' 维和兵', [(1, ('PLAYER_HAS_OBJECT_COMPARISON', m.player(side), 3, n, PK))
                                                         for n in (1, 2)])
        s8.frames(t, 'CNV_PKA_Frame', '逻辑帧', [])
        s8.watch(t, 16., .5)
        return t


    MISSION = {'engine_playerkill': mission, 'engine_pkallied': allied}
    CHECKS = {'engine_playerkill': {'a': check}, 'engine_pkallied': {'a': check_allied}}
    return dict(MISSION=MISSION, CHECKS=CHECKS)


def engine_propbody():
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

    PREDICTED before the bench (the simulator then gave a body without MaxHealth 300 HP): a 97 x 3, all left; b each
    destroyed the frame of the kill and dying one frame; c none shot.
    Read (测, 2026-11-10, run_queue, all PASS; work/bench_results/engine_propbody*__*.json):
      a  血1..3 0 0 0 throughout, 存 333333333 at s21 (all three there): no health to read or take
      b  帧数 332, 行1 332 (the street segment never goes), 行2 61, 行3 121 (the tree / lantern gone 61 / 121 frames after
         the kill -- their ToppleUpdate removal delay, 60 / 120 -- and never dying)
      c  332 x 4: the Hammers never fire, nothing goes
    Simulated since (the PropBody module, engine/modules/body.py; simunits.prop_death, World.kill):
    tests/test_simbench_c.py::test_prop_body_no_health_a_kill_leaves_the_street_and_topples_the_tree_and_lantern_at_the_bench_frames.
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
    return dict(MISSION=MISSION, CHECKS=CHECKS)


def engine_highlander():
    """Compare full and wounded HighlanderBody with ActiveBody under lethal NAMED_DAMAGE.

    The rewind bench suggested a full Highlander might survive. Without the belt
    or movement, the bench measured all three destroyed after the lethal hit.
    """
    from pathlib import Path

    import labpaths
    from maps import festival
    from parts import Mission, Script, Test, Unit

    arms = ('Full', 'Wounded', 'Active')
    labels = ('满血', '伤血', '普通')
    host = 'AlliedPowerPlant'

    def mission():
        m = Mission(name='CampHighlander', map=festival, units=[])
        source = (Path(labpaths.SDK3) / 'SageXML/Allied/Structures/AlliedPowerPlant.xml').read_text(encoding='utf-8-sig')
        for i, arm in enumerate(arms):
            ident = 'CNVHighlander' + arm
            xml = source.replace(f'id="{host}"', f'id="{ident}"', 1).replace('MaxHealth="1000.0"', 'MaxHealth="100"')
            if arm != 'Active':
                xml = xml.replace('<ActiveBody', '<HighlanderBody', 1)
            m.units.append(Unit(ident, xml))
            m.put(ident, 'west field', 0, 220 * (i - 1), role=arm, name='Highlander ' + arm)
        return m

    def check(m):
        t = Test()
        names = [m.role(arm).name for arm in arms]
        t.scripts = [
            Script('Highlander start', [], [('SET_MILLISECOND_TIMER', 'Wound at', 4.0),
                                            ('SET_MILLISECOND_TIMER', 'Lethal at', 8.0)]),
            Script('Highlander wound', [('TIMER_EXPIRED', 'Wound at')], [('NAMED_DAMAGE', names[1], 40)]),
            Script('Highlander lethal', [('TIMER_EXPIRED', 'Lethal at')],
                   [('NAMED_DAMAGE', name, 200) for name in names]),
            Script('Highlander reset reads', [], [('SET_COUNTER', arm, -1) for arm in arms], once=False),
        ]
        for arm, name in zip(arms, names):
            t.scripts.append(Script('Highlander read ' + arm, [('NAMED_NOT_DESTROYED', name)],
                                    [('SET_UNIT_HEALTH_PERCENTAGE_TO_COUNTER', name, arm)], once=False))
        t.counters = list(zip(arms, labels))
        t.expect = [(label, start, '==', hp, end)
                    for start, end, values in ((1, 2, (100, 100, 100)), (5, 6, (100, 60, 100)),
                                               (9, 11, (-1, -1, -1)))
                    for label, hp in zip(labels, values)]
        t.bench = [('bench_watch', dict(seconds=12, every=1, sheet=False, lines=3))]
        return t

    return dict(MISSION={'engine_highlander': mission}, CHECKS={'engine_highlander': {'a': check}})


def engine_rewind():
    """A8's Liberty rewind (engine line D, user 11-11; benches/body_death/state/scenes.py#engine_rewind has the rules, units/rewind.py the
    carrier). Counters: 血 = the carrier's health %, 回溯 = presses of its belt, 原处 = 1 while it is within 150 of
    where it started, 归我 = 1 while it is the player's.

    auto  (item 1) GO: health set to 60 %; GO + 3: teleported 400 east; GO + 5: NAMED_DAMAGE 100000 (fatal) -- alive,
          back where it was 3 s ago (原处 1) with that health (60); GO + 12, inside the cooldown: fatal again -- dead.
    own   (item 2) GO: ours (control); GO + 1.5: fatal -- rewound to Soviet_1's carrier (ours 3 s ago: no), 归我 0.
    ctrl  (item 3) GO: ours for CONTROL s, then Soviet_1's again (归我 1 then 0); nothing else.
    trick (items 2 + 3) GO: ours; GO + 4: health 10 %, our two Multigunners force-attack it (NAMED_FORCE_ATTACK_NAMED:
          can they shoot an aircraft of their own?) and are stopped at the first rewind; ours 3 s before the fatal
          shot, so ours for good: 归我 1 after the control ends.
    """
    from parts import Script, Test, counted, square

    GO = 10.0
    CONTROL = 15.0      # the launcher's hold, the mission's rule (control: ours, back CONTROL s later unless Rw Perm)


    def _control(at):
        """Starts the mission's control rule at `at` (its timer Rw Control): checks ask the mission, never import it."""
        return Script('Test - control at', [], [('SET_MILLISECOND_TIMER', 'Rw Control', at), ('SET_FLAG', 'Rw Control On', 1)])


    def _base(m, run, owner=False):
        t = Test()
        t.scripts.append(Script('Test - start', [], [('MAP_REVEAL_ALL_PERM', m.player('p1')),
                                                     ('SET_MILLISECOND_TIMER', 'Test Go', GO)]))
        counted('Test Health', '血', t, health=m.role("carrier").name)
        t.counters.append(('Rw Rewinds', '回溯'))
        if owner:
            counted('Test Ours', '归我', t, owner=m.role("carrier").name)
        else:
            t.areas['Test Start'] = square(*m.waypoints[m.mark('start')], 150.0)
            counted('Test Home', '原处', t, named=m.role("carrier").name, area='Test Start')
        t.bench = [('bench_watch', dict(seconds=run, every=1, sheet=False, lines=len(t.counters)))]
        return t


    def _at(t, tag, at, actions):
        t.scripts += [Script(f'Test - {tag} timer', [('TIMER_EXPIRED', 'Test Go')],
                             [('SET_MILLISECOND_TIMER', f'Test {tag}', at)]),
                      Script(f'Test - {tag}', [('TIMER_EXPIRED', f'Test {tag}')], actions)]


    def still(m):
        """auto without the move: H1 (a moving carrier is not held at 1 hp) against H2 (one below full health is not)."""
        t = auto(m)
        t.scripts = [s if s.name != 'Test - hurt' else Script(s.name, s.when, s.do[:1]) for s in t.scripts]
        return t


    def auto(m):
        """Bench 11-11 round 1 (CampRwAuto_mcp_1111_161159): UNIT_SET_HEALTH and UNIT_TELEPORT_TO_WAYPOINT did nothing
        to this carrier (血 100, 原处 1 throughout); the fatal blow was survived and rewound (回溯 1, 血 100), the one
        inside the cooldown killed it. So: hurt by NAMED_DAMAGE, moved by a move order, its track from ra3ext's probe."""
        t = _base(m, GO + 22)
        _at(t, 'hurt', 0.01, [('NAMED_DAMAGE', m.role("carrier").name, 2400), ('MOVE_NAMED_UNIT_TO', m.role("carrier").name, m.mark('away'))])
        _at(t, 'fatal', 8.0, [('NAMED_DAMAGE', m.role("carrier").name, 100000)])
        _at(t, 'fatal2', 15.0, [('NAMED_DAMAGE', m.role("carrier").name, 100000)])
        t.expect += [('血', GO + 2, '==', 60), ('回溯', GO + 11, '==', 1), ('血', GO + 11, '==', 60)]
        return t


    def own(m):
        t = _base(m, GO + 8, owner=True)
        t.scripts.append(_control(GO))
        _at(t, 'fatal', 1.5, [('NAMED_DAMAGE', m.role("carrier").name, 100000)])
        t.expect += [('归我', GO + 1, '==', 1), ('回溯', GO + 5, '==', 1), ('归我', GO + 5, '==', 0)]
        return t


    def ctrl(m):
        t = _base(m, GO + CONTROL + 6, owner=True)
        t.scripts.append(_control(GO))
        t.expect += [('归我', GO - 2, '==', 0), ('归我', GO + 3, '==', 1), ('归我', GO + CONTROL + 4, '==', 0)]
        return t


    def trick(m):
        t = _base(m, GO + CONTROL + 8, owner=True)
        t.scripts.append(_control(GO))
        guns = [m.role(f'gun {k}').name for k in (1, 2)]
        _at(t, 'shoot', 4.0, [('UNIT_SET_HEALTH', m.role("carrier").name, 10)] + [('NAMED_FORCE_ATTACK_NAMED', g, m.role("carrier").name) for g in guns])
        t.scripts.append(Script('Test - hold fire', [('COUNTER', 'Rw Rewinds', 3, 1)], [('NAMED_STOP', g) for g in guns]))
        t.expect += [('归我', GO + 3, '==', 1), ('回溯', GO + CONTROL, '>=', 1), ('归我', GO + CONTROL + 6, '==', 1)]
        return t


    def fire(m):
        """Item 3's question alone: ours (control) at GO, our two Multigunners ordered at GO + 2 to force-attack it
        (NAMED_FORCE_ATTACK_NAMED); 血 < 100 by GO + 12 = they shoot an aircraft of their own side."""
        t = _base(m, GO + 14, owner=True)
        t.scripts.append(_control(GO))
        _at(t, 'shoot', 2.0, [('NAMED_FORCE_ATTACK_NAMED', m.role(f'gun {k}').name, m.role("carrier").name) for k in (1, 2)])
        t.expect += [('归我', GO + 3, '==', 1), ('血', GO + 12, '<', 100)]
        return t


    def swap(m):
        """rewind_swap (the show version; round 49: the carrier stays on as the new one): ours at 1 s for CONTROL s;
        our two Multigunners, 100 south of it, ordered at 5 s to force-attack it (血 falling while 归我 1 = they shoot an
        aircraft of their own) and stopped at the swap; at 10 s NAMED_DAMAGE 99999 (ImmortalBody: 1 hp, the swap
        comes then). After it: 血 50 (the mission's top-up), 归我 1 to the end (ours at the swap: ours for good, the
        control's end at 16 s leaves it), 残骸 = presses of its wreck button (Rw Wrecks)."""
        car = m.role("carrier").name
        guns = [m.role(f'gun {k}').name for k in (1, 2)]
        t = Test()
        t.scripts.append(Script('Test - start', [], [('MAP_REVEAL_ALL_PERM', m.player('p1')),
                                                     ('SET_MILLISECOND_TIMER', 'Test Go', 0.01)]))
        t.scripts.append(_control(1.0))
        _at(t, 'shoot', 5.0, [('NAMED_FORCE_ATTACK_NAMED', g, car) for g in guns])
        _at(t, 'finish', 10.0, [('NAMED_DAMAGE', car, 99999)])
        t.scripts.append(Script('Test - hold fire', [('COUNTER', 'Rw Wrecks', 3, 1)], [('NAMED_STOP', g) for g in guns]))
        counted('Test Health', '血', t, health=car)
        counted('Test Ours', '归我', t, owner=car)
        t.counters.append(('Rw Wrecks', '残骸'))
        # bench CampRwSSwap_mcp_1111_163719 (round 46): 98 -> 90 while ours (s1-s10: our guns shoot their own aircraft)
        t.expect += [('归我', 4, '==', 1, 10), ('血', 8, '<', 98, 9), ('残骸', 12, '==', 1), ('血', 12, '>=', 45),
                     ('血', 12, '<', 56), ('归我', 20, '==', 1)]
        t.bench = [('bench_watch', dict(seconds=26, every=1, sheet=False, lines=4))]
        return t


    def wreck(m):
        """rewind_swap, the swap's look: swap's run plus 残骸数 = the wrecks of ours on the map (the OCL really made one:
        it is dropped by our carrier, so it is ours; it dies units/rewind.py WRECK_LIFE s later). The camera is on the
        carrier, so the frames from the swap on show the enlarged time-warp FX, the crash, and whether the wreck faces
        the way the carrier does."""
        t = swap(m)
        counted('Test Wrecks', '残骸数', t, template=m.role("wreck").template)
        t.expect.append(('残骸数', 9, 'ever>=', 1, 14))
        # round 53, the carrier dressed (280 across): at the default zoom it filled the screen and its white hull behind
        # the counters misread them (CampRwSWreck_mcp_1111_200658); zoomed out, and frames 4 a second round the swap
        # (the time-warp ball lives 10-15 frames, a second's frame missed it)
        t.scripts.append(Script('Test - zoom out', [], [('ZOOM_CAMERA', ZOOM_OUT, 0.1, 0.0, 0.0)]))
        # one watch through the swap: a second one started 3 s late (_201029: s9.2 then s12.4)
        t.bench = [('bench_watch', dict(seconds=14, every=0.25, sheet=False, lines=4)),
                   ('bench_watch', dict(seconds=13, every=1, sheet=False, lines=4))]
        return t


    ZOOM_OUT = 1.4      # ZOOM_CAMERA's first argument: > 1 farther (_201029: 2.0 showed the map's black edge)
    REVIVE_ZOOM = 1.7   # revive: the wreck's spiral in sight


    def revive(m):
        """rewind_swap, round 58 (user 11-11: revive in place, crash like the Giga Fortress): swap's run (ours at 1 s,
        our guns shoot it from 5 s, fatal at 10 s). Counters 血; 隐身 = 1 while the carrier carries the mission's hidden
        model condition (asked of the mission: rw.HIDDEN via the carrier's unit, never a waypoint); 原处 = the carrier
        within 150 of where it was placed (it never moves); 残骸数 = the crashing wrecks on the map (alive CRASH_LIFE s).
        Frames 2 a second for the coordinator's three (crashing, the warp, revived)."""
        car = m.role("carrier").name
        hidden = next(u for u in m.units if u.id == m.role("carrier").template).params['hidden']
        guns = [m.role(f'gun {k}').name for k in (1, 2)]
        t = Test()
        t.scripts.append(Script('Test - start', [], [('MAP_REVEAL_ALL_PERM', m.player('p1')),
                                                     ('SET_MILLISECOND_TIMER', 'Test Go', 0.01),
                                                     ('ZOOM_CAMERA', REVIVE_ZOOM, 0.1, 0.0, 0.0)]))
        t.scripts.append(_control(1.0))
        _at(t, 'shoot', 5.0, [('NAMED_FORCE_ATTACK_NAMED', g, car) for g in guns])
        _at(t, 'finish', 10.0, [('NAMED_DAMAGE', car, 99999)])
        t.scripts.append(Script('Test - hold fire', [('COUNTER', 'Rw Wrecks', 3, 1)], [('NAMED_STOP', g) for g in guns]))
        counted('Test Health', '血', t, health=car)
        t.counters.append(('Test Hidden', '隐身'))
        t.scripts += [Script('Test - count hidden zero', [], [('SET_COUNTER', 'Test Hidden', 0)], once=False),
                      Script('Test - count hidden', [('UNIT_HAS_MODELCONDITION', car, hidden)],
                             [('SET_COUNTER', 'Test Hidden', 1)], once=False)]
        t.areas['Test Start'] = square(*m.waypoints[m.mark('start')], 150.0)
        counted('Test Home', '原处', t, named=car, area='Test Start')
        counted('Test Wrecks', '残骸数', t, template=m.role("wreck").template)
        # the swap's second varies with our guns' shots (s8-s10 in _211904 / _212455 / _212823)
        t.expect += [('隐身', 6, '==', 0, 7), ('残骸数', 7, 'ever>=', 1, 12), ('隐身', 11, '==', 1, 14),
                     ('隐身', 19, '==', 0, 23), ('原处', 8, '==', 1, 23), ('血', 19, '>=', 45, 23)]
        t.bench = [('bench_watch', dict(seconds=24, every=0.25, sheet=False, lines=4))]
        return t


    _ALL = {'fire': fire,'auto': auto, 'still': still, 'own': own, 'ctrl': ctrl, 'trick': trick}
    CHECKS = {'rewind': _ALL, 'rewind_imm': _ALL, 'rewind_swap': {'swap': swap, 'wreck': wreck, 'revive': revive}}
    return dict(CHECKS=CHECKS)


def engine_storestate_e():
    """E223: StoreCurrentStateUpdate -- how far back Tanya's time belt can take her.

    Retail: AlliedCommandoTech1's ReconstituteStateSpecialAbility (SpecialPower_TimeBelt, TimeStepsBack 10 s) reads
    the states her StoreCurrentStateUpdate keeps (SleepTime 0.25 s, MaxTime 5 s): the belt asks for twice what is kept.

    Three clones of Tanya, one per lane: On as retail, Long with MaxTime 12 s, Short with MaxTime 2 s (with the store
    taken out the game crashed a few seconds in, twice: the belt's UpdateModuleId names it). Her health is the clock: from
    GO she loses 15 (of 300) every second for 12 s, at PRESS (GO + 12.5 s) the script presses her belt.
    Prediction: the oldest kept state caps the jump -- On back to GO + 7.5 s's health (about 65 %), Long to GO + 2.5 s's
    (about 90 %), Short to GO + 10.5 s's (about 50 %). Counters: each arm's health in percent.
    """
    import re
    from pathlib import Path

    import labpaths
    from maps import probe_range
    from parts import Mission, Script, Test, Unit, counted

    GO, STEPS, HIT = 15 * 25, 12, 15     # frames (run 1: GO 30, the watch's first frame came after the press, s14.9)
    PRESS, END = GO + 15 * STEPS + 7, GO + 15 * 20
    ARMS = {'On': ('base', None), 'Long': ('high', '12s'), 'Short': ('order', '2s')}    # arm: (lane, MaxTime: None retail)
    HOST, TAG = 'AlliedCommandoTech1', 'StoreCurrentStateUpdate'
    BELT = 'Command_TimeBeltSpecialPower'


    def mission():
        m = Mission(name='CampStoreSt', map=probe_range, units=[])
        source = (Path(labpaths.SDK3) / 'SageXML/Allied/Units' / (HOST + '.xml')).read_text(encoding='utf-8-sig')
        for arm, (lane, keep) in ARMS.items():
            ident = 'CNVE223' + arm
            xml = source.replace(f'id="{HOST}"', f'id="{ident}"', 1)
            store = re.compile(rf'\s*<{TAG}\s+id="ModuleTag_StoreCurrentStateUpdate".*?/>', re.S)
            if keep is not None:
                xml, n = store.subn(f'\n\t\t\t<{TAG} id="ModuleTag_StoreCurrentStateUpdate" SleepTime="0.25s" '
                                    f'MaxTime="{keep}"/>', xml)
                assert n == 1, (arm, n)
            m.units.append(Unit(ident, xml))
            m.put(ident, lane + ' gun', side='p1', role=arm, name='E223 ' + arm, angle=1.570796)
        return m


    def check(m, bleed=False):
        """bleed: 1 hit point a frame from GO to PRESS instead of the hits (the health then says the frame to 3)."""
        t = Test()
        for arm in ARMS:
            counted('E223' + arm, {'On': '原版', 'Long': '记12秒', 'Short': '记2秒'}[arm], t, health=m.role(arm).name)
        t.scripts += [Script('Test - clock', [('COUNTER', 'E223Frame', 0, END)],
                             [('INCREMENT_COUNTER', 1, 'E223Frame')], once=False),
                      Script('Test - reveal', [], [('MAP_REVEAL_ALL_PERM', m.player('p1'))])]
        names = [m.role(arm).name for arm in ARMS]
        for k in range(1, STEPS + 1) if not bleed else ():
            t.scripts.append(Script(f'Test - hit {k}', [('COUNTER', 'E223Frame', 2, GO + 15 * k)],
                                    [('NAMED_DAMAGE', n, HIT) for n in names]))
        if bleed:
            t.scripts.append(Script('Test - bleed', [('COUNTER', 'E223Frame', 3, GO), ('COUNTER', 'E223Frame', 0, PRESS)],
                                    [('NAMED_DAMAGE', n, 1) for n in names], once=False))
        t.scripts.append(Script('Test - press', [('COUNTER', 'E223Frame', 2, PRESS)],
                                [('NAMED_USE_COMMANDBUTTON_ABILITY', n, BELT) for n in names]))
        t.expect = [('原版', 0, 'ever>', 0)]
        t.bench = [('bench_camera', dict(x=2300, y=500, look=False)),
                   ('bench_watch', dict(seconds=END // 15 + 10, every=1, sheet=False, lines=3))]
        return t


    MISSION = {'engine_storest_e': mission}
    CHECKS = {'engine_storest_e': {'a': check, 'b': lambda m: check(m, bleed=True)}}
    return dict(MISSION=MISSION, CHECKS=CHECKS)


def engine_topple():
    """Engine unit test: ToppleUpdate -- do the crushable props (lanterns, street lamps, fences, trees) fall when a vehicle
    drives through them, and who can topple them (engine line C round 10; docs/engine/crush.md). Retail data (SDK SageXML):
    OK_Lantern01 / SA_Fence09 inherit BaseSimulatedProp (prop body, CrusherInfo CrushableLevel 0, KindOf CRUSHABLE_OBSTACLE
    ...) with a topple module `KillWhenStartToppled=true` (ToppleFX FX_WoodCrush / FX_StreetLampCrush); trees (CS_Tree01,
    BaseTree) have `KillWhenToppled=true` and a SlowDeath (SinkDelay 2 s, DestructionDelay 4 s). CrusherLevel of a Hammer is
    20, of an Apocalypse 30, of a conscript 0. Questions: does the Hammer drive straight through (reach its goal) or go
    round / stop; is the prop dead (NAMED_NOT_DESTROYED false) or dying (NAMED_DYING) afterwards, and when; can a conscript
    (level 0, not strictly above the prop's 0) topple one; does the simulator's rule "a crusher strictly above the crushable
    level kills it" (locomotion.crush) apply to a prop at all.

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
    return dict(MISSION=MISSION, CHECKS=CHECKS)


BENCHES = (
    engine_crash_fall, engine_crush, engine_drain, engine_immortal, engine_invuln,
    engine_highlander, engine_kill, engine_levelup, engine_life, engine_managerbody, engine_maxhealth,
    engine_playerkill, engine_propbody, engine_rewind, engine_storestate_e, engine_topple,
)
