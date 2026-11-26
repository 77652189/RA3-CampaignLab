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
"""
from maps import probe_range
from parts import Mission, Script, Test, square

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


MISSION = {'engine_dogbite': mission}
CHECKS = {'engine_dogbite': {'a': bite_check}}
