"""Engine unit test: the firing state machine (ADR 0019 layer 3, batch "firing"; docs/engine/weapons.md) -- what fills
the 35-40 frames between NAMED_ATTACK_NAMED and the V4's launch (docs/engine/missile.md 3: the model has only the
0.5 s pre-attack, 8 frames).

The flight is taken out: each shooter is retail's V4 with its rocket weapon swapped for a copy whose nuggets are one
instant DamageNugget (500 EXPLOSIVE, radius 0, WeaponSpeed 999999: hits the frame it fires) and no scatter (an instant
shot that scatters lands beside the victim). The copies differ only in PreAttackDelay and FiringDuration:

  I     retail's timers: pre-attack 0.5 s, firing 1.0 s, reload 4.5-5.5 s
  I0P   pre-attack 0
  I0F   firing 0
  I00   both 0

On the range probe map (maps/probe_range.py, flat) four lanes; shooters face north, their target (engine_missile's
10 000-health Hammer, held with NO_ATTACK) FAR straight north. The shooters are held with NO_ATTACK and at ORDER
freed and told to attack. Counters as in engine_missile: frames from the order to the first hit, + 1000 per percent
lost (a hit is 5 %), so later hits show in the second-by-second watch. Two checks swap the copies between the early
lanes (base, high) and the late ones (removed, switch: ~8 frames later every run of engine_missile, not read why).
"""
import os
import re

from maps import probe_range
from parts import Mission, Script, Test, Unit
from checks.engine_missile import FAR, LOST_MAX, ORDER, SAGE, TARGET_ID, V4, V4_WEAPON, _sub1, target

RUN = 24.0
COPIES = {   # id: (pre-attack s, firing s, label)
    'CNV_FireI': (0.5, 1.0, '原时'),
    'CNV_FireI0P': (0.0, 1.0, '无预瞄'),
    'CNV_FireI0F': (0.5, 0.0, '无持续'),
    'CNV_FireI00': (0.0, 0.0, '都无'),
}
INSTANT = ('<Nuggets>\n\t\t\t<DamageNugget Damage="500.0" DamageType="EXPLOSIVE" DeathType="EXPLODED" Radius="0" />\n'
           '\t\t</Nuggets>')


def fire_v4(id, pre, firing):
    """Retail's V4 under `id`, its rocket weapon swapped for `id`Weapon: one instant DamageNugget, no scatter,
    PreAttackDelay `pre` s, FiringDuration `firing` s; nothing else differs (ADR 0016 G5: the probe builds it)."""
    wid = id + 'Weapon'
    x = open(os.path.join(SAGE, 'Soviet', 'Units', V4 + '.xml'), encoding='utf-8').read()
    x = _sub1(x, f'id="{V4}"', f'id="{id}"')
    x = re.sub(rf'EditorName="{V4}"', f'EditorName="{id}"', x)
    x = _sub1(x, f'Template="{V4_WEAPON}"', f'Template="{wid}"')
    w = open(os.path.join(SAGE, 'GlobalData', 'Weapon.xml'), encoding='utf-8').read()
    s = re.search(rf'\t*<WeaponTemplate\s+id="{V4_WEAPON}".*?</WeaponTemplate>\n', w, re.S).group(0)
    s = _sub1(s, f'id="{V4_WEAPON}"', f'id="{wid}"')
    s = _sub1(s, 'inheritFrom="ScatterableWeapon"', '')
    s = _sub1(s, 'WeaponSpeed="200"', 'WeaponSpeed="999999"')
    s, k = re.subn(r'<Nuggets>.*?</Nuggets>', INSTANT, s, flags=re.S)
    assert k == 1, k
    s, k = re.subn(r'\s*<ScatterRadiusVsType\s+Radius="0\.1">.*?</ScatterRadiusVsType>', '', s, flags=re.S)
    assert k == 1, k
    s = _sub1(s, 'MinSeconds=".5s"\n\t\t  MaxSeconds=".5s"', f'MinSeconds="{pre:g}s"\n\t\t  MaxSeconds="{pre:g}s"')
    s = _sub1(s, '<FiringDuration\n\t\t\tMinSeconds="1.0s"\n\t\t\tMaxSeconds="1.0s"',
              f'<FiringDuration\n\t\t\tMinSeconds="{firing:g}s"\n\t\t\tMaxSeconds="{firing:g}s"')
    x = _sub1(x, '</AssetDeclaration>', s + '</AssetDeclaration>')
    return Unit(id, x, link=[f'WeaponTemplate:{wid}'], names=dict(unit=id, weapon=wid),
                what=f'瞬发 V4（探针）：预瞄 {pre:g} 秒、开火持续 {firing:g} 秒，伤害当场结算，无散布，其余同原版',
                params=dict(pre=pre, firing=firing))


