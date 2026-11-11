"""Creation-veterancy upgrades each add one level (retail BaseVehicle), capped at 4.

PREDICT: one HEROIC creation grant does not itself make a heroic unit; three
distinct creation upgrades do. Repeating an already-held upgrade adds no level.
Read the mirage's heroic WEAPON_UPGRADED_01 bit, with no combat or experience.
Bench 2026-11-10 PASS: s1-s4 0/0/1/0, s5-s13 0/1/1/0.
These are heroic-state booleans, not numeric rank readings.
"""
from maps import probe_range
from parts import Mission, Script, Test, status, counted, square

CREATION = tuple('Upgrade_CreationVeterancy_' + x for x in ('VETERAN', 'ELITE', 'HEROIC'))


def mission():
    m = Mission(name='CampLevel', map=probe_range, units=[])
    for lane in ('base', 'high', 'order', 'removed'):
        m.put('AlliedAntiVehicleVehicleTech3', lane + ' gun', role=lane,
              name='Level ' + lane)
    return m


def check(m):
    t = Test()
    grant = lambda lane, up: ('NAMED_RECEIVE_UPGRADE', up, m.role(lane).name)
    t.scripts = [Script('Test - start', [], [
        ('MAP_REVEAL_ALL_PERM', m.player('p1')),
        ('SET_MILLISECOND_TIMER', 'Level late', 6.0),
        grant('high', CREATION[2]),
        *[grant('order', up) for up in CREATION],
        *[grant('removed', CREATION[0]) for _ in range(3)]]),
        Script('Test - late', [('TIMER_EXPIRED', 'Level late')], [
            grant('high', CREATION[0]), grant('high', CREATION[1])])]
    for lane in ('base', 'high', 'order', 'removed'):
        c = 'Level ' + lane
        t.counters.append((c, lane + ' rank'))
        t.scripts += [
            Script('Test - zero ' + lane, [], [('SET_COUNTER', c, 0)], once=False),
            Script('Test - heroic ' + lane,
                   [('UNIT_HAS_OBJECT_STATUS', m.role(lane).name, status('WEAPON_UPGRADED_01'))],
                   [('SET_COUNTER', c, 1)], once=False)]
    t.expect = [('base rank', 2, '==', 0, 12), ('high rank', 2, '==', 0, 4),
                ('high rank', 8, '==', 1, 12), ('order rank', 2, '==', 1, 12),
                ('removed rank', 2, '==', 0, 12)]
    t.bench = [('bench_watch', dict(seconds=12.0, every=.5, sheet=False, lines=4))]
    return t


MISSION = {'engine_levelup': mission}
CHECKS = {'engine_levelup': {'a': check}}


