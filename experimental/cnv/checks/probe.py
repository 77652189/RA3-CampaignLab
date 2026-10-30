"""Engine probe (missions/probe_bench.py), read off the counters:

engine: the difficulty counter shows 1, 2 or 3 (exactly one of the three copies ran: the bench starts on whatever
  difficulty the profile has); the money counter shows the money set; the mission runs past the autosave.

The border is checked by hand, no counter sees it (bench 2026-10-25): bench_camera east of the canal does not move
before `open at` (west of it does), and does after. A unit a script moves crosses the border at any time -- the
first version of this check sent one east and counted it, and it got there before the border opened.
"""
from parts import NOT, Obj, Script, Test, counted, kindof, square

RUN = 15.0                                      # past the autosave (5 s), margin
STOP, DOOM = 10.0, 6.0                          # align: the NOT counter stops; the victim is killed, the other deleted


def engine(m):
    t = Test()
    t.scripts.append(Script('Test - reveal', [], [('MAP_REVEAL_ALL_PERM', m.player('p1'))]))
    t.counters += [('CNV_Probe_Difficulty', '难度'), ('CNV_Probe_Money', '资金')]
    t.expect += [('难度', 3, '>=', 1), ('难度', 3, '<=', 3), ('资金', 3, '==', m.facts['money']),
                 ('资金', RUN - 3, 'ever==', m.facts['money'])]
    t.bench = [('bench_watch', dict(seconds=RUN, every=3, sheet=False, lines=len(t.counters)))]
    return t


def align(m):
    """The simulator's engine guesses (sim.ALIGN), each as a counter that reads what the simulator assumes -- a FAIL is a
    guess to correct, the readings say the engine's way:
      frame rate + inverted: 帧数 counts every frame; 取反帧数 counts while flag CNV Probe Stop is NOT set, the flag
        set at STOP s -- plain negation: it stops near STOP x the logic rate, the inverted bit ignored: it stays 0 till
        STOP and runs on after; the rate is 帧数 per mission second (bench 2026-10-28: ~15 a second; 取反帧数 0 till
        the flag was set, then counting -- our inverted bit did not invert: the FAIL stands till the compiler's NOT
        is fixed);
      timer unset: TIMER_EXPIRED of a timer nobody sets is false."""
    t = Test()
    t.counters += [('CNV_Probe_Frames', '帧数'), ('CNV_Probe_NotFrames', '取反帧数'), ('CNV_Probe_Unset', '未设计时器')]
    t.scripts += [
        Script('Test - stop timer', [], [('SET_MILLISECOND_TIMER', 'CNV Probe Stop', STOP)]),
        Script('Test - frames', [], [('INCREMENT_COUNTER', 1, 'CNV_Probe_Frames')], once=False),
        Script('Test - not frames', [('FLAG', 'CNV Probe Stop', 1, NOT)],
               [('INCREMENT_COUNTER', 1, 'CNV_Probe_NotFrames')], once=False),
        Script('Test - stop', [('TIMER_EXPIRED', 'CNV Probe Stop')], [('SET_FLAG', 'CNV Probe Stop', 1)]),
        Script('Test - unset', [('TIMER_EXPIRED', 'CNV Probe Never')], [('SET_COUNTER', 'CNV_Probe_Unset', 1)])]
    t.expect += [('取反帧数', 2, '>=', 1), ('未设计时器', 2, '==', 0)]
    t.bench = [('bench_watch', dict(seconds=RUN + 5, every=1, sheet=False, lines=len(t.counters)))]
    return t


def death(m):
    """More of the simulator's guesses (sim.ALIGN), read the same way:
      death linger, health of the dead: the victim killed at DOOM s, 1 in 死者在区内 while the engine still has it in
        the area (the simulator: LINGER 3 s), 死者血量 0 once dead;
      deleted: the other one deleted at DOOM s, NAMED_DESTROYED of it true from the next frame (删除算摧毁)."""
    t = Test()
    t.scripts.append(Script('Test - reveal', [], [('MAP_REVEAL_ALL_PERM', m.player('p1'))]))
    for k, name in ((0, 'UNIT - Probe Victim'), (1, 'UNIT - Probe Gone')):
        t.objects.append(Obj('AlliedAntiVehicleVehicleTech1', *m.site('west field', 150, -90 + 60 * k), name=name,
                             site='west field'))
    t.areas['Test field'] = square(*m.site('west field'), 450)
    t.scripts += [
        Script('Test - doom timer', [], [('SET_MILLISECOND_TIMER', 'CNV Probe Doom', DOOM)]),
        Script('Test - doom', [('TIMER_EXPIRED', 'CNV Probe Doom')],
               [('NAMED_KILL', 'UNIT - Probe Victim'), ('NAMED_DELETE', 'UNIT - Probe Gone')])]
    counted('CNV_Probe_Linger', '死者在区内', t, named='UNIT - Probe Victim', area='Test field')
    counted('CNV_Probe_DeadHealth', '死者血量', t, health='UNIT - Probe Victim')
    t.counters.append(('CNV_Probe_GoneDead', '删除算摧毁'))
    t.scripts += [Script('Test - gone zero', [], [('SET_COUNTER', 'CNV_Probe_GoneDead', 0)], once=False),
                  Script('Test - gone dead', [('NAMED_DESTROYED', 'UNIT - Probe Gone')],
                         [('SET_COUNTER', 'CNV_Probe_GoneDead', 1)], once=False)]
    # bench 2026-10-28: out of the area the reading the kill shows in (no linger; the simulator guessed 3 s)
    t.expect += [('死者在区内', 2, '==', 1, DOOM - 2), ('死者在区内', DOOM + 1, '==', 0),
                 ('死者血量', DOOM + 1, '==', 0), ('删除算摧毁', DOOM + 1, '==', 1)]
    t.bench = [('bench_watch', dict(seconds=RUN + 5, every=1, sheet=False, lines=len(t.counters)))]
    return t


