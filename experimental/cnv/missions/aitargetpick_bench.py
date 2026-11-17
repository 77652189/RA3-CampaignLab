"""Engine probe: which target a strategic state's team picks -- AITargetingHeuristic VitalKindOf / ForbiddenKindOf /
HeuristicType EnemyUnit, the state's TargetHeuristic Priority, and MaxTargets (read back by
checks/engine_aitargetpick.py; private ai/targets.py, simai through it).

aiteamfilter_bench's set-up (Niagara, the enemy s1 Allied with a yard and no money, every inherited strategic state
removed, woken at 10 s), one always-on state CNVStateTP (ConstantHeuristic): a SimpleAttack team, IncludeKindOf
CAN_ATTACK, MinUnits 1, MaxUnits 4. s1 has 4 Guardians at home (8 in the MaxTargets variants). The player has three
targets, all kept at full health by the check (so a team stays on its first pick):
  plant    AlliedPowerPlant (KindOf FS_POWER) at the east gate, ~710 west of the AI's base centre
  barracks AlliedBarracks (FS_BARRACKS) at the carrier's spot, ~1010 south
  tank     a player Guardian (VEHICLE, a unit) 700 north of the east gate, ~910 north-west
Builds (the state's TargetHeuristic list):
  aitpnear  ClosestStructureHeuristic (control): plant
  aitpvk    CNVHBarracks (EnemyStructure, SortType Distance, VitalKindOf FS_BARRACKS): barracks
  aitpfk    CNVHNoPower (EnemyStructure, VitalKindOf STRUCTURE, ForbiddenKindOf FS_POWER): barracks
  aitpunit  CNVHVehicle (HeuristicType EnemyUnit, VitalKindOf VEHICLE, as retail's vehicle heuristics): tank
  aitpphi   CNVHBarracks Priority 20 + ClosestStructureHeuristic Priority 10: the higher first -> barracks
  aitpplo   CNVHBarracks Priority 5 + ClosestStructureHeuristic Priority 10: plant
  aitpmt1   ClosestStructureHeuristic, MaxTargets 1, 8 Guardians: one team of 4 at the plant, 4 at home
  aitpmt2   the same with MaxTargets 2: the model's reading -- a team per slot, the second slot's unique nearest is
            the barracks: 4 at the plant, 4 at the barracks
Facts: wake at, ai tanks, expect plant / barracks / tank / home (the model's guess, Guardians there at the end).
"""
import resources
from maps import niagara
from missions.aistate_bench import BASE, INHERITED
from parts import Mission, Script

WAKE_AT = 10.0
PID = 'CNVTPick'
TANK = 'AlliedAntiVehicleVehicleTech1'
WALLS = ('NEUTRAL_TECH CIVILIAN_BUILDING WALK_ON_TOP_OF_WALL DEFENSIVE_WALL WALL_UPGRADE WALL_HUB WALL_SEGMENT '
         'WALL_PIECE WALL_GATE BASE_FOUNDATION')
HEURISTICS = {
    'CNVHBarracks': dict(HeuristicType='EnemyStructure', SortType='Distance', VitalKindOf='FS_BARRACKS',
                         ForbiddenKindOf=WALLS, RequireUniqueTarget='true'),
    'CNVHNoPower': dict(HeuristicType='EnemyStructure', SortType='Distance', VitalKindOf='STRUCTURE',
                        ForbiddenKindOf='FS_POWER ' + WALLS, RequireUniqueTarget='true'),
    'CNVHVehicle': dict(HeuristicType='EnemyUnit', SortType='Distance', VitalKindOf='VEHICLE', ForbiddenKindOf='',
                        RequireUniqueTarget='true'),
}


def state_xml(sid, targets, max_targets, priority='STANDARD', end='RAMPAGE'):
    th = ['    <TargetHeuristic TargetHeuristic="{}"{}/>'.format(h, '' if p is None else f' Priority="{p}"')
          for h, p in targets]
    return '\n'.join([
        f'  <AIStrategicStateDefinition id="{sid}" MaxTargets="{max_targets}">',
        '    <Heuristic>',
        '      <ConstantHeuristic/>',
        '    </Heuristic>',
        *th,
        '''    <Tactic id="Attack" Tactic="SimpleAttack" EndBehavior="''' + end + '''" EndIfStateTurnsOff="true">
      <TeamTemplate MinUnits="1" MaxUnits="4" IncludeKindOf="CAN_ATTACK" ExcludeKindOf="IGNORES_SELECT_ALL HARVESTER"
                    AllowedLocomotorTypes="LAND AMPHIBIOUS" Priority="''' + priority + '''" AlwaysRecruit="false"
                    MicroManager="StandardMicroManager_MEDIUM"/>
    </Tactic>
  </AIStrategicStateDefinition>'''])


