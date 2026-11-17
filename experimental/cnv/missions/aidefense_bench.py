"""Engine probe: the skirmish AI's StaticDefense tactic -- the Distance circle and the pull-back (read back by
checks/engine_aidefense.py; engine line B).

The enemy (s1, Allied) runs a personality of this probe's own: the Allied co-op base with every inherited strategic
state removed (as aistate_bench.py) and one state, always on (ConstantHeuristic, MaxTargets 1), whose target is
FriendlyLandStructureHeuristic (the retail BalancedDefense pick) and whose tactic is
  StaticDefense EndBehavior="DISBAND" Distance=D UpdateTime=U CombatLeashSlack=S UseAestheticsManager="false"
with a team of 2-4 Peacekeepers. s1 owns one structure, its yard at 'east base' (the thing to defend), and four
Peacekeepers beside it (100 west, 90 north .. 90 south of the yard centre, all within 150). The player has only
its own yard at 'base yard' on the west bank, no turret, no enemy near: nothing fights.
Ten seconds after the start the AI wakes (as aitarget_bench); 20 s later (mission second 30) a script orders the four
Peacekeepers by name to MOVE (plain move, not attack-move) to FAR: FAR_DIST from the yard centre toward 'east gate'
(direction (-0.990, -0.141); yard (3850, 3400)). FAR_DIST was 1200 (FAR (2662, 3231)) for every reading taken on
2026-11-06; it is 1150 (FAR (2712, 3237)) since round 65, because 1175..1250 on that line is a thicket of trees
(sapporo's MR_Tree06 pair at (2659, 3223) / (2648, 3249); test_maps keeps waypoints off scenery). The check reads how
far they get from the yard and whether the team pulls them back inside Distance.
Builds:
  aidef250    D=250, U=1 s, S=1.5 (the schema default slack)
  aidef450    D=450
  aidefupd4   D=250, UpdateTime 4 s
  aidefslack  D=250, CombatLeashSlack 3.0
Round 62 (the push must not take the Peacekeepers out of the AI's team, so the mission gives no move): the four start
START_FAR (700) from the yard toward the gate -- outside every ring but the 900 one -- so the team's own attack-move to
the yard is the control (the team formed and defends); at mission second PUSH_AT (55) checks/engine_aidefense.py
moves them out to FAR itself, with no UNIT_SET_TEAM:
  aidefctl    D=250, U=1 s: UNIT_TELEPORT_TO_WAYPOINT FAR, one by one
  aidefctl4   D=250, U=4 s: the same teleport
  (since round 70 the teleports go to OUT, OUT_DIST (1200) straight south of the yard on open grass: bench 11-07, the
  teleport to FAR at 1150 moved no one -- both builds 4 4 4 4 from s9 to the end; FAR sits on the river bank. 11-06's
  readings were teleports to FAR at 1200 west, the same distance.)
  aidefmv     D=250, U=1 s: MOVE_NAMED_UNIT_TO FAR, one by one (the AI's attack-move against a plain script move)
KNOWN PIT (engine line A round 136): s1 is one of the players the container hands to the skirmish AI at the start
(model.handed_to_ai, Lib_Skirmish_Setup), which takes the four placed Peacekeepers off every team. aidef250 / 450 /
upd4 / slack's 'CNV AI - Move' (m.order: UNIT_SET_TEAM, then MOVE_TEAM_TO) does reach them -- a join after the start
holds -- but puts them on a script team, out of the AI's (round 61's "nobody pulled back"): those four builds read no
pull-back. Use the far=True builds (no mission order; the check moves them by name), or put AI-run units the mission
must order on s4..s6 / make them by script (contract G6c refuses a team order that reaches none).
"""
import resources
from maps import niagara
from missions import aistate_bench as ab
from parts import Mission, Script

WAKE_AT = 10.0
MOVE_AT = 30.0
PUSH_AT = 55.0
START_FAR = 700.0
FAR_DIST = 1150.0   # 1200 until round 65 (on two trees), see the docstring
OUT_DIST = 1200.0   # the teleports' OUT, straight south of the yard (round 70)
PID = 'CNVDefenseTest'
INF = ab.INF
HEURISTIC = 'FriendlyLandStructureHeuristic'


def _state(dist, upd, slack):
    return f'''  <AIStrategicStateDefinition id="CNVStateGo" MaxTargets="1">
    <Heuristic>
      <ConstantHeuristic/>
    </Heuristic>
    <TargetHeuristic TargetHeuristic="{HEURISTIC}"/>
    <Tactic id="Defend" Tactic="StaticDefense" EndBehavior="DISBAND" Distance="{dist}" UpdateTime="{upd}s"
            CombatLeashSlack="{slack}" UseAestheticsManager="false">
      <TeamTemplate MinUnits="2" MaxUnits="4" IncludeKindOf="CAN_ATTACK" ExcludeKindOf="IGNORES_SELECT_ALL HARVESTER"
                    AllowedLocomotorTypes="LAND AMPHIBIOUS" Priority="STANDARD" AlwaysRecruit="false"
                    MicroManager="StandardMicroManager_MEDIUM">
        <ObjectFilter Rule="ANY">
          <IncludeThing>{INF}</IncludeThing>
        </ObjectFilter>
      </TeamTemplate>
    </Tactic>
  </AIStrategicStateDefinition>'''


