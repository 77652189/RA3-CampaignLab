"""The attack dog's pounce (A, 11-26; handoff-e.md E248: the simulator's dog stops 20 off and never bites). Retail
AlliedScoutInfantry's AlliedScoutInfantryMaul (Weapon.xml): AttackRange 30, ProjectileSelf at WeaponSpeed 125,
FiringDuration 0.5 s ("the time the dog should spend in the air"), ClipReloadTime 1.5 s. At the leap, on the target:
1 UNRESISTABLE (BITTEN), MaulAttributeModifier 1.5 s (IGNORE_AI_COMMAND NO_AUTO_ACQUIRE NO_ATTACK, SPEED 0%); on
landing (its warhead, HitStoredTarget): MaulLanded 2 s (NO_ATTACK, BEING_MAULED), 200 MELEE (BITTEN). On probe_range.

  a pounce, three lanes, the player's dog 200 east of an s1 target (NO_ATTACK from the start), all ordered to attack
    at 2 s (frame 30). Each count is the frames from the start while its event has not come yet (+1 a frame), two to
    a counter line (征起死 = 征起 x 1000 + 征死, 娜起落 = 娜起 x 1000 + 娜落, 走娜死 = 走 x 1000 + 娜死):
      base  a conscript (100):  征起 = until it is hurt (the 1 at the leap), 征死 = until it is gone (the 200)
      high  Natasha (300, MELEE 100 %): 娜起 = until < 100 % (the leap), 娜落 = until < 50 % (the landing: 99 left,
            33 %), 娜死 = until gone (the second leap and landing after the reload)
      order Natasha again; once < 50 % the dog is deleted and she is told every frame to walk 300 west:
            走 = until she is out of a 20 square round her spot (the stun's end)
Predicted (data): 征起 = 娜起 = 30 + the run to 30 off + the aim; 落 - 起 ~ 4-8 (30 at 125 a second, or the 0.5 s of
air); 娜死 - 娜落 ~ 23 (the 1.5 s reload); 走 - 娜起 ~ 23 (1.5 s of SPEED 0 from the leap), later if IGNORE_AI_COMMAND
dropped the orders given under it. The simulator: the dog stops 20 off and never bites -- all six run to the end.

11-26 (run_queue): 征起死 31034, 娜起落 31034, 走娜死 58063 (s3 on). The leap at frame 31 in both lanes (the dogs see
their prey at 200 and run at it from the start: 170 in ~31 frames, so the 2 s order adds nothing -- INFERRED), the
landing 3 frames later (30 at 125 a second, not the 0.5 s FiringDuration); Natasha's second leap lands at 63 (29
after the first: the 0.5 s + 1.5 s reload, ~30); told to walk every frame from 34, she is out of her square at 58 --
the 1.5 s stun from the leap (54) and a few frames of walking: the orders under IGNORE_AI_COMMAND are not dropped
for good, she goes the moment it ends.

  b dead in the air (review 141 A386): as a, but the dog is killed (base, the conscript's) or deleted (high,
    Natasha's) the frame its prey is hurt -- the leap's 1, frames before the warhead lands; order is a's lane
    untouched (the control). Counts as a: 征起死 (base), 娜起落 (high), 控起落 (order: Natasha < 100 % / < 50 %).
Predicted (data): the landing is the dog's own weapon's warhead (HitStoredTarget), fired by nothing once the dog is
gone -- 征死 / 娜落 run to the end; the control 31034 as a. The simulator: the queued 200 lands all the same.

  c the conscript's HitReactionBehavior (HeavyDamageHitReactionLifeTimer 2 s, RotateToSourceWhenDamaged +
    IgnoreIdleCheck, GoIdleWhenDamaged, RequiredDeathTypes BITTEN; handoff-e.md E248), build engine_dogbite_c: two
    arms 300 apart, On a clone of the retail conscript, Off the same less its HitReactionBehavior. Each conscript (s1,
    NO_ATTACK) is told at 2 s to walk 400 east, through its dog (p1, 200 east, told to attack it then); the frame the
    leap's 1 (BITTEN) hurts it, its dog is deleted (b: a deleted dog lands nothing), so it lives on at 99. Counts, two
    to a line as a: 起应 = until hurt x 1000 + until HIT_REACTION; 长到 = frames HIT_REACTION is on x 1000 + until
    it is inside a 30 square at its goal.
Predicted (data): On 应 = 起 (the 1 is BITTEN), 长 = 30 (2 s), 到 runs to the end (GoIdle drops the walk); Off 应
runs to the end, 长 = 0, 到 = 起 + the 1.5 s stun + the walk left. The facing is not read.
"""
import re
from pathlib import Path