def regrant_check(m):
    """PREDICT: removing creation grants keeps rank; regrant adds another level.

    Retail BaseVehicle's three modules each gain one level, cap four, and use
    UpgradeModuleData's Permanent=false default. This is a prediction from data,
    not from the simulator's existing first-activation-only approximation.
    Lanes: one veteran grant; veteran removed/regranted twice; veteran+elite
    then veteran removed/regranted; all three grants then all three removed.
    Heroic bits: 0/0/0/1 initially and after removal, 0/0/1/1 after the first
    regrant, 0/1/1/1 after the second. No enemies, attacks or combat XP.
    Stable windows allow dispatch; exact activation frames remain INFERRED.
    Bench 2026-11-11 PASS: 0/0/0/1 -> 0/0/1/1 -> 0/1/1/1.
    """
    t = Test()
    lanes = ('base', 'high', 'order', 'removed')
    action = lambda kind, lane, up: ('NAMED_' + kind + '_UPGRADE', up, m.role(lane).name)
    start = [('MAP_REVEAL_ALL_PERM', m.player('p1'))]
    for sec, timer in ((6, 'remove'), (12, 'regrant'), (18, 'remove again'), (24, 'regrant again')):
        start.append(('SET_MILLISECOND_TIMER', 'Level ' + timer, float(sec)))
    for lane, count in zip(lanes, (1, 1, 2, 3)):
        start.append(('UNIT_CHANGE_OBJECT_STATUS', m.role(lane).name, 'NO_ATTACK', 1))
        start += [action('RECEIVE', lane, up) for up in CREATION[:count]]
    steps = [
        ('remove', [action('REMOVE', lane, CREATION[0]) for lane in ('high', 'order')]
         + [action('REMOVE', 'removed', up) for up in CREATION]),
        ('regrant', [action('RECEIVE', lane, CREATION[0]) for lane in ('high', 'order')]),
        ('remove again', [action('REMOVE', 'high', CREATION[0])]),
        ('regrant again', [action('RECEIVE', 'high', CREATION[0])])]
    t.scripts = [Script('Test - start', [], start)] + [
        Script('Test - ' + timer, [('TIMER_EXPIRED', 'Level ' + timer)], actions)
        for timer, actions in steps]
    for lane in lanes:
        counter = 'Level regrant ' + lane
        t.counters.append((counter, lane + ' heroic'))
        t.scripts += [
            Script('Test - zero ' + lane, [], [('SET_COUNTER', counter, 0)], once=False),
            Script('Test - heroic ' + lane,
                   [('UNIT_HAS_OBJECT_STATUS', m.role(lane).name, status('WEAPON_UPGRADED_01'))],
                   [('SET_COUNTER', counter, 1)], once=False)]
    for first, last, values in ((2, 4, (0, 0, 0, 1)), (8, 10, (0, 0, 0, 1)),
                                (14, 16, (0, 0, 1, 1)), (20, 22, (0, 0, 1, 1)),
                                (26, 28, (0, 1, 1, 1))):
        t.expect += [(lane + ' heroic', first, '==', value, last)
                     for lane, value in zip(lanes, values)]
    t.bench = [('bench_watch', dict(seconds=28.0, every=.5, sheet=False, lines=4))]
    return t


CHECKS['engine_levelup']['b'] = regrant_check


def elite_heroic_regrant_check(m):
    """PREDICT: elite and heroic creation grants each rearm after removal.

    Retail BaseVehicle has gain=1, cap=4 for each of the three triggers;
    Permanent defaults to false. Each tested lane starts with only one grant,
    so neither the initial grant nor first regrant should set the heroic bit.
    The second regrant should. Keep the all-grants-removed control heroic.
    Stable windows only: exact dispatch frames remain INFERRED.
    Bench 2026-11-11 PASS: 0/0/0/1 through first regrant, then 0/1/1/1.
    """
    t = Test()
    lanes = ('base', 'high', 'order', 'removed')
    triggers = {'high': CREATION[1], 'order': CREATION[2]}
    action = lambda kind, lane, up: ('NAMED_' + kind + '_UPGRADE', up, m.role(lane).name)
    start = [('MAP_REVEAL_ALL_PERM', m.player('p1'))]
    for sec, timer in ((6, 'remove'), (12, 'regrant'), (18, 'remove again'), (24, 'regrant again')):
        start.append(('SET_MILLISECOND_TIMER', 'Level ' + timer, float(sec)))
    for lane in lanes:
        start.append(('UNIT_CHANGE_OBJECT_STATUS', m.role(lane).name, 'NO_ATTACK', 1))
        grants = CREATION if lane == 'removed' else (triggers.get(lane, CREATION[0]),)
        start += [action('RECEIVE', lane, up) for up in grants]
    steps = []
    for timer, kind in (('remove', 'REMOVE'), ('regrant', 'RECEIVE'),
                        ('remove again', 'REMOVE'), ('regrant again', 'RECEIVE')):
        actions = [action(kind, lane, up) for lane, up in triggers.items()]
        if timer == 'remove':
            actions += [action('REMOVE', 'removed', up) for up in CREATION]
        steps.append(Script('Test - ' + timer, [('TIMER_EXPIRED', 'Level ' + timer)], actions))
    t.scripts = [Script('Test - start', [], start)] + steps
    for lane in lanes:
        counter = 'Level regrant ' + lane
        t.counters.append((counter, lane + ' heroic'))
        t.scripts += [
            Script('Test - zero ' + lane, [], [('SET_COUNTER', counter, 0)], once=False),
            Script('Test - heroic ' + lane,
                   [('UNIT_HAS_OBJECT_STATUS', m.role(lane).name, status('WEAPON_UPGRADED_01'))],
                   [('SET_COUNTER', counter, 1)], once=False)]
    for first, last, values in ((2, 4, (0, 0, 0, 1)), (8, 10, (0, 0, 0, 1)),
                                (14, 16, (0, 0, 0, 1)), (20, 22, (0, 0, 0, 1)),
                                (26, 28, (0, 1, 1, 1))):
        t.expect += [(lane + ' heroic', first, '==', value, last)
                     for lane, value in zip(lanes, values)]
    t.bench = [('bench_watch', dict(seconds=28.0, every=.5, sheet=False, lines=4))]
    return t


