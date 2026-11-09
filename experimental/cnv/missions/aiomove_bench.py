"""Engine probe: which opening a personality draws (<OpeningMove> Weight / Difficulty), and OpeningMoveHeuristic
Complete gating a strategic state on the opening being done (read back by checks/engine_aiomove.py; private
ai/opening.py choose(), ai/states.py value 'OpeningMoveHeuristic').

aiotime_bench's set-up (Niagara, s1 Allied with a yard at the east base, woken at 10 s with 50000,
AlliedCoopBasePersonality with every inherited strategic state removed), the openings the probe's own:
  CNVOpenP  Build AlliedPowerPlant            CNVOpenB  Build AlliedBarracks
  CNVOpenT  aiotime's: plant / Time 30s / plant / Time 20s / plant (the third ~s59 on the bench)
Variants (which opening: count the plants and barracks s1 has):
  aiowt   P Weight 0%, B 100%                     -> a barracks, no plant (a 0 weight is never drawn)
  aiowt2  P 100%, B 0%                            -> a plant (the control: not just the first / last line)
  aiodf   P 100% Difficulty EASY, B 100% MEDIUM HARD BRUTAL -> a barracks (the bench plays MEDIUM, aidiff)
  aiodf2  P MEDIUM HARD BRUTAL, B EASY            -> a plant
OpeningMoveHeuristic (opening T; one more state CNVStateOM: a SimpleAttack team of 4 Guardians at the closest enemy
structure, a player power plant ~750 west, as aipoweradv; count the Guardians at home):
  aiohc1  Complete true  -> home while the opening runs, out after the third plant (~s59)
  aiohc0  Complete false -> out right after the wake (~s14), as an always-on state

Facts: wake at, money, plants, barracks (what stands at s40), and for aiohc*: ai tanks, home until, out by.
"""
from maps import niagara
from missions.aistate_bench import BASE, INHERITED
from missions.aiotime_bench import ORDERS as T_ORDERS
from parts import Mission, Script

WAKE_AT, MONEY = 10.0, 50000
PLANT, BARRACKS, TANK = 'AlliedPowerPlant', 'AlliedBarracks', 'AlliedAntiVehicleVehicleTech1'
ALL = 'EASY MEDIUM HARD BRUTAL'
MOVES = {'CNVOpenP': (('Build', PLANT),), 'CNVOpenB': (('Build', BARRACKS),), 'CNVOpenT': T_ORDERS}


def personality_xml(pid, lines, gate=None):
    """lines: [(move id, weight, difficulty)]; gate: OpeningMoveHeuristic Complete (True / False) or None."""
    removed = [f'    <StrategicState id="{k}" xai:joinAction="Remove"/>' for k in INHERITED]
    used = sorted({mid for mid, _, _ in lines})
    out = ['<?xml version="1.0" encoding="utf-8"?>',
           '<AssetDeclaration xmlns="uri:ea.com:eala:asset" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"'
           ' xmlns:xai="uri:ea.com:eala:asset:instance">',
           '  <Tags></Tags>',
           '  <Includes>',
           f'    <Include type="instance" source="DATA:SkirmishAI/Personalities/{BASE}.xml" />',
           '  </Includes>']
    for mid in used:
        out += [f'  <SkirmishOpeningMove id="{mid}" Side="PlayerTemplate:Allies">',
                *[f'    <Order {k}="{v}" />' for k, v in MOVES[mid]],
                '  </SkirmishOpeningMove>']
    if gate is not None:
        out.append(f'''  <AIStrategicStateDefinition id="CNVStateOM" MaxTargets="1">
    <Heuristic>
      <OpeningMoveHeuristic Complete="{'true' if gate else 'false'}"/>
    </Heuristic>
    <TargetHeuristic TargetHeuristic="ClosestStructureHeuristic"/>
    <Tactic id="Attack" Tactic="SimpleAttack" EndBehavior="RAMPAGE" EndIfStateTurnsOff="false">
      <TeamTemplate MinUnits="2" MaxUnits="8" IncludeKindOf="CAN_ATTACK" ExcludeKindOf="IGNORES_SELECT_ALL HARVESTER"
                    AllowedLocomotorTypes="LAND AMPHIBIOUS" Priority="STANDARD" AlwaysRecruit="false"
                    MicroManager="StandardMicroManager_MEDIUM">
        <ObjectFilter Rule="ANY">
          <IncludeThing>{TANK}</IncludeThing>
        </ObjectFilter>
      </TeamTemplate>
    </Tactic>
  </AIStrategicStateDefinition>''')
    out += [f'  <AIPersonalityDefinition id="{pid}" PersonalityType="{pid}" inheritFrom="{BASE}">',
            *[f'    <OpeningMove Name="{mid}" Weight="{w}" Difficulty="{d}"/>' for mid, w, d in lines],
            *removed]
    if gate is not None:
        out.append('    <StrategicState id="CNVStateOM" State="CNVStateOM"/>')
    out += ['  </AIPersonalityDefinition>', '</AssetDeclaration>', '']
    return '\n'.join(out)