import labpaths
from maps import probe_range
from parts import Mission, Script, Test, Unit, square, status

DOG, CON, NAT = 'AlliedScoutInfantry', 'SovietAntiInfantryInfantry', 'SovietCommandoTech1'
LANES = {'base': CON, 'high': NAT, 'order': NAT}
GAP = 200


def mission():
    m = Mission(name='CampDogBite', map=probe_range, units=[])
    for lane, victim in LANES.items():
        m.put(victim, lane + ' gun', side='s1', role='prey ' + lane, name='Prey ' + lane)
        m.put(DOG, lane + ' gun', GAP, 0, role='dog ' + lane, name='Dog ' + lane)
    return m


def _until(counter, step, cond):
    """counter + step every frame `cond` (still) holds: the frame its event comes (x 1000 or x 1: two in a line)."""
    return Script(f'Test - {counter} {step}', [cond], [('INCREMENT_COUNTER', step, counter)], once=False)


def bite_check(m):
    t = Test()
    prey = {lane: 'Prey ' + lane for lane in LANES}
    t.areas['Dog home'] = square(*m.site('order gun'), 20.0)
    t.waypoints['Dog away'] = m.site('order gun', -300, 0)
    t.scripts = [Script('Test - start', [], [('MAP_REVEAL_ALL_PERM', m.player('p1')), ('SET_MILLISECOND_TIMER', 'Dog go', 2.0),
                                             *[('UNIT_CHANGE_OBJECT_STATUS', n, 'NO_ATTACK', 1) for n in prey.values()]]),
                 Script('Test - go', [('TIMER_EXPIRED', 'Dog go')],
                        [('NAMED_ATTACK_NAMED', 'Dog ' + lane, n) for lane, n in prey.items()]),
                 Script('Test - let go', [('UNIT_HEALTH', prey['order'], 0, 50)], [('NAMED_DELETE', 'Dog order')]),
                 Script('Test - walk', [('UNIT_HEALTH', prey['order'], 0, 50), ('NAMED_INSIDE_AREA', prey['order'], 'Dog home')],
                        [('MOVE_NAMED_UNIT_TO', prey['order'], 'Dog away')], once=False)]
    for counter, label, big, small in (
            ('Dog con', '征起死', ('UNIT_HEALTH', prey['base'], 3, 100), ('NAMED_NOT_DESTROYED', prey['base'])),
            ('Dog nat', '娜起落', ('UNIT_HEALTH', prey['high'], 3, 100), ('UNIT_HEALTH', prey['high'], 3, 50)),
            ('Dog end', '走娜死', ('NAMED_INSIDE_AREA', prey['order'], 'Dog home'), ('NAMED_NOT_DESTROYED', prey['high']))):
        t.scripts += [_until(counter, 1000, big), _until(counter, 1, small)]
        t.counters.append((counter, label))
    t.bench = [('bench_watch', dict(seconds=20, every=2, sheet=False, lines=3))]
    return t


def air_check(m):
    t = Test()
    prey = {lane: 'Prey ' + lane for lane in LANES}
    t.scripts = [Script('Test - start', [], [('MAP_REVEAL_ALL_PERM', m.player('p1')), ('SET_MILLISECOND_TIMER', 'Dog go', 2.0),
                                             *[('UNIT_CHANGE_OBJECT_STATUS', n, 'NO_ATTACK', 1) for n in prey.values()]]),
                 Script('Test - go', [('TIMER_EXPIRED', 'Dog go')],
                        [('NAMED_ATTACK_NAMED', 'Dog ' + lane, n) for lane, n in prey.items()]),
                 Script('Test - kill', [('UNIT_HEALTH', prey['base'], 0, 100)], [('NAMED_KILL', 'Dog base')]),
                 Script('Test - delete', [('UNIT_HEALTH', prey['high'], 0, 100)], [('NAMED_DELETE', 'Dog high')])]
    for counter, label, big, small in (
            ('Dog con', '征起死', ('UNIT_HEALTH', prey['base'], 3, 100), ('NAMED_NOT_DESTROYED', prey['base'])),
            ('Dog nat', '娜起落', ('UNIT_HEALTH', prey['high'], 3, 100), ('UNIT_HEALTH', prey['high'], 3, 50)),
            ('Dog end', '控起落', ('UNIT_HEALTH', prey['order'], 3, 100), ('UNIT_HEALTH', prey['order'], 3, 50))):
        t.scripts += [_until(counter, 1000, big), _until(counter, 1, small)]
        t.counters.append((counter, label))
    t.bench = [('bench_watch', dict(seconds=20, every=2, sheet=False, lines=3))]
    return t