def personality_xml(pid, targets, max_targets, priority='STANDARD', second=None, end='RAMPAGE'):
    """second = (TargetHeuristic list, team Priority) of a second always-on state CNVStateTQ, or None."""
    removed = [f'    <StrategicState id="{k}" xai:joinAction="Remove"/>' for k in INHERITED]
    every = list(targets) + (list(second[0]) if second else [])
    own = sorted({h for h, _ in every if h in HEURISTICS})
    heur = ['  <AITargetingHeuristic id="{}" {} />'.format(
        h, ' '.join(f'{k}="{v}"' for k, v in HEURISTICS[h].items())) for h in own]
    states = [state_xml('CNVStateTP', targets, max_targets, priority, end)]
    if second:
        states.append(state_xml('CNVStateTQ', second[0], max_targets, second[1]))
    return '\n'.join([
        '<?xml version="1.0" encoding="utf-8"?>',
        '<AssetDeclaration xmlns="uri:ea.com:eala:asset" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"'
        ' xmlns:xai="uri:ea.com:eala:asset:instance">',
        '  <Tags></Tags>',
        '  <Includes>',
        f'    <Include type="instance" source="DATA:SkirmishAI/Personalities/{BASE}.xml" />',
        '  </Includes>',
        *heur,
        *states,
        f'  <AIPersonalityDefinition id="{pid}" PersonalityType="{pid}" inheritFrom="{BASE}">',
        *removed,
        '    <StrategicState id="CNVStateTP" State="CNVStateTP"/>',
        *(['    <StrategicState id="CNVStateTQ" State="CNVStateTQ"/>'] if second else []),
        '  </AIPersonalityDefinition>',
        '</AssetDeclaration>', ''])


