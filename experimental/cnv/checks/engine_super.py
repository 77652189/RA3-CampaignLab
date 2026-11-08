"""Engine probe: two superweapons cast by script (missions/super_bench.py; engine_power showed a scripted fire is counted
although the power is not ready).

Counters (four lines each variant), all from the cast on: 帧数 = frames since the cast order (cast at frame 75 after Go).
  p  proton collider: NAMED_FIRE_SPECIAL_POWER_AT_WAYPOINT SpecialPowerParticleCannon at the cast point; health % of the
     four targets (AlliedBaseDefense s1, 800 hp, NO_ATTACK) at 0 / 150 / 240 / 300 centre distance: 血0 血150 血240 血300
  q  same cast; 帧数, 满血帧 (frames target 0 has health 100 after the cast = frames to the first loss), 血0, 血300
  (r, the command-button cast, was not run: the script cast worked, and the build says 'Command_ParticleCannonSuperWeapon
     not published' for NAMED_USE_COMMANDBUTTON_ABILITY_AT_WAYPOINT; the code stays but the variant is not registered)
  i  iron curtain: cast at the spot where player tank 0 stands, tank 150 beside; both script-damaged NAMED_DAMAGE 48 at
     +1 s, +5 s, +19 s, +21 s after the cast: 帧数, 血0, 血150, 施放数

bench 2026-11-07 (rows every ~7 frames; target base defense MaxHealth 1000 in the SDK, tank 480 so 48 = 10 %):
  p CampSuperP  a scripted SpecialPowerParticleCannon at a waypoint DOES fire (power not ready). Health % 血0 / 血150 /
                血240 / 血300: first loss in the row at s8 (cast at ~s6): 44 / 50 / 61 / 100; one second later (s9)
                44 / 6 / 27 / 100; then 44 / 7 / 12 / 100 (s11: only 血240 moves, 29 -> 12). End 44 / 7 / 12 / 100.
                So several hits, ~1 s apart for 150 and 240 (240 has a third ~2 s later); target 300 untouched (100);
                the centre target lost least (56 %, one step only) -- not a taper from the centre (not chased).
  q CampSuperQ  frames from cast to first loss of target 0 = 56 (满血帧 56 = 3.7 s, +-1); 血0 100 -> 44 in one row,
                no second step in 25 s.
  r             not run (see above).
  i CampSuperI  cast counted (施放数 1) but NO protection seen: both tanks (centre 0 and 150) lost 10 % at every hit:
                +1 s 90 / 90, +5 s 80 / 80, +19 s 70 / 70, +21 s 60 / 60. Either the scripted cast made no curtain, or
                NAMED_DAMAGE bypasses invulnerability -- this probe cannot tell which; a control (player-click cast,
                or enemy fire on a curtained tank) is needed. The effect object is not counted.
  j CampSuperJ  (iron curtain control: player tanks 0 / 150 NO_ATTACK, enemy s1 tanks 200 behind each, released 15
                frames after the cast; counters 帧数 血0 血150 施放数.) The scripted cast DOES make a curtain: both
                tanks stay 100 % from the cast until frame 354 (23.6 s), then 86 at 362, 73 at 391, 60 at 422, 47 at
                452, 34 at 483 (~13 % per ~30 frames = enemy fire) -- identical for 0 and 150. So protection lasts
                ~355-360 frames (~23.7 s; fits modifier 20 s + effect lifetime 3 s) and the aura covers a tank 150 away
                (no unprotected control in range; radius >= 150, XML said 100). Caveat: no far control tank, so that
                the enemy was shooting during the first 23 s is inferred (equal start of damage on both, evenly
                spaced steps), not seen. Variant i's loss under NAMED_DAMAGE thus means NAMED_DAMAGE bypasses the curtain.
  v CampSuperV  vacuum imploder (SovietSuperWeaponAdvanced, SpecialPowerVacuumBomb, in
                contract.RETAIL_POWERS), cast at 'Test
                Vacuum Spot', enemy AlliedBaseDefense NO_ATTACK; counters 满血帧 血0 血150 血280. 满血帧 = 62 (4.1 s):
                first loss of the centre target 62 frames after the cast (the 4 s seed). Health % (rows ~7 frames):
                first row after (s8) 86 / 90 / 94; then 73 / 81 / 89, 52 / 67 / 80, 39 / 57 / 75, 19 / 43 / 67,
                5 / 29 / 58, 5 / 20 / 53, 5 / 6 / 45, ... end 5 / 1 / 1 (血0 / 血150 / 血280; reached ~s11 / s12 / s15,
                the cast at ~s6.2 so the whole effect ~9 s). Loss is gradual (~1 % to 14 % per row), not a few steps.
  w CampSuperW  same cast, counters 满血帧 血0 血280 血350: 62; 血0 5, 血280 1 as in v; 血350 stays 100 for the whole run
                (outside the radius 300: not hit, not pulled). Neither target dies completely except 150 / 280 at 1 %
                (centre stops at 5 %), probably the taper floor.

bench 2026-11-07 round 2 (Sonnet probe; more_test below; XML: iron curtain aura Range 100, effect 3 s, modifier 20 s;
nanoswarm ring 200, one shot, IN_STASIS 20 s; Psionic Decimator = SpecialPowerTelekineticProjectorDevice on
JapanSuperWeaponAdvanced, effect 4 s then TelekineticExplosion Damage 2000 Radius 300 taper 500; chronosphere: the script
actions NAMED_/PLAYER_FIRE_SPECIAL_POWER_AT_WAYPOINT take ONE waypoint, so source + destination cannot be given: not tested).
Tanks / targets stand at the given distance from the cast spot; counters 帧数 = frames since the cast.
  k CampSuperK  curtain, tanks 150 / 200 / 250 (foes released 15 frames after the cast): all three stay 100 until frame 354,
                then 86 at 360, 73 at 391, 60 at 422, 47 at 452, 34 at 483 -- identical. No control in this run.
  l CampSuperL  tanks 350 / 450 / 600: the same, 100 until 354, then identical steps. Protected out to 600?!
  m CampSuperM  control: the same cast 695 / 1010 / 1389 from the tanks (cast at 'Test Proton Spot'): 450 and 600 lose
                health from frame ~28 (86 at 37, ... 8 % at 210): the foes do fire; but tank 350 (695 from the cast) stays
                100 until 358 -- like a protected one.
  o CampSuperO  cast at 'Test Vacuum Spot', tanks 350 / 250 / 150 at 782 / 832 / 890: 250 and 150 lose health from frame ~28
                (to 8 %), 350 stays 100 until 361.
                重跑 2026-11-07（挪真空点后）：只有 150 早挨打（86 在帧 32，60 在 92，34 在 149，21 在 181，8 在 211 后不动）；
                250 和 350 都保护到帧 361（86），之后同步降（361 86 / 391 73 / 419 60 / 484 34）。与旧读数不一致：
                250 不再早挨打（旧读数 250 和 150 都从帧 ~28 掉到 8 %）。挪后离施放点 350 / 250 / 150 = 770 / 807 / 872：
                807 保护、872 和旧的 832 不保护 -> 中心距减坦克半径 23.3 在 800 内（sim.CURTAIN 照此改，INFERRED）。
  s CampSuperS  same cast, tanks 450 / 600 / 250 at 540 / 707 / 832: ALL stay 100 until 354-475 (450: 86 at 361, 600: 86 at
                354, 250: 100 until 475). So tank 250 (832) was shot early in o but not in s: the protection radius is NOT
                a clean function of distance in these runs (or the foes differ: tank 350 is always hit only at ~358 -- its foe
                stands 211 from the player's yard and may shoot that first). Radius measured: protected at 600-707, hurt at
                832 (o) but protected at 832 (s): unresolved, between ~700 and ~900, far above the XML's 100.
  n CampSuperN  nanoswarm, tanks 0 / 150 / 250 (foes start 300 / 335 / 450 out, NAMED_DAMAGE 48 at +60 and +150 frames):
                tanks 0 and 150 (inside ring 200) take NO fire damage in 497 frames; their health goes 100 -> 90 at frame 65
                and 90 -> 80 at ~157 = only the two NAMED_DAMAGE hits (NAMED_DAMAGE goes through the stasis). Tank 250
                (outside) is shot from frame ~27: 86, 73 (+hit 63), 50, 37, 24, 14, 1 % at 180 (hit at 150 -> 14).
                Protection lasts at least 497 frames (>> 300 = 20 s; no foe damage either after the stasis ended, the
                foes never approached; the end of the stasis is therefore not seen).
  d CampSuperD  Psionic Decimator at 'Test Psi Spot', 1000-hp defenses at 0 / 150 / 250: 满血帧 61 (first loss 61 frames
                after the cast), then 血 stays 100 for 0 / 150 / 250 -- a dead object's health counter freezes, so all
                three died within one row (~7 frames) of frame 61: one hit, not gradual.
  e CampSuperE  same, counters 满血帧 / 满250 / 满350 (frames still at 100) / 血250: 61 / 61 / keeps counting (528 at the
                end) / 100. So 0 and 250 are destroyed at frame ~61, 350 (outside radius 300) untouched.
  c CampSuperC  proton collider cooldown (countdown 0 at Go makes it ready, as engine_power): 前就绪 74 (ready every frame
                before the cast at 75); cast; 后就绪 0 up to 5445 frames after the cast (XML ReloadTime 360 s = 5400 frames
                at 15/s): NOT ready again within that time.

bench 2026-11-07 round 3 (Sonnet probe; checks f / g / h / a; mission 'Test Radius *' spots; frame counter in rows of ~10 s):
  f CampSuperF  c to ~8500 frames (counters 帧数 缺电帧 后就绪 施放数). 缺电帧 stays 0 (the yard + plant never ran short, so no
                frozen cooldown). Ready again from frame 5550 after the cast (370 s; 后就绪 122 at 帧数 5672, 256 at 5806, 407 at
                5957 ... all give 5550, +-2): XML ReloadTime 5400 + ~150 frames (10 s; the cast's own delay or charge). It stays
                ready afterwards (counts every frame to the end, 2972 at 帧数 8522).
  g CampSuperG  iron curtain radius, a foe ordered (NAMED_ATTACK_NAMED) at its own tank 15 frames after the cast, nothing else
                near: 满100 / 满300 / 满500 / 满800 = 353 / 357 / 351 / 354 (the curtain's end, as j) -- all four protected.
  h CampSuperH  tanks 1200 / 1600 / 2000 (spot (2300, 2300)): 满 = 20 / 21 / 23 -- hit at once (the foes do fire), NOT protected.
                2400 (south-east diagonal) counter garbled (7 / 25 / 77 flicker), ignore.
  a CampSuperA  tanks 850 / 950 / 1050 / 1150 (same spot as h): 满 = 20 / 23 / 23 / 25 -- all hit at once, none protected.
                2026-11-08, the spot moved 50 east off the trees (test_maps scenery): 20 / never / 23 / 25 -- the 950 tank
                is not hit at all (also with the spot 40 east): its foe, not the curtain (950 is past 850), so not a
                radius reading; h (same spot) still reads 20 / 24 / 23 / 25.
  Conclusion: the curtain's radius is between 800 (protected) and 850 (not): ~800+, far above the XML Range 100. The earlier
  k / l / m / o / s contradiction (832 once hit, once not) came from the foes' own target choice (they shot buildings), not the
  radius; with one foe forced at each tank the line is clean. Not measured: the exact value in 800-850.
"""
from parts import Script, Test

