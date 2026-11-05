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
"""
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
DAMAGE = '<DamageNugget Damage="{d:.1f}" DamageType="EXPLOSIVE" DeathType="EXPLODED" Radius="{r:g}"{extra} />'
LASER = ('<ActivateLaserNugget id="DefaultLaserNugget" Lifetime="0.1s" LaserId="1" />')


def _nuggets(*items):
    return '<Nuggets>\n\t\t\t' + '\n\t\t\t'.join(items) + '\n\t\t</Nuggets>'


def shot_v4(id, nuggets, speed=999999.0, files=None, extra='', what=''):
    """Retail's V4 under `id`, its rocket weapon swapped for `id`Weapon: `nuggets`, WeaponSpeed `speed`, no scatter,
    pre-attack 0, FiringDuration 0; nothing else differs (ADR 0016 G5: the probe builds it). `extra`: more assets
    laid into the unit's file, `files`: {name: xml} of its own."""
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


def shell_v4(id='CNV_ShotShell'):
    """The V4 firing retail's Hammer shell (copied as `id`Projectile) with a warhead (`id`Warhead) of one radius-0
    DamageNugget of 500."""
    proj, wh = id + 'Projectile', id + 'Warhead'
    p = open(os.path.join(SAGE, 'Soviet', 'Props', SHELL + '.xml'), encoding='utf-8').read()
    p = _sub1(p, f'id="{SHELL}"', f'id="{proj}"')
    p = _sub1(p, f'EditorName="{SHELL}"', f'EditorName="{proj}"')
    warhead = (f'\t<WeaponTemplate id="{wh}" ProjectileCollidesWith="ALLIES ENEMIES NEUTRAL STRUCTURES WALLS"\n'
               f'\t\tRadiusDamageAffects="ENEMIES" RequiredAntiMask="ANTI_WATER ANTI_GROUND ANTI_STRUCTURE">\n'
               f'\t\t{_nuggets(DAMAGE.format(d=500.0, r=0, extra=""))}\n\t</WeaponTemplate>\n')
    nug = f'<ProjectileNugget WarheadTemplate="{wh}" ProjectileTemplate="{proj}" />'
    u = shot_v4(id, _nuggets(nug), files={proj + '.xml': p}, extra=warhead,
                what='打锤子炮弹的 V4（探针）：直射弹（原版锤子炮弹），弹头半径 0、500 伤害，无预瞄、无开火持续、无散布')
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
        shot_v4('CNV_ShotLaser', _nuggets(LASER, one),
                what='激光 V4（探针）：开激光光束 + 500 伤害，WeaponSpeed 999999，无预瞄、无开火持续、无散布'),
        shot_v4('CNV_ShotSplash', _nuggets(splash),
                what=f'溅射 V4（探针）：{SPLASH_DAMAGE:g} 伤害、半径 {SPLASH_RADIUS:g}、边缘衰减到 {SPLASH_TAPER:g}，'
                     '无预瞄、无开火持续、无散布'),
        target(),
    ]


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
    m.spawns |= {'CNV_ShotShellProjectile'}
    return m




def shot_test(m, group):
    """group 'way': the four lanes (counter: frames to the first hit + 1000 per percent); 'splash': the four splash
    Hammers (counter: percent lost). The other group's shooters keep NO_ATTACK."""
    t = Test()

    def n(part):
        return m.role(part).name

    lanes = [(LABELS[lane], n(f'{lane} shooter'), n(f'{lane} target')) for lane in LANES]
    splash = [(f'splash{dx:g}', n(f'splash {dx:g}')) for dx in (0.0,) + SPLASH_AT]
    if group == 'way':
        pairs = [(s, tg) for _, s, tg in lanes]
    else:
        pairs = [(n('splash shooter'), splash[0][1])]
    held = [s for _, s, _ in lanes] + [tg for _, _, tg in lanes] + [n('splash shooter')] + [tg for _, tg in splash]
    start = [('MAP_REVEAL_ALL_PERM', m.player('p1'))]
    start += [('UNIT_CHANGE_OBJECT_STATUS', x, 'NO_ATTACK', 1) for x in held]
    start += [('SET_MILLISECOND_TIMER', 'Test Order', ORDER)]
    t.scripts.append(Script('Test - start', [], start))
    t.scripts.append(Script('Test - order', [('TIMER_EXPIRED', 'Test Order')],
                            [('UNIT_CHANGE_OBJECT_STATUS', s, 'NO_ATTACK', 0) for s, _ in pairs]
                            + [('NAMED_ATTACK_NAMED', s, tg) for s, tg in pairs]
                            + [('SET_FLAG', 'Test Ordered', 1)]))
    if group == 'way':
        for k, (label, _, tg) in enumerate(lanes):
            c = f'CNV_Shot_W{k}'
            t.counters.append((c, label))
            t.scripts.append(Script(f'Test - {c} frames', [('FLAG', 'Test Ordered', 1), ('UNIT_HEALTH', tg, 2, 100)],
                                    [('INCREMENT_COUNTER', 1, c)], once=False))
            t.scripts += [Script(f'Test - {c} lost {j}', [('UNIT_HEALTH', tg, 0, 100 - j + 1)],
                                 [('INCREMENT_COUNTER', 1000, c)]) for j in range(1, LOST_MAX + 1)]
        t.expect = [('instant', 0, 'ever>=', 1000, RUN - 2)]
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
CHECKS = {'engine_shot': {'way': lambda m: shot_test(m, 'way'), 'splash': lambda m: shot_test(m, 'splash')}}
