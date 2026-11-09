"""Engine probe: which of the AI's units a team template takes -- ObjectFilter Rule ANY / ALL / NONE with IncludeThing
/ ExcludeThing, TeamTemplate IncludeKindOf / ExcludeKindOf, MaxUnits (read back by checks/engine_aiteamfilter.py;
private ai/teams.py fits() / Team.full, simai through it).

aipoweradv_bench's set-up (Niagara, the enemy s1 Allied with a yard and no money, every inherited strategic state
removed, woken at 10 s), one always-on state CNVStateTF (ConstantHeuristic, MaxTargets 1): a SimpleAttack team at
the closest enemy structure (a player power plant ~750 west of them). s1 has 4 Guardians (AlliedAntiVehicleVehicleTech1)
and 4 Peacekeepers (AlliedAntiInfantryInfantry) at home; the team's filter is the variant's:
  aitfany   ObjectFilter Rule ANY, IncludeThing Guardian (the earlier probes' filter): tanks only
  aitfnone  Rule NONE, IncludeThing Guardian (retail CaptureLandHusks: "any 1 basic infantry" = NONE + the list)
  aitfall   Rule ALL, ExcludeThing Guardian (retail AIStateLibrary's ALL + aircraft list)
  aitfki    no ObjectFilter, IncludeKindOf INFANTRY
  aitfke    no ObjectFilter, IncludeKindOf CAN_ATTACK, ExcludeKindOf INFANTRY
  aitfmax   no ObjectFilter, IncludeKindOf CAN_ATTACK, MaxUnits 3, 8 Guardians and no Peacekeepers
Round 81 (no ObjectFilter, KindOf CAN_ATTACK): aitfland / aitfamph / aitfwat -- AllowedLocomotorTypes LAND /
AMPHIBIOUS / WATER, the Peacekeepers swapped for 4 Riptide ACVs (AlliedAntiInfantryVehicle, KindOf AMPHIBIOUS);
aitfosi / aitfosv / aitfosc -- RegisteredObjectSet INFANTRY / VEHICLES / SKIRMISH_AI_NORMAL_COMBAT_UNITS.
Every team: MinUnits 1, MaxUnits 8 (but aitfmax), AllowedLocomotorTypes LAND AMPHIBIOUS (but round 81's), Priority
STANDARD.

Facts: wake at, ai tanks, ai infantry, expect tanks home, expect infantry home (the model's guess before the bench:
ANY / NONE + Include = only those, ALL + Exclude = all but those; kinds: any of Include, none of Exclude).
"""
from maps import niagara
from missions.aistate_bench import BASE, INHERITED
from parts import Mission, Script

WAKE_AT = 10.0
PID = 'CNVTeamF'
TANK, INF = 'AlliedAntiVehicleVehicleTech1', 'AlliedAntiInfantryInfantry'
RIPTIDE = 'AlliedAntiInfantryVehicle'           # KindOf AMPHIBIOUS (simai's surface 'AMPHIBIOUS')
KINDS = 'IncludeKindOf="CAN_ATTACK" ExcludeKindOf="IGNORES_SELECT_ALL HARVESTER"'


def personality_xml(pid, kinds, filt, max_units, locos='LAND AMPHIBIOUS', objset=''):
    removed = [f'    <StrategicState id="{k}" xai:joinAction="Remove"/>' for k in INHERITED]
    return '\n'.join([
        '<?xml version="1.0" encoding="utf-8"?>',
        '<AssetDeclaration xmlns="uri:ea.com:eala:asset" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"'
        ' xmlns:xai="uri:ea.com:eala:asset:instance">',
        '  <Tags></Tags>',
        '  <Includes>',
        f'    <Include type="instance" source="DATA:SkirmishAI/Personalities/{BASE}.xml" />',
        '  </Includes>',
        f'''  <AIStrategicStateDefinition id="CNVStateTF" MaxTargets="1">
    <Heuristic>
      <ConstantHeuristic/>
    </Heuristic>
    <TargetHeuristic TargetHeuristic="ClosestStructureHeuristic"/>
    <Tactic id="Attack" Tactic="SimpleAttack" EndBehavior="RAMPAGE" EndIfStateTurnsOff="true">
      <TeamTemplate MinUnits="1" MaxUnits="{max_units}" {kinds}
                    AllowedLocomotorTypes="{locos}" Priority="STANDARD" AlwaysRecruit="false"{objset}
                    MicroManager="StandardMicroManager_MEDIUM">{filt}
      </TeamTemplate>
    </Tactic>
  </AIStrategicStateDefinition>''',
        f'  <AIPersonalityDefinition id="{pid}" PersonalityType="{pid}" inheritFrom="{BASE}">',
        *removed,
        '    <StrategicState id="CNVStateTF" State="CNVStateTF"/>',
        '  </AIPersonalityDefinition>',
        '</AssetDeclaration>', ''])


def objfilter(rule, inc=(), exc=()):
    body = [f'          <IncludeThing>{t}</IncludeThing>' for t in inc] + \
           [f'          <ExcludeThing>{t}</ExcludeThing>' for t in exc]
    return '\n'.join(['', f'        <ObjectFilter Rule="{rule}">', *body, '        </ObjectFilter>'])


