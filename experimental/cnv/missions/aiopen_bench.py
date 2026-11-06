"""Engine probe: the skirmish AI's opening build order and timing (read back by checks/engine_aiopen.py).

Same Niagara map as ai_bench.py. The enemy (s1) is Allied with the stock AlliedBalanced personality, one construction
yard at the east base and nothing else; the player has a yard at home. Asleep until WAKE_AT, then the retail wake set
(UNIT_AI_TRANSFER_ALL, SKIRMISH_AI_MAKE_BASE, priorities 20, no repairs, no rebuilding) with 50000 money so money is
no limit (aiopenpoor: 3000, the opening short of money). No attack script.

Facts: wake at, money.
"""
from maps import niagara
from parts import Mission, Script

WAKE_AT, MONEY, POOR = 10.0, 50000, 3000
PERSONALITY = 'AIPersonalityDefinition:1AlliedBalanced'
COUNTED = ('AlliedBarracks', 'AlliedPowerPlant', 'AlliedRefinery', 'AlliedWarFactory', 'AlliedAntiInfantryVehicle',
           'AlliedAntiInfantryVehicle_Ground', 'AlliedNavalYard', 'AlliedMiner')


def mission(name='CampAIOpen', money=MONEY):
    m = Mission(name=name, map=niagara, facts={'wake at': WAKE_AT, 'money': money})
    m.sides['s1'] = {'playerFaction': 'PlayerTemplate:Allies', 'aiPersonality': PERSONALITY}
    m.spawns |= set(COUNTED)
    s1 = m.player('s1')
    m.put('AlliedConstructionYard', 'east base', 0, 0, side='s1', name='UNIT - CNV AI Yard', role='ai yard')
    m.put('AlliedConstructionYard', 'base yard', name='UNIT - CNV AI Player Yard', role='player yard')
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
MISSION = {'aiopen': mission, 'aiopenpoor': lambda: mission('CampAIPoor', money=POOR)}
