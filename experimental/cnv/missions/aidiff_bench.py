"""Engine probe: a personality's <StrategicState Difficulty=...> -- does the AI run only the states listed for its
difficulty, and which difficulty does an AI player of a campaign map get (read back by checks/engine_aidiff.py;
private ai/data.py Personality.of / ai/states.py StrategicStates, simai's DIFFICULTY map: campaign normal -> MEDIUM).

aiteamfilter_bench's set-up (Niagara, the enemy s1 Allied with a yard and no money, every inherited strategic state
removed, woken at 10 s; 4 Guardians and 4 Peacekeepers at home) with TWO always-on states (ConstantHeuristic,
MaxTargets 1, SimpleAttack at the closest player structure, MinUnits 1, MaxUnits 8):
  CNVStateDT  listed Difficulty="MEDIUM"              its team takes Guardians only (ObjectFilter ANY + IncludeThing)
  CNVStateDI  listed Difficulty="EASY HARD BRUTAL"    its team takes Peacekeepers only
Two player power plants ~750 west (one target goes to one state, engine_aistate aistatefar2), so both could leave.
Builds: aidiff (as above) and aidiffx (the two Difficulty lists swapped: the same answer with the other unit type,
so a type that never leaves is not read as a difficulty).

Facts: wake at, swapped (1: the Guardians' state is the EASY HARD BRUTAL one), expect tanks home, expect infantry home (the
model's guess: the bench walks the campaign at normal = MEDIUM, only the MEDIUM state runs).
"""
from maps import niagara
from missions.aistate_bench import BASE, INHERITED
from missions.aiteamfilter_bench import TANK, INF, objfilter
from parts import Mission, Script

WAKE_AT = 10.0
MEDIUM, OTHERS = 'MEDIUM', 'EASY HARD BRUTAL'


def state_xml(sid, unit):
    return f'''  <AIStrategicStateDefinition id="{sid}" MaxTargets="1">
    <Heuristic>
      <ConstantHeuristic/>
    </Heuristic>
    <TargetHeuristic TargetHeuristic="ClosestStructureHeuristic"/>
    <Tactic id="Attack" Tactic="SimpleAttack" EndBehavior="RAMPAGE" EndIfStateTurnsOff="true">
      <TeamTemplate MinUnits="1" MaxUnits="8" IncludeKindOf="CAN_ATTACK" ExcludeKindOf="IGNORES_SELECT_ALL HARVESTER"
                    AllowedLocomotorTypes="LAND AMPHIBIOUS" Priority="STANDARD" AlwaysRecruit="false"
                    MicroManager="StandardMicroManager_MEDIUM">{objfilter('ANY', inc=(unit,))}
      </TeamTemplate>
    </Tactic>
  </AIStrategicStateDefinition>'''


def personality_xml(pid, tank_diff, inf_diff):
    removed = [f'    <StrategicState id="{k}" xai:joinAction="Remove"/>' for k in INHERITED]
    return '\n'.join([
        '<?xml version="1.0" encoding="utf-8"?>',
        '<AssetDeclaration xmlns="uri:ea.com:eala:asset" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"'
        ' xmlns:xai="uri:ea.com:eala:asset:instance">',
        '  <Tags></Tags>',
        '  <Includes>',
        f'    <Include type="instance" source="DATA:SkirmishAI/Personalities/{BASE}.xml" />',
        '  </Includes>',
        state_xml('CNVStateDT', TANK),
        state_xml('CNVStateDI', INF),
        f'  <AIPersonalityDefinition id="{pid}" PersonalityType="{pid}" inheritFrom="{BASE}">',
        *removed,
        f'    <StrategicState id="CNVStateDT" State="CNVStateDT" Difficulty="{tank_diff}"/>',
        f'    <StrategicState id="CNVStateDI" State="CNVStateDI" Difficulty="{inf_diff}"/>',
        '  </AIPersonalityDefinition>',
        '</AssetDeclaration>', ''])


def mission(name, swapped=False):
    pid = 'CNVDiff' + ('X' if swapped else 'M')
    tank_diff, inf_diff = (OTHERS, MEDIUM) if swapped else (MEDIUM, OTHERS)
    m = Mission(name=name, map=niagara, facts={'wake at': WAKE_AT, 'swapped': int(swapped),
                                               'expect tanks home': 4 if swapped else 0,
                                               'expect infantry home': 0 if swapped else 4})
    m.sides['s1'] = {'playerFaction': 'PlayerTemplate:Allies', 'aiPersonality': f'AIPersonalityDefinition:{pid}'}
    m.assets.append((f'{pid}.xml', personality_xml(pid, tank_diff, inf_diff), f'AIPersonalityDefinition:{pid}'))
    m.cnv_units = (TANK, INF)
    m.spawns |= {TANK, INF}
    s1 = m.player('s1')
    m.put('AlliedConstructionYard', 'east base', 0, 0, side='s1', name='UNIT - CNV AI Yard', role='ai yard')
    m.put('AlliedConstructionYard', 'base yard', name='UNIT - CNV AI Player Yard', role='player yard')
    m.put('AlliedPowerPlant', 'east gate', -300.0, 120.0, name='UNIT - CNV AI Player Target', role='player target')
    m.put('AlliedPowerPlant', 'east gate', -300.0, -120.0, name='UNIT - CNV AI Player Target 2', role='player target 2')
    for k in range(4):
        m.put(TANK, 'east base', -200.0, 160.0 + 70.0 * k, side='s1', angle=3.1416,
              name=f'UNIT - CNV AI Tank {k + 1}', role=f'ai guardian {k + 1}')
        m.put(INF, 'east base', -200.0, -160.0 - 50.0 * k, side='s1', angle=3.1416,
              name=f'UNIT - CNV AI Peacekeeper {k + 1}', role=f'ai peacekeeper {k + 1}')
    base = 'CNV AI Base'
    m.waypoint('ai base', base, 'east base')
    m.scripts += [
        Script('CNV AI - Start', [], [('PLAYER_SET_MONEY', s1, 0), ('SET_MILLISECOND_TIMER', 'CNV AI Wake', WAKE_AT)]),
        Script('CNV AI - Wake', [('TIMER_EXPIRED', 'CNV AI Wake')],
               [('UNIT_AI_TRANSFER_ALL', s1, 1), ('SKIRMISH_AI_MAKE_BASE', s1, base),
                ('SKIRMISH_AI_SET_ALL_ENEMY_PLAYERS_PRIORITIES', s1, 20), ('SKIRMISH_AI_USE_REPAIRS', s1, 0),
                ('SKIRMISH_AI_USE_REBUILD_SYSTEM', s1, 0), ('PLAYER_SET_MONEY', s1, 0)])]
    return m


MISSION = {'aidiff': lambda: mission('CampAIDiff'), 'aidiffx': lambda: mission('CampAIDiffX', swapped=True)}