def mission(name, targets, expect, max_targets=1, tanks=4, priority='STANDARD', second=None, end='RAMPAGE',
            kill_at=None):
    """expect = (plant, barracks, tank, home): Guardians there at the end, the model's guess."""
    pid = PID + name[-3:]
    plant, barracks, tank, home = expect
    m = Mission(name=name, map=resources.measured(niagara), facts={'wake at': WAKE_AT, 'ai tanks': tanks, 'expect plant': plant,
                                               'expect barracks': barracks, 'expect tank': tank,
                                               'expect home': home})
    if kill_at is not None:
        m.facts['kill plant at'] = kill_at
    m.sides['s1'] = {'playerFaction': 'PlayerTemplate:Allies', 'aiPersonality': f'AIPersonalityDefinition:{pid}'}
    m.assets.append((f'{pid}.xml', personality_xml(pid, targets, max_targets, priority, second, end),
                     f'AIPersonalityDefinition:{pid}'))
    m.cnv_units = (TANK,)
    m.spawns |= {TANK}
    s1 = m.player('s1')
    m.put('AlliedConstructionYard', 'east base', 0, 0, side='s1', name='UNIT - CNV AI Yard', role='ai yard')
    m.put('AlliedConstructionYard', 'base yard', name='UNIT - CNV AI Player Yard', role='player yard')
    m.put('AlliedPowerPlant', 'east gate', 0.0, 0.0, name='UNIT - CNV TP Plant', role='plant')
    m.put('AlliedBarracks', 'carrier home', 0.0, 0.0, name='UNIT - CNV TP Barracks', role='barracks')
    m.put(TANK, 'east gate', 0.0, 700.0, name='UNIT - CNV TP Tank', role='tank')
    for k in range(tanks):
        m.put(TANK, 'east base', -200.0 - 80.0 * (k // 4), 160.0 + 70.0 * (k % 4), side='s1', angle=3.1416,
              name=f'UNIT - CNV AI Tank {k + 1}', role=f'ai guardian {k + 1}')
    base = 'CNV AI Base'
    m.waypoint('ai base', base, 'east base')
    m.scripts += [
        Script('CNV AI - Start', [], [('PLAYER_SET_MONEY', s1, 0), ('SET_MILLISECOND_TIMER', 'CNV AI Wake', WAKE_AT)]),
        Script('CNV AI - Wake', [('TIMER_EXPIRED', 'CNV AI Wake')],
               [('UNIT_AI_TRANSFER_ALL', s1, 1), ('SKIRMISH_AI_MAKE_BASE', s1, base),
                ('SKIRMISH_AI_SET_ALL_ENEMY_PLAYERS_PRIORITIES', s1, 20), ('SKIRMISH_AI_USE_REPAIRS', s1, 0),
                ('SKIRMISH_AI_USE_REBUILD_SYSTEM', s1, 0), ('PLAYER_SET_MONEY', s1, 0)])]
    return m


CLOSEST = 'ClosestStructureHeuristic'
BARRACKS = [('CNVHBarracks', None)]
MISSION = {
    'aitpnear': lambda: mission('CampAITPNear', [(CLOSEST, None)], (4, 0, 0, 0)),
    'aitpvk': lambda: mission('CampAITPVk', [('CNVHBarracks', None)], (0, 4, 0, 0)),
    'aitpfk': lambda: mission('CampAITPFk', [('CNVHNoPower', None)], (0, 4, 0, 0)),
    'aitpunit': lambda: mission('CampAITPUnit', [('CNVHVehicle', None)], (0, 0, 4, 0)),
    'aitpphi': lambda: mission('CampAITPPhi', [('CNVHBarracks', 20), (CLOSEST, 10)], (0, 4, 0, 0)),
    'aitpplo': lambda: mission('CampAITPPlo', [('CNVHBarracks', 5), (CLOSEST, 10)], (4, 0, 0, 0)),
    'aitpmt1': lambda: mission('CampAITPMt1', [(CLOSEST, None)], (4, 0, 0, 4), tanks=8),
    'aitpmt2': lambda: mission('CampAITPMt2', [(CLOSEST, None)], (4, 4, 0, 0), max_targets=2, tanks=8),
    # round 82: TeamTemplate.Priority -- two always-on states, P (CNVStateTP, the plant, a target from s13) and B
    # (CNVStateTQ, the barracks, from s19), both general-path teams of MaxUnits 4 over the same 4 Guardians.
    # The model guessed (4, 0, 0, 0) for all four (the plant's team first, no taking from another team); the bench
    # (round 82) sent all 4 to the barracks unless the plant's team is the higher (HIGH over STANDARD): expected now
    # as read.
    'aitpprs': lambda: mission('CampAITPPrS', [(CLOSEST, None)], (0, 4, 0, 0), second=(BARRACKS, 'STANDARD')),
    'aitpprh': lambda: mission('CampAITPPrH', [(CLOSEST, None)], (0, 4, 0, 0), second=(BARRACKS, 'HIGH')),
    'aitpprp': lambda: mission('CampAITPPrP', [(CLOSEST, None)], (4, 0, 0, 0), priority='HIGH',
                               second=(BARRACKS, 'STANDARD')),
    'aitpprl': lambda: mission('CampAITPPrL', [(CLOSEST, None)], (0, 4, 0, 0), priority='LOW',
                               second=(BARRACKS, 'STANDARD')),
    # round 84: Tactic EndBehavior -- ClosestStructure's team at the plant, the check kills the plant at s35 (the
    # barracks and the tank stay full). From the plant the tank is 700 off, the barracks 1055; from the AI's base the
    # barracks is the closest structure left (1010; the player's yard 2740). The model (private ai/tactics.py _end):
    # RAMPAGE = the nearest enemy of the team -> the tank; DISBAND = the team ends, the state's target re-picked ->
    # a new team to the barracks; RETURN_HOME_AND_DISBAND = home first, then the barracks; PICK_NEW_TARGET = the
    # barracks straight from the plant. expect = where they stand at the end.
    'aiendr': lambda: mission('CampAIEndR', [(CLOSEST, None)], (0, 0, 4, 0), kill_at=35.0),
    'aiendd': lambda: mission('CampAIEndD', [(CLOSEST, None)], (0, 4, 0, 0), end='DISBAND', kill_at=35.0),
    'aiendh': lambda: mission('CampAIEndH', [(CLOSEST, None)], (0, 4, 0, 0), end='RETURN_HOME_AND_DISBAND',
                              kill_at=35.0),
    'aiendp': lambda: mission('CampAIEndP', [(CLOSEST, None)], (0, 4, 0, 0), end='PICK_NEW_TARGET', kill_at=35.0),
}
