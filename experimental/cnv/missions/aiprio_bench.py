"""Engine probe: SKIRMISH_AI_SET_ENEMY_PLAYER_PRIORITY -- one enemy player's priority (retail: 343 uses, mostly at an
AI's start, one line per enemy, e.g. a01 Soviet_1 30 / Soviet_2 20 / Soviet_3 10 / Soviet_4 5). Read back by
checks/engine_aiprio.py; engine line A; model: RA3-EngineModel ra3model/ai/player.py set_enemy_priority.

aitarget_bench's map and AI (ClosestStructureHeuristic + SimpleAttack: the team goes for the enemy structure nearest
its base), with a second enemy: the near plant and its two turrets are Soviet_4's, made an enemy of Soviet_1 both ways
at the start (Soviet_4 has no script library, its AI asleep); the far plant and the yard stay the player's.
  aipriodef  the wake's SET_ALL_ENEMY_PLAYERS_PRIORITIES 20 only (the control). Bench 11-10: the far plant first (s25),
             the near one only by RAMPAGE (s55): Soviet_4, made an enemy by script, is not in the table SET_ALL fills
  aiprio1    no SET_ALL; Soviet_4 30, Player_1 10: the script's put does not ask the enemy list (read) -> tiers by
             score, the top one alone (HighestPriorityEnemyPlayersOnly) -> s4's near plant
  aiprio0    SET_ALL 20, then Player_1 0: 0 takes the player out -> Soviet_4 alone (bench 11-10: the near plant)
  aipriorm   no SET_ALL; Soviet_4 0 alone: is there a table for the script to change (the personality's, built
             when the AI runs -> the far plant) or none yet (-> nobody leaves)? Bench 11-10: nobody left
Facts: wake at.
"""
import dataclasses

from missions import aitarget_bench as at

SET_ALL = 'SKIRMISH_AI_SET_ALL_ENEMY_PLAYERS_PRIORITIES'
SET_ONE = 'SKIRMISH_AI_SET_ENEMY_PLAYER_PRIORITY'
REL = (0, 0.0, 'Enemy')


def mission(name, prio=(), keep_all=True):
    """aitargetnear with the near plant's group Soviet_4's; prio: (side, n) set one by one after the wake's switches."""
    m = at.mission(name, 'ClosestStructureHeuristic', 'SimpleAttack')
    s1, s4 = m.player('s1'), m.player('s4')
    for role in ('near plant', 'near turret 1', 'near turret 2'):
        m.cast[role] = dataclasses.replace(m.cast[role], side='s4')
        m.find(m.cast[role].name).side = 's4'
    start = next(s for s in m.scripts if s.name == 'CNV AI - Start')
    start.do = list(start.do) + [('PLAYER_RELATES_PLAYER', s1, s4, REL), ('PLAYER_RELATES_PLAYER', s4, s1, REL)]
    wake = next(s for s in m.scripts if s.name == 'CNV AI - Wake')
    do = [a for a in wake.do if keep_all or a[0] != SET_ALL]
    wake.do = do + [(SET_ONE, s1, m.player(side), n) for side, n in prio]
    return m


MISSION = {
    'aipriodef': lambda: mission('CampAIPrioDef'),
    'aiprio1': lambda: mission('CampAIPrio1', (('s4', 30), ('p1', 10)), keep_all=False),
    'aiprio0': lambda: mission('CampAIPrio0', (('p1', 0),)),
    'aipriorm': lambda: mission('CampAIPrioRm', (('s4', 0),), keep_all=False),
}
