"""InformTarget black box: second run PASS for the qualitative response.

Observed automatic packed:1187051068/87135068/101003068/87135089.
First damage frames87/87/1/87; first shield51/none/3/none.
Actual health68/68/68/89: the side-facing miners take the native105% flank
scalar (raw150/50, 500HP), rather than the nominal70/90 percent.
The51->87 advance is2.4s, not exactly the original2s-window prediction;
arrival estimation and micro phase remain unmodeled. PASS only means the
broad before/after-hit controls below, not the original exact-window claim.
No matched no-InformTarget lane was run, so the nugget's necessity is not
independently isolated. Do not promote whole-item coverage.

PREDICTION before the first run:

Retail SovietMiner: MaxHealth500, TrackIncomingWeaponFireBehavior,
Toggle DEFENSE_SELF_ONLY, look-ahead/behind2s, damage fraction0.2.
Create named retail miners at11s, AFTER the standard10s skirmish wake;
transfer their AI at12s. The unit's TOGGLE command is MICRO_MANAGER too; the instant lane is the
positive control for reaching its self-defense evaluator.
Stationary miners (IMMOBILE, not NO_ATTACK) at450 distance; order20s,
finite single shot, Hammer shell MuzzleVelocity5 units/frame => ~90frames.
UNRESISTABLE150/500=30%, low50/500=10%. InformTarget is on the launching
weapon, beside ProjectileNugget, as the retail Hammer cannon.

Predict: AI high shields BEFORE damage within the last2s of flight;
player high never auto-shields; AI instant can shield only AFTER damage;
AI low never auto-shields. Instant's post-hit response is an AI positive
control, not evidence of advance notification. A scripted press at40s
checks the status detector separately, after automatic measurements end.

Four counters: 1e9*shieldSeenBeforeDamage +1e8*shieldSeenAutomatically
+1e6*framesUntilFirstDamage +1000*framesUntilFirstShield +HPpercent.
After40s player/low manual-control sightings add1e9 as a separate bit.
Frame counts start at the order and freeze at29s (never-seen sentinel).
Damage/shield frame ordering uses script samples, not internal timings.
Round2: WeaponSpeed75 matches MuzzleVelocity5*15, unlike round1
WeaponSpeed999999. Fix the hit latch to UNIT_HEALTH comparison0 (<),
not2 (==); delay manual controls beyond the automatic assertion window.
Do not register InformTarget from a no-response or HP-only result.
"""
import re

from maps import probe_range
from parts import Mission, Script, Test, status
from checks.engine_shot import shell_v4, shot_v4, _nuggets

MINER = 'SovietMiner'
ARMOR = 'SPECIAL_ARMOR_ACTIVE'
COMMAND = 'Command_ToggleArmorUp'
LANES = ('base', 'high', 'order', 'removed')


def mission():
    units = []
    for lane in LANES:
        damage = 50 if lane == 'removed' else 150
        uid = 'CNV_Info_' + lane
        if lane == 'order':
            u = shot_v4(uid, _nuggets(f'<DamageNugget Damage="{damage}" DamageType="UNRESISTABLE" DeathType="NORMAL"/>',
                                      '<InformTargetNugget/>'), reload=1)
        else:
            u = shell_v4(uid, damage=damage, reload=1)
            u.xml = u.xml.replace('DamageType="EXPLOSIVE"', 'DamageType="UNRESISTABLE"')
            # Only the launch weapon gains InformTarget, never the warhead.
            u.xml = re.sub(r'(<ProjectileNugget[^>]*/>)', r'\1<InformTargetNugget/>', u.xml)
            u.files = {k: v.replace('MuzzleVelocity="50.0"', 'MuzzleVelocity="5.0"') for k, v in u.files.items()}
        units.append(u)
        if lane != 'order':
            u.xml = u.xml.replace('WeaponSpeed="999999"', 'WeaponSpeed="75"')
    m = Mission(name='CampInfoAI', map=probe_range, units=units,
                facts={'wake at': 10.0, 'make at': 11.0, 'order at': 20.0, 'freeze at': 29.0})
    # Use B's proven wake actions; the miner's own toggle evaluator needs no Hunt team.
    m.put('AlliedConstructionYard', 'power 1', side='s1', name='Info AI Yard')
    m.waypoint('ai base', 'Info AI Base', 'power 1')
    for lane, u in zip(LANES, units):
        m.put(u.id, lane + ' gun', side='s1' if lane == 'high' else 'p1',
              angle=1.5708, name='Info gun ' + lane)
        m.waypoint(lane + ' target', 'Info Target ' + lane, lane + ' gun', 0, 450)
    m.spawns.add(MINER)
    return m