CHECKS['engine_levelup']['c'] = elite_heroic_regrant_check


def damage_mission():
    m = mission()
    m.name = 'CampLevelD'
    for lane in ('base', 'high', 'order', 'removed'):
        m.put('JapanAntiVehicleVehicleTech1', lane + ' gun', 0, 100,
              side='s1', role=lane + ' target', name='Level target ' + lane)
    return m


def damage_check(m):
    """PREDICT: one shot, 200/250/250/312.5 damage into 380 HP, 100% armor.

    Creation grants add the veteran DAMAGE_MULT125 as well as the heroic gun.
    Direct veterancy upgrades (engine_statusbits a) only selected the gun.
    Bench 11-10 PASS: s5-s15 47/34/34/17, with no Tsunami healing.
    """
    t = Test()
    lanes = ('base', 'high', 'order', 'removed')
    start = [('MAP_REVEAL_ALL_PERM', m.player('p1')),
             ('SET_MILLISECOND_TIMER', 'Level fire', 6.0),
             ('SET_MILLISECOND_TIMER', 'Level stop', 6 + 4 / 15)]
    fire, stop = [], []
    for n, lane in enumerate(lanes):
        gun, target = m.role(lane).name, m.role(lane + ' target').name
        start += [('UNIT_CHANGE_OBJECT_STATUS', name, 'NO_ATTACK', 1) for name in (gun, target)]
        start += [('NAMED_RECEIVE_UPGRADE', up, gun) for up in CREATION[:n]]
        fire += [('UNIT_CHANGE_OBJECT_STATUS', gun, 'NO_ATTACK', 0), ('NAMED_ATTACK_NAMED', gun, target)]
        stop += [('UNIT_CHANGE_OBJECT_STATUS', gun, 'NO_ATTACK', 1)]
        counted('Level hp ' + lane, lane + ' HP', t, health=target)
    t.scripts[:0] = [Script('Test - start', [], start),
                     Script('Test - fire', [('TIMER_EXPIRED', 'Level fire')], fire),
                     Script('Test - stop', [('TIMER_EXPIRED', 'Level stop')], stop)]
    t.expect = [(lane + ' HP', 10, '==', hp, 14) for lane, hp in zip(lanes, (47, 34, 34, 17))]
    t.bench = [('bench_watch', dict(seconds=14.0, every=.5, sheet=False, lines=4))]
    return t


MISSION['engine_leveldamage'] = damage_mission
CHECKS['engine_leveldamage'] = {'a': damage_check}


def health_mission():
    m = mission()
    m.name = 'CampLevelH'
    return m


def health_check(m):
    """PREDICT: 500/500/625/625 max HP leaves 80/80/84/84% after NAMED_DAMAGE 100.

    Freeze each reading immediately after script damage in the same script, before
    heroic AutoHeal can tick. No enemy, weapon, armor or combat experience involved.
    This check measures promotion from full health; check b covers injured promotion.
    Bench 2026-11-10 PASS: frozen counters s4-s14 80/80/84/84.
    """
    t = Test()
    start = [('MAP_REVEAL_ALL_PERM', m.player('p1')),
             ('SET_MILLISECOND_TIMER', 'Level hurt', 6.0)]
    hurt = []
    for n, lane in enumerate(('base', 'high', 'order', 'removed')):
        name, counter = m.role(lane).name, 'Level frozen ' + lane
        start += [('UNIT_CHANGE_OBJECT_STATUS', name, 'NO_ATTACK', 1)]
        start += [('NAMED_RECEIVE_UPGRADE', up, name) for up in CREATION[:n]]
        start += [('SET_COUNTER', counter, -1)]
        hurt += [('NAMED_DAMAGE', name, 100),
                 ('SET_UNIT_HEALTH_PERCENTAGE_TO_COUNTER', name, counter)]
        t.counters.append((counter, lane + ' frozen HP'))
    t.scripts = [Script('Test - start', [], start),
                 Script('Test - freeze damage', [('TIMER_EXPIRED', 'Level hurt')], hurt)]
    t.expect = [(lane + ' frozen HP', 8, '==', hp, 12)
                for lane, hp in zip(('base', 'high', 'order', 'removed'), (80, 80, 84, 84))]
    t.bench = [('bench_watch', dict(seconds=12.0, every=.5, sheet=False, lines=4))]
    return t


