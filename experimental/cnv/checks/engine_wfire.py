"""Engine unit test: WeaponFireSpecialAbilityUpdate -- a unit's button fires its SpecialWeapon once (after UnpackTime,
within StartAbilityRange of its target), then packs (PackTime). The three of our 9 levels' templates that are not ships
or aircraft, one lane each on the probe range, every unit NO_ATTACK (no ordinary fire), all pressed at PRESS:
  yuri   (base lane)  Yuriko (JapanCommandoTech1), Command_PsyonicBlastSpecialPower (TargetType NONE): weapon
         JapanCommandoTech1PsyonicBlast, DamageNugget 500 SNIPER radius 250, DelayTimeSeconds 1 s, ENEMIES NEUTRALS;
         UnpackTime 0, PackTime 2 s, BUSY_DURING_PACK. Enemy conscripts 100 / 200 / 300 north of her. MOVE_AT after
         the press she is sent 300 south (again at AGAIN).
  snipe  (high / order lanes) Natasha (SovietCommandoTech1), Command_ActivatePilotSnipeSpecialPower on a named enemy
         Hammer (TargetType OBJECT): SovietCommandoPilotSnipeWeapon, ParalyzeNugget UNMANNED on an enemy VEHICLE;
         UnpackTime 2 s, StartAbilityRange 500. The high lane's Hammer 400 north (in range), the order lane's 700 north
         (she must walk 200 first).
  bark   (switch lane) a dog (AlliedScoutInfantry), Command_ActivateBarkSpecialPower: AlliedScoutInfantryBark,
         ParalyzeNugget EMP radius 100, 10 s, enemy INFANTRY; FreezeAfterTriggerDuration 2 s. Enemy conscripts 60 and
         150 north of it, both sent 300 further north MOVE_AT after the press; the dog sent 300 south then too.
Counters, frames added from the press on (four lines):
  尤活   +1 a frame the 100 conscript lives, +1000 the 200 one, +1000000 the 300 one
  走帧   +1 a frame Yuriko stands within 30 of her start, +1000 a frame the dog does
  狙     +1 a frame s1 owns the near Hammer, +1000 the far one, +1000000 a frame Natasha (order lane) is in her start
  吠     +1 a frame the 60 conscript stands within 30 of its start, +1000 a frame the 150 one does

Predictions from the data (15 logic frames a second): Yuriko's blast at the press + 1 s: the 100 / 200 conscripts die
~15 (尤活 15 / 15000 + run), the 300 one lives; she stands till ~45 (1 s firing + 2 s pack, BUSY_DURING_PACK). Natasha
near: the Hammer s1's ~30 frames (UnpackTime 2 s) then neutral; far: she walks 200 (~?), then 30 more. Bark: the 60
conscript stays ~150 frames (10 s EMP), the 150 one leaves at once; the dog stays ~30 (2 s freeze).

Bench 11-11 (round 160, work/logs/a160_wfire_bench.log, PASS), 尤活 走帧 狙 吠 at the last reading:
  310016016 36039 8074031 15160 -- the 100 / 200 conscripts die at frame 16, the 300 one lives (as predicted, +1);
  Yuriko out of her square at 39, the dog at 36: both stand 30 (PackTime under BUSY_DURING_PACK / the freeze) and
  walk 30 in 6-9 frames; the near Hammer neutral at 31, the far one at 74 -- Natasha leaves at 8 and walks ~44
  frames at 60: till the Hammer's edge, not its centre, is 500 off (INFERRED); the bark holds the 60 conscript 160
  (10 s + its walk), the 150 one walks at 15. Simulator (frame clock): 331016016 35037 8075031 14159.
"""
from maps import probe_range
from parts import Mission, Script, Test, square

PRESS, MOVE_AT, AGAIN, RUN = 2.0, 0.3, 5.0, 20.0
YURI, NATASHA, DOG = 'JapanCommandoTech1', 'SovietCommandoTech1', 'AlliedScoutInfantry'
CONSCRIPT, HAMMER = 'SovietAntiInfantryInfantry', 'SovietAntiVehicleVehicleTech1'
BLAST, SNIPE, BARK = ('Command_PsyonicBlastSpecialPower', 'Command_ActivatePilotSnipeSpecialPower',
                      'Command_ActivateBarkSpecialPower')
N = 'UNIT - CNV WF '


