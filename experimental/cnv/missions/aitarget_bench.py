"""Engine probe: which of the player's structures a skirmish AI attack team goes for first (read back by
checks/engine_aitarget.py; engine line A, layer 4 block 4, RA3-EngineModel ra3model/ai/targets.py).

The enemy (s1, Allied) runs a personality of this probe's own: the Allied co-op base with every inherited strategic
state removed (as aistate_bench.py) and one state, always on (ConstantHeuristic), sending a team of 2-4 Peacekeepers.
The player has three structures:
  near  a power plant at the east gate, ~710 from the AI's base centre, two Multigunner turrets 150 north and south
  far   a power plant south of the AI's base (the carrier's spot), ~1010 from the base centre, nothing near it
  yard  the player's yard on the west bank, ~2700 away, one Multigunner turret beside it (so it is not as safe as far)
Builds:
  aitargetsafe  the retail main attack's pair: SafestToGroundStructureHeuristic + DefenseAvoidanceAttack
                (1AlliedBalanced BalancedAttackGround_MEDIUM). The model (least threat within 400) says: far.
  aitargetnear  ClosestStructureHeuristic + SimpleAttack, the control. The model (nearest the base centre): near.
Facts: wake at.
"""
from maps import niagara
from missions import aistate_bench as ab
from parts import Mission, Script

WAKE_AT = 10.0
PID = 'CNVTargetTest'
INF = ab.INF
TURRET = 'AlliedBaseDefense'


def _state(heuristic, tactic):
    return f'''  <AIStrategicStateDefinition id="CNVStateGo" MaxTargets="1">
    <Heuristic>
      <ConstantHeuristic/>
    </Heuristic>
    <TargetHeuristic TargetHeuristic="{heuristic}"/>
    <Tactic id="Attack" Tactic="{tactic}" EndBehavior="RAMPAGE">
      <TeamTemplate MinUnits="2" MaxUnits="4" IncludeKindOf="CAN_ATTACK" ExcludeKindOf="IGNORES_SELECT_ALL HARVESTER"
                    AllowedLocomotorTypes="LAND AMPHIBIOUS" Priority="STANDARD" AlwaysRecruit="false"
                    MicroManager="StandardMicroManager_MEDIUM">
        <ObjectFilter Rule="ANY">
          <IncludeThing>{INF}</IncludeThing>
        </ObjectFilter>
      </TeamTemplate>
    </Tactic>
  </AIStrategicStateDefinition>'''


def personality_xml(heuristic, tactic):
    removed = [f'    <StrategicState id="{k}" xai:joinAction="Remove"/>' for k in ab.INHERITED]
    return '\n'.join([
        '<?xml version="1.0" encoding="utf-8"?>',
        '<AssetDeclaration xmlns="uri:ea.com:eala:asset" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"'
        ' xmlns:xai="uri:ea.com:eala:asset:instance">',
        '  <Tags></Tags>',
        '  <Includes>',
        f'    <Include type="instance" source="DATA:SkirmishAI/Personalities/{ab.BASE}.xml" />',
        '  </Includes>',
        _state(heuristic, tactic),
        f'  <AIPersonalityDefinition id="{PID}" PersonalityType="{PID}" inheritFrom="{ab.BASE}">',
        *removed,
        '    <StrategicState id="CNVStateGo" State="CNVStateGo"/>',
        '  </AIPersonalityDefinition>',
        '</AssetDeclaration>', ''])


def mission(name, heuristic, tactic):
    m = Mission(name=name, map=niagara, facts={'wake at': WAKE_AT})
    m.cnv_heuristic = heuristic             # the check says the model's pick by it
    m.sides['s1'] = {'playerFaction': 'PlayerTemplate:Allies', 'aiPersonality': f'AIPersonalityDefinition:{PID}'}
    m.assets.append((f'{PID}.xml', personality_xml(heuristic, tactic), f'AIPersonalityDefinition:{PID}'))
    m.cnv_units = (INF,)
    s1 = m.player('s1')
    m.put('AlliedConstructionYard', 'east base', 0, 0, side='s1', name='UNIT - CNV AI Yard', role='ai yard')
    m.put('AlliedConstructionYard', 'base yard', name='UNIT - CNV AI Player Yard', role='player yard')
    m.put(TURRET, 'base yard', 220.0, 0.0, name='UNIT - CNV AI Yard Turret', role='yard turret')
    m.put('AlliedPowerPlant', 'east gate', 0.0, 0.0, name='UNIT - CNV AI Near Plant', role='near plant')
    for k, dy in enumerate((-150.0, 150.0)):
        m.put(TURRET, 'east gate', 0.0, dy, name=f'UNIT - CNV AI Near Turret {k + 1}', role=f'near turret {k + 1}')
    m.put('AlliedPowerPlant', 'carrier home', 0.0, 0.0, name='UNIT - CNV AI Far Plant', role='far plant')
    m.spawns |= {INF}
    for k in range(4):
        m.put(INF, 'east base', -260.0, -90.0 + 60.0 * k, side='s1', angle=3.1416, name=f'UNIT - CNV AI Inf {k + 1}',
              role=f'peacekeeper {k + 1}')
    base = 'CNV AI Base'
    m.waypoint('ai base', base, 'east base')
    m.scripts += [
        Script('CNV AI - Start', [], [('PLAYER_SET_MONEY', s1, 0), ('SET_MILLISECOND_TIMER', 'CNV AI Wake', WAKE_AT)]),
        Script('CNV AI - Wake', [('TIMER_EXPIRED', 'CNV AI Wake')],
               [('UNIT_AI_TRANSFER_ALL', s1, 1), ('SKIRMISH_AI_MAKE_BASE', s1, base),
                ('SKIRMISH_AI_SET_ALL_ENEMY_PLAYERS_PRIORITIES', s1, 20), ('SKIRMISH_AI_USE_REPAIRS', s1, 0),
                ('SKIRMISH_AI_USE_REBUILD_SYSTEM', s1, 0), ('PLAYER_SET_MONEY', s1, 0)])]
    return m


MISSION = {'aitargetsafe': lambda: mission('CampAISafe', 'SafestToGroundStructureHeuristic', 'DefenseAvoidanceAttack'),
           'aitargetnear': lambda: mission('CampAINearest', 'ClosestStructureHeuristic', 'SimpleAttack')}
