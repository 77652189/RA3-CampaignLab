"""C: retail shotgun's narrow-arc payload versus its unfiltered control.

Copy the retail MetaImpactNugget, including Arc=5d and forbidden flailing,
onto a V4 warhead so a detonation is positively observed. The other lane
removes only those two restrictions. Both neighbours stand 20 east of the
victim (inside Radius40, transverse to the incoming rocket). Prediction:
plain neighbour moves, restricted neighbour stays; both victims99/near100.
No delay, stunned victim, instant-shot dispatch or whole-shotgun coverage.
Bench 11-11: health99/100/99/100. Plain neighbour moves at frames175..177
to (2320,3740,212.5); restricted victim AND neighbour remain stationary.
This establishes a payload difference, not an arc-axis rule. The incoming
direction/arc dispatch interface remains a gap; do not register filter cover.
Line A, b (CampKArcB): one field each -- yuri keeps only Arc=5d, rocket
keeps only the forbidden STUNNED_FLAILING; each lane adds a counterless
probe man 20 behind the victim along the rocket's way in (+y), read off the
position log. Prediction: a standing man is not flailing, so rocket moves
like a's plain lane; yuri stays as a's restricted lane (Arc decides). If
yuri's behind man alone moves, the arc points along the way in.
Bench 11-24 CampKArcB_mcp_1124_225031 PASS 99/100/99/100: rocket shocks all three at 174 (centre
(2300,3750,219), the same flights as a's plain lane); yuri shocks none, the behind man too. Arc decides, and
not about the way in: retail's entry is the shooter's own position (engine_knock_self).
engine_knock_kami a (A393): the kamikaze's shock (Arc 5d, Radius 20, LEECHED + STUNNED*) on yuri's V4, rocket's
without the arc, near 12 east; counters still-on-spot. Predicted (as b) yuri none, rocket both. Bench 11-26
CampKKamiA_mcp_1126_211950 PASS: 1 1 0 0 from s11.73; rocket's two shocked at 174, yuri's none.
"""
import os
import re

import labpaths
from model import Obj, square
from parts import Script
from checks import engine_knock_probe as probe

DROP = {'a': {'yuri': (), 'rocket': ('ShockWaveArc', 'ForbiddenTargetModelCondition')},
        'b': {'yuri': ('ForbiddenTargetModelCondition',), 'rocket': ('ShockWaveArc',)},
        'kami': {'yuri': (), 'rocket': ('ShockWaveArc',)}}
SHOTGUN, KAMI = 'AlliedAntiInfantryInfantryShotgun', 'JapanFinalSquadronAircraftKamikazeWarhead'


def retail_shock(weapon_id=SHOTGUN):
    with open(os.path.join(labpaths.SDK3, 'SageXML', 'GlobalData', 'Weapon.xml'), encoding='utf-8') as f:
        text = f.read()
    weapon = re.search(rf'<WeaponTemplate\s+id="{weapon_id}".*?</WeaponTemplate>', text, re.S).group(0)
    shock, = re.findall(r'<MetaImpactNugget\b[^>]*/>', weapon)
    assert 'ShockWaveArc="5d"' in shock
    return shock


def mission(gap=20, name='CampKArc'):
    m = probe.mission()
    m.name = name
    for lane in ('yuri', 'rocket'):
        victim = next(o for o in m.objects if o.name == probe.name(lane, 'man'))
        near = next(o for o in m.objects if o.name == probe.name(lane, 'near'))
        near.x = victim.x + gap
    return m


def check(m, which='a'):
    t = probe.check(m, 'retail')
    shock = retail_shock(KAMI if which == 'kami' else SHOTGUN)
    for lane, uid in (('yuri', 'CNV_KnockYuri'), ('rocket', 'CNV_KnockRocket')):
        gun = probe.rocket_gun(uid)
        payload = shock
        for field in DROP[which][lane]:
            payload, n = re.subn(rf'\s+{field}="[^"]*"', '', payload)
            assert n == 1
        gun.xml, n = re.subn(r'<MetaImpactNugget\b[^>]*/>', lambda _: payload, gun.xml)
        assert n == 1
        m.units = [gun if u.id == uid else u for u in m.units]
    # Both guns are projectiles now: retain their half-second pre-attack delay.
    for script in t.scripts:
        script.do = [(a[0], a[1], probe.ORDER + 2.0)
                     if a[0] == 'SET_MILLISECOND_TIMER' and a[1] == 'Knock Stop 0' else a
                     for a in script.do]
    if which == 'b':
        start = next(s for s in t.scripts if s.name == 'Test - start')
        for lane in ('yuri', 'rocket'):
            victim = next(o for o in m.objects if o.name == probe.name(lane, 'man'))
            t.objects.append(Obj(probe.PROBE, victim.x, victim.y + 20, side=victim.side,
                                 name=probe.name(lane, 'behind'), site=victim.site))
            start.do.append(('UNIT_CHANGE_OBJECT_STATUS', probe.name(lane, 'behind'), 'NO_ATTACK', 1))
    if which == 'kami':     # A393: the victim and his neighbour 12 east still on their spot (a 3 box)
        t.scripts = [s for s in t.scripts if not s.name.startswith(('Test - health', 'Test - dead'))]
        t.counters, t.expect = [], []
        for lane in ('yuri', 'rocket'):
            for part in ('man', 'near'):
                o = next(o for o in m.objects if o.name == probe.name(lane, part))
                c, area = f'CNV_Kami_{lane}_{part}', probe.name(lane, part + ' home')
                t.areas[area] = square(o.x, o.y, 3)
                t.counters.append((c, f'{lane} {part}'))
                t.scripts += [Script(f'Test - away {lane} {part}', [], [('SET_COUNTER', c, 0)], once=False),
                              Script(f'Test - home {lane} {part}', [('NAMED_INSIDE_AREA', o.name, area)],
                                     [('SET_COUNTER', c, 1)], once=False)]
                t.expect.append((f'{lane} {part}', 18, '==', int(lane == 'yuri'), 20))
        t.bench = [('bench_watch', dict(seconds=20, every=.5, sheet=False, lines=4))]
    return t


MISSION = {'engine_knock_arc': mission, 'engine_knock_kami': lambda: mission(12, 'CampKKami')}
CHECKS = {'engine_knock_arc': {k: (lambda m, k=k: check(m, k)) for k in ('a', 'b')},
          'engine_knock_kami': {'a': lambda m: check(m, 'kami')}}