def mission():
    m = Mission(name='CampWFire', map=probe_range, units=[], facts={})
    m.put(YURI, 'base gun', side='p1', name=N + 'Yuri')
    for d in (100, 200, 300):
        m.put(CONSCRIPT, 'base gun', 0, d, side='s1', name=N + f'Yc{d}')
    m.waypoint('yuri away', 'Test WF Yuri Away', 'base gun', 0, -300)
    m.put(NATASHA, 'high gun', side='p1', name=N + 'Nat near')
    m.put(HAMMER, 'high gun', 0, 400, side='s1', name=N + 'Ham near')
    m.put(NATASHA, 'order gun', side='p1', name=N + 'Nat far')
    m.put(HAMMER, 'order gun', 0, 700, side='s1', name=N + 'Ham far')
    m.put(DOG, 'switch gun', side='p1', name=N + 'Dog')
    for d in (60, 150):
        m.put(CONSCRIPT, 'switch gun', 0, d, side='s1', name=N + f'Dc{d}')
        m.waypoint(f'dog c{d} away', f'Test WF Dc{d} Away', 'switch gun', 0, d + 300)
    m.waypoint('dog away', 'Test WF Dog Away', 'switch gun', 0, -300)
    return m


def frames(m):
    t = Test()
    p1, s1 = m.player('p1'), m.player('s1')
    names = [N + k for k in ('Yuri', 'Yc100', 'Yc200', 'Yc300', 'Nat near', 'Ham near', 'Nat far', 'Ham far', 'Dog',
                             'Dc60', 'Dc150')]
    for k, key in (('Yuri', 'base gun'), ('Nat far', 'order gun'), ('Dog', 'switch gun')):
        t.areas[f'Test WF {k} Home'] = square(*m.site(key), 30.0)
    for d in (60, 150):
        t.areas[f'Test WF Dc{d} Home'] = square(*m.site('switch gun', 0, d), 30.0)
    t.scripts.append(Script('Test - start', [], [('MAP_REVEAL_ALL_PERM', p1)] +
                            [('UNIT_CHANGE_OBJECT_STATUS', n, 'NO_ATTACK', 1) for n in names] +
                            [('SET_MILLISECOND_TIMER', 'Test Press', PRESS),
                             ('SET_MILLISECOND_TIMER', 'Test Move', PRESS + MOVE_AT),
                             ('SET_MILLISECOND_TIMER', 'Test Again', PRESS + AGAIN)]))
    t.scripts.append(Script('Test - press', [('TIMER_EXPIRED', 'Test Press')], [
        ('NAMED_USE_COMMANDBUTTON_ABILITY', N + 'Yuri', BLAST),
        ('NAMED_USE_COMMANDBUTTON_ABILITY_ON_NAMED', N + 'Nat near', SNIPE, N + 'Ham near'),
        ('NAMED_USE_COMMANDBUTTON_ABILITY_ON_NAMED', N + 'Nat far', SNIPE, N + 'Ham far'),
        ('NAMED_USE_COMMANDBUTTON_ABILITY', N + 'Dog', BARK),
        ('SET_FLAG', 'Test Going', 1)]))
    moves = [('MOVE_NAMED_UNIT_TO', N + 'Yuri', m.mark('yuri away')), ('MOVE_NAMED_UNIT_TO', N + 'Dog', m.mark('dog away'))]
    t.scripts.append(Script('Test - move', [('TIMER_EXPIRED', 'Test Move')], moves + [
        ('MOVE_NAMED_UNIT_TO', N + f'Dc{d}', m.mark(f'dog c{d} away')) for d in (60, 150)]))
    t.scripts.append(Script('Test - again', [('TIMER_EXPIRED', 'Test Again')], moves))
    going = ('FLAG', 'Test Going', 1)

    def per_frame(counter, label, rows):
        t.counters.append((counter, label))
        t.scripts.extend(Script(f'Test - {counter} {k}', [going, cond], [('INCREMENT_COUNTER', step, counter)],
                                once=False) for k, (cond, step) in enumerate(rows))

    per_frame('CNV_WF_Yuri', '尤活', [(('NAMED_NOT_DESTROYED', N + f'Yc{d}'), step)
                                     for d, step in ((100, 1), (200, 1000), (300, 1000000))])
    per_frame('CNV_WF_Stand', '走帧', [(('NAMED_INSIDE_AREA', N + 'Yuri', 'Test WF Yuri Home'), 1),
                                      (('NAMED_INSIDE_AREA', N + 'Dog', 'Test WF Dog Home'), 1000)])
    per_frame('CNV_WF_Snipe', '狙', [(('NAMED_OWNED_BY_PLAYER', s1, N + 'Ham near'), 1),
                                    (('NAMED_OWNED_BY_PLAYER', s1, N + 'Ham far'), 1000),
                                    (('NAMED_INSIDE_AREA', N + 'Nat far', 'Test WF Nat far Home'), 1000000)])
    per_frame('CNV_WF_Bark', '吠', [(('NAMED_INSIDE_AREA', N + f'Dc{d}', f'Test WF Dc{d} Home'), step)
                                   for d, step in ((60, 1), (150, 1000))])
    t.expect = [('尤活', 0, 'ever>=', 1, RUN)]
    t.bench = [('bench_watch', dict(seconds=RUN, every=0.5, sheet=False, lines=len(t.counters)))]
    return t


MISSION = {'engine_wfire': mission}
CHECKS = {'engine_wfire': {'all': frames}}      # mod CampWFireAll: 13 characters
