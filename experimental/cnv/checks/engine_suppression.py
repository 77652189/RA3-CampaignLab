"""Suppression closure, rounds 11-13 (RA3 bench).

SETTLED checks (strict == over the final two seconds):
  threshold: 24x2/3s ->44, 25x2/3s ->59, 5x10/3s ->59,
    6x10/3s ->59. Suppressability=50 is inclusive (48 fails, 50 works).
  speed: zero contribution ->44; 6x10/3s ->59. The data's modifier
    SPEED 75% means 50*.75=37.5; fast independently reads37 at80*.75=60.
    59 is the observed arrival counter; continuous 145/37.5*15 gives58.
    Sub-frame movement/entry is not explained: do not truncate speed to fit59.
  armor / armored: control has zero contribution; high has26x2/3s.
    MaxHealth150, one40 hit: UNRESISTABLE bypasses ARMOR (native0x785370),
    round(110/150*100)=73 on both lanes. EXPLOSIVE base scalar100%,
    ARMOR75% gives round((150-40*.75)/150*100)=80 on the high lane.
    Each health counter is followed by ALIVE=1.
  immune: zero-contribution ordinary control44; Tanya6x10/3s40.
    Speed50/55 explains ceil(145*15/speed)=44/40; Tanya removes the behavior.
  fast: long25/26x2 lanes37/37, from ceil(145/(80*.75/15)).

UNCONFIRMED checks: recorded, not explained. Strict expectations record
bench readings only; these are NOT simulator validation or fitted rules:
  expiry44/44/59/59 (48 long,52 short,50 long,60 long);
  phasea44/44, phaseb44/44 (1s, shots shifted1/3 or2/3s);
  lifetime44/59 (1.1s/2s), fraction59/59 (1.95s);
  duration44/45/44/45 (1s, early/late legs);
  tail56/56 (3s, move at12s; rejected predictions48/51/52).
Short-lived contributions and late recovery still lack a common timing rule.
edge59/59 is also recorded, not explained: moving the entry145->144
rejected strict-boundary-only; fast37 rejected a uniform extra frame.
Round12 archived fraction0030/tail0033 confirmed the counters.

Probe contract: finite burst ordered at6s, guns initially load in1s and
NO_ATTACK stops each before its next clip. Two guns split25/26 hits within
3s. Pressure hits each deal1.5 UNRESISTABLE damage (1% of150HP), so the
pre-move health platform verifies the burst. Armor resets health at9s and
fires one separate40 hit at11s. Walk at9s (duration10s/17s; tail12s),
through a gate145 units away with the destination75 beyond the goal.
SUPPRESSED is a model condition, not a script object status. ForceMove and
Cover are out of scope. Timers/health parameters must be Python floats.

Existing per-hit expiry, sample phase and5s refresh in Sim remain INFERRED;
no new timing rule is selected here. BENCHED_TESTS has only whole-item
registration, so neither SuppressionUpdate nor SuppressionNugget is registered.
"""
import os
import re

from maps import probe_range
from parts import Mission, Script, Test, Unit, square
from checks.engine_clip import ORDER, SAGE, clip_v4

CASES = {'base': (25, 2, 3), 'high': (26, 2, 3),
         'order': (5, 10, 1), 'removed': (6, 10, 1), 'low': (6, 10, 1)}
# Copy clip's 6 s order; shift the round 7 schedule by the same 5 s.
SHIFT = ORDER - 1.0
RUN = 18 + SHIFT


def cases_for(which):
    cases = dict(CASES)
    if which == 'threshold':
        cases.update(base=(24, 2, 3), high=(25, 2, 3),
                     order=(5, 10, 3), removed=(6, 10, 3))
    if which in ('speed', 'armor', 'armored', 'immune'):
        cases.update(order=(5, 0, 3), removed=(6, 10, 3), low=(6, 10, 3))
    if which == 'expiry':
        cases.update(base=(24, 2, 3), high=(26, 2, 1),
                     order=(5, 10, 3), removed=(6, 10, 3))
    if which == 'lifetime':
        cases.update(order=(5, 10, 1.1), removed=(6, 10, 2))
    if which == 'fraction':
        cases.update(order=(5, 10, 1.95), removed=(6, 10, 1.95))
    return cases