MISSION['engine_levelhealth'] = health_mission
CHECKS['engine_levelhealth'] = {'a': health_check}


def injured_health_check(m):
    """PREDICT: injured elite promotion preserves health fraction: 50/80/50/20.

    Base is an unpromoted half-health control. The other lanes start at
    400/250/100 of 500 HP, then gain veteran and elite at six seconds.
    HEALTH_MULT125 predicts 500/312.5/125 of 625 HP. Keeping absolute HP
    would read 64/40/16; adding the max-HP delta would read 84/60/36.
    No heroic grant, healing, enemy, combat experience or player input.
    Freeze at eight seconds to allow upgrade dispatch to finish. At twelve
    seconds deal another 100 damage and freeze again: 30/64/34/4. This second
    reading proves max HP increased; unchanged percentages alone cannot.
    Bench 2026-11-11 PASS: 50/80/50/20 before the hit, 30/64/34/4 after.
    """
    t = Test()
    start = [('MAP_REVEAL_ALL_PERM', m.player('p1')),
             ('SET_MILLISECOND_TIMER', 'Level promote injured', 6.0),
             ('SET_MILLISECOND_TIMER', 'Level freeze injured', 8.0),
             ('SET_MILLISECOND_TIMER', 'Level verify injured', 12.0)]
    promote, freeze, verify = [], [], []
    lanes = ('base', 'high', 'order', 'removed')
    for lane, damage in zip(lanes, (250, 100, 250, 400)):
        name, counter = m.role(lane).name, 'Level injured ' + lane
        start += [('UNIT_CHANGE_OBJECT_STATUS', name, 'NO_ATTACK', 1),
                  ('NAMED_DAMAGE', name, damage), ('SET_COUNTER', counter, -1)]
        if lane != 'base':
            promote += [('NAMED_RECEIVE_UPGRADE', up, name) for up in CREATION[:2]]
        freeze += [('SET_UNIT_HEALTH_PERCENTAGE_TO_COUNTER', name, counter)]
        verify += [('NAMED_DAMAGE', name, 100),
                   ('SET_UNIT_HEALTH_PERCENTAGE_TO_COUNTER', name, counter)]
        t.counters.append((counter, lane + ' injured HP'))
    t.scripts = [Script('Test - start', [], start),
                 Script('Test - promote injured', [('TIMER_EXPIRED', 'Level promote injured')], promote),
                 Script('Test - freeze injured', [('TIMER_EXPIRED', 'Level freeze injured')], freeze),
                 Script('Test - verify injured', [('TIMER_EXPIRED', 'Level verify injured')], verify)]
    t.expect = [(lane + ' injured HP', 9, '==', hp, 10)
                for lane, hp in zip(lanes, (50, 80, 50, 20))]
    t.expect += [(lane + ' injured HP', 14, '==', hp, 16)
                 for lane, hp in zip(lanes, (30, 64, 34, 4))]
    t.bench = [('bench_watch', dict(seconds=16.0, every=.5, sheet=False, lines=4))]
    return t


CHECKS['engine_levelhealth']['b'] = injured_health_check


def range_mission():
    m = mission()
    m.name = 'CampLevelR'
    for lane, distance in zip(('base', 'high', 'order', 'removed'), (220, 220, 260, 260)):
        m.put('JapanAntiVehicleVehicleTech1', lane + ' gun', 0, distance,
              side='s1', role=lane + ' target', name='Level range target ' + lane)
        m.waypoint(lane + ' target', 'Level range mark ' + lane, lane + ' gun', 0, distance)
    return m


