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


# aiar*: the AI builds `late` more Guardians itself (script-made units are never recruited: engine_aimicro
# aimicbuilth), by aimicro_bench's opener (Time 0s with a Deposit, the Builds, Time 90s: both built there)
LATE_MONEY, LATE_DEPOSIT, LATE_CHECK_AT = 10000, 5000, 60.0
OPENER = 'CNVTeamFOpener'
FACTORY_DY, PLANT_DY = -250.0, 400.0   # round 90: factory -400 -> -250, inside the yard's Tech2 reach (~300)
TECH2 = 'Upgrade_AlliedTech2'


def personality_xml(pid, kinds, filt, max_units, locos='LAND AMPHIBIOUS', objset='', always=False, late=0,
                    late_unit=TANK):
    removed = [f'    <StrategicState id="{k}" xai:joinAction="Remove"/>' for k in INHERITED]
    opener, first = [], []
    if late:
        removed += ['    <BuildState id="AlliedNeededUnits" xai:joinAction="Remove"/>']
        opener = [f'  <SkirmishOpeningMove id="{OPENER}" Side="PlayerTemplate:Allies">',
                  f'    <Order Time="0s" Account="PRODUCTION" Deposit="{LATE_DEPOSIT}" />',
                  *[f'    <Order Build="{late_unit}" />'] * late, '    <Order Time="90s"/>', '  </SkirmishOpeningMove>']
        first = [f'    <OpeningMove Name="{OPENER}" Weight="100%">', '      <Heuristic>',
                 '        <ConstantHeuristic/>', '      </Heuristic>', '    </OpeningMove>']
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
                    AllowedLocomotorTypes="{locos}" Priority="STANDARD" AlwaysRecruit="{'true' if always else 'false'}"{objset}
                    MicroManager="StandardMicroManager_MEDIUM">{filt}
      </TeamTemplate>
    </Tactic>
  </AIStrategicStateDefinition>''',
        *opener,
        f'  <AIPersonalityDefinition id="{pid}" PersonalityType="{pid}" inheritFrom="{BASE}">',
        *first,
        *removed,
        '    <StrategicState id="CNVStateTF" State="CNVStateTF"/>',
        '  </AIPersonalityDefinition>',
        '</AssetDeclaration>', ''])


def objfilter(rule, inc=(), exc=()):
    body = [f'          <IncludeThing>{t}</IncludeThing>' for t in inc] + \
           [f'          <ExcludeThing>{t}</ExcludeThing>' for t in exc]
    return '\n'.join(['', f'        <ObjectFilter Rule="{rule}">', *body, '        </ObjectFilter>'])


def mission(name, kinds=KINDS, filt='', max_units=8, tanks=4, inf=4, tanks_home=0, inf_home=4, second=INF,
            locos='LAND AMPHIBIOUS', objset='', always=False, late=0, late_unit=TANK):
    """second: the other unit type (Peacekeepers, or Riptide ACVs in the locomotor builds); inf / inf_home count it.
    always: the team's AlwaysRecruit; late: Guardians the AI builds itself (a war factory, a plant, the opener);
    late_unit: what the opener builds instead (round 89: aiar4 Riptides)."""
    pid = PID + name[-1]
    facts = {'wake at': WAKE_AT, 'ai tanks': tanks, 'ai infantry': inf,
             'expect tanks home': tanks_home, 'expect infantry home': inf_home}
    if late:
        facts |= {'late tanks': late, 'check at': LATE_CHECK_AT}
    m = Mission(name=name, map=niagara, facts=facts)
    m.sides['s1'] = {'playerFaction': 'PlayerTemplate:Allies', 'aiPersonality': f'AIPersonalityDefinition:{pid}'}
    xml = personality_xml(pid, kinds, filt, max_units, locos, f' RegisteredObjectSet="{objset}"' if objset else '',
                          always, late, late_unit)
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
        Script('CNV AI - Start', [], [('PLAYER_SET_MONEY', s1, 0), ('SET_MILLISECOND_TIMER', 'CNV AI Wake', WAKE_AT),
                                      # round 90: the Guardian needs Upgrade_AlliedTech2 (its GameDependency); the
                                      # yard holding it lends it to a war factory within ~300 (engine_tech c / d)
                                      *([('NAMED_RECEIVE_UPGRADE', TECH2, 'UNIT - CNV AI Yard')] if late else [])]),
        Script('CNV AI - Wake', [('TIMER_EXPIRED', 'CNV AI Wake')],
               [('UNIT_AI_TRANSFER_ALL', s1, 1), ('SKIRMISH_AI_MAKE_BASE', s1, base),
                ('SKIRMISH_AI_SET_ALL_ENEMY_PLAYERS_PRIORITIES', s1, 20), ('SKIRMISH_AI_USE_REPAIRS', s1, 0),
                ('SKIRMISH_AI_USE_REBUILD_SYSTEM', s1, 0), ('PLAYER_SET_MONEY', s1, LATE_MONEY if late else 0)])]
    if late:
        m.put('AlliedWarFactory', 'east base', 0, FACTORY_DY, side='s1', name='UNIT - CNV AI Factory', role='ai factory')
        m.put('AlliedPowerPlant', 'east base', 0, PLANT_DY, side='s1', name='UNIT - CNV AI Plant', role='ai plant')
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
    # round 88: AlwaysRecruit -- 4 Guardians go at ~s14 (ANY Guardian, MaxUnits 8), 2 more the AI builds itself after:
    # does the gone team take them (private ai/teams.py keep_recruiting, switched off: TeamMaker.keep_on False)?
    'aiar0': lambda: mission('CampAITFAr0', filt=objfilter('ANY', inc=(TANK,)), inf=0, inf_home=0, late=2,
                             tanks_home=2),
    'aiar1': lambda: mission('CampAITFAr1', filt=objfilter('ANY', inc=(TANK,)), inf=0, inf_home=0, late=2,
                             always=True, tanks_home=0),
    'aiar2': lambda: mission('CampAITFAr2', filt=objfilter('ANY', inc=(TANK,)), inf=0, inf_home=0, late=2,
                             always=True, max_units=4, tanks_home=2),     # full at 4: no room for the late ones
    # round 89: aiar0-2 owned 4 Guardians throughout -- the opener built none. Why: the script-placed war factory
    # (aiar3: no Guardians placed, does it build the 2) or owning that template already (aiar4: 4 Guardians, the
    # opener builds 2 Riptides). Guesses: both built, then out with the team (homes 0).
    # Bench round 90 (factory still at -400, no Tech2): aiar3 owned 0 Guardians to s75 -- the Guardian needs
    # Upgrade_AlliedTech2, nobody had it. From round 90 every late build gives the yard Tech2, factory at -250.
    # Then (round 90, 坦克在家 / 坦克拥有): aiar0 built s20 / s30, both stay home (2/6); aiar1 built s19 -> taken s29,
    # s30 -> taken s56 (0/6): the gone team recruits on; aiar2 (full at 4) both stay (2/6); aiar3 (none placed) the
    # first s21 forms a team and goes s30, the second s32 stays (expectation 0 was a guess; reading 1).
    'aiar3': lambda: mission('CampAITFAr3', filt=objfilter('ANY', inc=(TANK,)), tanks=0, inf=0, inf_home=0, late=2,
                             tanks_home=1),
    'aiar4': lambda: mission('CampAITFAr4', filt=objfilter('ANY', inc=(TANK, RIPTIDE)), second=RIPTIDE, inf=0,
                             inf_home=0, late=2, late_unit=RIPTIDE, tanks_home=0),
}
