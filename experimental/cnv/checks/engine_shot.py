"""Engine unit test: how the shot reaches the target (ADR 0019 layer 3, batch two; docs/engine/weapons.md) -- an
instant weapon's WeaponSpeed, a straight-line shell (ProjectileUpdate StateMachine="StraightLineProjectile", the
tanks'), a laser (ActivateLaserNugget beside a DamageNugget) -- and the splash taper (DamageTaperOff).

Every shooter is engine_fire's V4 with both timers 0 (pre-attack and FiringDuration: copy I00) and no scatter; only
the nuggets and WeaponSpeed differ. The order comes at ORDER = 6 s, when every clip is loaded (the first clip is
reloaded from the frame the unit is made, at most 83 frames: docs/engine/weapons.md 0), so the first hit's frame
is one constant C plus the way to the target, the same on every lane:

  base     instant, WeaponSpeed 999999            C (engine_fire late's cells without a pre-attack)
  high     instant, WeaponSpeed SLOW              C + the 3D distance / (SLOW / 15)
  removed  retail's Hammer shell (MuzzleVelocity 50), its warhead one radius-0 DamageNugget of 500
  switch   a laser (retail's LockDown laser nugget) and a DamageNugget of 500, WeaponSpeed 999999

The target is engine_missile's 10 000-health Hammer FAR north (a hit is 5 %); counters as there: frames from the
order to the first hit + 1000 per percent lost.

splash (lane low, check splash; the lanes above are check way): one more I00 V4 whose nugget is Damage SPLASH_DAMAGE, Radius 100, DamageTaperOff 20; its target
NEAR north, three more of the same Hammers SPLASH_AT east of it (the last outside the radius). Counter per Hammer:
percent lost (1 per percent).

Bench 11-05 (round 30, docs/engine/weapons.md 2):

  way     instant 2, slow 2, shell 11, laser 2 frames after the order; every lane 5 % a hit. WeaponSpeed does not
          delay an instant weapon; the laser neither delays nor deals damage; the radius-0 shell hits its victim and
          lands 9 frames after the instant shot (the model: 11). C = 2 (engine_fire late agrees; the model: 1).
  splash  first shot: 0 / 40 / 80 / 120 east lose 20 / 17 / 9 / 0 %. The taper goes by the distance less the
          Hammer's bounding circle (40 and 80 fit it; by the bare distance 40 would lose 12 %), but the Hammer at
          120 -- beyond Radius by its centre, within it less the circle -- is spared (the model gives it 2 %).
          From the fourth shot on splash0 stops gaining and the others gain 9 each: not read (the Hammers pushed
          apart?); only the first shot is used.

shells (round 32; the order lane): four CNV_ShotReach -- the shell V4 with AttackRange SHELLS_REACH -- each at its
own Hammer SHELLS_AT north; counters as in way. Bench 11-05: 250 / 350 / 450 / 550 read 7 / 9 / 11 / 13 = 2 +
floor(d / 50): the distance alone, 1 / MuzzleVelocity a unit, no launch offset (the model before read 9 / 11 / 13 /
15; now Idle leaves at the launch and the move ending in the victim detonates, INFERRED collision).

The splash 120 Hammer (round 33): the radius takes by the shape (the default PartitionFilterTestType EXTENTS_3D: the
ball against the box), the taper by the circle; the Hammer faces south, its box 14 wide east, the edge 106 away.

Round 33 (counters: percent lost, a step counted once begun, so 6.25 shows as 7; only the first hit is read):

  armor   instant V4s of 2000 GUN / AUTO_CANNON / IMPACT / RADIATION at Hammers 250 north (front hits): 10 / 5 /
          15 / 1 = BaseTankArmor's 50 / 25 / 75 / 5 %.
  flank   4000 EXPLOSIVE from 0 / 40 / 90 / 180 degrees off the Hammer's facing (it faces south): 40 / 40 / 42 /
          44 -- Side 105 beyond 45 degrees, Rear 110 beyond 135, by the attacker's position.
  vet     retail V4s given 0 / 3600 / 7200 / 10800 points (ranks 1-4): 5 / 7 / 7 / 7 -- the veteran's DAMAGE_MULT
          125 stays at elite and heroic; the heroic's second rocket came sooner (RATE_OF_FIRE 120 %). A copy of the
          V4 with its own ExperienceLevelTemplates (linked) read 20 % at every level: copies do not get ranks so.
"""
import math
import os
import re