def range_check(m):
    """PREDICT: normal/heroic at 220, normal/heroic at 260: only heroic 220 hits.

    Retail normal/heroic guns have AttackRange 125/150; Unit_Heroic RANGE125%
    makes the latter 187.5. Bounding radii total 49.01, so even the heroic gun
    without the modifier cannot reach 220 (limit 199.01); with it 260 is out.
    All objects IMMOBILE, shooters HOLD_FIRE; only named orders may shoot.
    Four-frame fire window, no kills or XP. Counter = target HP percent +
    10000*heroic + 1000*ever-gun-moved + 100000*ever-target-moved. Movement
    means leaving a 2-unit square, latched throughout; margins exceed 20 units.
    Stable prediction: 100/10100/100/10100 -> 100/10017/100/10100.
    Bench 2026-11-11 PASS: s1-s4 initial, s5-s16 final, no movement flags.
    Exact activation/shot frames and the precise range boundary remain INFERRED.
    """
    t = Test()
    start = [('MAP_REVEAL_ALL_PERM', m.player('p1')),
             ('PLAYER_SET_MONEY', m.player('s1'), 0),
             ('SET_MILLISECOND_TIMER', 'Level range fire', 6.0),
             ('SET_MILLISECOND_TIMER', 'Level range stop', 6 + 4 / 15)]
    fire, stop = [], []
    for lane in ('base', 'high', 'order', 'removed'):
        gun, target = m.role(lane).name, m.role(lane + ' target').name
        start += [('UNIT_CHANGE_OBJECT_STATUS', n, bit, 1)
                  for n in (gun, target) for bit in ('NO_ATTACK', 'IMMOBILE')]
        start.append(('UNIT_SET_STANCE', gun, 3))  # HOLD_FIRE, explicit orders still fire
        if lane in ('high', 'removed'):
            start += [('NAMED_RECEIVE_UPGRADE', up, gun) for up in CREATION]
        fire += [('UNIT_CHANGE_OBJECT_STATUS', gun, 'NO_ATTACK', 0), ('NAMED_ATTACK_NAMED', gun, target)]
        stop.append(('UNIT_CHANGE_OBJECT_STATUS', gun, 'NO_ATTACK', 1))
        counter = 'Level range ' + lane
        t.counters.append((counter, lane + ' range'))
        for name, point in ((gun, m.site(lane + ' gun')[:2]),
                            (target, m.point(lane + ' target'))):
            area = 'Level range pad ' + name
            flag = area + ' moved'
            t.areas[area] = square(*point, 2.0)
            t.scripts.append(Script('Test - latch ' + name, [('NAMED_OUTSIDE_AREA', name, area)],
                                    [('SET_FLAG', flag, 1)]))
        t.scripts.append(Script('Test - range HP ' + lane, [],
                                [('SET_UNIT_HEALTH_PERCENTAGE_TO_COUNTER', target, counter)], once=False))
        for name, weight in ((gun, 1000), (target, 100000)):
            t.scripts.append(Script('Test - range moved ' + name,
                                    [('FLAG', 'Level range pad ' + name + ' moved', 1)],
                                    [('INCREMENT_COUNTER', weight, counter)], once=False))
        t.scripts.append(Script('Test - range heroic ' + lane,
                                [('UNIT_HAS_OBJECT_STATUS', gun, status('WEAPON_UPGRADED_01'))],
                                [('INCREMENT_COUNTER', 10000, counter)], once=False))
    t.scripts[:0] = [Script('Test - start', [], start),
                     Script('Test - range fire', [('TIMER_EXPIRED', 'Level range fire')], fire),
                     Script('Test - range stop', [('TIMER_EXPIRED', 'Level range stop')], stop)]
    for first, last, values in ((2, 4, (100, 10100, 100, 10100)),
                                (10, 14, (100, 10017, 100, 10100))):
        t.expect += [(lane + ' range', first, '==', value, last)
                     for lane, value in zip(('base', 'high', 'order', 'removed'), values)]
    t.bench = [('bench_watch', dict(seconds=14.0, every=.5, sheet=False, lines=4))]
    return t


MISSION['engine_levelrange'] = range_mission
CHECKS['engine_levelrange'] = {'a': range_check}


