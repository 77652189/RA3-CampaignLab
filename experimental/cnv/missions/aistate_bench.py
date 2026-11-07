"""Engine probe: the skirmish AI's strategic states switched by map flags (read back by checks/engine_aistate.py).

docs/design/skirmish-ai.md 五: does a script flag (ScriptedFlagHeuristic) turn an AI state on and off, and does each
state send only the units its team asks for? The enemy (s1, Allied) runs a personality of this probe's own: the
Allied co-op base with every inherited strategic state removed and two states of its own --
  CNVStateInf   on while flag 'CNV AI Infantry' is set: a SimpleAttack team of 2-4 Peacekeepers (AlliedAntiInfantryInfantry)
  CNVStateTank  on while flag 'CNV AI Tanks' is set: a SimpleAttack team of 2-4 Guardians (AlliedAntiVehicleVehicleTech1)
both aimed at the closest enemy structure (the player's yard on the west bank). The AI has a yard, 4 of each unit
and no money (it builds nothing). Woken at WAKE_AT the retail way (as aiopen_bench.py); INF_AT the infantry flag goes
on, TANK_AT it goes off and the tank flag on.
aistateoff / aistateoffhome (EndIfStateTurnsOff): the infantry flag also goes off at OFF_AT, while the team is on its
way (out of the base ~5 s after the flag, ~400 short of the target at OFF_AT); EndBehavior RAMPAGE / RETURN_HOME_AND_DISBAND.
aistateoff1 / aistateoffh: the same, off 1 s / 0.5 s after it went on -- while the team is still home.
aihunt / aihunt2: instead of the two, one always-on state with a Targetless Hunt tactic and a team of exactly one
Peacekeeper; MaxRunningCopies not written / 2. How soon does each next copy start, and how many run at once?

Facts: wake at, infantry at, tanks at, infantry off at (OFF_AT, or None).
"""
from maps import niagara
from parts import Mission, Script

WAKE_AT, INF_AT, TANK_AT = 10.0, 20.0, 60.0
OFF_AT = 28.0
PID = 'CNVStateTest'
INF, TANK = 'AlliedAntiInfantryInfantry', 'AlliedAntiVehicleVehicleTech1'
FLAG_INF, FLAG_TANK = 'CNV AI Infantry', 'CNV AI Tanks'
PLAIN = ('CNVAIInfantry', 'CNVAITanks')     # aistateplain: letters only (is the space the trouble?)
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


def _state(sid, flag, unit, gate='flag', end='RAMPAGE'):
    when = f'<ScriptedFlagHeuristic FlagName="{flag}"/>' if gate == 'flag' else '<ConstantHeuristic/>'
    return f'''  <AIStrategicStateDefinition id="{sid}" MaxTargets="1">
    <Heuristic>
      {when}
    </Heuristic>
    <TargetHeuristic TargetHeuristic="ClosestStructureHeuristic"/>
    <Tactic id="Attack" Tactic="SimpleAttack" EndBehavior="{end}" EndIfStateTurnsOff="true">
      <TeamTemplate MinUnits="2" MaxUnits="4" IncludeKindOf="CAN_ATTACK" ExcludeKindOf="IGNORES_SELECT_ALL HARVESTER"
                    AllowedLocomotorTypes="LAND AMPHIBIOUS" Priority="STANDARD" AlwaysRecruit="false"
                    MicroManager="StandardMicroManager_MEDIUM">
        <ObjectFilter Rule="ANY">
          <IncludeThing>{unit}</IncludeThing>
        </ObjectFilter>
      </TeamTemplate>
    </Tactic>
  </AIStrategicStateDefinition>'''


def _hunt(copies):
    """round 10: one always-on state with only a Targetless Hunt tactic (as retail AIStateLibrary.xml Hunt), a team
    of exactly one Peacekeeper; MaxRunningCopies = copies (None: not written)."""
    cap = '' if copies is None else f' MaxRunningCopies="{copies}"'
    return f'''  <AIStrategicStateDefinition id="CNVStateHunt"{cap}>
    <Heuristic>
      <ConstantHeuristic/>
    </Heuristic>
    <Tactic id="Hunt" Tactic="Hunt" Targetless="true">
      <TeamTemplate MinUnits="1" MaxUnits="1" IncludeKindOf="CAN_ATTACK" ExcludeKindOf="IGNORES_SELECT_ALL HARVESTER"
                    AllowedLocomotorTypes="LAND AMPHIBIOUS" Priority="STANDARD" AlwaysRecruit="false"
                    MicroManager="StandardMicroManager_MEDIUM">
        <ObjectFilter Rule="ANY">
          <IncludeThing>{INF}</IncludeThing>
        </ObjectFilter>
      </TeamTemplate>
    </Tactic>
  </AIStrategicStateDefinition>'''