def name(lane, part):
    return f'UNIT - CNV Supp {lane} {part}'


def gun(lane, armor=False, second=False, cases=None):
    hits, value, duration = (cases or CASES)[lane]
    if lane in ('base', 'high') and not armor:
        hits = hits // 2 if second else (hits + 1) // 2
    uid = 'CNV_Supp' + lane.title() + ('Armor' if armor else 'Second' if second else '')
    u = clip_v4('bare', hit=40 if armor else 1.5, uid=uid,
                spec=(0, 1 / 15, 1.0, 1 if armor else hits, 'PRE_FIRE', (), RUN, 'pressure'))
    effect = '' if armor else f'<SuppressionNugget Radius="20" Suppression="{value}" DurationSeconds="{duration}s"/>'
    u.xml, n = re.subn(r'<Nuggets>.*?</Nuggets>',
                       f'<Nuggets><DamageNugget Damage="{40 if armor else 1.5}" DamageType="UNRESISTABLE" '
                       f'DeathType="NORMAL" Radius="0"/>{effect}</Nuggets>', u.xml, flags=re.S)
    assert n == 1
    return u


def mission():
    units = [gun(k, a) for k in CASES for a in (False, True)] + [gun(k, second=True) for k in ('base', 'high')]
    m = Mission(name='CampSu', map=probe_range, units=units, facts={})
    for lane in CASES:
        for armor in (False, True):
            m.put('CNV_Supp' + lane.title() + ('Armor' if armor else ''), f'{lane} gun',
                  100 if armor else 0, 0, side='p1', angle=1.5708,
                  name=name(lane, 'armor' if armor else 'gun'))
        if lane in ('base', 'high'):
            m.put('CNV_Supp' + lane.title() + 'Second', f'{lane} gun', -100, 0,
                  side='p1', angle=1.5708, name=name(lane, 'second'))
        # Stasis' benched s1 theirs/chaser follow MOVE_NAMED_UNIT_TO + m.mark().
        # Clip's target is 450 from its V4: retain the inherited 200..500 range.
        m.put('AlliedCommandoTech1' if lane == 'low' else 'AlliedAntiInfantryInfantry',
              f'{lane} gun', 0, 450, side='s1', role=lane, name=name(lane, 'man'))
        m.waypoint(lane + ' goal', 'Supp ' + lane + ' goal', f'{lane} gun', 0, 600)
        m.waypoint(lane + ' late', 'Supp ' + lane + ' late', f'{lane} gun', 0, 750)
        # Walk THROUGH the timing gate, rather than stopping short of a tiny destination square.
        for leg, dy in (('goal', 675), ('late', 825)):
            m.waypoint(lane + ' ' + leg + ' runout', 'Supp ' + lane + ' ' + leg + ' runout',
                       f'{lane} gun', 0, dy)
    return m


