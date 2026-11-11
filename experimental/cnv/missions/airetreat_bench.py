"""Engine probe: the skirmish AI's team state (0x8cdb70) -- retreat on a lost power advantage and the
EngagePassiveTargets switch (engine line B, layer 4; read back by checks/engine_airetreat.py; program: work/re
l4_micro_retreat.md, l4_micro_engage.md; model: RA3-EngineModel ra3model/ai/tactics.py TacticsBlock._team_state,
simai.Brain.fight).

The map, AI and the player's structures are ainamed_bench's ainmfar (one always-on state sends 2-4 Peacekeepers by
SimpleAttack at the far power plant, ~1010 south of the AI's base); the team's micro manager is the probe's own:
StandardMicroManager_MEDIUM flattened (aitarget_bench._micro_xml) with RetreatMinDistanceFromBase 300 (retail 900:
the far plant is too near the base for a retreat by the retail number) and:
  airet    RetreatPowerAdvantage 0.2 (retail MEDIUM); GUARDS of the player's Peacekeepers stand round the far plant:
           the team is outgunned there (power advantage = their time to kill us / ours to kill them, ~0.1) -> the
           model: the team turns round to the AI's base (state 1, attack-move home), then stands where the retreat
           ends (RetreatMinDistanceToFallback 500 from where it began, or 300 from the base)
  airetd   airet with the tactic's DisbandAfterRetreatTeamSize 999 (retail 999 x71, 1 x10, 4 x3, 5, 0; xsd 0): the
           team ends its tactic the update its retreat ends (0x8fbb40: was state 1, now 8, members <= the size);
           the always-on state makes a new team at once -- the simulator: out again 2 s later than airet, no reading
  airetf   airet with the state on a map flag: on at the wake, off FLAG_OFF later (one team, no second) -> the
           model: the team cycles as airet's (the tactic goes on with its state off: bench aistateoff1)
  airetfd  airetf + DisbandAfterRetreatTeamSize 999 -> the model: the tactic ends when the retreat does, no state
           to make a new team: the four stay home to the end
  airet0   RetreatPowerAdvantage 0.0: the same fight, no retreat (the advantage is never below 0) -> it fights there
  aipas1   no guards; a SIDE plant of the player's 250 west of the team's way to the far plant; EngagePassiveTargets
           true -> the model: the side plant (a structure: the passive list) comes within a member's vision x 1.5,
           the team attacks it first (state 6)
  aipas0   the same, EngagePassiveTargets false -> straight on to the far plant
Facts: wake at, side plant (name; aipas*).
"""
import math

from missions import ainamed_bench as an
from missions import aitarget_bench as at
from parts import Script

MICRO_ID = 'CNVMicroRetreat'
GUARDS = 12
GUARD_RING = 60.0                       # packed: the whole guard is in a member's search circle at once
SIDE = 'UNIT - CNV AI Side Plant'
SIDE_AT = (3400.0, 2823.0)              # 250 west of the line from the AI's Peacekeepers to the far plant: inside a
#                                         member's search circle (vision 200 x 1.5), outside its vision
FLAG = 'CNVRetGo'                       # airetf*: the state's ScriptedFlagHeuristic; the scripts write '/' + FLAG
FLAG_OFF = 8.0                          # s after the wake: the team has its slot (bench aistateoff1: off 1 s after on
#                                         still sends the team), well before its retreat ends (bench airet ~s26)


def micro_xml(**fields):
    """aitarget_bench's flattened StandardMicroManager_MEDIUM under MICRO_ID with these fields replaced."""
    xml = at._micro_xml(15).replace(f'id="{at.IDLE_ID}"', f'id="{MICRO_ID}"', 1)
    fields.setdefault('RetreatMinDistanceFromBase', '300.0')
    for k, v in fields.items():
        key = f' {k}="'
        if key in xml:
            head, rest = xml.split(key, 1)
            xml = head + key + str(v) + rest[rest.index('"'):]
        else:
            xml = xml.replace(f'id="{MICRO_ID}"', f'id="{MICRO_ID}" {k}="{v}"', 1)
    return xml


def mission(mod, guards=0, side=False, disband=None, flag=False, **fields):
    m = an.mission(mod, 'NamedObject', an.FAR_NAME)
    (fname, xml, asset), = m.assets
    if flag:                                # the state on at the wake, off FLAG_OFF later: one team, never a second
        const = '<ConstantHeuristic/>'
        assert xml.count(const) == 1
        xml = xml.replace(const, f'<ScriptedFlagHeuristic FlagName="{FLAG}"/>', 1)
        m.scripts += [Script('CNV AI - Ret on', [('TIMER_EXPIRED', 'CNV AI Wake')],
                             [('SET_FLAG', '/' + FLAG, 1), ('SET_MILLISECOND_TIMER', 'CNV AI Ret Off', FLAG_OFF)]),
                      Script('CNV AI - Ret off', [('TIMER_EXPIRED', 'CNV AI Ret Off')], [('SET_FLAG', '/' + FLAG, 0)])]
        m.facts['state off at'] = m.facts['wake at'] + FLAG_OFF
    if disband is not None:
        tac = 'EndBehavior="RAMPAGE">'
        assert xml.count(tac) == 1
        xml = xml.replace(tac, f'EndBehavior="RAMPAGE" DisbandAfterRetreatTeamSize="{disband}">', 1)
        m.facts['disband after retreat'] = disband
    head = '  <AIStrategicStateDefinition'
    xml = xml.replace(head, micro_xml(**fields) + '\n' + head, 1)
    xml = xml.replace('MicroManager="StandardMicroManager_MEDIUM"', f'MicroManager="{MICRO_ID}"', 1)
    m.assets = [(fname, xml, asset)]
    m.facts['micro'] = dict(fields)
    for k in range(guards):
        a =2 * math.pi * k / guards
        m.put(at.INF, 'carrier home', GUARD_RING * math.cos(a), GUARD_RING * math.sin(a),
              name=f'UNIT - CNV AI Guard {k + 1}', role=f'guard {k + 1}')
    if side:
        cx, cy = m.site('carrier home')[:2]
        m.put('AlliedPowerPlant', 'carrier home', SIDE_AT[0] - cx, SIDE_AT[1] - cy, name=SIDE, role='side plant')
        m.facts['side plant'] = SIDE
    return m


MISSION = {
    'airet': lambda: mission('CampAIRet', guards=GUARDS, RetreatPowerAdvantage='0.2'),
    'airetd': lambda: mission('CampAIRetD', guards=GUARDS, disband=999, RetreatPowerAdvantage='0.2'),
    'airetf': lambda: mission('CampAIRetF', guards=GUARDS, flag=True, RetreatPowerAdvantage='0.2'),
    'airetfd': lambda: mission('CampAIRetFD', guards=GUARDS, flag=True, disband=999, RetreatPowerAdvantage='0.2'),
    'airet0': lambda: mission('CampAIRet0', guards=GUARDS, RetreatPowerAdvantage='0.0'),
    'aipas1': lambda: mission('CampAIPas1', side=True, EngagePassiveTargets='true'),
    'aipas0': lambda: mission('CampAIPas0', side=True, EngagePassiveTargets='false'),
}
