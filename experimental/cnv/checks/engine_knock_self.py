"""Line A: the retail shotgun's own entry -- a Peacekeeper's instant shot, DamageDealtAtSelfPosition.

engine_knock_arc b (CampKArcB_mcp_1124_225031): on a V4 detonation, Forbidden STUNNED_FLAILING alone still
shocks every standing man (as the plain lane), Arc 5d alone shocks none -- the victim, his side neighbour and
the man 20 behind him along the rocket's way in. So the arc does not point along the projectile's way in from
the detonation. Retail's shotgun is instant with DamageDealtAtSelfPosition (its DamageNugget: Radius 155,
DamageArc 5d, from the shooter). Here two lanes, each a probe Peacekeeper (retail shotgun) facing +y at the
target 25 ahead: 'retail' with the weapon as it is, 'plain' a copy without ShockWaveArc only. Each lane: 'man'
(0, 25), 'behind' (0, 38: in line, 38 from the shooter), 'side' (20, 25: 32 off, 39 deg out of line) and 'far'
(0, 60: 35 from the man, 60 from the shooter). ra3ext's shockinfo logs each shock's centre.
Prediction (self position for the shock too, the arc about the shooter's line): retail shocks man and behind,
plain also side, far in neither; the man hit (< 100), the side man unhurt by the 5d damage arc (100).
Bench 11-24 CampKSelfA_mcp_1124_225511 PASS, as predicted: every shock at frame 92 is centred on the shooter's
feet ((x, 3300, 212.5); dir = the body's feet + 6.5 less the centre). retail: man v (0, 3.2261, 0.8388) lands
(+0, 3340) N=6, behind v (0, 3.2856, 0.5620) lands 3340 N=3; side and far none. plain: the same two plus side
v (2.0407, 2.5509, 0.6632) lands (2320, 3320) N=3; far none. Health man 74 / side 100 in both (behind 113 / far
115.13 of 150 off the damage log: the 155 damage arc reaches them in line).
b (A364): the same shot, counting instead whether man / side are still on their spot (a 3 box): CampKSelfB_mcp_1124_231636
PASS, retail 0 / 1, plain 0 / 0 from s6.47.
"""
import os
import re

import labpaths
from maps import probe_range
from parts import Mission, Script, Test, Unit
from model import square
from benches.weapon.firing.checks import engine_clip
ORDER = engine_clip()["shared"].ORDER
from benches.weapon.target_effects.checks import engine_suppress_probe
suppress_probe = engine_suppress_probe()["shared"]
PROBE = suppress_probe.PROBE
probe_man = suppress_probe.probe_man

RETAIL = 'AlliedAntiInfantryInfantryShotgun'
PLAIN, PLAIN_WEAPON = 'CNV_KnockShot', 'CNV_KnockShotWeapon'
SITE = {'retail': 'removed gun', 'plain': 'switch gun'}
SPOTS = {'man': (0, 25), 'behind': (0, 38), 'side': (20, 25), 'far': (0, 60)}
STOP = 1.0          # FiringDuration 0.5 s, ClipReloadTime 1 s: one shot
RUN = ORDER + 6.0


def name(lane, part):
    return f'UNIT - CNV KSelf {lane} {part}'


def plain_shooter():
    """The probe Peacekeeper with its shotgun copied without ShockWaveArc (nothing else changed)."""
    man = probe_man()
    with open(os.path.join(labpaths.SDK3, 'SageXML', 'GlobalData', 'Weapon.xml'), encoding='utf-8') as f:
        text = f.read()
    weapon = re.search(rf'<WeaponTemplate\s+id="{RETAIL}".*?</WeaponTemplate>', text, re.S).group(0)
    weapon, n = re.subn(r'\s+ShockWaveArc="5d"', '', weapon.replace(f'id="{RETAIL}"', f'id="{PLAIN_WEAPON}"'))
    assert n == 1
    x = man.xml.replace(f'id="{PROBE}"', f'id="{PLAIN}"', 1).replace(f'EditorName="{PROBE}"', f'EditorName="{PLAIN}"')
    assert x.count(f'Template="{RETAIL}"') == 1
    x = x.replace(f'Template="{RETAIL}"', f'Template="{PLAIN_WEAPON}"')
    x = x.replace('</AssetDeclaration>', f'\t{weapon}\n</AssetDeclaration>', 1)
    u = Unit(PLAIN, x, names=dict(unit=PLAIN), what='维和探针的复制：散弹只删 ShockWaveArc（对照）',
             params=dict(man.params))
    u.link = list(u.link) + [f'WeaponTemplate:{PLAIN_WEAPON}']
    return u