def reveal(m):
    """Border reveal: a permanent reveal made while the border is west of the canal (at 2 s), the whole map opened at
    `open at` -- the simulator takes the reveal to cover the new ground too. Read by hand off the frame east of the
    canal after the opening: ground in the clear, or black (shrouded)."""
    t = Test()
    t.scripts += [Script('Test - reveal timer', [], [('SET_MILLISECOND_TIMER', 'CNV Probe Reveal', 2.0)]),
                  Script('Test - reveal', [('TIMER_EXPIRED', 'CNV Probe Reveal')],
                         [('MAP_REVEAL_ALL_PERM', m.player('p1'))])]
    t.counters.append(('CNV_Probe_Money', '资金'))
    t.expect.append(('资金', 3, '==', m.facts['money']))
    t.bench = [('bench_watch', dict(seconds=m.facts['open at'] + 3, every=5, sheet=False, lines=1)),
               ('bench_camera', dict(x=4400.0, y=3400.0))]          # east of the canal; it returns the frame
    return t


def both(m, first='Mission Won', then='Mission Lost'):
    """Won and lost in one frame (sim 'both endings': the simulator takes the later one, the Generals way): both flags
    set by one script at 5 s, `first` then `then`; the frame after says which the game made of it."""
    t = Test()
    t.scripts += [Script('Test - end timer', [], [('SET_MILLISECOND_TIMER', 'CNV Probe End', 5.0)]),
                  Script('Test - both', [('TIMER_EXPIRED', 'CNV Probe End')],
                         [('SET_FLAG', first, 1), ('SET_FLAG', then, 1)])]
    t.counters.append(('CNV_Probe_Money', '资金'))
    t.expect.append(('ENDED', 5, '==', 1))
    t.bench = [('bench_watch', dict(seconds=12, every=2, sheet=False, lines=1)),
               ('bench_look', dict(note=f'{first} then {then}: which ending?'))]
    return t


def count(m):
    """Whose units the area conditions count (bench 2026-10-25: a kind-in-area count for the enemy came out as every
    player's): the player's guardian and two more of ours at the west field, two enemy warriors far off at the north
    base; the enemy's count in the west field, three ways, against the player's own."""
    t = Test()
    t.scripts.append(Script('Test - reveal', [], [('MAP_REVEAL_ALL_PERM', m.player('p1'))]))
    for k in (1, 2):
        t.objects.append(Obj('AlliedAntiVehicleVehicleTech1', *m.site('west field', 250, 30 + 60 * k), site='west field'))
        t.objects.append(Obj('JapanAntiInfantryInfantry', *m.site('north base', 60 * k, 0), side='s1',
                             site='north base'))
    t.areas['Test field'] = square(*m.site('west field'), 450)
    s1 = m.player('s1')
    counted('CNV_Probe_KindP1', '我方能打的', t, kind=kindof('CAN_ATTACK'), area='Test field')
    counted('CNV_Probe_KindS1', '敌方能打的', t, kind=kindof('CAN_ATTACK'), area='Test field', player=s1)
    counted('CNV_Probe_TypeS1', '敌方守护者', t, template='AlliedAntiVehicleVehicleTech1', area='Test field', player=s1)
    t.counters.append(('CNV_Probe_EnterS1', '敌方进入'))
    t.scripts += [Script('Test - enter zero', [], [('SET_COUNTER', 'CNV_Probe_EnterS1', 0)], once=False),
                  Script('Test - enter', [('SKIRMISH_PLAYER_HAS_UNITS_IN_AREA', s1, 'Test field')],
                         [('SET_COUNTER', 'CNV_Probe_EnterS1', 1)], once=False)]
    t.expect += [('我方能打的', 3, '==', 3), ('敌方能打的', 3, '==', 0), ('敌方守护者', 3, '==', 0), ('敌方进入', 3, '==', 0)]
    t.bench = [('bench_watch', dict(seconds=12, every=3, sheet=False, lines=len(t.counters)))]
    return t
