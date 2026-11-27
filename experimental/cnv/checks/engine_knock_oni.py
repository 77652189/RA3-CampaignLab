"""Line A: King Oni's two MetaImpactNugget spellings (Arc 135d / 180d + LEECHED + STUNNED* + Rule ANY Include INFANTRY).

Each lane a probe Peacekeeper copy (facing +y, the target man 25 ahead) armed with retail
JapanAntiVehicleVehicleTech3MeleeAttackWeapon (Damage 10 Radius 1, range 50). 'melee' carries it verbatim
(DamageDealtAtSelfPosition, Arc 135d); 'rush' the same without DamageDealtAtSelfPosition and with the
RushAttackWeapon's MetaImpactNugget (Arc 180d, TaperOff 1) -- the Rush weapon itself kills the man (Damage 500).
Spots from the shooter: melee 'in' (35, 25) 54.5 deg off its line, 'out' (35, 5) 82 deg off; rush 'beyond' (0, 45)
20 past the man, 'before' (15, 10) 135 deg off the shooter->man line about the man. Counters: still on its spot
(a 3 box) for melee in / out, rush beyond / before.
Prediction (half-angle arc/2, the melee as the shotgun about the shooter's feet, the rush centred on the man with
the arc along the shooter->man line): 0 1 0 1.
Bench 11-26 (A393) CampKOniA_mcp_1126_211718: 1 1 1 1 to s5.87, 0 0 0 0 from s6.6 -- wrong twice. ra3ext: every shock
at frame 92 centred on its shooter's feet ((800 | 2300, 3300, 212.5)), the rush lane's too (no
DamageDealtAtSelfPosition: an instant shot's shock is the shooter's); melee out v (3.0536, 0.4362, 0.5671): 82 deg
off is inside 135d, so the half-angle is not arc / 2. Rush (TaperOff 1) beyond v (0, 5.8724, 0.8482), before
(4.6442, 3.0961, 2.0125), the man (0, 5.7424, 1.4930); the shooters none.
"""
import os
import re

import labpaths
from maps import probe_range
from model import square
from parts import Mission, Script, Test, Unit
from checks import engine_knock_self as self_
from benches.weapon.target_effects.checks import engine_suppress_probe

PROBE = engine_suppress_probe()["shared"].PROBE
MELEE = 'JapanAntiVehicleVehicleTech3MeleeAttackWeapon'
SITE = {'melee': 'removed gun', 'rush': 'switch gun'}
SPOTS = {'melee': {'man': (0, 25), 'in': (35, 25), 'out': (35, 5)},
         'rush': {'man': (0, 25), 'beyond': (0, 45), 'before': (15, 10)}}
COUNT = (('melee', 'in'), ('melee', 'out'), ('rush', 'beyond'), ('rush', 'before'))
PREDICT = (0, 0, 0, 0)      # the bench's (the prediction 0 1 0 1 was wrong)


def weapon(lane):
    with open(os.path.join(labpaths.SDK3, 'SageXML', 'GlobalData', 'Weapon.xml'), encoding='utf-8') as f:
        text = f.read()
    w = re.search(rf'<WeaponTemplate\s+id="{MELEE}".*?</WeaponTemplate>', text, re.S).group(0)
    if lane == 'rush':
        rush = re.search(r'<WeaponTemplate\s+id="JapanAntiVehicleVehicleTech3RushAttackWeapon".*?</WeaponTemplate>',
                         text, re.S).group(0)
        shock = re.search(r'<MetaImpactNugget\b.*?</MetaImpactNugget>', rush, re.S).group(0)
        assert 'ShockWaveArc="180d"' in shock
        w, n = re.subn(r'\s+DamageDealtAtSelfPosition="true"', '', w)
        assert n == 1
        w, n = re.subn(r'<MetaImpactNugget\b.*?</MetaImpactNugget>', lambda _: shock, w, flags=re.S)
        assert n == 1
    return w.replace(f'id="{MELEE}"', f'id="CNV_KOni{lane.title()}Weapon"')


