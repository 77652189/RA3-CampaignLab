"""Engine probe: the skirmish AI's ReactiveDefense tactic and the personality's ReactiveDefenseRadius (read back by
checks/engine_aireactive.py; engine line B round 199).

Same setup as aidefense_bench's non-far builds: s1 (Allied AI) owns its yard at 'east base' and four Peacekeepers
beside it, the player has only its yard at 'base yard', s1's money is 0, the AI wakes at WAKE_AT (the retail wake
actions, MAKE_BASE included). The personality is the Allied co-op base with every inherited strategic state removed
and one state, always on: a Targetless ReactiveDefense tactic (EndBehavior DISBAND, aesthetics off) with a team of 2-4
Peacekeepers. The AIPersonalityDefinition carries ReactiveDefenseRadius = R.
One player Peacekeeper (the 'foe') stands FOE_DIST straight south of the AI yard on open grass (aidefense's OUT
direction), facing north, owner p1. Between the radii: 750 < 1000 < 1200.
Builds:
  aireact750   R = 750   (the foe is outside the radius)
  aireact1200  R = 1200  (inside)
"""
import resources
from maps import niagara
from missions import aistate_bench as ab
from parts import Mission, Script

WAKE_AT = 10.0
FOE_DIST = 1000.0
PID = 'CNVReactiveTest'
INF = ab.INF


def _state():
    return f'''  <AIStrategicStateDefinition id="CNVStateGo" MaxTargets="1">
    <Heuristic>
      <ConstantHeuristic/>
    </Heuristic>
    <Tactic id="Defend" Tactic="ReactiveDefense" Targetless="true" EndBehavior="DISBAND"
            UseAestheticsManager="false">
      <TeamTemplate MinUnits="2" MaxUnits="4" IncludeKindOf="CAN_ATTACK" ExcludeKindOf="IGNORES_SELECT_ALL HARVESTER"
                    AllowedLocomotorTypes="LAND AMPHIBIOUS" Priority="STANDARD" AlwaysRecruit="false"
                    MicroManager="StandardMicroManager_MEDIUM">
        <ObjectFilter Rule="ANY">
          <IncludeThing>{INF}</IncludeThing>
        </ObjectFilter>
      </TeamTemplate>
    </Tactic>
  </AIStrategicStateDefinition>'''


def personality_xml(radius):
    removed = [f'    <StrategicState id="{k}" xai:joinAction="Remove"/>' for k in ab.INHERITED]
    return '\n'.join([
        '<?xml version="1.0" encoding="utf-8"?>',
        '<AssetDeclaration xmlns="uri:ea.com:eala:asset" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"'
        ' xmlns:xai="uri:ea.com:eala:asset:instance">',
        '  <Tags></Tags>',
        '  <Includes>',
        f'    <Include type="instance" source="DATA:SkirmishAI/Personalities/{ab.BASE}.xml" />',
        '  </Includes>',
        _state(),
        f'  <AIPersonalityDefinition id="{PID}" PersonalityType="{PID}" inheritFrom="{ab.BASE}"'
        f' ReactiveDefenseRadius="{int(radius)}">',
        *removed,
        '    <StrategicState id="CNVStateGo" State="CNVStateGo"/>',
        '  </AIPersonalityDefinition>',
        '</AssetDeclaration>', ''])


def mission(name, radius):
    m = Mission(name=name, map=resources.measured(niagara), facts={'wake at': WAKE_AT, 'radius': radius})
    m.sides['s1'] = {'playerFaction': 'PlayerTemplate:Allies', 'aiPersonality': f'AIPersonalityDefinition:{PID}'}
    m.assets.append((f'{PID}.xml', personality_xml(radius), f'AIPersonalityDefinition:{PID}'))
    m.cnv_units = (INF,)
    s1 = m.player('s1')
    m.put('AlliedConstructionYard', 'east base', 0, 0, side='s1', name='UNIT - CNV AI Yard', role='ai yard')
    m.put('AlliedConstructionYard', 'base yard', name='UNIT - CNV AI Player Yard', role='player yard')
    m.spawns |= {INF}
    for k in range(4):
        m.put(INF, 'east base', -100.0, -90.0 + 60.0 * k, side='s1', angle=3.1416, name=f'UNIT - CNV AI Inf {k + 1}',
              role=f'peacekeeper {k + 1}')
    m.put(INF, 'east base', 0.0, -FOE_DIST, angle=1.5708, name='UNIT - CNV RD Foe', role='foe')
    base = 'CNV AI Base'
    m.waypoint('ai base', base, 'east base')
    m.scripts += [
        Script('CNV AI - Start', [], [('PLAYER_SET_MONEY', s1, 0), ('SET_MILLISECOND_TIMER', 'CNV AI Wake', WAKE_AT)]),
        Script('CNV AI - Wake', [('TIMER_EXPIRED', 'CNV AI Wake')],
               [('UNIT_AI_TRANSFER_ALL', s1, 1), ('SKIRMISH_AI_MAKE_BASE', s1, base),
                ('SKIRMISH_AI_SET_ALL_ENEMY_PLAYERS_PRIORITIES', s1, 20), ('SKIRMISH_AI_USE_REPAIRS', s1, 0),
                ('SKIRMISH_AI_USE_REBUILD_SYSTEM', s1, 0), ('PLAYER_SET_MONEY', s1, 0)])]
    return m


MISSION = {'aireact750': lambda: mission('CampAIReact750', 750),
           'aireact1200': lambda: mission('CampAIRea1200', 1200)}
