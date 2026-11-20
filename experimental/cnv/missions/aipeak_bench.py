"""The skirmish AI's peak scene (step S 11c-2, ADR 0034 item 10's B0 benchmark: simbench_peak --ai): two AIs at war
on the Niagara map, each building a base and an army out of a million credits and sending it at the other.

aiskirm_bench's map, wake and stock AlliedBalanced, twice over: s1 (Soviet_1) from its yard at the east base as
there, s2 (Soviet_2) from a second yard on the player's start (the west bank's base yard), enemies both ways from
frame 0 (the container leaves the Soviet_N players at peace with one another). The player owns nothing. Not a bench
check: it is the simulator's load at its busiest -- both sides hundreds strong and fighting -- timed by
simbench_peak.run_ai from a snapshot taken some minutes in (ai_start).

Facts: wake at, money.
"""
from missions.aiskirm_bench import PERSONALITY, WAKE_AT, ai_map
import resources
from maps import niagara
from parts import Mission, Script

MONEY = 1_000_000                     # each side's: the simulator's miners gather nothing, so this is all they spend
ENEMY = (0, 0.0, 'Enemy')
# side -> (where its yard and base waypoint stand, the waypoint's name)
BASES = {'s1': ('east base', 'CNV Peak Base 1'), 's2': ('base yard', 'CNV Peak Base 2')}


def mission(name='CampAIPeak', money=MONEY):
    m = Mission(name=name, map=ai_map(resources.measured(niagara)), facts={'wake at': WAKE_AT, 'money': money})
    players = {side: m.player(side) for side in BASES}
    for side, (site, base) in BASES.items():
        m.sides[side] = {'playerFaction': 'PlayerTemplate:Allies', 'aiPersonality': PERSONALITY, 'playerAllies': ''}
        m.put('AlliedConstructionYard', site, 0, 0, side=side, name=f'UNIT - CNV Peak Yard {side[1:]}',
              role=f'yard {side}')
        m.waypoint(f'base {side}', base, site)
    s1, s2 = players['s1'], players['s2']
    m.scripts += [
        Script('CNV Peak - Start', [], [*(('PLAYER_SET_MONEY', p, 0) for p in players.values()),
                                        ('PLAYER_RELATES_PLAYER', s1, s2, ENEMY), ('PLAYER_RELATES_PLAYER', s2, s1, ENEMY),
                                        ('SET_MILLISECOND_TIMER', 'CNV Peak Wake', WAKE_AT)]),
        Script('CNV Peak - Wake', [('TIMER_EXPIRED', 'CNV Peak Wake')],
               [step for side, p in players.items() for step in (
                   ('UNIT_AI_TRANSFER_ALL', p, 1), ('SKIRMISH_AI_MAKE_BASE', p, BASES[side][1]),
                   ('SKIRMISH_AI_SET_ALL_ENEMY_PLAYERS_PRIORITIES', p, 20), ('SKIRMISH_AI_USE_REPAIRS', p, 0),
                   ('SKIRMISH_AI_USE_REBUILD_SYSTEM', p, 0), ('PLAYER_SET_MONEY', p, money))])]
    return m


MISSION = {'aipeak': mission}