def mission(name, kinds=KINDS, filt='', max_units=8, tanks=4, inf=4, tanks_home=0, inf_home=4, second=INF,
            locos='LAND AMPHIBIOUS', objset=''):
    """second: the other unit type (Peacekeepers, or Riptide ACVs in the locomotor builds); inf / inf_home count it."""
    pid = PID + name[-1]
    m = Mission(name=name, map=niagara, facts={'wake at': WAKE_AT, 'ai tanks': tanks, 'ai infantry': inf,
                                               'expect tanks home': tanks_home, 'expect infantry home': inf_home})
    m.sides['s1'] = {'playerFaction': 'PlayerTemplate:Allies', 'aiPersonality': f'AIPersonalityDefinition:{pid}'}
    xml = personality_xml(pid, kinds, filt, max_units, locos, f' RegisteredObjectSet="{objset}"' if objset else '')
    m.assets.append((f'{pid}.xml', xml, f'AIPersonalityDefinition:{pid}'))
    m.cnv_units = (TANK, second)
    m.cnv_labels = ('坦克在家', '步兵在家' if second == INF else '气垫船在家')
    m.spawns |= {TANK, second}
    s1 = m.player('s1')
    m.put('AlliedConstructionYard', 'east base', 0, 0, side='s1', name='UNIT - CNV AI Yard', role='ai yard')
    m.put('AlliedConstructionYard', 'base yard', name='UNIT - CNV AI Player Yard', role='player yard')
    m.put('AlliedPowerPlant', 'east gate', -300.0, 0.0, name='UNIT - CNV AI Player Target', role='player target')
    for k in range(tanks):
        m.put(TANK, 'east base', -200.0 - 80.0 * (k // 4), 160.0 + 70.0 * (k % 4), side='s1', angle=3.1416,
              name=f'UNIT - CNV AI Tank {k + 1}', role=f'ai guardian {k + 1}')
    for k in range(inf):
        if second == INF:
            m.put(INF, 'east base', -200.0, -160.0 - 50.0 * k, side='s1', angle=3.1416,
                  name=f'UNIT - CNV AI Peacekeeper {k + 1}', role=f'ai peacekeeper {k + 1}')
        else:
            m.put(second, 'east base', -200.0 - 70.0 * (k % 2), -160.0 - 70.0 * (k // 2), side='s1', angle=3.1416,
                  name=f'UNIT - CNV AI Riptide {k + 1}', role=f'ai riptide {k + 1}')
    base = 'CNV AI Base'
    m.waypoint('ai base', base, 'east base')
    m.scripts += [
        Script('CNV AI - Start', [], [('PLAYER_SET_MONEY', s1, 0), ('SET_MILLISECOND_TIMER', 'CNV AI Wake', WAKE_AT)]),
        Script('CNV AI - Wake', [('TIMER_EXPIRED', 'CNV AI Wake')],
               [('UNIT_AI_TRANSFER_ALL', s1, 1), ('SKIRMISH_AI_MAKE_BASE', s1, base),
                ('SKIRMISH_AI_SET_ALL_ENEMY_PLAYERS_PRIORITIES', s1, 20), ('SKIRMISH_AI_USE_REPAIRS', s1, 0),
                ('SKIRMISH_AI_USE_REBUILD_SYSTEM', s1, 0), ('PLAYER_SET_MONEY', s1, 0)])]
    return m


MISSION = {
    'aitfany': lambda: mission('CampAITFAny', filt=objfilter('ANY', inc=(TANK,))),
    'aitfnone': lambda: mission('CampAITFNone', filt=objfilter('NONE', inc=(TANK,))),
    'aitfall': lambda: mission('CampAITFAll', filt=objfilter('ALL', exc=(TANK,)), tanks_home=4, inf_home=0),
    'aitfki': lambda: mission('CampAITFKi', kinds='IncludeKindOf="INFANTRY"', tanks_home=4, inf_home=0),
    'aitfke': lambda: mission('CampAITFKe', kinds='IncludeKindOf="CAN_ATTACK" ExcludeKindOf="INFANTRY"'),
    'aitfmax': lambda: mission('CampAITFMax', max_units=3, tanks=8, inf=0, tanks_home=5, inf_home=0),
    # round 81: AllowedLocomotorTypes (Guardians: no AMPHIBIOUS kind = LAND; Riptide ACVs: AMPHIBIOUS) and
    # RegisteredObjectSet (the model reads it but filters on nothing; the guesses are "a filter by kind")
    'aitfland': lambda: mission('CampAITFLand', second=RIPTIDE, locos='LAND', tanks_home=0, inf_home=4),
    'aitfamph': lambda: mission('CampAITFAmph', second=RIPTIDE, locos='AMPHIBIOUS', tanks_home=4, inf_home=0),
    'aitfwat': lambda: mission('CampAITFWat', second=RIPTIDE, locos='WATER', tanks_home=4, inf_home=4),
    'aitfosi': lambda: mission('CampAITFOsI', objset='INFANTRY', tanks_home=4, inf_home=0),
    'aitfosv': lambda: mission('CampAITFOsV', objset='VEHICLES', tanks_home=0, inf_home=4),
    'aitfosc': lambda: mission('CampAITFOsC', objset='SKIRMISH_AI_NORMAL_COMBAT_UNITS', tanks_home=0, inf_home=0),
}