def personality_xml(dist, upd, slack):
    removed = [f'    <StrategicState id="{k}" xai:joinAction="Remove"/>' for k in ab.INHERITED]
    return '\n'.join([
        '<?xml version="1.0" encoding="utf-8"?>',
        '<AssetDeclaration xmlns="uri:ea.com:eala:asset" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"'
        ' xmlns:xai="uri:ea.com:eala:asset:instance">',
        '  <Tags></Tags>',
        '  <Includes>',
        f'    <Include type="instance" source="DATA:SkirmishAI/Personalities/{ab.BASE}.xml" />',
        '  </Includes>',
        _state(dist, upd, slack),
        f'  <AIPersonalityDefinition id="{PID}" PersonalityType="{PID}" inheritFrom="{ab.BASE}">',
        *removed,
        '    <StrategicState id="CNVStateGo" State="CNVStateGo"/>',
        '  </AIPersonalityDefinition>',
        '</AssetDeclaration>', ''])


def mission(name, dist, upd, slack, far=False):
    m = Mission(name=name, map=resources.measured(niagara), facts={'wake at': WAKE_AT, 'move at': MOVE_AT, 'push at': PUSH_AT})
    m.cnv_dist = dist
    m.sides['s1'] = {'playerFaction': 'PlayerTemplate:Allies', 'aiPersonality': f'AIPersonalityDefinition:{PID}'}
    m.assets.append((f'{PID}.xml', personality_xml(dist, upd, slack), f'AIPersonalityDefinition:{PID}'))
    m.cnv_units = (INF,)
    s1 = m.player('s1')
    m.put('AlliedConstructionYard', 'east base', 0, 0, side='s1', name='UNIT - CNV AI Yard', role='ai yard')
    m.put('AlliedConstructionYard', 'base yard', name='UNIT - CNV AI Player Yard', role='player yard')
    m.spawns |= {INF}
    ex, ey = m.site('east base')
    gx, gy = m.site('east gate')
    L = ((gx - ex) ** 2 + (gy - ey) ** 2) ** 0.5
    ux, uy = (gx - ex) / L, (gy - ey) / L
    for k in range(4):
        side_off = -90.0 + 60.0 * k
        dx, dy = (START_FAR * ux - side_off * uy, START_FAR * uy + side_off * ux) if far else (-100.0, side_off)
        m.put(INF, 'east base', dx, dy, side='s1', angle=3.1416, name=f'UNIT - CNV AI Inf {k + 1}',
              role=f'peacekeeper {k + 1}')
    base = 'CNV AI Base'
    m.waypoint('ai base', base, 'east base')
    m.waypoint('far', 'CNV AI Far', 'east base', FAR_DIST * (gx - ex) / L, FAR_DIST * (gy - ey) / L)
    if far:
        m.waypoint('out', 'CNV AI Out', 'east base', 0.0, -OUT_DIST)
    timers = [('SET_MILLISECOND_TIMER', 'CNV AI Push', PUSH_AT)] if far else [
        ('SET_MILLISECOND_TIMER', 'CNV AI Move', MOVE_AT)]
    m.scripts += [
        Script('CNV AI - Start', [], [('PLAYER_SET_MONEY', s1, 0), ('SET_MILLISECOND_TIMER', 'CNV AI Wake', WAKE_AT),
                                      *timers]),
        Script('CNV AI - Wake', [('TIMER_EXPIRED', 'CNV AI Wake')],
               [('UNIT_AI_TRANSFER_ALL', s1, 1), ('SKIRMISH_AI_MAKE_BASE', s1, base),
                ('SKIRMISH_AI_SET_ALL_ENEMY_PLAYERS_PRIORITIES', s1, 20), ('SKIRMISH_AI_USE_REPAIRS', s1, 0),
                ('SKIRMISH_AI_USE_REBUILD_SYSTEM', s1, 0), ('PLAYER_SET_MONEY', s1, 0)])]
    if not far:
        m.scripts.append(Script('CNV AI - Move', [('TIMER_EXPIRED', 'CNV AI Move')],
                                m.order('move', [m.role(f'peacekeeper {k}').name for k in range(1, 5)], 'CNV AI Far',
                                        side='s1', crew='CNVDefMove')))
    return m


MISSION = {'aidef250': lambda: mission('CampAIDef250', 250, 1, 1.5),
           'aidef450': lambda: mission('CampAIDef450', 450, 1, 1.5),
           'aidefupd4': lambda: mission('CampAIDefUpd4', 250, 4, 1.5),
           'aidefslack': lambda: mission('CampAIDefSlack', 250, 1, 3.0),
           'aidefctl': lambda: mission('CampAIDefCtl', 250, 1, 1.5, far=True),
           'aidefctl4': lambda: mission('CampAIDefCtl4', 250, 4, 1.5, far=True),
           'aidefmv': lambda: mission('CampAIDefMv', 250, 1, 1.5, far=True)}