from maps import probe_range
from parts import Mission, Script, Test, Unit
from checks.engine_missile import FAR, LOST_MAX, SAGE, TARGET_ID, V4, V4_WEAPON, _sub1, target

ORDER, RUN = 6.0, 20.0
SLOW = 60.0                         # 4 a frame: FAR's ~450 takes ~113 frames
SPLASH_DAMAGE, SPLASH_RADIUS, SPLASH_TAPER = 2000.0, 100.0, 20.0
SPLASH_NEAR = 250.0
SPLASH_AT = (40.0, 80.0, 120.0)
SHELL = 'SovietAntiVehicleVehicleTech1TankProjectile'
SHELLS_AT = (250.0, 350.0, 450.0, 550.0)   # check shells: each shell's target this far north of its shooter
SHELLS_DX = (-600.0, -200.0, 200.0, 600.0)  # the shooters along the order lane, 400 apart (the lanes 1 500)
SHELLS_REACH = 800.0                       # past 550 (retail's 500 would drive the V4 nearer first)
DAMAGE = '<DamageNugget Damage="{d:.1f}" DamageType="EXPLOSIVE" DeathType="EXPLODED" Radius="{r:g}"{extra} />'
# check armor (round 33): one instant V4 per DamageType, ARMOR_DAMAGE a hit, each at its own Hammer ARMOR_AT north
# (the Hammer faces south, the map's default for s1: a front hit); retail's BaseTankArmor gives these percents
ARMOR_KINDS = (('GUN', 50), ('AUTO_CANNON', 25), ('IMPACT', 75), ('RADIATION', 5))
ARMOR_DAMAGE, ARMOR_AT, ARMOR_DX = 2000.0, 250.0, -500.0
# check flank: four EXPLOSIVE V4s of FLANK_DAMAGE, each at its own Hammer (at lane + FLANK_AT, facing south) from
# FLANK_REACH away at this many degrees off the Hammer's facing (BaseTankArmor Side 105, Rear 110)
FLANK_OFF = (0.0, 40.0, 90.0, 180.0)
FLANK_DAMAGE, FLANK_AT, FLANK_REACH = 4000.0, (500.0, 300.0), 250.0
SHORT = ORDER + 3.0                  # armor / flank: only the first hit (the next is >= 4.5 s later)
# check vet: four retail V4s (SovietAntiStructureVehicle: retail's ranks name it as their Target; a copy given its
# own ExperienceLevelTemplates read 20 % at every point level, round 33 -- the copy's levels did not take or the
# points did nothing, not told apart), given these points at the start (ranks 1-4 at 1 / 3600 / 7200 / 10800), each
# at its own Hammer; the first rocket lands ~108 frames after the order (engine_missile miss), 5 % at rank 1
VET, VET_DX, VET_POINTS, VET_RUN = 'SovietAntiStructureVehicle', 250.0, (0, 3600, 7200, 10800), ORDER + 9.0
LASER = ('<ActivateLaserNugget id="DefaultLaserNugget" Lifetime="0.1s" LaserId="1" />')


def _nuggets(*items):
    return '<Nuggets>\n\t\t\t' + '\n\t\t\t'.join(items) + '\n\t\t</Nuggets>'


