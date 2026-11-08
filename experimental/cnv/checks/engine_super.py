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


CHECKS = {'engine_super': {w: (lambda m, w=w: super_test(m, w)) for w in 'pqijvw'}}
