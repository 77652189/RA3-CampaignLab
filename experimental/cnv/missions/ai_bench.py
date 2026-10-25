"""Engine probe: an enemy run by the game's skirmish AI the way the retail missions wake one (docs/story/plans/retail:
Miyako, Havana) -- read back by checks/ai.py.

The Niagara map's enemy player (Soviet_1, the Heidelberg container's, Soviet with a Heidelberg personality) is made
Allied with the Mount Rushmore president's personality (mapxml.set_player: Mission.sides); it starts with a
construction yard at the east base and three guardians by it, the player with a yard and three guardians at home.

  - asleep until `wake at`: does it build or move on its own?
  - wake (retail "enable naomi ai"): UNIT_AI_TRANSFER_ALL, SKIRMISH_AI_MAKE_BASE at the east base, all enemies
    priority 20, no repairs, no rebuilding, money;
  - attack at `attack at` (retail "give units to tatsu"): SKIRMISH_AI_TRANSFER_ALL -- does its army come over?

Facts: wake at, attack at, money.
"""
from maps import niagara
from parts import Mission, Script

WAKE_AT, ATTACK_AT, MONEY = 60.0, 150.0, 10000
PERSONALITY = 'AIPersonalityDefinition:AIP_A06_AlliedPresident'


def mission(name='CampAI', wake=True):
    m = Mission(name=name, map=niagara, facts={'wake at': WAKE_AT, 'attack at': ATTACK_AT, 'money': MONEY})
    m.sides['s1'] = {'playerFaction': 'PlayerTemplate:Allies', 'aiPersonality': PERSONALITY}
    m.spawns |= {'AlliedPowerPlant', 'AlliedBarracks'}                 # what the AI builds, the check counts
    s1 = m.player('s1')
    m.put('AlliedConstructionYard', 'east base', 0, 0, side='s1', name='UNIT - CNV AI Yard', role='ai yard')
    for k in range(3):
        m.put('AlliedAntiVehicleVehicleTech1', 'east base', -250, -60 + 60 * k, side='s1')
        m.put('AlliedAntiVehicleVehicleTech1', 'base edge', 0, -60 + 60 * k)
    m.put('AlliedConstructionYard', 'base yard', name='UNIT - CNV AI Player Yard', role='player yard')
    base = 'CNV AI Base'
    m.waypoint('ai base', base, 'east base')
    m.scripts.append(Script('CNV AI - Start', [], [('PLAYER_SET_MONEY', s1, 0),
                                                   ('SET_MILLISECOND_TIMER', 'CNV AI Wake', WAKE_AT),
                                                   ('SET_MILLISECOND_TIMER', 'CNV AI Attack', ATTACK_AT)]))
    if wake:
        m.scripts += [
            Script('CNV AI - Wake', [('TIMER_EXPIRED', 'CNV AI Wake')],
                   [('UNIT_AI_TRANSFER_ALL', s1, 1), ('SKIRMISH_AI_MAKE_BASE', s1, base),
                    ('SKIRMISH_AI_SET_ALL_ENEMY_PLAYERS_PRIORITIES', s1, 20), ('SKIRMISH_AI_USE_REPAIRS', s1, 0),
                    ('SKIRMISH_AI_USE_REBUILD_SYSTEM', s1, 0), ('PLAYER_SET_MONEY', s1, MONEY)]),
            Script('CNV AI - Attack', [('TIMER_EXPIRED', 'CNV AI Attack')], [('SKIRMISH_AI_TRANSFER_ALL', s1, 1)])]
    return m
