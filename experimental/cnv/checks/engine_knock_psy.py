"""A391: retail PsyonicBlast's MetaImpactNugget (1.0 s delay, Z 8.5, ShockWaveClearRadius false = the SDK default,
SpecialObjectFilter Rule NONE Include INFANTRY + StatusBitFlagsExclude NO_COLLISIONS) on the V4 rocket.

Each lane's rocket hits an enemy man; 40 east stands a second man, 40 west a Hammer copy with ShockwaveResistance 0
(BaseVehicle's 90 is over the nugget's 89: a real Hammer never lifts, engine_knock_water). 'yuri' carries the nugget
verbatim, 'rocket' the same with the SpecialObjectFilter removed. Counters: script frames each neighbour is still
on its spot (a 3 box). Prediction (Rule NONE = none of the Include kinds): yuri's man stays, its tank flies ~1 s after
the hit; the rocket lane's man and tank both fly. Bench 11-26 (A391): the other way -- yuri's man leaves at 190, its
tank never moves; rocket's both at 191 / 190 (NONE + a list = the list). Readings: engine_knock_psy.readings.toml.
"""
import re

from model import square
from parts import Script
from checks import engine_knock_kind as kind
from checks import engine_knock_probe as probe

SOFT = 'CNV_KnockSoftTank'
LANES = ('yuri', 'rocket')


def soft_tank():
    u = probe.probe_tank()
    u.id = SOFT
    u.names = dict(unit=SOFT)
    u.xml = u.xml.replace(probe.PROBE_TANK, SOFT)
    head = re.search(r'<GameObject\b', u.xml)
    u.xml = u.xml[:head.end()] + ' ShockwaveResistance="0"' + u.xml[head.end():]
    u.what = '击飞探针：锤子坦克的复制，ShockwaveResistance 0（基类 90 高过念力爆的 89）'
    return u


def mission():
    m = kind.mission()
    m.name = 'CampKPsy'
    for lane in LANES:
        man = next(o for o in m.objects if o.name == probe.name(lane, 'man'))
        near = next(o for o in m.objects if o.name == probe.name(lane, 'near'))
        near.template, near.side, near.x = probe.TARGET[lane], man.side, man.x + 40
        m.put(SOFT, probe.SITE[lane], -40, 450, side=man.side, name=probe.name(lane, 'tank'))
    return m


def check(m):
    t = kind.check(m)
    payload = probe.yuri_shock()
    plain = re.sub(r'\s*<SpecialObjectFilter\b[^>]*/>', '', payload)
    assert plain != payload and 'SpecialObjectFilter' not in plain
    for lane, uid in (('yuri', 'CNV_KnockYuri'), ('rocket', 'CNV_KnockRocket')):
        gun = next(u for u in m.units if u.id == uid)
        gun.xml, n = re.subn(r'<MetaImpactNugget\b.*?</MetaImpactNugget>',
                             lambda _, p=(payload if lane == 'yuri' else plain): p, gun.xml, flags=re.S)
        assert n == 1
    m.units.append(soft_tank())
    t.scripts[0].do += [('UNIT_CHANGE_OBJECT_STATUS', probe.name(lane, 'tank'), 'NO_ATTACK', 1) for lane in LANES]
    t.scripts = [s for s in t.scripts if not s.name.startswith(('Test - health', 'Test - dead'))]
    t.counters, t.expect = [], []
    for lane in LANES:
        for part in ('near', 'tank'):
            o = next(o for o in m.objects if o.name == probe.name(lane, part))
            c, area = f'CNV_Psy_{lane}_{part}', probe.name(lane, part + ' home')
            t.areas[area] = square(o.x, o.y, 3)
            t.counters.append((c, f'{lane} {part}'))
            t.scripts.append(Script(f'Test - home {lane} {part}', [('NAMED_INSIDE_AREA', o.name, area)],
                                    [('INCREMENT_COUNTER', 1, c)], once=False))
            t.expect.append((f'{lane} {part}', 18, '>=', 150, 20))
    t.bench = [('bench_watch', dict(seconds=20, every=.5, sheet=False, lines=4))]
    return t


MISSION = {'engine_knock_psy': mission}
CHECKS = {'engine_knock_psy': {'a': check}}