def idle_mission():
    m = Mission(name='CampDogBiteC', map=probe_range, units=[])
    source = (Path(labpaths.SDK3) / 'SageXML/Soviet/Units/SovietAntiInfantryInfantry.xml').read_text(encoding='utf-8-sig')
    for tag, dy in (('On', 0), ('Off', 300)):
        ident = 'CNVDogC' + tag
        xml = source.replace(f'id="{CON}"', f'id="{ident}"', 1)
        for key, value in re.findall(r'<Define\s+name="([^"]+)"\s+value="([^"]+)"\s*/>', xml):
            xml = xml.replace('$' + key, value)
        xml = re.sub(r'<Defines>.*?</Defines>', '', xml, flags=re.S)
        if tag == 'Off':
            xml, n = re.subn(r'<HitReactionBehavior\b.*?/>', '', xml, flags=re.S)
            assert n == 1
        m.units.append(Unit(ident, xml))
        m.put(ident, 'base gun', 0, dy, side='s1', role='prey ' + tag, name='Prey ' + tag)
        m.put(DOG, 'base gun', GAP, dy, role='dog ' + tag, name='Dog ' + tag)
        m.waypoint('goal ' + tag, 'Dog Goal ' + tag, 'base gun', 2 * GAP, dy)
    return m


def idle_check(m):
    t = Test()
    t.scripts = [Script('Test - start', [], [('MAP_REVEAL_ALL_PERM', m.player('p1')), ('SET_MILLISECOND_TIMER', 'Dog go', 2.0)])]
    for tag, label in (('On', '原'), ('Off', '删')):
        prey, dog = 'Prey ' + tag, 'Dog ' + tag
        reaction = ('UNIT_HAS_MODELCONDITION', prey, 'HIT_REACTION')
        t.areas['Dog Goal ' + tag] = square(*m.point('goal ' + tag), 30.0)
        t.scripts += [Script('Test - quiet ' + tag, [], [('UNIT_CHANGE_OBJECT_STATUS', prey, status('NO_ATTACK'), 1)]),
                      Script('Test - go ' + tag, [('TIMER_EXPIRED', 'Dog go')],
                             [('MOVE_NAMED_UNIT_TO', prey, 'Dog Goal ' + tag), ('NAMED_ATTACK_NAMED', dog, prey)]),
                      Script('Test - delete ' + tag, [('UNIT_HEALTH', prey, 0, 100)], [('NAMED_DELETE', dog)]),
                      _until('Dog up ' + tag, 1000, ('UNIT_HEALTH', prey, 3, 100)),
                      _until('Dog up ' + tag, 1, reaction + ('NOT',)),
                      _until('Dog on ' + tag, 1000, reaction),
                      _until('Dog on ' + tag, 1, ('NAMED_INSIDE_AREA', prey, 'Dog Goal ' + tag) + ('NOT',))]
        t.counters += [('Dog up ' + tag, label + '起应'), ('Dog on ' + tag, label + '长到')]
    t.bench = [('bench_watch', dict(seconds=20, every=2, sheet=False, lines=4))]
    return t


MISSION = {'engine_dogbite': mission, 'engine_dogbite_c': idle_mission}
CHECKS = {'engine_dogbite': {'a': bite_check, 'b': air_check}, 'engine_dogbite_c': {'c': idle_check}}
CONTROL_ARMS = {'engine_dogbite_c': ('On', 'Off')}