def rate_mission():
    m = mission()
    m.name = 'CampLevelRate'
    for lane in ('base', 'high', 'order', 'removed'):
        m.put('SovietConstructionYard', lane + ' gun', 0, 150,
              side='s1', role=lane + ' target', name='Level rate target ' + lane)
    return m


def rate_check(m):
    """Four retail Mirage guns: normal, direct heroic upgrade, rank4, rank3.

    PREDICT: both retail guns fire1.5/reload0.1 = 23+2 = 25 frames.
    Initial ceil-parts candidate21 predicted four heroic hits, but the first
    run read68% (five). Its reversed span conditions made intervals unreadable.
    Corrected run distinguishes effective20 (five hits) from21 (four hits).
    Bench2026-11-11 at x1 PASS:252525/252525/202020/252525, then84/80/68/80.
    This only distinguishes the effective cycle, not individual timing parts.
    Counter packs three successive inter-hit spans as a + 100*b + 10000*c;
    after second14 switches to final target HP (84/80/68/80). Four/five shots,
    no kill/XP, repair or target healing; order6, stop11.5, both IMMOBILE.
    Exact first-hit timing is outside this probe's claim.
    """
    t = Test()
    start = [('MAP_REVEAL_ALL_PERM', m.player('p1')),
             ('PLAYER_SET_MONEY', m.player('s1'), 0),
             ('SET_MILLISECOND_TIMER', 'Level rate fire', 6.0),
             ('SET_MILLISECOND_TIMER', 'Level rate stop', 11.5),
             ('SET_MILLISECOND_TIMER', 'Level rate hp', 14.0)]
    fire, stop = [], []
    for lane, grants, loss in zip(('base', 'high', 'order', 'removed'),
                                  ((), ('Upgrade_Veterancy_HEROIC',), CREATION, CREATION[:2]),
                                  (4, 5, 6.25, 5)):
        gun, target = m.role(lane).name, m.role(lane + ' target').name
        start += [('UNIT_CHANGE_OBJECT_STATUS', n, bit, 1)
                  for n in (gun, target) for bit in ('NO_ATTACK', 'IMMOBILE')]
        start.append(('UNIT_SET_STANCE', gun, 3))
        start += [('NAMED_RECEIVE_UPGRADE', up, gun) for up in grants]
        fire += [('UNIT_CHANGE_OBJECT_STATUS', gun, 'NO_ATTACK', 0), ('NAMED_ATTACK_NAMED', gun, target)]
        stop.append(('UNIT_CHANGE_OBJECT_STATUS', gun, 'NO_ATTACK', 1))
        counter = 'Level rate ' + lane
        t.counters.append((counter, lane + ' timing'))
        # Integer-percent plateaux uniquely identify shots1..3; unlike total
        # damage this holds all three intervals independently to the readings.
        for shot, weight in ((1, 1), (2, 100), (3, 10000)):
            upper = int(100 - shot * loss)
            lower = int(100 - (shot + 1) * loss)
            t.scripts.append(Script('Test - rate span ' + lane + str(shot),
                                    [('UNIT_HEALTH', target, 0, upper + 1),
                                     ('UNIT_HEALTH', target, 4, lower)],
                                    [('INCREMENT_COUNTER', weight, counter)], once=False))
        t.scripts.append(Script('Test - rate final HP ' + lane,
                                [('TIMER_EXPIRED', 'Level rate hp')],
                                [('SET_UNIT_HEALTH_PERCENTAGE_TO_COUNTER', target, counter)], once=False))
    t.scripts[:0] = [Script('Test - start', [], start),
                     Script('Test - rate fire', [('TIMER_EXPIRED', 'Level rate fire')], fire),
                     Script('Test - rate stop', [('TIMER_EXPIRED', 'Level rate stop')], stop)]
    for first, last, values in ((12, 13, (252525, 252525, 202020, 252525)),
                                (15, 17, (84, 80, 68, 80))):
        t.expect += [(lane + ' timing', first, '==', value, last)
                     for lane, value in zip(('base', 'high', 'order', 'removed'), values)]
    t.bench = [('bench_watch', dict(seconds=17.0, every=.5, sheet=False, lines=4))]
    return t