CAST_FRAME, DMG = 75, 48
HITS = (15, 75, 285, 315)           # frames after the cast: +1, +5, +19, +21 s
RUN = {'p': 25.0, 'q': 25.0, 'r': 25.0, 'i': 30.0, 'j': 28.0, 'v': 30.0, 'w': 30.0}
DIST = (0, 150, 240, 300)
VDIST = (0, 150, 280, 350)


def super_test(m, which='p'):
    t = Test()
    p1 = m.player('p1')
    iron = which in 'ij'
    vac = which in 'vw'
    power = {'i': 'SpecialPowerIronCurtain', 'j': 'SpecialPowerIronCurtain', 'v': 'SpecialPowerVacuumBomb',
             'w': 'SpecialPowerVacuumBomb'}.get(which, 'SpecialPowerParticleCannon')
    holder = m.role('vacuum' if vac else 'curtain' if iron else 'collider').name
    spot = 'Test Vacuum Spot' if vac else 'Test Curtain Spot' if iron else 'Test Proton Spot'
    if vac:
        keep = {'vacuum'} | {f'vtarget {d}' for d in VDIST}
    elif iron:
        keep = {'curtain', 'tank 0', 'tank 150'}
        if which == 'j':
            keep |= {'foe 0', 'foe 150'}
    else:
        keep = {'collider'} | {f'target {d}' for d in DIST}
    allroles = (['collider', 'curtain', 'vacuum'] + [f'target {d}' for d in DIST] + ['tank 0', 'tank 150']
                + [f'vtarget {d}' for d in VDIST] + ['foe 0', 'foe 150'])
    delete = [m.role(r).name for r in allroles if r not in keep]
    start = [('MAP_REVEAL_ALL_PERM', p1), ('SET_MILLISECOND_TIMER', 'Test Go', 1.0)]
    if iron:
        start += [('UNIT_CHANGE_OBJECT_STATUS', m.role(f'tank {d}').name, 'NO_ATTACK', 1) for d in (0, 150)]
    if which == 'j':
        start += [('UNIT_CHANGE_OBJECT_STATUS', m.role(f'foe {d}').name, 'NO_ATTACK', 1) for d in (0, 150)]
    if vac:
        start += [('UNIT_CHANGE_OBJECT_STATUS', m.role(f'vtarget {d}').name, 'NO_ATTACK', 1) for d in VDIST]
    if not iron and not vac:
        start += [('UNIT_CHANGE_OBJECT_STATUS', m.role(f'target {d}').name, 'NO_ATTACK', 1) for d in DIST]
    start += [('NAMED_DELETE', n) for n in delete]
    t.scripts.append(Script('Test - start', [], start))
    t.scripts.append(Script('Test - go', [('TIMER_EXPIRED', 'Test Go')], [('SET_FLAG', 'Test Going', 1)]))
    going = ('FLAG', 'Test Going', 1)
    t.scripts.append(Script('Test - tick', [going], [('INCREMENT_COUNTER', 1, 'CNV_Super_Tick')], once=False))
    if which == 'r':
        cast = [('NAMED_USE_COMMANDBUTTON_ABILITY_AT_WAYPOINT', holder, 'Command_ParticleCannonSuperWeapon', spot)]
    else:
        cast = [('NAMED_FIRE_SPECIAL_POWER_AT_WAYPOINT', holder, power, spot)]
    t.scripts.append(Script('Test - cast', [going, ('COUNTER', 'CNV_Super_Tick', 2, CAST_FRAME)],
                            cast + [('SET_FLAG', 'Test Cast', 1)]))
    cast_on = ('FLAG', 'Test Cast', 1)
    if which in 'qij':
        t.counters.append(('CNV_Super_Frames', '帧数'))
    t.scripts.append(Script('Test - frames', [cast_on], [('INCREMENT_COUNTER', 1, 'CNV_Super_Frames')], once=False))

    def health(name, label, ident):
        t.counters.append((f'CNV_Super_{ident}', label))
        t.scripts.append(Script(f'Test - health {ident}', [cast_on],
                                [('SET_UNIT_HEALTH_PERCENTAGE_TO_COUNTER', name, f'CNV_Super_{ident}')], once=False))
    if which == 'j':
        for d in (0, 150):
            health(m.role(f'tank {d}').name, f'血{d}', f'T{d}')
        t.scripts.append(Script('Test - foes fire', [cast_on, ('COUNTER', 'CNV_Super_Frames', 2, 15)],
                                [('UNIT_CHANGE_OBJECT_STATUS', m.role(f'foe {d}').name, 'NO_ATTACK', 0)
                                 for d in (0, 150)]))
        t.counters.append(('CNV_Super_Cast', '施放数'))
        t.scripts.append(Script('Test - cast seen', [going, ('PLAYER_TRIGGERED_SPECIAL_POWER', p1, power)],
                                [('INCREMENT_COUNTER', 1, 'CNV_Super_Cast')], once=False))
    elif which == 'i':
        for d in (0, 150):
            health(m.role(f'tank {d}').name, f'血{d}', f'T{d}')
        for k, h in enumerate(HITS):
            t.scripts.append(Script(f'Test - hit {k}', [cast_on, ('COUNTER', 'CNV_Super_Frames', 2, h)],
                                    [('NAMED_DAMAGE', m.role(f'tank {d}').name, DMG) for d in (0, 150)]))
        t.counters.append(('CNV_Super_Cast', '施放数'))
        t.scripts.append(Script('Test - cast seen', [going, ('PLAYER_TRIGGERED_SPECIAL_POWER', p1, power)],
                                [('INCREMENT_COUNTER', 1, 'CNV_Super_Cast')], once=False))
    elif vac:
        t.counters.append(('CNV_Super_Full', '满血帧'))
        t.scripts.append(Script('Test - full', [cast_on, ('UNIT_HEALTH', m.role('vtarget 0').name, 3, 100)],
                                [('INCREMENT_COUNTER', 1, 'CNV_Super_Full')], once=False))
        for d in ((0, 150, 280) if which == 'v' else (0, 280, 350)):
            health(m.role(f'vtarget {d}').name, f'血{d}', f'V{d}')
    elif which == 'q':
        t.counters.append(('CNV_Super_Full', '满血帧'))
        t.scripts.append(Script('Test - full', [cast_on, ('UNIT_HEALTH', m.role('target 0').name, 3, 100)],
                                [('INCREMENT_COUNTER', 1, 'CNV_Super_Full')], once=False))
        health(m.role('target 0').name, '血0', 'H0')
        health(m.role('target 300').name, '血300', 'H300')
    else:
        for d in DIST:
            health(m.role(f'target {d}').name, f'血{d}', f'H{d}')
    t.expect = []
    t.bench = [('bench_watch', dict(every=0.5, sheet=False, lines=len(t.counters), seconds=RUN[which] + 8.0))]
    return t


