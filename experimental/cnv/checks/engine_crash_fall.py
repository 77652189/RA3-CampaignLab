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


MISSION = {'engine_crash_fall': mission}
CHECKS = {'engine_crash_fall': {'fall': check}}