def shooter(lane):
    unit, wid = f'CNV_KOni{lane.title()}', f'CNV_KOni{lane.title()}Weapon'
    man = self_.probe_man()
    x = man.xml.replace(f'id="{PROBE}"', f'id="{unit}"', 1).replace(f'EditorName="{PROBE}"', f'EditorName="{unit}"')
    assert x.count(f'Template="{self_.RETAIL}"') == 1
    x = x.replace(f'Template="{self_.RETAIL}"', f'Template="{wid}"')
    x = x.replace('</AssetDeclaration>', f'\t{weapon(lane)}\n</AssetDeclaration>', 1)
    u = Unit(unit, x, names=dict(unit=unit), params=dict(man.params),
             what=f'维和探针的复制：武器换成鬼王近战（{lane}）')
    u.link = list(u.link) + [f'WeaponTemplate:{wid}']
    return u


def name(lane, part):
    return f'UNIT - CNV KOni {lane} {part}'


def units():
    return [self_.probe_man(), shooter('melee'), shooter('rush')]


def mission():
    m = Mission(name='CampKOni', map=probe_range, units=units(), facts={})
    m.ext = True
    for lane, site in SITE.items():
        m.put(f'CNV_KOni{lane.title()}', site, 0, 0, side='p1', angle=1.5708, name=name(lane, 'gun'))
        for part, (dx, dy) in SPOTS[lane].items():
            m.put(PROBE, site, dx, dy, side='s1', angle=-1.5708, name=name(lane, part))
    return m


def check(m):
    m.units = units()
    t = Test()
    start = [('MAP_REVEAL_ALL_PERM', m.player('p1'))]
    start += [('UNIT_CHANGE_OBJECT_STATUS', name(k, p), 'NO_ATTACK', 1) for k in SITE for p in ('gun', *SPOTS[k])]
    start += [('SET_MILLISECOND_TIMER', 'KOni Fire', float(self_.ORDER)),
              ('SET_MILLISECOND_TIMER', 'KOni Stop', float(self_.ORDER + self_.STOP))]
    t.scripts.append(Script('Test - start', [], start))
    t.scripts.append(Script('Test - fire', [('TIMER_EXPIRED', 'KOni Fire')], [
        a for k in SITE for a in (('UNIT_CHANGE_OBJECT_STATUS', name(k, 'gun'), 'NO_ATTACK', 0),
                                  ('NAMED_ATTACK_NAMED', name(k, 'gun'), name(k, 'man')))]))
    t.scripts.append(Script('Test - stop', [('TIMER_EXPIRED', 'KOni Stop')],
                            [('UNIT_CHANGE_OBJECT_STATUS', name(k, 'gun'), 'NO_ATTACK', 1) for k in SITE]))
    for (k, p), stays in zip(COUNT, PREDICT):
        x, y = m.site(SITE[k])[:2]
        dx, dy = SPOTS[k][p]
        c, area = f'CNV_KOni_{k}_{p}', name(k, p + ' home')
        t.areas[area] = square(x + dx, y + dy, 3)
        t.counters.append((c, f'{k} {p}'))
        t.scripts += [Script(f'Test - away {k} {p}', [], [('SET_COUNTER', c, 0)], once=False),
                      Script(f'Test - home {k} {p}', [('NAMED_INSIDE_AREA', name(k, p), area)],
                             [('SET_COUNTER', c, 1)], once=False)]
        t.expect.append((f'{k} {p}', self_.RUN - 2, '==', stays, self_.RUN))
    t.bench = [('bench_watch', dict(seconds=self_.RUN, every=.5, sheet=False, lines=len(t.counters)))]
    return t


MISSION = {'engine_knock_oni': mission}
CHECKS = {'engine_knock_oni': {'a': check}}