def mission(name, lines, plants, barracks, gate=None, home_until=None, out_by=None):
    pid = 'CNVOMove' + name[len('CampAIOM'):]
    facts = {'wake at': WAKE_AT, 'money': MONEY, 'plants': plants, 'barracks': barracks}
    tanks = 4 if gate is not None else 0
    if tanks:
        facts |= {'ai tanks': tanks, 'out by': out_by}
        if home_until is not None:
            facts['home until'] = home_until
    m = Mission(name=name, map=niagara, facts=facts)
    m.sides['s1'] = {'playerFaction': 'PlayerTemplate:Allies', 'aiPersonality': f'AIPersonalityDefinition:{pid}'}
    m.assets.append((f'{pid}.xml', personality_xml(pid, lines, gate), f'AIPersonalityDefinition:{pid}'))
    m.spawns |= {PLANT, BARRACKS, TANK}
    if tanks:
        m.cnv_units = (TANK,)
    s1 = m.player('s1')
    m.put('AlliedConstructionYard', 'east base', 0, 0, side='s1', name='UNIT - CNV AI Yard', role='ai yard')
    m.put('AlliedConstructionYard', 'base yard', name='UNIT - CNV AI Player Yard', role='player yard')
    if tanks:
        m.put(PLANT, 'east gate', -300.0, 0.0, name='UNIT - CNV AI Player Target', role='player target')
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
                ('SKIRMISH_AI_USE_REBUILD_SYSTEM', s1, 0), ('PLAYER_SET_MONEY', s1, MONEY)])]
    return m


MISSION = {
    'aiowt': lambda: mission('CampAIOMWt', [('CNVOpenP', '0%', ALL), ('CNVOpenB', '100%', ALL)], 0, 1),
    'aiowt2': lambda: mission('CampAIOMWt2', [('CNVOpenP', '100%', ALL), ('CNVOpenB', '0%', ALL)], 1, 0),
    'aiodf': lambda: mission('CampAIOMDf', [('CNVOpenP', '100%', 'EASY'), ('CNVOpenB', '100%', 'MEDIUM HARD BRUTAL')],
                             0, 1),
    'aiodf2': lambda: mission('CampAIOMDf2', [('CNVOpenP', '100%', 'MEDIUM HARD BRUTAL'), ('CNVOpenB', '100%', 'EASY')],
                              1, 0),
    'aiohc1': lambda: mission('CampAIOMHc1', [('CNVOpenT', '100%', ALL)], 1, 0, gate=True, home_until=42, out_by=46),
    'aiohc0': lambda: mission('CampAIOMHc0', [('CNVOpenT', '100%', ALL)], 1, 0, gate=False, home_until=None,
                              out_by=25),
}