# k / n / d / e / c (bench 2026-11-07, round 2): the aura radii of the curtain and the nanoswarm, the Psionic Decimator,
# the proton collider's cooldown. (Four counters at most: k leaves out j's centre tank.)
RUN |= {'k': 28.0, 'l': 28.0, 'm': 28.0, 'o': 28.0, 's': 28.0, 'n': 28.0, 'd': 30.0, 'e': 30.0, 'c': 380.0, 'f': 530.0, 'g': 28.0, 'h': 28.0, 'a': 28.0}
NANO_HITS = (60, 150)               # NAMED_DAMAGE on the nanoswarm's tanks, frames after the cast
# variant: (power, holder role, spot, kept roles, health roles shown, foes released 15 frames after the cast)
VARIANTS = {
    'k': ('SpecialPowerIronCurtain', 'curtain', 'Test Curtain Spot',
          ['curtain', 'tank 150', 'tank 200', 'tank 250', 'foe 150', 'foe 200', 'foe 250'],
          ['tank 150', 'tank 200', 'tank 250'], ['foe 150', 'foe 200', 'foe 250']),
    'l': ('SpecialPowerIronCurtain', 'curtain', 'Test Curtain Spot',
          ['curtain', 'tank 350', 'tank 450', 'tank 600', 'foe 350', 'foe 450', 'foe 600'],
          ['tank 350', 'tank 450', 'tank 600'], ['foe 350', 'foe 450', 'foe 600']),
    'm': ('SpecialPowerIronCurtain', 'curtain', 'Test Proton Spot',        # control of l: the cast ~900 away from the tanks
          ['curtain', 'tank 350', 'tank 450', 'tank 600', 'foe 350', 'foe 450', 'foe 600'],
          ['tank 350', 'tank 450', 'tank 600'], ['foe 350', 'foe 450', 'foe 600']),
    'o': ('SpecialPowerIronCurtain', 'curtain', 'Test Vacuum Spot',        # tanks 770 / 807 / 872 from the cast (since the spot moved)
          ['curtain', 'tank 350', 'tank 250', 'tank 150', 'foe 350', 'foe 250', 'foe 150'],
          ['tank 350', 'tank 250', 'tank 150'], ['foe 350', 'foe 250', 'foe 150']),
    's': ('SpecialPowerIronCurtain', 'curtain', 'Test Vacuum Spot',        # tanks 540 / 707 / 832 from the cast
          ['curtain', 'tank 450', 'tank 600', 'tank 250', 'foe 450', 'foe 600', 'foe 250'],
          ['tank 450', 'tank 600', 'tank 250'], ['foe 450', 'foe 600', 'foe 250']),
    'n': ('SpecialPowerNanoSwarmHive', 'nano', 'Test Curtain Spot',
          ['nano', 'tank 0', 'tank 150', 'tank 250', 'nfoe 0', 'nfoe 150', 'foe 250'],
          ['tank 0', 'tank 150', 'tank 250'], ['nfoe 0', 'nfoe 150', 'foe 250']),
    'd': ('SpecialPowerTelekineticProjectorDevice', 'psi', 'Test Psi Spot',
          ['psi', 'dtarget 0', 'dtarget 150', 'dtarget 250'], ['dtarget 0', 'dtarget 150', 'dtarget 250'], []),
    'e': ('SpecialPowerTelekineticProjectorDevice', 'psi', 'Test Psi Spot',
          ['psi', 'dtarget 0', 'dtarget 250', 'dtarget 350'], ['dtarget 250'], []),      # + 满250 满350 below (d: a dead
          # target's 血 stays at its last value, so e counts the frames each target is still at 100)
    'c': ('SpecialPowerParticleCannon', 'collider', 'Test Proton Spot', ['collider'], [], []),
    'f': ('SpecialPowerParticleCannon', 'collider', 'Test Proton Spot', ['collider'], [], []),     # c to 7500 frames
    'g': ('SpecialPowerIronCurtain', 'curtain', 'Test Radius Spot', ['curtain'] + [f'{k} {d}' for d in (100, 300, 500, 800)
          for k in ('rtank', 'rfoe')], [], []),     # one foe per tank, ordered at it 15 frames after the cast
    'a': ('SpecialPowerIronCurtain', 'curtain', 'Test Radius Edge', ['curtain'] + [f'{k} {d}' for d in (850, 950, 1050, 1150)
          for k in ('rtank', 'rfoe')], [], []),
    'h': ('SpecialPowerIronCurtain', 'curtain', 'Test Radius Far', ['curtain'] + [f'{k} {d}' for d in (1200, 1600, 2000, 2400)
          for k in ('rtank', 'rfoe')], [], []),
}
RADIUS = {'a': (850, 950, 1050, 1150), 'g': (100, 300, 500, 800), 'h': (1200, 1600, 2000, 2400)}
ALLROLES = (['collider', 'curtain', 'vacuum', 'nano', 'psi'] + [f'target {d}' for d in DIST]
            + [f'vtarget {d}' for d in VDIST] + [f'dtarget {d}' for d in (0, 150, 250, 350)]
            + [f'tank {d}' for d in (0, 150, 200, 250, 350, 450, 600)]
            + [f'foe {d}' for d in (0, 150, 200, 250, 350, 450, 600)] + ['nfoe 0', 'nfoe 150']
            + [f'{k} {d}' for d in (100, 300, 500, 800, 850, 950, 1050, 1150, 1200, 1600, 2000, 2400) for k in ('rtank', 'rfoe')])


