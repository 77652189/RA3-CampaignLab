"""A: the all-enemies building action after a relation change (engine line A round 274).

C's aiallbuildon / aiallbuildoff (missions/aiallbuild_bench.py) set the secondary enemy s5 in the Start script and
never changed it before the end of the run, so the action could not show anything. Here s5 (twenty Hammer tanks)
starts as s1's friend and turns enemy both ways at 5 s; s1 wakes at 10 s as in C's.

  aiallflipon     the action at the wake (10 s, after the change)
  aiallflipoff    no action
  aiallfliplate   the action at 3 s (before the change)
  aiallflipnever  no action, s5 stays a friend (the control: s5 is not in the enemies whatever the action does)

Prediction (INFERRED, from the program; notes in the private work/re/a273_consider_all.md): the AI's building
enemies are a snapshot taken at the start and retaken by the action only, so off / late / never build alike and
on differs (the twenty tanks count: more anti-vehicle). Read by teamlog.build_picks / build_orders, same frames.
"""
from missions.aiallbuild_bench import mission as allbuild
from missions.aiskirm_bench import FRIEND
from parts import Script

ACTION = 'SKIRMISH_AI_CONSIDER_ALL_ENEMIES_WHEN_BUILDING'
ENEMY = (0, 0.0, 'Enemy')
FLIP_AT, LATE_AT = 5., 3.
AFTER_FLIP, AFTER_ACT = 15., 20.     # round 2: the change after the wake (10 s), the action after that


def mission(name, when, flip=FLIP_AT, act=LATE_AT):
    """when: 'wake' / 'late' (the action at `act`) / None (no action) / 'never' (no action and no change)."""
    m = allbuild(when == 'wake')
    m.name = name
    m.facts['consider all'] = {'wake': 10, 'late': act}.get(when, 0)
    m.facts['enemy at'] = 0 if when == 'never' else flip
    ai, secondary = m.player('s1'), m.player('s5')
    # C's 70 s friendship is past the run's end (C's runs reached f598 at most); drop it, the change here is the flip
    m.scripts = [s for s in m.scripts if not s.name.startswith('CNV AllB') or 'friend' not in s.name]
    start = next(s for s in m.scripts if s.name == 'CNV AI - Start')
    pair = ((ai, secondary), (secondary, ai))
    start.do = [d for d in start.do if not (d[0] == 'PLAYER_RELATES_PLAYER' and (d[1], d[2]) in pair)]
    start.do += [('PLAYER_RELATES_PLAYER', a, b, FRIEND) for a, b in pair]
    if when != 'never':
        start.do.append(('SET_MILLISECOND_TIMER', 'CNV AllF Flip', flip))
        m.scripts.append(Script('CNV AllF flip', [('TIMER_EXPIRED', 'CNV AllF Flip')],
                                [('PLAYER_RELATES_PLAYER', a, b, ENEMY) for a, b in pair]))
    if when == 'late':
        start.do.append(('SET_MILLISECOND_TIMER', 'CNV AllF Late', act))
        m.scripts.append(Script('CNV AllF late', [('TIMER_EXPIRED', 'CNV AllF Late')], [(ACTION, ai)]))
    return m


MISSION = {'aiallflipon': lambda: mission('CampAllFOn', 'wake'),
           'aiallflipoff': lambda: mission('CampAllFOff', None),
           'aiallfliplate': lambda: mission('CampAllFLate', 'late'),
           'aiallflipnever': lambda: mission('CampAllFNever', 'never'),
           # round 2: on / off / late all built like s5-enemy-from-the-start, never apart -- the change at 5 s
           # reached the building enemies with no action. These move the change past the wake (15 s): the wake
           # retaking the snapshot vs the enemies following the relation as it changes.
           'aiallflipwoff': lambda: mission('CampAllFWOff', None, flip=AFTER_FLIP),
           'aiallflipwon': lambda: mission('CampAllFWOn', 'late', flip=AFTER_FLIP, act=AFTER_ACT)}
