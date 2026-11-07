"""Engine probe: when the AI's micro manager fires the Imperial Warriors' Bonzai charge (missions/aimicro_bench.py).

s1's StaticDefense team is the two warriors; an unarmed player engineer stands D west of each (90 or 140), kept at
full health every frame. The charge is read as the warrior's ObjectStatus WEAPON_UPGRADED_02 (10 s; reload 30 s).
One check per build, r (aimicnear also c: the control, the script presses warrior 2's charge at frame PRESS_AT):
  aimicnear (D 90, HARD)   aimicmed (D 90, MEDIUM)   aimicfar (D 140, HARD)   aimichurt (D 140, HARD, health 70 %)
  aimicmade (D 90, HARD, the warriors created on s1's team by script 1 s after the wake)
The verdicts after 帧数 are the model's answer (FIRES): 冲1 / 冲2 ever >= 1 where it charges, == 0 throughout where it
does not -- a FAIL there is the bench reading otherwise, the charge count readable without the rows.
Counters (four lines), from the wake on (run 60 s after it):
  帧数   frames since the wake (the wake frame is +-1)
  冲1    frames since warrior 1 was first seen charging  -> charged at frame = 帧数 - 冲1
  冲2    the same for warrior 2
  再冲1  frames since warrior 1 was seen charging again, once 冲1 >= 200 (the first charge ends at 150)
Before the wake: a charge seen before the wake makes 冲k > 帧数.

读数
Bench 2026-11-06 (one run each; charged at = 帧数 - 冲k at the last row):
  aimicpre r (first design: the warriors s1's from the start, as aimicnear but no hand-over; run as CampAIMicNearR):
    冲1 冲2 再冲1 all 0 through 帧数 947 -- never charged, though the engineer stood 90 away in gun range. Read
    afterwards: a unit's AI powers are registered only when it is made / changes hands with the AI brain awake.
Bench 2026-11-07 (Sonnet, one run each, no dropout):
  aimicnear c: 冲2 counting from about frame 300 (100 at s51, 404 at s71 of 帧数 704) -- the scripted press is seen,
    so the status reads a charge.
  aimicnear r / aimicmed r / aimicfar r / aimichurt r: 冲1 冲2 再冲1 all 0 through 帧数 949 / 940 / 948 / 933 --
    nobody charged, the hand-over 1 s after the wake did not help. The model fires in near / med / hurt (strict xfail
    in RA3-EngineModel tests/test_ai_bench.py); far agrees. Not known yet why: the hand-over not registering either,
    the StaticDefense team not taking handed-over units, or one of the 6 preconditions (l4_micro_powers.md 1).
  aimicmade r (Sonnet): 冲1 冲2 再冲1 all 0 through 帧数 939 -- warriors created on s1's team after the wake did not
    charge either: not the hand-over. Same in engine_aitoggle (no shield). INFERRED: StaticDefense runs no micro.
"""
from parts import Script, Test, status

LAG = 4.0
RUN = 60.0
CHARGE = 'WEAPON_UPGRADED_02'


COMMAND = 'Command_JapanAntiInfantryInfantryBonzai'
PRESS_AT = 300     # control c: frames after the wake at which the script presses warrior 2's charge


def names(m, group):
    """A group's unit names in order: the cast's roles, or (units the mission's scripts create) m.cnv_named."""
    made = getattr(m, 'cnv_named', {})
    return [r.name for r in m.roles(group)] or [made[k] for k in sorted(made) if k.startswith(group + ' ')]


# what the model (RA3-EngineModel ra3model/ai/micro.py) expects of each build: does each warrior charge within the run
FIRES = {'aimicpre': False, 'aimicnear': True, 'aimicmed': True, 'aimicfar': False, 'aimichurt': True,
         'aimicmade': True}


def probe(m, press=False, build=''):
    t = Test()
    p1 = m.player('p1')
    wake = m.facts['wake at']
    t.scripts.append(Script('Test - reveal', [], [('MAP_REVEAL_ALL_PERM', p1)]))
    t.scripts.append(Script('Test - keep the engineers up', [],
                            [('UNIT_SET_HEALTH', r.name, 100.0) for r in m.roles('engineer')], once=False))
    t.scripts += [Script('Test - tick', [], [('INCREMENT_COUNTER', 1, 'CNV_AM_Tick')], once=False),
                  Script('Test - woke', [('TIMER_EXPIRED', 'CNV AI Wake'), ('COUNTER', 'CNV_AM_Tick', 3, 30)],
                         [('SET_FLAG', 'Test Woke', 1)])]
    t.counters += [('CNV_AM_Frames', '帧数'), ('CNV_AM_Rush1', '冲1'), ('CNV_AM_Rush2', '冲2'),
                   ('CNV_AM_Again1', '再冲1')]
    t.scripts.append(Script('Test - frames', [('FLAG', 'Test Woke', 1)], [('INCREMENT_COUNTER', 1, 'CNV_AM_Frames')],
                            once=False))
    warriors = names(m, 'warrior')
    for k, w in enumerate(warriors, 1):
        on = ('UNIT_HAS_OBJECT_STATUS', w, status(CHARGE))
        t.scripts += [
            Script(f'Test - rush seen {k}', [on], [('SET_FLAG', f'Test Rush {k}', 1)]),
            Script(f'Test - rush count {k}', [('FLAG', f'Test Rush {k}', 1)],
                   [('INCREMENT_COUNTER', 1, f'CNV_AM_Rush{k}')], once=False)]
    if press:
        t.scripts.append(Script('Test - press 2', [('FLAG', 'Test Woke', 1), ('COUNTER', 'CNV_AM_Frames', 2, PRESS_AT)],
                                [('NAMED_USE_COMMANDBUTTON_ABILITY', warriors[1], COMMAND)]))
    w1 = warriors[0]
    t.scripts += [
        Script('Test - again seen 1', [('UNIT_HAS_OBJECT_STATUS', w1, status(CHARGE)),
                                       ('COUNTER', 'CNV_AM_Rush1', 3, 200)], [('SET_FLAG', 'Test Again 1', 1)]),
        Script('Test - again count 1', [('FLAG', 'Test Again 1', 1)], [('INCREMENT_COUNTER', 1, 'CNV_AM_Again1')],
               once=False)]
    t.expect += [('帧数', wake + LAG, 'ever>=', 1, wake + RUN)]
    # did they charge (the model's answer; FAIL = the bench reads otherwise): 冲k > 0 once warrior k was seen charging
    if press:
        t.expect += [('冲2', wake + LAG, 'ever>=', 1)]
    elif build in FIRES:
        t.expect += [(f'冲{k}', wake + LAG, 'ever>=' if FIRES[build] else '==', 1 if FIRES[build] else 0)
                     for k in (1, 2)]
    t.bench = [('bench_watch', dict(seconds=wake + RUN + LAG, every=10, sheet=False, lines=len(t.counters)))]
    return t


CHECKS = {b: {'r': lambda m, b=b: probe(m, build=b)} for b in FIRES}
CHECKS['aimicnear']['c'] = lambda m: probe(m, press=True)
