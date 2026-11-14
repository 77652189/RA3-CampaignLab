"""Engine probe: when the skirmish AI fires its superweapon and at which pile (missions/aispecial_bench.py).

s1 (AlliedBalanced, woken at 10 s, money 0) owns a proton collider (SpecialPowerParticleCannon). Piles of the player's
structures: A 4 barracks (2000), B 3 war factories (6000), C 5 base defenses (4000) -- see the mission. The countdown
unit of NAMED_SET_SPECIAL_POWER_COUNTDOWN is not known (engine_power: 5 s did not make it ready in 15 s, 0 does), so the
power is made ready by countdown 0 set k frames after the wake, k = 0 / 5 / 10 (the ready frame then lands on different
phases of the AI's 15-frame check):

  a  k = 0     b  k = 5     c  k = 10     t  k = 0, which pile is hit     (build aispecial, run 60 s after the wake)
  d  k = 0 on build aispecialhid: one pile of 5 defenses far from the AI, not revealed to s1

Counters (four lines), all from the wake on:
  帧数    frames since the wake (the wake frame is +-1)
  就绪帧  frames since SKIRMISH_SPECIAL_POWER_READY(s1) was first seen   -> ready at frame = 帧数 - 就绪帧
  放帧    frames since PLAYER_TRIGGERED_SPECIAL_POWER(s1) was first seen -> fired at frame = 帧数 - 放帧
  受损    structures of the player that were ever hurt or destroyed, A x 1 + B x 10 + C x 100 (d: H x 1)

(Final design: a / b / c set countdown 5 (seconds, integer) at wake frame 1 / 6 / 11; t and d set 0. A first try of a / b / c
with 5.2 / 5.4 s: the fractions acted as 0, see below. 就绪帧 latches only when seen at frame >= delay + 3.)

读数
Bench 2026-11-06 (one run each; fired at / ready at = 帧数 - 放帧 / 帧数 - 就绪帧 at the last row, +-1):
  Weapon: ParticleCannonWeapon -> ParticleAcceleratorFinalWeapon, Damage 400, Radius 250, DamageTaperOff 200. Building
  AlliedSuperWeaponAdvanced (BuildCost 2500, -75 power). Piles: A 4 AlliedBarracks 500 = 2000; B 3 AlliedWarFactory 2000
  = 6000; C 5 AlliedBaseDefense 800 = 4000.
  First try, countdown 0 at frame 1 (CampAISpecialA): ready from the first frame; fired at frame 61 after the wake.
  t CampAISpecialT (countdown 0): ready ~2, fired at 61 (948-887); 受损 500 = all five of C hit, A 0, B 0 (stable
    from s21). The model (C: A and C both qualify, the dearer; B has only 3) holds.
  a CampAISpecialA (5 s at frame 1): 就绪帧 stayed 0 (READY never seen in 950 frames although it fired); fired at
    136 (950-814); 受损 500.
  b (5 s set at frame 6): 就绪帧 0, fired at 136; c (set at frame 11): 就绪帧 0, fired at 136. So the fire frame did
    NOT move with the phase of the countdown set (0 / 5 / 10 frames): 61 with ready at once, 136 = 61 + 75 (= 5 s x
    15) with a 5 s countdown. The "ready at frame 0..14 later" phase shift was not seen. 受损 500 each.
  5.2 / 5.4 s (first try, b / c at frame 1): READY seen at frame 2, fired at 61 (950-889, 953-892): a fractional
    countdown acts as 0 (the integer 5 is 5 s: +75 frames).
  d CampAIHidD (5 defenses at west field, s1 not revealed, countdown 0): ready ~2, fired at 61 (951-890); 受损 5 =
    all five hit. The model "unseen -> not fired" is REFUTED here: the AI fires at structures it was never shown
    (not chased: whether s1 shares the map's initial vision / sees all structures).
    Round 13: the program's test (work/re/l4_specials.md) is "stealthed and not detected", nothing about the shroud -- so this fits.
Round 13 (2026-11-06, one run each; countdown 60 at frame 1 holds the power, then the late setting):
  e  0 at frame 201: ready 202, fired 256      f  0 at 208: ready 209, fired 256      g  0 at 214: ready 215, fired 271
  h  5 at frame 201: READY never seen, fired 331                                       受损 500 in all four
  One rule fits all eight fire frames (t a b c e f g h): the AI looks every 15 frames, at frames 1, 16, 31 ... after
  the wake; a countdown of N whole seconds set at frame k makes the power ready at k + 1 + 15 N; a look fires it only
  once it has been ready 45 frames (3 s). t: ready 2, the look at 46 is 44 frames on, so 61. So the 61 is not a
  start-up wait: every fire comes >= 3 s after ready. Where the 3 s comes from is not read. READY (the script
  condition) is never true after a countdown > 0, though the power fires (not chased).
"""
from parts import Script, Test