def shot_v4(id, nuggets, speed=999999.0, files=None, extra='', what='', reach=None, scatter=0.0, reload=None):
    """Retail's V4 under `id`, its rocket weapon swapped for `id`Weapon: `nuggets`, WeaponSpeed `speed`, no scatter,
    pre-attack 0, FiringDuration 0; nothing else differs (ADR 0016 G5: the probe builds it). `extra`: more assets
    laid into the unit's file, `files`: {name: xml} of its own; `reach`: AttackRange instead of retail's 500;
    `scatter`: a ScatterRadius (engine_scatter); `reload`: ClipReloadTime seconds instead of retail's 4.5-5.5."""
    wid = id + 'Weapon'
    x = open(os.path.join(SAGE, 'Soviet', 'Units', V4 + '.xml'), encoding='utf-8').read()
    x = _sub1(x, f'id="{V4}"', f'id="{id}"')
    x = re.sub(rf'EditorName="{V4}"', f'EditorName="{id}"', x)
    x = _sub1(x, f'Template="{V4_WEAPON}"', f'Template="{wid}"')
    w = open(os.path.join(SAGE, 'GlobalData', 'Weapon.xml'), encoding='utf-8').read()
    s = re.search(rf'\t*<WeaponTemplate\s+id="{V4_WEAPON}".*?</WeaponTemplate>\n', w, re.S).group(0)
    s = _sub1(s, f'id="{V4_WEAPON}"', f'id="{wid}"')
    s = _sub1(s, 'inheritFrom="ScatterableWeapon"', '')
    s = _sub1(s, 'WeaponSpeed="200"', f'WeaponSpeed="{speed:g}"')
    if reach is not None:
        s = _sub1(s, 'AttackRange="500.0"', f'AttackRange="{reach:g}"')
    if scatter:
        s = _sub1(s, 'MinimumAttackRange=', f'ScatterRadius="{scatter:g}" MinimumAttackRange=')
    if reload is not None:
        s, k = re.subn(r'(<ClipReloadTime\s+MinSeconds=")4\.5s("\s+MaxSeconds=")5\.5s"', rf'\g<1>{reload:g}s\g<2>{reload:g}s"', s)
        assert k == 1, k
    s, k = re.subn(r'<Nuggets>.*?</Nuggets>', nuggets, s, flags=re.S)
    assert k == 1, k
    s, k = re.subn(r'\s*<ScatterRadiusVsType\s+Radius="0\.1">.*?</ScatterRadiusVsType>', '', s, flags=re.S)
    assert k == 1, k
    s = _sub1(s, 'MinSeconds=".5s"\n\t\t  MaxSeconds=".5s"', 'MinSeconds="0s"\n\t\t  MaxSeconds="0s"')
    s = _sub1(s, '<FiringDuration\n\t\t\tMinSeconds="1.0s"\n\t\t\tMaxSeconds="1.0s"',
              '<FiringDuration\n\t\t\tMinSeconds="0s"\n\t\t\tMaxSeconds="0s"')
    x = _sub1(x, '</AssetDeclaration>', s + extra + '</AssetDeclaration>')
    files = files or {}
    return Unit(id, x, files=files, also=list(files), link=[f'WeaponTemplate:{wid}'],
                names=dict(unit=id, weapon=wid), what=what, params=dict(speed=speed))


def shell_v4(id='CNV_ShotShell', reach=None, damage=500.0, what=None, **kw):
    """The V4 firing retail's Hammer shell (copied as `id`Projectile) with a warhead (`id`Warhead) of one radius-0
    DamageNugget of `damage` (500); `reach`: its AttackRange (retail 500); `kw`: shot_v4's scatter / reload."""
    proj, wh = id + 'Projectile', id + 'Warhead'
    p = open(os.path.join(SAGE, 'Soviet', 'Props', SHELL + '.xml'), encoding='utf-8').read()
    p = _sub1(p, f'id="{SHELL}"', f'id="{proj}"')
    p = _sub1(p, f'EditorName="{SHELL}"', f'EditorName="{proj}"')
    warhead = (f'\t<WeaponTemplate id="{wh}" ProjectileCollidesWith="ALLIES ENEMIES NEUTRAL STRUCTURES WALLS"\n'
               f'\t\tRadiusDamageAffects="ENEMIES" RequiredAntiMask="ANTI_WATER ANTI_GROUND ANTI_STRUCTURE">\n'
               f'\t\t{_nuggets(DAMAGE.format(d=damage, r=0, extra=""))}\n\t</WeaponTemplate>\n')
    nug = f'<ProjectileNugget WarheadTemplate="{wh}" ProjectileTemplate="{proj}" />'
    far = '' if reach is None else f'，射程 {reach:g}'
    u = shot_v4(id, _nuggets(nug), files={proj + '.xml': p}, extra=warhead, reach=reach, **kw,
                what=what or f'打锤子炮弹的 V4（探针）：直射弹（原版锤子炮弹），弹头半径 0、500 伤害，无预瞄、无开火持续、无散布{far}')
    u.names.update(projectile=proj, warhead=wh)
    return u