MISSION['engine_levelrate'] = rate_mission
CHECKS['engine_levelrate'] = {'a': rate_check}


SHROUD_LANES = ('base', 'high', 'order', 'removed')


def shroud_mission():
    m = mission()
    m.name = 'CampLevelFog'
    for lane, distance in zip(SHROUD_LANES, (580, 580, 750, 750)):
        for tag, dy in (('target', distance), ('near', 200)):
            m.put('JapanAntiVehicleVehicleTech1', lane + ' gun', 0, dy,
                  side='s1', role=lane + ' ' + tag, name='Level fog ' + lane + ' ' + tag)
    return m


def shroud_check(m):
    """PREDICT: retail Mirage shroud500 -> heroic625; baseline VisionRange200.

    Normal/heroic at580, normal/heroic at750; an enemy at200 is the positive
    visibility control in each lane. Creation grants at6s, no attack/reveal.
    Counter=near discovered +10*target discovered +100*heroic status,
    +1000*ever moved (any of the lane's three objects). All IMMOBILE/NO_ATTACK.
    Lanes1500 apart, flat ground; even combined bounding radii (<60) cannot
    bridge the normal580 or heroic750 gaps. Precise fog cell edges and heroic
    VISION/auto-acquire are unmeasured; discovery cannot establish their values.
    Stable windows2-4:1/1/1/1;18-22:1/111/1/101. No discovery latch.
    Bench2026-11-11 x1 PASS: s1-s4 1/1/1/1; s5-s23 1/111/1/101.
    """
    t = Test()
    start = [('PLAYER_SET_MONEY', m.player('s1'), 0),
             ('SET_MILLISECOND_TIMER', 'Level fog promote', 6.0)]
    promote = []
    for lane in SHROUD_LANES:
        gun = m.role(lane).name
        if lane in ('high', 'removed'):
            promote += [('NAMED_RECEIVE_UPGRADE', up, gun) for up in CREATION]
        c, moved = 'Level fog ' + lane, 'Level fog moved ' + lane
        t.counters.append((c, lane + ' fog'))
        for role in (lane, lane + ' target', lane + ' near'):
            obj = m.role(role)
            start += [('UNIT_CHANGE_OBJECT_STATUS', obj.name, bit, 1) for bit in ('IMMOBILE', 'NO_ATTACK')]
            placed = next(o for o in m.objects if o.name == obj.name)
            t.areas[obj.name] = square(placed.x, placed.y, 2.0)
            t.scripts.append(Script('Test - fog latch ' + role, [('NAMED_OUTSIDE_AREA', obj.name, obj.name)],
                                    [('SET_FLAG', moved, 1)]))
        t.scripts.append(Script('Test - fog reset ' + lane, [], [('SET_COUNTER', c, 0)], once=False))
        for tag, weight in (('near', 1), ('target', 10)):
            t.scripts.append(Script('Test - fog see ' + lane + tag,
                                    [('NAMED_DISCOVERED', m.player('p1'), m.role(lane + ' ' + tag).name)],
                                    [('INCREMENT_COUNTER', weight, c)], once=False))
        t.scripts.append(Script('Test - fog heroic ' + lane,
                                [('UNIT_HAS_OBJECT_STATUS', gun, status('WEAPON_UPGRADED_01'))],
                                [('INCREMENT_COUNTER', 100, c)], once=False))
        t.scripts.append(Script('Test - fog moved ' + lane, [('FLAG', moved, 1)],
                                [('INCREMENT_COUNTER', 1000, c)], once=False))
    t.scripts[:0] = [Script('Test - start', [], start),
                     Script('Test - fog promote', [('TIMER_EXPIRED', 'Level fog promote')], promote)]
    for first, last, values in ((2, 4, (1, 1, 1, 1)), (18, 22, (1, 111, 1, 101))):
        t.expect += [(lane + ' fog', first, '==', value, last) for lane, value in zip(SHROUD_LANES, values)]
    t.bench = [('bench_watch', dict(seconds=22.0, every=1, sheet=False, lines=4))]
    return t


MISSION['engine_levelshroud'] = shroud_mission
CHECKS['engine_levelshroud'] = {'a': shroud_check}