def more_test(m, which):
    t = Test()
    p1 = m.player('p1')
    power, holder_role, spot, keep, shown, released = VARIANTS[which]
    holder = m.role(holder_role).name
    delete = [m.role(r).name for r in ALLROLES if r not in keep]
    start = [('MAP_REVEAL_ALL_PERM', p1), ('SET_MILLISECOND_TIMER', 'Test Go', 1.0)]
    start += [('UNIT_CHANGE_OBJECT_STATUS', m.role(r).name, 'NO_ATTACK', 1)
              for r in keep if r.startswith(('tank', 'dtarget', 'foe', 'nfoe', 'rtank', 'rfoe'))]
    start += [('NAMED_DELETE', n) for n in delete]
    if which in 'cf':
        start.append(('NAMED_SET_SPECIAL_POWER_COUNTDOWN', holder, power, 0))      # engine_power: 0 makes it ready
    t.scripts.append(Script('Test - start', [], start))
    t.scripts.append(Script('Test - go', [('TIMER_EXPIRED', 'Test Go')], [('SET_FLAG', 'Test Going', 1)]))
    going = ('FLAG', 'Test Going', 1)
    t.scripts.append(Script('Test - tick', [going], [('INCREMENT_COUNTER', 1, 'CNV_Super_Tick')], once=False))
    t.scripts.append(Script('Test - cast', [going, ('COUNTER', 'CNV_Super_Tick', 2, CAST_FRAME)],
                            [('NAMED_FIRE_SPECIAL_POWER_AT_WAYPOINT', holder, power, spot), ('SET_FLAG', 'Test Cast', 1)]))
    cast_on = ('FLAG', 'Test Cast', 1)
    if which in 'klmosncfgha':
        if which not in 'gha':       # g / h keep the four lines for the four tanks (the frame counter runs unshown)
            t.counters.append(('CNV_Super_Frames', '帧数'))
        t.scripts.append(Script('Test - frames', [cast_on], [('INCREMENT_COUNTER', 1, 'CNV_Super_Frames')], once=False))
    if which in 'de':
        t.counters.append(('CNV_Super_Full', '满血帧'))
        t.scripts.append(Script('Test - full', [cast_on, ('UNIT_HEALTH', m.role('dtarget 0').name, 3, 100)],
                                [('INCREMENT_COUNTER', 1, 'CNV_Super_Full')], once=False))
    if which == 'e':
        for d in (250, 350):
            t.counters.append((f'CNV_Super_Full{d}', f'满{d}'))
            t.scripts.append(Script(f'Test - full {d}', [cast_on, ('UNIT_HEALTH', m.role(f'dtarget {d}').name, 3, 100)],
                                    [('INCREMENT_COUNTER', 1, f'CNV_Super_Full{d}')], once=False))
    for r in shown:
        ident = r.replace(' ', '')
        t.counters.append((f'CNV_Super_{ident}', '血' + r.split()[1]))
        t.scripts.append(Script(f'Test - health {ident}', [cast_on],
                                [('SET_UNIT_HEALTH_PERCENTAGE_TO_COUNTER', m.role(r).name, f'CNV_Super_{ident}')],
                                once=False))
    if released:
        t.scripts.append(Script('Test - foes fire', [cast_on, ('COUNTER', 'CNV_Super_Frames', 2, 15)],
                                [('UNIT_CHANGE_OBJECT_STATUS', m.role(r).name, 'NO_ATTACK', 0) for r in released]))
    if which == 'n':
        for k, h in enumerate(NANO_HITS):
            t.scripts.append(Script(f'Test - hit {k}', [cast_on, ('COUNTER', 'CNV_Super_Frames', 2, h)],
                                    [('NAMED_DAMAGE', m.role(r).name, DMG) for r in shown]))
    if which in RADIUS:
        for d in RADIUS[which]:
            t.counters.append((f'CNV_Super_R{d}', f'满{d}'))
            t.scripts.append(Script(f'Test - full r{d}', [cast_on, ('UNIT_HEALTH', m.role(f'rtank {d}').name, 3, 100)],
                                    [('INCREMENT_COUNTER', 1, f'CNV_Super_R{d}')], once=False))
        t.scripts.append(Script('Test - foes aim', [cast_on, ('COUNTER', 'CNV_Super_Frames', 2, 15)],
                                [a for d in RADIUS[which] for a in (
                                    ('UNIT_CHANGE_OBJECT_STATUS', m.role(f'rfoe {d}').name, 'NO_ATTACK', 0),
                                    ('NAMED_ATTACK_NAMED', m.role(f'rfoe {d}').name, m.role(f'rtank {d}').name))]))
    if which in 'cf':
        ready = ('SKIRMISH_SPECIAL_POWER_READY', p1, power)
        if which == 'c':
            t.counters.append(('CNV_Super_Pre', '前就绪'))
            t.scripts.append(Script('Test - ready before', [going, ('COUNTER', 'CNV_Super_Tick', 0, CAST_FRAME), ready],
                                    [('INCREMENT_COUNTER', 1, 'CNV_Super_Pre')], once=False))
        else:       # f: frames without power (a deficit would freeze the cooldown)
            t.counters.append(('CNV_Super_Low', '缺电帧'))
            t.scripts.append(Script('Test - low power', [cast_on, ('PLAYER_EXCESS_POWER_COMPARE_VALUE', p1, 0, 0)],
                                    [('INCREMENT_COUNTER', 1, 'CNV_Super_Low')], once=False))
        t.counters.append(('CNV_Super_Post', '后就绪'))
        t.scripts.append(Script('Test - ready after', [cast_on, ready],
                                [('INCREMENT_COUNTER', 1, 'CNV_Super_Post')], once=False))
        t.counters.append(('CNV_Super_Cast', '施放数'))
        t.scripts.append(Script('Test - cast seen', [going, ('PLAYER_TRIGGERED_SPECIAL_POWER', p1, power)],
                                [('INCREMENT_COUNTER', 1, 'CNV_Super_Cast')], once=False))
    t.expect = []
    every = 10.0 if which in 'cf' else 0.5
    t.bench = [('bench_watch', dict(every=every, sheet=False, lines=len(t.counters), seconds=RUN[which] + 8.0))]
    return t


CHECKS = {'engine_super': {**{w: (lambda m, w=w: super_test(m, w)) for w in 'pqijvw'},
                          **{w: (lambda m, w=w: more_test(m, w)) for w in 'klmosndecfgha'}}}
