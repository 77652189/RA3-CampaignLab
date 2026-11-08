"""A small skirmish for the skirmish AI in the simulator (simai.py, tests/test_simai.py): the AI builds, makes units,
teams them up and goes out.

Same Niagara map and wake as aiopen_bench.py: the enemy (s1) is Allied with the stock AlliedBalanced personality, one
construction yard at the east base, woken at WAKE_AT the retail way with MONEY. Unlike aiopen the player has a base
worth attacking -- a yard, a war factory and a power plant on the west bank -- so the AI's attack states have
structures to pick (RequireUniqueTarget heuristics take one each) and its teams somewhere to go. No player units, no
scripts beyond the wake. Not run on the bench yet (no check): the readings it would give are the opening's
(aiopen) and when the first attack team leaves / reaches the west bank.

Facts: wake at, money.
"""
from maps import niagara
from parts import Mission, Script

WAKE_AT, MONEY = 10.0, 50000         # the simulator's miners gather nothing: the AI lives on this
PERSONALITY = 'AIPersonalityDefinition:1AlliedBalanced'


def mission(name='CampAISkirm', money=MONEY):
    m = Mission(name=name, map=niagara, facts={'wake at': WAKE_AT, 'money': money})
    m.sides['s1'] = {'playerFaction': 'PlayerTemplate:Allies', 'aiPersonality': PERSONALITY}
    s1 = m.player('s1')
    m.put('AlliedConstructionYard', 'east base', 0, 0, side='s1', name='UNIT - CNV AI Yard', role='ai yard')
    m.put('AlliedConstructionYard', 'base yard', name='UNIT - CNV AI Player Yard', role='player yard')
    m.put('AlliedWarFactory', 'base factory', angle=3.1416, role='player factory')
    m.put('AlliedPowerPlant', 'base power', angle=0.0, role='player power')
    base = 'CNV AI Base'
    m.waypoint('ai base', base, 'east base')
    m.scripts += [
        Script('CNV AI - Start', [], [('PLAYER_SET_MONEY', s1, 0), ('SET_MILLISECOND_TIMER', 'CNV AI Wake', WAKE_AT)]),
        Script('CNV AI - Wake', [('TIMER_EXPIRED', 'CNV AI Wake')],
               [('UNIT_AI_TRANSFER_ALL', s1, 1), ('SKIRMISH_AI_MAKE_BASE', s1, base),
                ('SKIRMISH_AI_SET_ALL_ENEMY_PLAYERS_PRIORITIES', s1, 20), ('SKIRMISH_AI_USE_REPAIRS', s1, 0),
                ('SKIRMISH_AI_USE_REBUILD_SYSTEM', s1, 0), ('PLAYER_SET_MONEY', s1, money)])]
    return m


# the builds this module makes (cnv/registry.py): build name -> mission factory
MISSION = {'aiskirm': mission, 'aiskirmlow': lambda: mission('CampAISkLow', money=15000)}
