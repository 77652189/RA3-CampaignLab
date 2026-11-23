"""ShieldSphereUpdate absorption: the retail Athena's shield under fire (after E153 engine_activate, which read only
its statuses).

Two lanes, each a 10 000-health Athena (p1, NO_ATTACK so it does not shoot back; one with the retail shield button,
one with ActivateModuleSpecialPower removed) and three retail V4s (s1) about 460 north, outside the sphere's 200.
Both Athenas press the button at PRESS; the V4s are told to attack at ORDER (first hit about 108 frames later,
docs/engine/missile.md; a V4 hit is 500 EXPLOSIVE, 100 % on BaseArtilleryArmor = 5 % here).

XML prediction (MaxDamage 2000 = four hits): off loses 15 % a volley from the first; on keeps 100 % through the first
volley, the fourth hit ends the shield early (its status bits drop before Duration 20 s) and the fifth and sixth
take 10 %. Counters: 盾车 = on's health % + 1000 while GENERIC_TOGGLE_STATE; 对照 = off's health %; 盾长 = frames
on's bit has been on (300 for the full Duration).
"""
import re
from pathlib import Path

import labpaths
from maps import probe_range
from parts import Mission, Script, Test, Unit, status
from checks.engine_missile import V4, _sub1

PRESS, ORDER, RUN, HEALTH = 2.0, 3.0, 40.0, 10000.0
V4_SPOTS = ((-100.0, 450.0), (0.0, 460.0), (100.0, 450.0))


def athena(tag):
    uid = 'CNVShield' + tag
    xml = (Path(labpaths.SDK3) / 'SageXML/Allied/Units/AlliedAntiStructureVehicle.xml').read_text(encoding='utf-8-sig')
    xml = _sub1(xml, 'id="AlliedAntiStructureVehicle"', f'id="{uid}"')
    xml = _sub1(xml, 'MaxHealth="400"', f'MaxHealth="{HEALTH:.1f}"')
    if tag == 'off':
        xml, n = re.subn(r'<ActivateModuleSpecialPower\b.*?</ActivateModuleSpecialPower>', '', xml, flags=re.S)
        assert n == 1
    return Unit(uid, xml, abilities={'shield button': 'Command_ToggleShieldSphere'})


def mission():
    m = Mission(name='CampShieldE', map=probe_range, units=[athena('on'), athena('off')])
    for tag, site in (('on', 'base gun'), ('off', 'high gun')):
        m.put('CNVShield' + tag, site, side='p1', role=tag, name='Shield ' + tag)
        for k, (dx, dy) in enumerate(V4_SPOTS, 1):
            m.put(V4, site, dx, dy, side='s1', role=f'{tag} v4 {k}', name=f'Shield {tag} V4 {k}')
    return m


def hold(athenas, pairs):
    """Nobody fires before the order (the V4s would pick their Athena by themselves) and the press, order timers."""
    return ([('UNIT_CHANGE_OBJECT_STATUS', x, 'NO_ATTACK', 1) for x in athenas + [v for v, _ in pairs]]
            + [('SET_MILLISECOND_TIMER', 'Shield press', PRESS), ('SET_MILLISECOND_TIMER', 'Shield order', ORDER)])


def order(pairs):
    return [('UNIT_CHANGE_OBJECT_STATUS', v, 'NO_ATTACK', 0) for v, _ in pairs] + \
        [('NAMED_ATTACK_NAMED', v, target) for v, target in pairs]