LAG = 4.0
RUN = 60.0
# countdowns set: [(frames after the wake, value)] (a first try of a / b / c with 5.2 / 5.4 read as 0)
SETS = {'a': [(0, 5)], 'b': [(5, 5)], 'c': [(10, 5)], 't': [(0, 0)], 'd': [(0, 0)],
        # round 13: hold the power with 60 s, free it late -> is 61 a one-off start delay or a delay after ready?
        'e': [(0, 60), (200, 0)], 'f': [(0, 60), (207, 0)], 'g': [(0, 60), (213, 0)], 'h': [(0, 60), (200, 5)]}


def probe(m, which):
    t = Test()
    p1, s1 = m.player('p1'), m.player('s1')
    wake, power, collider = m.facts['wake at'], m.facts['power'], m.role('collider').name
    start = [('MAP_REVEAL_ALL_PERM', p1)]
    if m.facts['reveal to ai']:
        start.append(('MAP_REVEAL_ALL_PERM', s1))
    t.scripts.append(Script('Test - reveal', [], start))
    t.scripts += [Script('Test - tick', [], [('INCREMENT_COUNTER', 1, 'CNV_AS_Tick')], once=False),
                  Script('Test - woke', [('TIMER_EXPIRED', 'CNV AI Wake'), ('COUNTER', 'CNV_AS_Tick', 3, 30)],
                         [('SET_FLAG', 'Test Woke', 1)])]
    woke = ('FLAG', 'Test Woke', 1)
    t.counters += [('CNV_AS_Frames', '帧数'), ('CNV_AS_Ready', '就绪帧'), ('CNV_AS_Cast', '放帧'),
                   ('CNV_AS_Hit', '受损')]
    t.scripts += [
        Script('Test - frames', [woke], [('INCREMENT_COUNTER', 1, 'CNV_AS_Frames')], once=False),
        *[Script(f'Test - countdown {i}', [woke, ('COUNTER', 'CNV_AS_Frames', 2, at + 1)],
                 [('NAMED_SET_SPECIAL_POWER_COUNTDOWN', collider, power, value)])
          for i, (at, value) in enumerate(SETS[which])],
        Script('Test - ready seen', [woke, ('COUNTER', 'CNV_AS_Frames', 3, SETS[which][-1][0] + 3),
                                     ('SKIRMISH_SPECIAL_POWER_READY', s1, power)],
               [('SET_FLAG', 'Test Ready', 1)]),
        Script('Test - ready count', [('FLAG', 'Test Ready', 1)], [('INCREMENT_COUNTER', 1, 'CNV_AS_Ready')],
               once=False),
        Script('Test - cast seen', [woke, ('PLAYER_TRIGGERED_SPECIAL_POWER', s1, power)],
               [('SET_FLAG', 'Test Cast', 1)]),
        Script('Test - cast count', [('FLAG', 'Test Cast', 1)], [('INCREMENT_COUNTER', 1, 'CNV_AS_Cast')],
               once=False)]
    for letter, weight in m.facts['piles'].items():
        for part in m.roles(letter):
            nm = part.name
            flag = f'Test Hurt {nm}'
            act = [('SET_FLAG', flag, 1), ('INCREMENT_COUNTER', weight, 'CNV_AS_Hit')]
            t.scripts += [Script(f'Test - hurt {nm}', [('UNIT_HEALTH', nm, 0, 100)], act),
                          Script(f'Test - dead {nm}', [('NAMED_DESTROYED', nm), ('FLAG', flag, 0)], act)]
    t.expect += [('帧数', wake + LAG, 'ever>=', 1, wake + RUN)]
    t.bench = [('bench_watch', dict(seconds=wake + RUN + LAG, every=10, sheet=False, lines=len(t.counters)))]
    return t


CHECKS = {'aispecial': {w: (lambda m, w=w: probe(m, w)) for w in 'abctefgh'},
          'aispecialhid': {'d': lambda m: probe(m, 'd')},
          'aispecoff': {'t': lambda m: probe(m, 't')},   # UsePlayerPowersAtDifficulty "" / "HARD BRUTAL" at MEDIUM
          'aispechb': {'t': lambda m: probe(m, 't')}}