def units():
    one = DAMAGE.format(d=500.0, r=0, extra='')
    splash = DAMAGE.format(d=SPLASH_DAMAGE, r=SPLASH_RADIUS, extra=f' DamageTaperOff="{SPLASH_TAPER:g}"')
    return [
        shot_v4('CNV_ShotInstant', _nuggets(one), what='瞬发 V4（探针）：WeaponSpeed 999999，500 伤害，无预瞄、无开火持续、无散布'),
        shot_v4('CNV_ShotSlow', _nuggets(one), SLOW,
                what=f'慢速瞬发 V4（探针）：WeaponSpeed {SLOW:g}，500 伤害，无预瞄、无开火持续、无散布'),
        shell_v4(),
        shell_v4('CNV_ShotReach', SHELLS_REACH),
        shot_v4('CNV_ShotLaser', _nuggets(LASER, one),
                what='激光 V4（探针）：开激光光束 + 500 伤害，WeaponSpeed 999999，无预瞄、无开火持续、无散布'),
        shot_v4('CNV_ShotSplash', _nuggets(splash),
                what=f'溅射 V4（探针）：{SPLASH_DAMAGE:g} 伤害、半径 {SPLASH_RADIUS:g}、边缘衰减到 {SPLASH_TAPER:g}，'
                     '无预瞄、无开火持续、无散布'),
        *[shot_v4(_kind_id(k), _nuggets(_kind_nugget(k, ARMOR_DAMAGE)),
                  what=f'{k} 瞬发 V4（探针）：{ARMOR_DAMAGE:g} 伤害、伤害类型 {k}，无预瞄、无开火持续、无散布')
          for k, _ in ARMOR_KINDS],
        shot_v4('CNV_ShotFlank', _nuggets(DAMAGE.format(d=FLANK_DAMAGE, r=0, extra='')),
                what=f'侧击 V4（探针）：{FLANK_DAMAGE:g} 伤害（EXPLOSIVE），无预瞄、无开火持续、无散布'),
        target(),
    ]


def _kind_id(kind):
    return 'CNV_ShotKind' + ''.join(p.title() for p in kind.split('_'))


def _kind_nugget(kind, d):
    return f'<DamageNugget Damage="{d:.1f}" DamageType="{kind}" DeathType="EXPLODED" Radius="0" />'


LANES = {'base': 'CNV_ShotInstant', 'high': 'CNV_ShotSlow', 'removed': 'CNV_ShotShell', 'switch': 'CNV_ShotLaser'}
LABELS = {'base': 'instant', 'high': 'slow', 'removed': 'shell', 'switch': 'laser'}