def check(m, which):
    cases = cases_for(which)
    m.units = [gun(k, a, cases=cases) for k in cases for a in (False, True)] + [
        gun(k, second=True, cases=cases) for k in ('base', 'high')]
    if which == 'armored':
        for u in m.units:
            if u.id.endswith('Armor'):
                u.xml = u.xml.replace('DamageType="UNRESISTABLE"', 'DamageType="EXPLOSIVE"')
    if which == 'fast':
        with open(os.path.join(SAGE, 'Allied', 'Units', 'AlliedAntiInfantryInfantry.xml'), encoding='utf-8') as f:
            xml = f.read()
        xml = xml.replace('id="AlliedAntiInfantryInfantry"', 'id="CNV_SuppFastMan"', 1)
        xml, n = re.subn(r'(Locomotor="TestReactiveLocomotorHUMAN"\s+Condition="NORMAL"\s+Speed=")50"',
                        r'\g<1>80"', xml)
        assert n == 1
        m.units.append(Unit('CNV_SuppFastMan', xml))
        for k in ('base', 'high'):
            m.role(k).template = 'CNV_SuppFastMan'
            next(o for o in m.objects if o.name == name(k, 'man')).template = 'CNV_SuppFastMan'
    armor_check = which in ('armor', 'armored')
    fire_at = ORDER + {'phasea': 1 / 3, 'phaseb': 2 / 3}.get(which, 0)
    t = Test()
    lanes = (tuple(CASES)[:4] if which in ('threshold', 'expiry') else
             ('order', 'high') if armor_check else
             ('base', 'high') if which in ('edge', 'fast', 'tail') else
             ('order', 'low') if which == 'immune' else ('order', 'removed'))
    # Match benched clip: reveal p1, hold both sides, then release only the gun.
    start = [('MAP_REVEAL_ALL_PERM', m.player('p1'))]
    start += [('UNIT_CHANGE_OBJECT_STATUS', name(k, part), 'NO_ATTACK', 1)
              for k in CASES for part in ('gun', 'armor', 'man')]
    start += [('UNIT_CHANGE_OBJECT_STATUS', name(k, 'second'), 'NO_ATTACK', 1) for k in ('base', 'high')]
    start += [('SET_MILLISECOND_TIMER', 'Supp Fire', float(fire_at)),
              ('SET_MILLISECOND_TIMER', 'Supp Move', 12.0 if which == 'tail' else SHIFT + (5.0 if which == 'duration' else 4.0)),
              ('SET_MILLISECOND_TIMER', 'Supp Late', SHIFT + 12.0),
              ('SET_MILLISECOND_TIMER', 'Supp Armor', SHIFT + 6.0)]
    t.scripts.append(Script('Test - start', [], start))
    fire = []
    for k in lanes:
        fire += [('UNIT_CHANGE_OBJECT_STATUS', name(k, 'gun'), 'NO_ATTACK', 0),
                 ('NAMED_ATTACK_NAMED', name(k, 'gun'), name(k, 'man'))]
        if k in ('base', 'high'):
            fire += [('UNIT_CHANGE_OBJECT_STATUS', name(k, 'second'), 'NO_ATTACK', 0),
                     ('NAMED_ATTACK_NAMED', name(k, 'second'), name(k, 'man'))]
    # Initial clips load in 1 s, before ORDER. Stop inside the reload gap:
    # first shot +2 frames, then 2 frames per shot; next clip is 15 frames away.
    for k in lanes:
        for part in ('gun', 'second') if k in ('base', 'high') else ('gun',):
            hits = cases[k][0]
            if k in ('base', 'high'):
                hits = hits // 2 if part == 'second' else (hits + 1) // 2
            timer = 'Supp Stop ' + k + part
            start.append(('SET_MILLISECOND_TIMER', timer, fire_at + (2 * hits + 2) / 15))
            t.scripts.append(Script('Test - stop ' + k + part, [('TIMER_EXPIRED', timer)],
                                    [('UNIT_CHANGE_OBJECT_STATUS', name(k, part), 'NO_ATTACK', 1)]))
    fire.append(('SET_FLAG', 'Supp Ordered', 1))
    t.scripts.append(Script('Test - fire', [('TIMER_EXPIRED', 'Supp Fire')], fire))
    for k in lanes:
        man = m.role(k).name
        if armor_check:
            t.scripts.append(Script('Test - reset ' + k, [('TIMER_EXPIRED', 'Supp Move')], [('UNIT_SET_HEALTH', man, 100.0)]))
            t.scripts.append(Script('Test - armor ' + k, [('TIMER_EXPIRED', 'Supp Armor')], [
                ('UNIT_CHANGE_OBJECT_STATUS', name(k, 'armor'), 'NO_ATTACK', 0),
                ('NAMED_ATTACK_NAMED', name(k, 'armor'), man)]))
            timer = 'Supp Stop armor ' + k
            start.append(('SET_MILLISECOND_TIMER', timer, SHIFT + 6.0 + 4 / 15))
            t.scripts.append(Script('Test - stop armor ' + k, [('TIMER_EXPIRED', timer)],
                                    [('UNIT_CHANGE_OBJECT_STATUS', name(k, 'armor'), 'NO_ATTACK', 1)]))
            hp, alive = 'CNV_Supp_' + k + '_HP', 'CNV_Supp_' + k + '_ALIVE'
            t.counters += [(hp, k + ' 血'), (alive, k + ' 活')]
            t.scripts += [Script('Test - health ' + k, [], [('SET_UNIT_HEALTH_PERCENTAGE_TO_COUNTER', man, hp)], once=False),
                          Script('Test - alive ' + k, [], [('SET_COUNTER', alive, 1)], once=False),
                          Script('Test - dead ' + k, [('NAMED_DESTROYED', man)], [('SET_COUNTER', alive, 0)], once=False)]
            continue
        for leg, timer in [('goal', 'Supp Move')] + ([('late', 'Supp Late')] if which == 'duration' else []):
            wp, c, flag = m.mark(k + ' ' + leg + ' runout'), 'CNV_Supp_' + k + '_' + leg, 'Supp moving ' + k + leg
            x, y = m.point(k + ' ' + leg)
            area = 'Supp area ' + k + leg
            # Crush uses square(..., 40); keep the existing y-5 entry line,
            # but allow lateral pathing drift rather than a ten-unit-wide slit.
            t.areas[area] = square(x, y + 35 - (1 if which == 'edge' else 0), 40)
            t.counters.append((c, k + ' ' + leg))
            # Before walking, reuse the goal line for health: 1.5 damage is
            # one percent of the ordinary man's 150 HP, making finite bursts visible.
            # The permanent started flag prevents arrival from overwriting frame counts.
            started = 'Supp started ' + k + leg
            if leg == 'goal':
                t.scripts.append(Script('Test - burst health ' + k,
                                        [('FLAG', started, 0)],
                                        [('SET_UNIT_HEALTH_PERCENTAGE_TO_COUNTER', man, c)], once=False))
            t.scripts.append(Script('Test - move ' + k + leg, [('TIMER_EXPIRED', timer)],
                                    [('SET_COUNTER', c, 0), ('SET_FLAG', started, 1),
                                     ('MOVE_NAMED_UNIT_TO', man, wp), ('SET_FLAG', flag, 1)]))
            t.scripts.append(Script('Test - arrived ' + k + leg, [('NAMED_INSIDE_AREA', man, area)], [('NAMED_STOP', man), ('SET_FLAG', flag, 0)]))
            t.scripts.append(Script('Test - frames ' + k + leg, [('FLAG', flag, 1)], [('INCREMENT_COUNTER', 1, c)], once=False))
    readings = {'threshold': (44, 59, 59, 59), 'expiry': (44, 44, 59, 59), 'speed': (44, 59),
                 'armor': (73, 1, 73, 1), 'armored': (73, 1, 80, 1),
                 'phasea': (44, 44), 'phaseb': (44, 44), 'lifetime': (44, 59), 'edge': (59, 59),
                 'fraction': (59, 59), 'fast': (37, 37), 'tail': (56, 56),
                 'duration': (44, 45, 44, 45), 'immune': (44, 40)}
    # judge has no 'at end' operator: require equality throughout the final 2 s.
    t.expect = [(label, RUN - 2, '==', value, RUN)
                for (_, label), value in zip(t.counters, readings[which])]
    # Keep every lane visible for the entire observation; no gun-digit takeover.
    t.bench = [('bench_watch', dict(seconds=RUN, every=.5, sheet=False, lines=len(t.counters)))]
    return t


MISSION = {'engine_suppression': mission}
CHECKS = {'engine_suppression': {k: (lambda m, k=k: check(m, k))
                               for k in ('threshold', 'expiry', 'phasea', 'phaseb', 'lifetime', 'fraction', 'edge', 'fast', 'tail',
                                         'speed', 'armor', 'armored', 'duration', 'immune')}}