def mission():
    m = Mission(name='CampKSelf', map=probe_range, units=[probe_man(), plain_shooter()], facts={})
    m.ext = True
    for lane, site in SITE.items():
        m.put(PROBE if lane == 'retail' else PLAIN, site, 0, 0, side='p1', angle=1.5708, name=name(lane, 'gun'))
        for part, (dx, dy) in SPOTS.items():
            m.put(PROBE, site, dx, dy, side='s1', angle=-1.5708, name=name(lane, part))
    return m


def check(m, home=False):
    m.units = [probe_man(), plain_shooter()]
    t = Test()
    parts = ('gun',) + tuple(SPOTS)
    start = [('MAP_REVEAL_ALL_PERM', m.player('p1'))]
    start += [('UNIT_CHANGE_OBJECT_STATUS', name(k, p), 'NO_ATTACK', 1) for k in SITE for p in parts]
    start += [('SET_MILLISECOND_TIMER', 'KSelf Fire', float(ORDER)),
              ('SET_MILLISECOND_TIMER', 'KSelf Stop', float(ORDER + STOP))]
    t.scripts.append(Script('Test - start', [], start))
    fire, stop = [], []
    for k in SITE:
        fire += [('UNIT_CHANGE_OBJECT_STATUS', name(k, 'gun'), 'NO_ATTACK', 0),
                 ('NAMED_ATTACK_NAMED', name(k, 'gun'), name(k, 'man'))]
        stop += [('UNIT_CHANGE_OBJECT_STATUS', name(k, 'gun'), 'NO_ATTACK', 1)]
    t.scripts.append(Script('Test - fire', [('TIMER_EXPIRED', 'KSelf Fire')], fire))
    t.scripts.append(Script('Test - stop', [('TIMER_EXPIRED', 'KSelf Stop')], stop))
    for k in SITE if not home else ():
        for p, op, hp in (('man', '<', 100), ('side', '==', 100)):
            c = f'CNV_KSelf_{k}_{p}'
            t.counters.append((c, f'{k} {p}'))
            t.scripts.append(Script(f'Test - health {k} {p}', [],
                                    [('SET_UNIT_HEALTH_PERCENTAGE_TO_COUNTER', name(k, p), c)], once=False))
            t.expect.append((f'{k} {p}', RUN - 2, op, hp, RUN))
    # b (A364): still on its spot (a 3 box) instead of health -- a lands man 15 on, plain's side 5 back (the 20 grid)
    for k, site in SITE.items() if home else ():
        x, y = m.site(site)[:2]
        for p, moved in (('man', True), ('side', k == 'plain')):
            c, area = f'CNV_KSelf_{k}_{p}_home', name(k, p + ' home')
            t.areas[area] = square(x + SPOTS[p][0], y + SPOTS[p][1], 3)
            t.counters.append((c, f'{k} {p} home'))
            t.scripts += [Script(f'Test - away {k} {p}', [], [('SET_COUNTER', c, 0)], once=False),
                          Script(f'Test - home {k} {p}', [('NAMED_INSIDE_AREA', name(k, p), area)],
                                 [('SET_COUNTER', c, 1)], once=False)]
            t.expect.append((f'{k} {p} home', RUN - 2, '==', int(not moved), RUN))
    t.bench = [('bench_watch', dict(seconds=RUN, every=.5, sheet=False, lines=len(t.counters)))]
    return t


MISSION = {'engine_knock_self': mission}
CHECKS = {'engine_knock_self': {'a': check, 'b': lambda m: check(m, home=True)}}