LANES = {   # check: {lane: shooter}
    'timers': {'base': 'CNV_FireI', 'high': 'CNV_FireI0P', 'removed': 'CNV_FireI0F', 'switch': 'CNV_FireI00'},
    'timers2': {'base': 'CNV_FireI0F', 'high': 'CNV_FireI00', 'removed': 'CNV_FireI', 'switch': 'CNV_FireI0P'},
}
ALL_LANES = ('base', 'high', 'removed', 'switch')


def mission():
    m = Mission(name='CampFire', map=probe_range,
                units=[fire_v4(i, p, f) for i, (p, f, _) in COPIES.items()] + [target()], facts={})
    for lane in ALL_LANES:
        L, site = lane.title(), f'{lane} gun'
        for i in COPIES:        # every copy on every lane, the check removes the ones it does not use
            m.put(i, site, side='p1', role=f'{lane} {i}', name=f'UNIT - CNV Fire {L} {i[8:]}')
        m.put(TARGET_ID, site, 0, FAR, side='s1', role=f'{lane} target', name=f'UNIT - CNV Fire {L} Target')
    return m


def fire_test(m, lanes):
    t = Test()

    def n(part):
        return m.role(part).name

    targets = [n(f'{lane} target') for lane in lanes]
    shooters = [n(f'{lane} {lanes[lane]}') for lane in lanes]
    idle = [n(f'{lane} {i}') for lane in lanes for i in COPIES if i != lanes[lane]]
    start = [('MAP_REVEAL_ALL_PERM', m.player('p1'))]
    start += [('NAMED_DELETE', x) for x in idle]
    start += [('UNIT_CHANGE_OBJECT_STATUS', x, 'NO_ATTACK', 1) for x in targets + shooters]
    start += [('SET_MILLISECOND_TIMER', 'Test Order', ORDER)]
    t.scripts.append(Script('Test - start', [], start))
    t.scripts.append(Script('Test - order', [('TIMER_EXPIRED', 'Test Order')],
                            [('UNIT_CHANGE_OBJECT_STATUS', s, 'NO_ATTACK', 0) for s in shooters]
                            + [('NAMED_ATTACK_NAMED', s, tg) for s, tg in zip(shooters, targets)]
                            + [('SET_FLAG', 'Test Ordered', 1)]))
    for lane, tg in zip(lanes, targets):
        c = f'CNV_Fire_{lane.title()}'
        t.counters.append((c, f'{lane}{COPIES[lanes[lane]][2]}'))
        t.scripts.append(Script(f'Test - {c} frames', [('FLAG', 'Test Ordered', 1), ('UNIT_HEALTH', tg, 2, 100)],
                                [('INCREMENT_COUNTER', 1, c)], once=False))
        t.scripts += [Script(f'Test - {c} lost {j}', [('UNIT_HEALTH', tg, 0, 100 - j + 1)],
                             [('INCREMENT_COUNTER', 1000, c)]) for j in range(1, LOST_MAX + 1)]
    first = next(iter(lanes))
    t.expect = [(f'{first}{COPIES[lanes[first]][2]}', 0, 'ever>=', 1000, RUN - 2)]
    t.bench = [('bench_watch', dict(seconds=RUN, every=1, sheet=False, lines=6))]
    return t


MISSION = {'engine_fire': mission}
CHECKS = {'engine_fire': {k: (lambda m, k=k: fire_test(m, LANES[k])) for k in LANES}}