def mission():
    m = Mission(name='CampShot', map=probe_range, units=units(), facts={})
    for lane, tpl in LANES.items():
        L, site = lane.title(), f'{lane} gun'
        m.put(tpl, site, side='p1', role=f'{lane} shooter', name=f'UNIT - CNV Shot {L} Shooter')
        m.put(TARGET_ID, site, 0, FAR, side='s1', role=f'{lane} target', name=f'UNIT - CNV Shot {L} Target')
    m.put('CNV_ShotSplash', 'low gun', side='p1', role='splash shooter', name='UNIT - CNV Shot Splash Shooter')
    for k, dx in enumerate((0.0,) + SPLASH_AT):
        m.put(TARGET_ID, 'low gun', dx, SPLASH_NEAR, side='s1', role=f'splash {dx:g}',
              name=f'UNIT - CNV Shot Splash {k}')
    for k, (dx, d) in enumerate(zip(SHELLS_DX, SHELLS_AT)):
        m.put('CNV_ShotReach', 'order gun', dx, 0, side='p1', role=f'shells {d:g} shooter',
              name=f'UNIT - CNV Shot Shells {k} Shooter')
        m.put(TARGET_ID, 'order gun', dx, d, side='s1', role=f'shells {d:g} target',
              name=f'UNIT - CNV Shot Shells {k} Target')
    for (kind, _), lane in zip(ARMOR_KINDS, LANES):
        m.put(_kind_id(kind), f'{lane} gun', ARMOR_DX, 0, side='p1', role=f'armor {kind} shooter',
              name=f'UNIT - CNV Shot Armor {kind} Shooter')
        m.put(TARGET_ID, f'{lane} gun', ARMOR_DX, ARMOR_AT, side='s1', role=f'armor {kind} target',
              name=f'UNIT - CNV Shot Armor {kind} Target')
    fx, fy = FLANK_AT
    for off, lane in zip(FLANK_OFF, LANES):
        a = math.radians(off)                       # the Hammer faces south: front is (0, -1)
        m.put('CNV_ShotFlank', f'{lane} gun', fx + FLANK_REACH * math.sin(a), fy - FLANK_REACH * math.cos(a),
              side='p1', role=f'flank {off:g} shooter', name=f'UNIT - CNV Shot Flank {off:g} Shooter',
              angle=math.atan2(math.cos(a), -math.sin(a)))  # facing its Hammer: no turn before the shot
        m.put(TARGET_ID, f'{lane} gun', fx, fy, side='s1', role=f'flank {off:g} target',
              name=f'UNIT - CNV Shot Flank {off:g} Target')
    for pts, lane in zip(VET_POINTS, LANES):
        m.put(VET, f'{lane} gun', VET_DX, 0, side='p1', role=f'vet {pts} shooter',
              name=f'UNIT - CNV Shot Vet {pts} Shooter')
        m.put(TARGET_ID, f'{lane} gun', VET_DX, ARMOR_AT, side='s1', role=f'vet {pts} target',
              name=f'UNIT - CNV Shot Vet {pts} Target')
    m.spawns |= {'CNV_ShotShellProjectile', 'CNV_ShotReachProjectile'}
    return m