def check(m):
    t = Test()
    on, off = m.role('on').name, m.role('off').name
    pairs = [(v.name, target) for target, tag in ((on, 'on'), (off, 'off')) for v in m.roles(f'{tag} v4')]
    t.counters = [('ShieldFrame', '帧数'), ('ShieldOn', '盾车'), ('ShieldOff', '对照'), ('ShieldDrop', '盾长')]
    t.scripts = [
        Script('Test - shield start', [], [('MAP_REVEAL_ALL_PERM', m.player('p1'))] + hold([on, off], pairs)),
        Script('Test - shield frame', [], [('INCREMENT_COUNTER', 1, 'ShieldFrame')], once=False),
        Script('Test - shield press', [('TIMER_EXPIRED', 'Shield press')], [
            ('NAMED_USE_COMMANDBUTTON_ABILITY', m.role(tag).name, m.ability(tag, 'shield button'))
            for tag in ('on', 'off')]),
        Script('Test - shield order', [('TIMER_EXPIRED', 'Shield order')], order(pairs)),
        Script('Test - shield hp on', [], [('SET_UNIT_HEALTH_PERCENTAGE_TO_COUNTER', on, 'ShieldOn')], once=False),
        Script('Test - shield hp off', [], [('SET_UNIT_HEALTH_PERCENTAGE_TO_COUNTER', off, 'ShieldOff')], once=False),
        Script('Test - shield bit', [('UNIT_HAS_OBJECT_STATUS', on, status('GENERIC_TOGGLE_STATE'))],
               [('INCREMENT_COUNTER', 1000, 'ShieldOn'), ('INCREMENT_COUNTER', 1, 'ShieldDrop')], once=False)]
    # 盾车 still 1100 after the first volley landed (f165-f173; bench 1100 to f204): a shield taking nothing reads
    # 1085 by then (review yy #10)
    t.expect = [('帧数', 0, 'ever>=', 450), ('盾车', 12, 'ever>=', 1100)]
    t.bench = [('bench_watch', dict(seconds=RUN, every=0.5, sheet=False, lines=4))]
    return t


# --- n: how many hits end it? (a: the shield went 189 frames, three hits absorbed by f167, then off with no hit) ---
# Three shielded Athenas, lane k under k V4s (k = 1..3; unhit, E153 read the full 20 s). Counter a lane: 1000 x frames
# its bit was on + percent lost.
LANES = ('base gun', 'high gun', 'order gun')
N_LABELS = ('一车', '二车', '三车')


def mission_n():
    m = Mission(name='CampShieldN', map=probe_range, units=[athena('on')])
    for k, site in enumerate(LANES):
        m.put('CNVShieldon', site, side='p1', role=f'athena {k + 1}', name=f'Shield N{k}')
        for j, (dx, dy) in enumerate(V4_SPOTS[:k + 1], 1):
            m.put(V4, site, dx, dy, side='s1', role=f'n{k} v4 {j}', name=f'Shield N{k} V4 {j}')
    return m


def check_n(m):
    t = Test()
    athenas = [r.name for r in m.roles('athena')]
    pairs = [(v.name, a) for k, a in enumerate(athenas) for v in m.roles(f'n{k} v4')]
    t.counters = [('ShieldNFrame', '帧数')] + [(f'ShieldN{k}', lab) for k, lab in enumerate(N_LABELS)]
    t.scripts = [
        Script('Test - shieldn start', [], [('MAP_REVEAL_ALL_PERM', m.player('p1'))] + hold(athenas, pairs)),
        Script('Test - shieldn frame', [], [('INCREMENT_COUNTER', 1, 'ShieldNFrame')], once=False),
        Script('Test - shieldn press', [('TIMER_EXPIRED', 'Shield press')], [
            ('NAMED_USE_COMMANDBUTTON_ABILITY', a, m.ability(f'athena {k + 1}', 'shield button'))
            for k, a in enumerate(athenas)]),
        Script('Test - shieldn order', [('TIMER_EXPIRED', 'Shield order')], order(pairs))]
    for k, a in enumerate(athenas):
        c = f'ShieldN{k}'
        t.scripts.append(Script(f'Test - {c} bit', [('UNIT_HAS_OBJECT_STATUS', a, status('GENERIC_TOGGLE_STATE'))],
                                [('INCREMENT_COUNTER', 1000, c)], once=False))
        t.scripts += [Script(f'Test - {c} lost {p}', [('UNIT_HEALTH', a, 0, 101 - p)], [('INCREMENT_COUNTER', 5, c)])
                      for p in range(5, 100, 5)]
    t.expect = [('帧数', 0, 'ever>=', 450), ('一车', 0, 'ever>=', 100000)]
    t.bench = [('bench_watch', dict(seconds=RUN, every=0.5, sheet=False, lines=4))]
    return t


MISSION = {'engine_shield': mission, 'engine_shieldn': mission_n}
CHECKS = {'engine_shield': {'a': check}, 'engine_shieldn': {'a': check_n}}
