"""A: the AI's subsystem switches PLAYER_AI_CHANGE* (engine line A round 294; retail a06 presses four of them "on").

C's aiallbuildoff (missions/aiallbuild_bench.py: s1 Allied AI woken at 10 s, its enemies the player and s5's twenty
tanks) with the switch pressed in the wake script, right after the AI takes over:

  aiubon     no switch (the control)
  aiuboff    PLAYER_AI_CHANGEUNITBUILDER 0
  aiubback   ... 0, then 1 at 40 s
  aitboff    PLAYER_AI_CHANGETEAMBUILDER 0 and PLAYER_AI_CHANGE_ECONOMY_MANAGER 0

Prediction (INFERRED, from the program; private work/re/a293_changebuilder.md): unit builder 0 turns off two of the
AI's builders (both on by default) -- what they do is not read yet, so whether units stop is the question; team
builder and economy manager do nothing whatever the value (their index falls through), so aitboff builds as aiubon.
"""
from missions.aiallbuild_bench import mission as allbuild
from parts import Script

UNIT, TEAM, ECONOMY = ('PLAYER_AI_CHANGEUNITBUILDER', 'PLAYER_AI_CHANGETEAMBUILDER',
                       'PLAYER_AI_CHANGE_ECONOMY_MANAGER')
BACK_AT = 40.


def mission(name, off=(), back=False):
    m = allbuild(False)
    m.name = name
    m.scripts = [s for s in m.scripts if not s.name.startswith('CNV AllB')]      # no 70 s friendship
    ai = m.player('s1')
    m.facts['switched off'] = ' '.join(off) or 'none'
    next(s for s in m.scripts if s.name == 'CNV AI - Wake').do += [(x, ai, 0) for x in off]
    if back:
        m.facts['back on at'] = BACK_AT
        m.scripts += [Script('CNV AISw back timer', [], [('SET_MILLISECOND_TIMER', 'CNV AISw Back', BACK_AT)]),
                      Script('CNV AISw back', [('TIMER_EXPIRED', 'CNV AISw Back')], [(x, ai, 1) for x in off])]
    return m


MISSION = {'aiubon': lambda: mission('CampAISwOn'),
           'aiuboff': lambda: mission('CampAISwUOff', (UNIT,)),
           'aiubback': lambda: mission('CampAISwBack', (UNIT,), back=True),
           'aitboff': lambda: mission('CampAISwTOff', (TEAM, ECONOMY))}