def personality_xml(gate='flag', flags=(FLAG_INF, FLAG_TANK), end='RAMPAGE', hunt=False, copies=None):
    removed = [f'    <StrategicState id="{k}" xai:joinAction="Remove"/>' for k in INHERITED]
    if hunt:
        states = [_hunt(copies)]
        used = ['    <StrategicState id="CNVStateHunt" State="CNVStateHunt"/>']
    else:
        states = [_state('CNVStateInf', flags[0], INF, gate, end), _state('CNVStateTank', flags[1], TANK, gate, end)]
        used = ['    <StrategicState id="CNVStateInf" State="CNVStateInf"/>',
                '    <StrategicState id="CNVStateTank" State="CNVStateTank"/>']
    return '\n'.join([
        '<?xml version="1.0" encoding="utf-8"?>',
        '<AssetDeclaration xmlns="uri:ea.com:eala:asset" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"'
        ' xmlns:xai="uri:ea.com:eala:asset:instance">',
        '  <Tags></Tags>',
        '  <Includes>',
        f'    <Include type="instance" source="DATA:SkirmishAI/Personalities/{BASE}.xml" />',
        '  </Includes>',
        *states,
        f'  <AIPersonalityDefinition id="{PID}" PersonalityType="{PID}" inheritFrom="{BASE}">',
        *removed,
        *used,
        '  </AIPersonalityDefinition>',
        '</AssetDeclaration>', ''])


def mission(name='CampAIState', near=False, gate='flag', flags=(FLAG_INF, FLAG_TANK), scope=None, off_at=None,
            end='RAMPAGE', hunt=False, copies=None):
    """near: the player also has a power plant 300 west of the east gate, ~750 from the AI's units (the yard on the
    west bank is ~2600 away; A round 67 read: ClosestStructureHeuristic measures no distance, SearchRange is only the
    tech heuristic's -- aistatefar tests it). gate 'const': both states
    always on (ConstantHeuristic) -- does a team go at all. scope: the scripts' flag names get this prefix
    ('/' = the empty scope, which ScriptedFlagHeuristic reads), the AI's FlagName stays the bare name.
    off_at: the infantry flag also goes off then (seconds); end: the tactics' EndBehavior."""
    facts = {'wake at': WAKE_AT, 'infantry at': INF_AT, 'tanks at': TANK_AT, 'infantry off at': off_at,
             'hunt copies': (copies or 0) if hunt else None}   # 0: not written
    m = Mission(name=name, map=niagara, facts={k: v for k, v in facts.items() if v is not None})
    m.sides['s1'] = {'playerFaction': 'PlayerTemplate:Allies', 'aiPersonality': f'AIPersonalityDefinition:{PID}'}
    m.assets.append((f'{PID}.xml', personality_xml(gate, flags, end, hunt, copies), f'AIPersonalityDefinition:{PID}'))
    if scope is not None:
        flags = tuple(scope + f for f in flags)
    m.cnv_flags = flags                     # the check counts with these names (as the scripts write them)
    m.cnv_units = (INF, TANK)               # and these templates
    if near:
        m.put('AlliedPowerPlant', 'east gate', -300.0, 0.0, name='UNIT - CNV AI Player Target', role='player target')
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
        Script('CNV AI - Infantry on', [('TIMER_EXPIRED', 'CNV AI Inf')], [('SET_FLAG', flags[0], 1)]),
        Script('CNV AI - Tanks on', [('TIMER_EXPIRED', 'CNV AI Tank')],
               [('SET_FLAG', flags[0], 0), ('SET_FLAG', flags[1], 1)])]
    if off_at is not None:
        next(s for s in m.scripts if s.name == 'CNV AI - Start').do.append(
            ('SET_MILLISECOND_TIMER', 'CNV AI Inf Off', off_at))
        m.scripts.append(Script('CNV AI - Infantry off', [('TIMER_EXPIRED', 'CNV AI Inf Off')],
                                [('SET_FLAG', flags[0], 0)]))
    return m


MISSION = {'aistate': mission,
           'aistateplain': lambda: mission('CampAIPlain', near=True, flags=PLAIN),
           'aistatenear': lambda: mission('CampAINear', near=True),
           'aistateconst': lambda: mission('CampAIConst', near=True, gate='const'),
           # both states always on, only the player's yard ~2600 away: does distance stop a team (A round 67 read:
           # the enemy structure / unit heuristics measure no distance, only the tech one uses SearchRange)
           'aistatefar': lambda: mission('CampAIFar', gate='const'),
           'aistateslash': lambda: mission('CampAISlash', near=True, flags=PLAIN, scope='/'),
           'aistateoff': lambda: mission('CampAIOff', near=True, flags=PLAIN, scope='/', off_at=OFF_AT),
           'aistateoffhome': lambda: mission('CampAIHome', near=True, flags=PLAIN, scope='/', off_at=OFF_AT,
                                             end='RETURN_HOME_AND_DISBAND'),
           # round 10: the flag off again while the team is still home (it leaves ~74 frames after the flag)
           'aistateoff1': lambda: mission('CampAIOff1', near=True, flags=PLAIN, scope='/', off_at=INF_AT + 1.0),
           'aistateoffh': lambda: mission('CampAIOffH', near=True, flags=PLAIN, scope='/', off_at=INF_AT + 0.5),
           # round 10: a Targetless always-on state, one Peacekeeper a team -- how often, how many at once
           'aihunt': lambda: mission('CampAIHunt', near=True, hunt=True),
           'aihunt2': lambda: mission('CampAIHunt2', near=True, hunt=True, copies=2)}