def shot_test(m, group):
    """group 'way': the four lanes (counter: frames to the first hit + 1000 per percent); 'splash': the four splash
    Hammers (counter: percent lost). The other group's shooters keep NO_ATTACK."""
    t = Test()

    def n(part):
        return m.role(part).name

    lanes = [(LABELS[lane], n(f'{lane} shooter'), n(f'{lane} target')) for lane in LANES]
    splash = [(f'splash{dx:g}', n(f'splash {dx:g}')) for dx in (0.0,) + SPLASH_AT]
    shells = [(f'shell{d:g}', n(f'shells {d:g} shooter'), n(f'shells {d:g} target')) for d in SHELLS_AT]
    kinds = [(k.lower(), n(f'armor {k} shooter'), n(f'armor {k} target')) for k, _ in ARMOR_KINDS]
    flank = [(f'flank{off:g}', n(f'flank {off:g} shooter'), n(f'flank {off:g} target')) for off in FLANK_OFF]
    vet = [(f'vet{p}', n(f'vet {p} shooter'), n(f'vet {p} target')) for p in VET_POINTS]
    rows = {'armor': kinds, 'flank': flank, 'vet': vet}
    if group == 'way':
        pairs = [(s, tg) for _, s, tg in lanes]
    elif group == 'shells':
        pairs = [(s, tg) for _, s, tg in shells]
    elif group in rows:
        pairs = [(s, tg) for _, s, tg in rows[group]]
    else:
        pairs = [(n('splash shooter'), splash[0][1])]
    held = [s for _, s, _ in lanes] + [tg for _, _, tg in lanes] + [n('splash shooter')] + [tg for _, tg in splash]
    held += [x for _, s, tg in shells + kinds + flank + vet for x in (s, tg)]
    start = [('MAP_REVEAL_ALL_PERM', m.player('p1'))]
    if group == 'vet':
        start += [('UNIT_GIVE_EXPERIENCE_POINTS', s, p) for (_, s, _), p in zip(vet, VET_POINTS) if p]
    start += [('UNIT_CHANGE_OBJECT_STATUS', x, 'NO_ATTACK', 1) for x in held]
    start += [('SET_MILLISECOND_TIMER', 'Test Order', ORDER)]
    t.scripts.append(Script('Test - start', [], start))
    t.scripts.append(Script('Test - order', [('TIMER_EXPIRED', 'Test Order')],
                            [('UNIT_CHANGE_OBJECT_STATUS', s, 'NO_ATTACK', 0) for s, _ in pairs]
                            + [('NAMED_ATTACK_NAMED', s, tg) for s, tg in pairs]
                            + [('SET_FLAG', 'Test Ordered', 1)]))
    if group in ('way', 'shells'):
        for k, (label, _, tg) in enumerate(lanes if group == 'way' else shells):
            c = f'CNV_Shot_{"W" if group == "way" else "D"}{k}'
            t.counters.append((c, label))
            t.scripts.append(Script(f'Test - {c} frames', [('FLAG', 'Test Ordered', 1), ('UNIT_HEALTH', tg, 2, 100)],
                                    [('INCREMENT_COUNTER', 1, c)], once=False))
            t.scripts += [Script(f'Test - {c} lost {j}', [('UNIT_HEALTH', tg, 0, 100 - j + 1)],
                                 [('INCREMENT_COUNTER', 1000, c)]) for j in range(1, LOST_MAX + 1)]
        t.expect = [(lanes[0][0] if group == 'way' else shells[0][0], 0, 'ever>=', 1000, RUN - 2)]
    elif group in rows:
        for k, (label, _, tg) in enumerate(rows[group]):
            c = f'CNV_Shot_{group[0].upper()}{k}'
            t.counters.append((c, label))
            t.scripts += [Script(f'Test - {c} lost {j}', [('UNIT_HEALTH', tg, 0, 100 - j + 1)],
                                 [('INCREMENT_COUNTER', 1, c)]) for j in range(1, LOST_MAX + 1)]
        run = VET_RUN if group == 'vet' else SHORT
        t.expect = [(rows[group][0][0], 0, 'ever>=', 1, run - 1)]
        t.bench = [('bench_watch', dict(seconds=run, every=1, sheet=False, lines=6))]
        return t
    else:
        for k, (label, tg) in enumerate(splash):
            c = f'CNV_Shot_S{k}'
            t.counters.append((c, label))
            t.scripts += [Script(f'Test - {c} lost {j}', [('UNIT_HEALTH', tg, 0, 100 - j + 1)],
                                 [('INCREMENT_COUNTER', 1, c)]) for j in range(1, LOST_MAX + 1)]
        t.expect = [('splash0', 0, 'ever>=', 1, RUN - 2)]
    t.bench = [('bench_watch', dict(seconds=RUN, every=1, sheet=False, lines=6))]
    return t


MISSION = {'engine_shot': mission}
CHECKS = {'engine_shot': {'way': lambda m: shot_test(m, 'way'), 'splash': lambda m: shot_test(m, 'splash'),
                          'shells': lambda m: shot_test(m, 'shells'), 'armor': lambda m: shot_test(m, 'armor'),
                          'flank': lambda m: shot_test(m, 'flank'), 'vet': lambda m: shot_test(m, 'vet')}}