def check(m):
    t = Test()
    p, enemy = m.player('p1'), m.player('s1')
    start = [('MAP_REVEAL_ALL_PERM', p), ('PLAYER_SET_MONEY', enemy, 0)]
    start += [('SET_MILLISECOND_TIMER', 'Info ' + k, v) for k, v in
              (('wake', 10.0), ('make', 11.0), ('transfer', 12.0), ('fire', 20.0),
               ('stop', 20 + 4/15), ('freeze', 29.0), ('control', 40.0))]
    start += [('UNIT_CHANGE_OBJECT_STATUS', 'Info gun ' + lane, 'NO_ATTACK', 1) for lane in LANES]
    t.scripts.append(Script('Test - start', [], start))
    t.scripts.append(Script('Test - wake', [('TIMER_EXPIRED', 'Info wake')],
                           [('UNIT_AI_TRANSFER_ALL', enemy, 1), ('SKIRMISH_AI_MAKE_BASE', enemy, m.mark('ai base')),
                            ('SKIRMISH_AI_SET_ALL_ENEMY_PLAYERS_PRIORITIES', enemy, 20),
                            ('SKIRMISH_AI_USE_REPAIRS', enemy, 0), ('SKIRMISH_AI_USE_REBUILD_SYSTEM', enemy, 0),
                            ('PLAYER_SET_MONEY', enemy, 0)]))
    make, fire, stop = [], [], []
    for lane in LANES:
        victim, gun = 'Info miner ' + lane, 'Info gun ' + lane
        c = 'CNV_Info_' + lane
        make += [('CREATE_NAMED_ON_TEAM_AT_WAYPOINT', victim, MINER, m.team('p1' if lane == 'high' else 's1'),
                  m.mark(lane + ' target')), ('UNIT_CHANGE_OBJECT_STATUS', victim, 'IMMOBILE', 1)]
        fire += [('UNIT_CHANGE_OBJECT_STATUS', gun, 'NO_ATTACK', 0), ('NAMED_ATTACK_NAMED', gun, victim)]
        stop += [('UNIT_CHANGE_OBJECT_STATUS', gun, 'NO_ATTACK', 1)]
        t.counters.append((c, lane + ' info'))
        active = [('FLAG', 'Info Ordered', 1), ('FLAG', 'Info Frozen', 0)]
        shield = ('UNIT_HAS_OBJECT_STATUS', victim, status(ARMOR))
        # Latch before incrementing first-observation clocks.
        t.scripts += [
            Script('Test - hit ' + lane, active + [('UNIT_HEALTH', victim, 0, 100)],
                   [('SET_FLAG', c + ' hit', 1)]),
            Script('Test - early shield ' + lane, active + [shield, ('FLAG', c + ' hit', 0)],
                   [('INCREMENT_COUNTER', 1000000000, c + ' state')]),
            Script('Test - shield ' + lane, active + [shield],
                   [('SET_FLAG', c + ' shield', 1), ('INCREMENT_COUNTER', 100000000, c + ' state')]),
            Script('Test - hit clock ' + lane, active + [('FLAG', c + ' hit', 0)],
                   [('INCREMENT_COUNTER', 1000000, c + ' state')], once=False),
            Script('Test - shield clock ' + lane, active + [('FLAG', c + ' shield', 0)],
                   [('INCREMENT_COUNTER', 1000, c + ' state')], once=False),
            Script('Test - display ' + lane, [], [('SET_COUNTER', c, 0),
                   ('SET_UNIT_HEALTH_PERCENTAGE_TO_COUNTER', victim, c),
                   ('COUNTER_MATH_COUNTER', c, 0, c + ' state')], once=False)]
    t.scripts += [Script('Test - make', [('TIMER_EXPIRED', 'Info make')], make),
                  Script('Test - transfer', [('TIMER_EXPIRED', 'Info transfer')], [('UNIT_AI_TRANSFER_ALL', enemy, 1)]),
                  Script('Test - fire', [('TIMER_EXPIRED', 'Info fire')], fire + [('SET_FLAG', 'Info Ordered', 1)]),
                  Script('Test - stop', [('TIMER_EXPIRED', 'Info stop')], stop),
                  Script('Test - freeze', [('TIMER_EXPIRED', 'Info freeze')], [('SET_FLAG', 'Info Frozen', 1)])]
    for lane in ('high', 'removed'):
        victim = 'Info miner ' + lane
        c = 'CNV_Info_' + lane
        t.scripts += [Script('Test - control press ' + lane, [('TIMER_EXPIRED', 'Info control')],
                            [('NAMED_USE_COMMANDBUTTON_ABILITY', victim, COMMAND)]),
                      Script('Test - control seen ' + lane, [('FLAG', 'Info Frozen', 1),
                             ('TIMER_EXPIRED', 'Info control'), ('FLAG', c + ' shield', 0),
                             ('UNIT_HAS_OBJECT_STATUS', victim, status(ARMOR))],
                             [('INCREMENT_COUNTER', 1000000000, c + ' state')])]
    # Early response is the distinguishing prediction; no exact first-shield phase presumed.
    t.expect = [('base info', 31.0, '>=', 1100000000, 34.0),
                ('high info', 31.0, '<', 100000000, 34.0),
                ('order info', 31.0, '>=', 100000000, 34.0),
                ('order info', 31.0, '<', 110000000, 34.0),
                ('removed info', 31.0, '<', 100000000, 34.0),
                ('high info', 43, '>=', 1000000000), ('removed info', 43, '>=', 1000000000)]
    t.bench = [('bench_watch', dict(seconds=44, every=1, sheet=False, lines=4))]
    return t


MISSION = {'engine_inform_ai': mission}
CHECKS = {'engine_inform_ai': {'a': check}}
