"""E168: one V4 rocket, retail Bezier module versus module removal.

Prediction before bench: at 450 range the enabled rocket lands for 500 damage
on a 10000 HP Hammer (95%); the module-removal control cannot fly to its
victim (100%). Both targets start at 100%. The weapon has no preattack,
duration or scatter, reloads in 1s, and is disabled four frames after the
order so only one rocket launches. The projectile itself is retail except
for its identity and, in the off lane, removal of BezierProjectile.
Sample HP at frame 240, not a video-clock flight-time estimate. Curved flight,
homing, launch geometry, collision and exact impact frame remain gaps.
"""
import os
import re

from maps import probe_range
from parts import Mission, Script, Test
from checks.engine_missile import SAGE, V4_ROCKET, target
from checks.engine_shot import DAMAGE, _nuggets, shot_v4


def launcher(tag):
    ident = 'CNVE168' + tag
    rocket, warhead = ident + 'Rocket', ident + 'Warhead'
    with open(os.path.join(SAGE, 'Soviet', 'Props', V4_ROCKET + '.xml'), encoding='utf-8') as f:
        xml = f.read()
    xml, count = re.subn(r'\s*<GameObject\s+inheritFrom="' + V4_ROCKET + r'".*?</GameObject>', '', xml, flags=re.S)
    assert count == 1
    xml = xml.replace(V4_ROCKET, rocket)
    if tag == 'Off':
        xml, count = re.subn(r'<BezierProjectile\b[^>]*/>', '', xml, flags=re.S)
        assert count == 1
    wh = (f'<WeaponTemplate id="{warhead}" RadiusDamageAffects="ENEMIES" '
          'RequiredAntiMask="ANTI_GROUND ANTI_STRUCTURE ANTI_WATER">' +
          _nuggets(DAMAGE.format(d=500, r=40, extra='')) + '</WeaponTemplate>')
    return shot_v4(ident, _nuggets(f'<ProjectileNugget WarheadTemplate="{warhead}" '
                                 f'ProjectileTemplate="{rocket}" />'), speed=200,
                   files={rocket + '.xml': xml}, extra=wh, reload=1,
                   what='single V4 rocket with retail Bezier module or module removal')


def mission():
    m = Mission(name='CampBezierE', map=probe_range,
                units=[launcher('On'), launcher('Off'), target()])
    for tag, site in [('On', 'base gun'), ('Off', 'high gun')]:
        m.put('CNVE168' + tag, site, side='p1', angle=1.5708,
              role=tag + 'gun', name='E168 ' + tag + ' gun')
        m.put('CNV_MslTarget', site, 0, 450, side='s1', angle=4.7124,
              role=tag + 'target', name='E168 ' + tag + ' target')
    return m


def check(m):
    t = Test()
    t.counters = [('E168Frame', '帧'), ('E168Base', '初始满血'),
                  ('E168On', '有模块血量'), ('E168Off', '删模块血量')]
    t.scripts = [Script('Test - frame', [('COUNTER', 'E168Frame', 0, 240)],
                        [('INCREMENT_COUNTER', 1, 'E168Frame')], once=False)]
    start, fire, stop = [('MAP_REVEAL_ALL_PERM', m.player('p1'))], [], []
    baseline = []
    snapshot = []
    for tag, bit in [('On', 1), ('Off', 2)]:
        gun, victim = m.role(tag + 'gun').name, m.role(tag + 'target').name
        start += [('UNIT_CHANGE_OBJECT_STATUS', name, 'NO_ATTACK', 1) for name in (gun, victim)]
        fire += [('UNIT_CHANGE_OBJECT_STATUS', gun, 'NO_ATTACK', 0), ('NAMED_ATTACK_NAMED', gun, victim)]
        stop += [('UNIT_CHANGE_OBJECT_STATUS', gun, 'NO_ATTACK', 1)]
        baseline.append(Script('Test - baseline ' + tag,
                               [('COUNTER', 'E168Frame', 2, 60), ('UNIT_HEALTH', victim, 2, 100)],
                               [('INCREMENT_COUNTER', bit, 'E168Base')]))
        snapshot.append(('SET_UNIT_HEALTH_PERCENTAGE_TO_COUNTER', victim, 'E168' + tag))
    t.scripts += [Script('Test - start', [], start)] + baseline + [
        Script('Test - fire', [('COUNTER', 'E168Frame', 2, 90)], fire),
        Script('Test - stop', [('COUNTER', 'E168Frame', 2, 94)], stop),
        Script('Test - snapshot', [('COUNTER', 'E168Frame', 2, 240)], snapshot)]
    # Run a ended at f216. Run b reached f240 (240/3/95/100), but late in
    # video time. Judge the frozen script-frame snapshot, not a video deadline.
    # Original time-window FAIL results are retained in work/re/e168_bezier.md.
    t.expect = [('帧', 0, 'ever==', 240), ('初始满血', 0, 'ever==', 3),
                ('有模块血量', 0, 'ever==', 95), ('删模块血量', 0, 'ever==', 100)]
    t.bench = [('bench_watch', dict(seconds=50, every=1, sheet=False, lines=4))]
    return t


MISSION = {'engine_bezier_e': mission}
CHECKS = {'engine_bezier_e': {'a': check}}
