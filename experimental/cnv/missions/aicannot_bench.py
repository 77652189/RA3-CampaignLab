"""CannotAttackTargetReaction: land-only Guardians versus a named Cryocopter.

Three otherwise identical states; predictions follow the SDK enum comments.
Ignore should retain execution, Disband should release the team, and
TreatLikeSuccess should apply RAMPAGE. These are predictions, not coverage.
CNVTeams records the actual team lifecycle; see work/re/c_cannot_report.md.
"""
import resources
from maps import niagara
from missions.aistate_bench import BASE, INHERITED
from missions.aiteams_bench import host_unit, HOST
from parts import Mission, Script

TANK = 'AlliedAntiVehicleVehicleTech1'
AIR = 'AlliedSupportAircraft'
TARGET = 'UNIT - CNV Cannot Air'
STATE = 'CNVCannot'


def mission(name, reaction):
    m = Mission(name=name, map=resources.measured(niagara), ext=True,
                facts={'wake at': 10, 'cannot reaction': reaction})
    pid = 'CNVCannotPersonality'
    removed = '\n'.join(f'<StrategicState id="{k}" xai:joinAction="Remove"/>' for k in INHERITED)
    xml = f'''<?xml version="1.0" encoding="utf-8"?>
<AssetDeclaration xmlns="uri:ea.com:eala:asset" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
 xmlns:xai="uri:ea.com:eala:asset:instance">
 <Tags/>
 <Includes><Include type="instance" source="DATA:SkirmishAI/Personalities/{BASE}.xml"/></Includes>
 <AITargetingHeuristic id="CNVCannotAir" HeuristicType="NamedObject" Name="{TARGET}"
  RequireUniqueTarget="true"/>
 <AIStrategicStateDefinition id="{STATE}" MaxTargets="1" CannotAttackTargetReaction="{reaction}">
  <Heuristic><ConstantHeuristic/></Heuristic>
  <TargetHeuristic TargetHeuristic="CNVCannotAir"/>
  <Tactic id="Attack" Tactic="SimpleAttack" EndBehavior="RAMPAGE" EndIfStateTurnsOff="false">
   <TeamTemplate MinUnits="2" MaxUnits="2" IncludeKindOf="CAN_ATTACK"
    ExcludeKindOf="IGNORES_SELECT_ALL HARVESTER" AllowedLocomotorTypes="LAND AMPHIBIOUS"
    Priority="STANDARD" AlwaysRecruit="false" MicroManager="StandardMicroManager_MEDIUM">
    <ObjectFilter Rule="ANY"><IncludeThing>{TANK}</IncludeThing></ObjectFilter>
   </TeamTemplate>
  </Tactic>
 </AIStrategicStateDefinition>
 <AIPersonalityDefinition id="{pid}" PersonalityType="{pid}" inheritFrom="{BASE}">
  {removed}
  <StrategicState id="{STATE}" State="{STATE}"/>
 </AIPersonalityDefinition>
</AssetDeclaration>
'''
    m.sides['s1'] = {'playerFaction': 'PlayerTemplate:Allies',
                     'aiPersonality': f'AIPersonalityDefinition:{pid}'}
    m.assets.append((pid + '.xml', xml, f'AIPersonalityDefinition:{pid}'))
    m.cnv_units = (TANK,)
    m.put('AlliedConstructionYard', 'east base', side='s1', role='ai yard')
    m.put('AlliedConstructionYard', 'base yard', role='player yard')
    m.put(AIR, 'east base', -650, 0, name=TARGET, role='air target')
    for k in range(2):
        m.put(TANK, 'east base', -200, -50 + 100*k, side='s1', role=f'guardian {k+1}')
    m.units.append(host_unit())
    m.put(HOST, 'east base', 250, 400, side='s1', role='teams host')
    m.waypoint('ai base', 'CNV Cannot Base', 'east base')
    s1 = m.player('s1')
    m.scripts += [Script('Cannot - timer', [], [('PLAYER_SET_MONEY', s1, 0),
                      ('SET_MILLISECOND_TIMER', 'CNV Cannot Wake', 10)]),
                  Script('Cannot - wake', [('TIMER_EXPIRED', 'CNV Cannot Wake')],
                         [('UNIT_AI_TRANSFER_ALL', s1, 1), ('SKIRMISH_AI_MAKE_BASE', s1, 'CNV Cannot Base'),
                          ('SKIRMISH_AI_SET_ALL_ENEMY_PLAYERS_PRIORITIES', s1, 20),
                          ('SKIRMISH_AI_USE_REPAIRS', s1, 0), ('SKIRMISH_AI_USE_REBUILD_SYSTEM', s1, 0),
                          ('PLAYER_SET_MONEY', s1, 0)])]
    return m


MISSION = {
    'aicantig': lambda: mission('CampCantIg', 'Ignore'),
    'aicantdi': lambda: mission('CampCantDi', 'Disband'),
    'aicantsu': lambda: mission('CampCantSu', 'TreatLikeSuccess'),
}
