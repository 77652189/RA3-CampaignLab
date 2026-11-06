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
  aitargetidle5 / aitargetidle30  aitargetsafe with the team's MaxTeamIdleTime 5 s / 30 s (retail 15 s): the
                DefenseAvoidanceAttack legs wait for the team to be ready or idle that long (l4_tactics.md).
  aitargetflank aitargetsafe with FlankAttack (the same class as DefenseAvoidanceAttack, a random side).
Facts: wake at.
"""
from maps import niagara
from missions import aistate_bench as ab
from parts import Mission, Script

WAKE_AT = 10.0
PID = 'CNVTargetTest'
INF = ab.INF
TURRET = 'AlliedBaseDefense'


def _state(heuristic, tactic, micro='StandardMicroManager_MEDIUM'):
    return f'''  <AIStrategicStateDefinition id="CNVStateGo" MaxTargets="1">
    <Heuristic>
      <ConstantHeuristic/>
    </Heuristic>
    <TargetHeuristic TargetHeuristic="{heuristic}"/>
    <Tactic id="Attack" Tactic="{tactic}" EndBehavior="RAMPAGE">
      <TeamTemplate MinUnits="2" MaxUnits="4" IncludeKindOf="CAN_ATTACK" ExcludeKindOf="IGNORES_SELECT_ALL HARVESTER"
                    AllowedLocomotorTypes="LAND AMPHIBIOUS" Priority="STANDARD" AlwaysRecruit="false"
                    MicroManager="{micro}">
        <ObjectFilter Rule="ANY">
          <IncludeThing>{INF}</IncludeThing>
        </ObjectFilter>
      </TeamTemplate>
    </Tactic>
  </AIStrategicStateDefinition>'''


IDLE_ID = 'CNVMicroIdle'


def _micro_xml(idle):
    # StandardMicroManager_MEDIUM with its chain (Standard, Base) flattened -- the type cannot be inherited from
    # (the build says: not BaseInheritableAsset) -- only MaxTeamIdleTime changed
    return f'''  <AIMicroManagerData id="{IDLE_ID}" UpdateTime="2.0s" MaxTeamIdleTime="{idle}s"
    MaxTeamIdleDistanceChange="50.0" MaxUnitIdleTime="10s" MaxUnitIdleDistanceChange="30.0"
    EnemySearchDistanceVisionMultiplier="1.5" MinTimeToKeepTempVisionRangeBonus="10s" SiegeWeaponBuffer="1.5"
    DodgeThreatsReactionTimeMin="6s" DodgeThreatsReactionTimeMax="14s" GatherTempVisionRangeBonus="1.5"
    RetreatTempVisionRangeBonus="1.5" MaxSecondaryDamageFraction="1.3" EngageHostileTargets="true"
    EngagePassiveTargets="true" EngageTacticalTarget="true" RetreatPowerAdvantage="0.2"
    RetreatMinDistanceFromBase="900.0" RetreatMinDistanceToFallback="500.0" AlphaStrikeTargetHealthPct="0.5"
    AlphaStrikeTargetTimeToKill="4.0" Crush="true" EnterGarrisons="true" EnterGarrisonableStructureDistance="150"
    EnterBaseDefensesWhenIdle="false" PullbackInjured="true" PullbackInjuredHealthPct="0.35" ReverseMove="true"
    DodgeThreats="true" UseSpecialPowers="true" TimeToKeepTargetMin="3s" TimeToKeepTargetMax="5s"
    RandomTargetScoreModifier="1.0" SpecialPowerDelayMinimum="2s" SpecialPowerDelayMaximum="8s">
    <SpecificSpecialPowerDelay PowerType="TOGGLE" TogglePowerSubType="TOGGLE_LOCKDOWN" MinimumDelay="20s" MaximumDelay="40s"/>
    <RetreatBaseCriteria PreferredNotBaseTypes="CAPTURED" SortOrder="PREFER_CLOSEST"/>
    <IgnoreTargets Rule="ANY" Include="TIME_BOMB"/>
  </AIMicroManagerData>'''


def personality_xml(heuristic, tactic, idle=None):
    removed = [f'    <StrategicState id="{k}" xai:joinAction="Remove"/>' for k in ab.INHERITED]
    return '\n'.join([
        '<?xml version="1.0" encoding="utf-8"?>',
        '<AssetDeclaration xmlns="uri:ea.com:eala:asset" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"'
        ' xmlns:xai="uri:ea.com:eala:asset:instance">',
        '  <Tags></Tags>',
        '  <Includes>',
        f'    <Include type="instance" source="DATA:SkirmishAI/Personalities/{ab.BASE}.xml" />',
        '  </Includes>',
        *([_micro_xml(idle)] if idle else []),
        _state(heuristic, tactic, IDLE_ID if idle else 'StandardMicroManager_MEDIUM'),
        f'  <AIPersonalityDefinition id="{PID}" PersonalityType="{PID}" inheritFrom="{ab.BASE}">',
        *removed,
        '    <StrategicState id="CNVStateGo" State="CNVStateGo"/>',
        '  </AIPersonalityDefinition>',
        '</AssetDeclaration>', ''])


def mission(name, heuristic, tactic, idle=None):
    m = Mission(name=name, map=niagara, facts={'wake at': WAKE_AT})
    m.cnv_heuristic = heuristic             # the check says the model's pick by it
    m.sides['s1'] = {'playerFaction': 'PlayerTemplate:Allies', 'aiPersonality': f'AIPersonalityDefinition:{PID}'}
    m.assets.append((f'{PID}.xml', personality_xml(heuristic, tactic, idle), f'AIPersonalityDefinition:{PID}'))
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
           'aitargetnear': lambda: mission('CampAINearest', 'ClosestStructureHeuristic', 'SimpleAttack'),
           'aitargetidle5': lambda: mission('CampAIIdle5', 'SafestToGroundStructureHeuristic',
                                            'DefenseAvoidanceAttack', idle=5),
           'aitargetidle30': lambda: mission('CampAIIdle30', 'SafestToGroundStructureHeuristic',
                                             'DefenseAvoidanceAttack', idle=30),
           'aitargetflank': lambda: mission('CampAIFlank', 'SafestToGroundStructureHeuristic', 'FlankAttack')}
