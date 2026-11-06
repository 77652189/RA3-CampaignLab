"""Engine probe: the skirmish AI's strategic states switched by map flags (read back by checks/engine_aistate.py).

docs/design/skirmish-ai.md 五: does a script flag (ScriptedFlagHeuristic) turn an AI state on and off, and does each
state send only the units its team asks for? The enemy (s1, Allied) runs a personality of this probe's own: the
Allied co-op base with every inherited strategic state removed and two states of its own --
  CNVStateInf   on while flag 'CNV AI Infantry' is set: a SimpleAttack team of 2-4 Peacekeepers (AlliedAntiInfantryInfantry)
  CNVStateTank  on while flag 'CNV AI Tanks' is set: a SimpleAttack team of 2-4 Guardians (AlliedAntiVehicleVehicleTech1)
both aimed at the closest enemy structure (the player's yard on the west bank). The AI has a yard, 4 of each unit
and no money (it builds nothing). Woken at WAKE_AT the retail way (as aiopen_bench.py); INF_AT the infantry flag goes
on, TANK_AT it goes off and the tank flag on.

Facts: wake at, infantry at, tanks at.
"""
from maps import niagara
from parts import Mission, Script

WAKE_AT, INF_AT, TANK_AT = 10.0, 20.0, 60.0
PID = 'CNVStateTest'
INF, TANK = 'AlliedAntiInfantryInfantry', 'AlliedAntiVehicleVehicleTech1'
FLAG_INF, FLAG_TANK = 'CNV AI Infantry', 'CNV AI Tanks'
BASE = 'AlliedCoopBasePersonality'
# its strategic states with the parents' (SDK BasePersonality, CoopBasePersonality, AlliedCoopBasePersonality);
# removed so only the probe's two can recruit
INHERITED = ('ScoutAircraft', 'EngineerIdle', 'JapanEggUnpacker', 'HarvesterController', 'BaseDefenseController',
             'CommandAssault_Gather_Land', 'CommandAssault_Gather_Water', 'CommandAssault_Land', 'CommandAssault_Water',
             'CommandAssault_FighterAircraft', 'CommandAssault_BomberAircraft', 'CommandHold_Land', 'CommandHold_Water',
             'CommandHold_BomberAircraft', 'CommandHold_FighterAircraft', 'Command_StrikeTarget_Land',
             'Command_StrikeTarget_Water', 'Command_StrikeTarget_BomberAircraft', 'CaptureLandHusks',
             'AttachedBurstDroneRemoval', 'AlliedExpansion', 'AlliedNavalBase', 'AlliedCaptureTech',
             'AlliedCaptureWaterHusks')


def _state(sid, flag, unit):
    return f'''  <AIStrategicStateDefinition id="{sid}" MaxTargets="1">
    <Heuristic>
      <ScriptedFlagHeuristic FlagName="{flag}"/>
    </Heuristic>
    <TargetHeuristic TargetHeuristic="ClosestStructureHeuristic"/>
    <Tactic id="Attack" Tactic="SimpleAttack" EndBehavior="RAMPAGE" EndIfStateTurnsOff="true">
      <TeamTemplate MinUnits="2" MaxUnits="4" IncludeKindOf="CAN_ATTACK" ExcludeKindOf="IGNORES_SELECT_ALL HARVESTER"
                    AllowedLocomotorTypes="LAND AMPHIBIOUS" Priority="STANDARD" AlwaysRecruit="false"
                    MicroManager="StandardMicroManager_MEDIUM">
        <ObjectFilter Rule="ANY">
          <IncludeThing>{unit}</IncludeThing>
        </ObjectFilter>
      </TeamTemplate>
    </Tactic>
  </AIStrategicStateDefinition>'''


def personality_xml():
    removed = [f'    <StrategicState id="{k}" xai:joinAction="Remove"/>' for k in INHERITED]
    return '\n'.join([
        '<?xml version="1.0" encoding="utf-8"?>',
        '<AssetDeclaration xmlns="uri:ea.com:eala:asset" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"'
        ' xmlns:xai="uri:ea.com:eala:asset:instance">',
        '  <Tags></Tags>',
        '  <Includes>',
        f'    <Include type="instance" source="DATA:SkirmishAI/Personalities/{BASE}.xml" />',
        '  </Includes>',
        _state('CNVStateInf', FLAG_INF, INF),
        _state('CNVStateTank', FLAG_TANK, TANK),
        f'  <AIPersonalityDefinition id="{PID}" PersonalityType="{PID}" inheritFrom="{BASE}">',
        *removed,
        '    <StrategicState id="CNVStateInf" State="CNVStateInf"/>',
        '    <StrategicState id="CNVStateTank" State="CNVStateTank"/>',
        '  </AIPersonalityDefinition>',
        '</AssetDeclaration>', ''])


def mission(name='CampAIState'):
    m = Mission(name=name, map=niagara, facts={'wake at': WAKE_AT, 'infantry at': INF_AT, 'tanks at': TANK_AT})
    m.sides['s1'] = {'playerFaction': 'PlayerTemplate:Allies', 'aiPersonality': f'AIPersonalityDefinition:{PID}'}
    m.assets.append((f'{PID}.xml', personality_xml(), f'AIPersonalityDefinition:{PID}'))
    m.spawns |= {INF, TANK}
    s1 = m.player('s1')
    m.put('AlliedConstructionYard', 'east base', 0, 0, side='s1', name='UNIT - CNV AI Yard', role='ai yard')
    m.put('AlliedConstructionYard', 'base yard', name='UNIT - CNV AI Player Yard', role='player yard')
    for k in range(4):
        m.put(INF, 'east base', -260.0, -90.0 + 60.0 * k, side='s1', angle=3.1416, name=f'UNIT - CNV AI Inf {k + 1}',
              role=f'peacekeeper {k + 1}')
        m.put(TANK, 'east base', -200.0, 160.0 + 70.0 * k, side='s1', angle=3.1416, name=f'UNIT - CNV AI Tank {k + 1}',
              role=f'guardian {k + 1}')
    base = 'CNV AI Base'
    m.waypoint('ai base', base, 'east base')
    m.scripts += [
        Script('CNV AI - Start', [], [('PLAYER_SET_MONEY', s1, 0), ('SET_MILLISECOND_TIMER', 'CNV AI Wake', WAKE_AT),
                                      ('SET_MILLISECOND_TIMER', 'CNV AI Inf', INF_AT),
                                      ('SET_MILLISECOND_TIMER', 'CNV AI Tank', TANK_AT)]),
        Script('CNV AI - Wake', [('TIMER_EXPIRED', 'CNV AI Wake')],
               [('UNIT_AI_TRANSFER_ALL', s1, 1), ('SKIRMISH_AI_MAKE_BASE', s1, base),
                ('SKIRMISH_AI_SET_ALL_ENEMY_PLAYERS_PRIORITIES', s1, 20), ('SKIRMISH_AI_USE_REPAIRS', s1, 0),
                ('SKIRMISH_AI_USE_REBUILD_SYSTEM', s1, 0), ('PLAYER_SET_MONEY', s1, 0)]),
        Script('CNV AI - Infantry on', [('TIMER_EXPIRED', 'CNV AI Inf')], [('SET_FLAG', FLAG_INF, 1)]),
        Script('CNV AI - Tanks on', [('TIMER_EXPIRED', 'CNV AI Tank')],
               [('SET_FLAG', FLAG_INF, 0), ('SET_FLAG', FLAG_TANK, 1)])]
    return m


MISSION = {'aistate': mission}
