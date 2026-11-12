"""Engine probe: PowerAdvantageHeuristic -- does a strategic state turn on by the two armies' kill times (read back by
checks/engine_aipoweradv.py; private ai/states.py PowerAdvantage, simai.Brain.power_advantage)?

aistate_bench's set-up (Niagara, the enemy s1 Allied with a yard and no money, every inherited strategic state
removed, woken at 10 s), one state of the probe's own:
  CNVStatePA  PowerAdvantageHeuristic Value="1" Above="true" (no defences either side, KindOf CAN_ATTACK, the
              defaults): a SimpleAttack team of 2-8 Guardians (AlliedAntiVehicleVehicleTech1) at the closest enemy
              structure (a player power plant ~750 from them, as aistatenear).
Program read (work/re l4_states.md 11): theirs = the enemy's time to kill all of ours, ours = ours to kill all of
theirs (template health, each capped 10000); theirs > 9999 -> Above; else ours > 9999 -> !Above; else
theirs / ours > Value == Above. Same units both sides: theirs / ours = (ours count / theirs count)^2.
  aipadv2  s1 8 Guardians, the player 4 (on the player's base, idle): 4 > 1 -> on, the tanks go
  aipadv1  s1 4, the player 8: 1/4 -> off, they stay home
  aipadvh  s1 4, the player only an Ore Collector (AlliedMiner, no CAN_ATTACK): nothing to kill us -> on
  aipadvc  aipadv1's armies, the state ConstantHeuristic: the control -- the team goes at all with 4 against 8

Facts: wake at, ai tanks, player tanks, expect on (1 / 0).
"""
import resources
from maps import niagara
from missions.aistate_bench import BASE, INHERITED
from parts import Mission, Script

WAKE_AT = 10.0
PID = 'CNVPowerAdv'
TANK, MINER = 'AlliedAntiVehicleVehicleTech1', 'AlliedMiner'


def personality_xml(pid, gate, min_power=None):
    removed = [f'    <StrategicState id="{k}" xai:joinAction="Remove"/>' for k in INHERITED]
    mpa = '' if min_power is None else f' MinPowerAdvantage="{min_power}"'
    if gate.startswith('<'):                      # round 83: any heuristic, as written
        when = gate
    else:
        when = ('<PowerAdvantageHeuristic Value="1.0" Above="true" IncludeOwnDefenses="false"'
                ' IncludeEnemyDefenses="false"/>' if gate == 'power' else '<ConstantHeuristic/>')
    return '\n'.join([
        '<?xml version="1.0" encoding="utf-8"?>',
        '<AssetDeclaration xmlns="uri:ea.com:eala:asset" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"'
        ' xmlns:xai="uri:ea.com:eala:asset:instance">',
        '  <Tags></Tags>',
        '  <Includes>',
        f'    <Include type="instance" source="DATA:SkirmishAI/Personalities/{BASE}.xml" />',
        '  </Includes>',
        f'''  <AIStrategicStateDefinition id="CNVStatePA" MaxTargets="1">
    <Heuristic>
      {when}
    </Heuristic>
    <TargetHeuristic TargetHeuristic="ClosestStructureHeuristic"/>
    <Tactic id="Attack" Tactic="SimpleAttack" EndBehavior="RAMPAGE" EndIfStateTurnsOff="true">
      <TeamTemplate MinUnits="2" MaxUnits="8"{mpa} IncludeKindOf="CAN_ATTACK" ExcludeKindOf="IGNORES_SELECT_ALL HARVESTER"
                    AllowedLocomotorTypes="LAND AMPHIBIOUS" Priority="STANDARD" AlwaysRecruit="false"
                    MicroManager="StandardMicroManager_MEDIUM">
        <ObjectFilter Rule="ANY">
          <IncludeThing>{TANK}</IncludeThing>
        </ObjectFilter>
      </TeamTemplate>
    </Tactic>
  </AIStrategicStateDefinition>''',
        f'  <AIPersonalityDefinition id="{pid}" PersonalityType="{pid}" inheritFrom="{BASE}">',
        *removed,
        '    <StrategicState id="CNVStatePA" State="CNVStatePA"/>',
        '  </AIPersonalityDefinition>',
        '</AssetDeclaration>', ''])


def mission(name, ai, player, miner=False, gate='power', expect=1, min_power=None, home_until=None, out_by=None,
            ai_miner=False):
    pid = PID + name[len('CampAIPAdv'):]
    facts = {'wake at': WAKE_AT, 'ai tanks': ai, 'player tanks': player, 'expect on': expect}
    if home_until is not None:
        facts['home until'] = home_until
    if out_by is not None:
        facts['out by'] = out_by
    m = Mission(name=name, map=resources.measured(niagara), facts=facts)
    m.sides['s1'] = {'playerFaction': 'PlayerTemplate:Allies', 'aiPersonality': f'AIPersonalityDefinition:{pid}'}
    m.assets.append((f'{pid}.xml', personality_xml(pid, gate, min_power), f'AIPersonalityDefinition:{pid}'))
    m.cnv_units = (TANK,)
    m.spawns |= {TANK, MINER}
    s1 = m.player('s1')
    m.put('AlliedConstructionYard', 'east base', 0, 0, side='s1', name='UNIT - CNV AI Yard', role='ai yard')
    m.put('AlliedConstructionYard', 'base yard', name='UNIT - CNV AI Player Yard', role='player yard')
    m.put('AlliedPowerPlant', 'east gate', -300.0, 0.0, name='UNIT - CNV AI Player Target', role='player target')
    for k in range(ai):
        m.put(TANK, 'east base', -200.0 - 80.0 * (k // 4), 160.0 + 70.0 * (k % 4), side='s1', angle=3.1416,
              name=f'UNIT - CNV AI Tank {k + 1}', role=f'ai guardian {k + 1}')
    for k in range(player):
        m.put(TANK, 'base yard', 300.0 + 80.0 * (k // 4), -120.0 + 70.0 * (k % 4), name=f'UNIT - CNV Player Tank {k + 1}',
              role=f'player guardian {k + 1}')
    if miner == 'ai base':                       # round 83 EnemyNearby: behind the AI's yard, 350 from its centre
        m.put(MINER, 'east base', 350.0, 0.0, name='UNIT - CNV Player Miner', role='player miner')
    elif miner:
        m.put(MINER, 'base yard', 300.0, 0.0, name='UNIT - CNV Player Miner', role='player miner')
    if ai_miner:
        m.put(MINER, 'east base', 350.0, 0.0, side='s1', name='UNIT - CNV AI Miner', role='ai miner')
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
    'aipadv2': lambda: mission('CampAIPAdv2', 8, 4, expect=1),
    'aipadv1': lambda: mission('CampAIPAdv1', 4, 8, expect=0),
    'aipadvh': lambda: mission('CampAIPAdvH', 4, 0, miner=True, expect=1),
    'aipadvc': lambda: mission('CampAIPAdvC', 4, 8, gate='const', expect=1),
    # round 82: the team's MinPowerAdvantage (the state always on). The first guess (the heuristic's ratio: 4 v 8 +
    # 1.0 and 8 v 4 + 5.0 stay home) was wrong on the bench -- all three go as without it; expected now as read.
    'aipadm1': lambda: mission('CampAIPAdvM1', 8, 4, gate='const', expect=1, min_power=1.0),
    'aipadm0': lambda: mission('CampAIPAdvM0', 4, 8, gate='const', expect=1, min_power=1.0),
    'aipadm5': lambda: mission('CampAIPAdvM5', 8, 4, gate='const', expect=1, min_power=5.0),
}

# round 83: the condition heuristics (4 Guardians against none; the gate any heuristic). Expected as the program read
# / the model (private ai/states.py value): 'home until' = all 4 still home that second, 'out by' = fewer by then.
_OOT = ('<ObjectOfTypeExistsHeuristic PassIfExists="{p}"><ObjectFilter Relationship="{r}" Rule="ANY">'
        '<IncludeThing>AlliedMiner</IncludeThing></ObjectFilter></ObjectOfTypeExistsHeuristic>')
HEUR = {
    # TimerHeuristic: on after StartTime from CountFrom (MAP_START default; AI_START = the wake), EndTime a length
    'aihtim': ('Tim', dict(gate='<TimerHeuristic StartTime="30s" EndTime="-1s"/>', home_until=29, out_by=42)),
    'aihtima': ('TimA', dict(gate='<TimerHeuristic StartTime="25s" EndTime="-1s" CountFrom="AI_START"/>',
                             home_until=34, out_by=47)),
    'aihtimx': ('TimX', dict(gate='<TimerHeuristic StartTime="20s" EndTime="10s"/>', home_until=19, out_by=30)),
    # IntervalHeuristic: off IntervalTime, then on ActiveTime
    'aihint': ('Int', dict(gate='<IntervalHeuristic IntervalTime="25s" ActiveTime="30s"/>', home_until=24,
                           out_by=37)),
    # EnemyNearbyHeuristic: an enemy (the player's Ore Collector: it drives to the ore node 527 off) within Distance
    'aihen1': ('En1', dict(gate='<EnemyNearbyHeuristic Distance="700.0" EnemyNearby="true"/>', miner='ai base')),
    'aihen0': ('En0', dict(gate='<EnemyNearbyHeuristic Distance="700.0" EnemyNearby="true"/>', expect=0)),
    'aihenn': ('Enn', dict(gate='<EnemyNearbyHeuristic Distance="700.0" EnemyNearby="false"/>')),
    # ObjectOfTypeExistsHeuristic with the retail's ObjectFilter Relationship (the model ignores it: own templates)
    'aihoe1': ('Oe1', dict(gate=_OOT.format(p='true', r='ENEMIES'), miner=True)),
    'aihoe0': ('Oe0', dict(gate=_OOT.format(p='true', r='ENEMIES'), expect=0)),
    'aihoef': ('Oef', dict(gate=_OOT.format(p='false', r='ENEMIES'), miner=True, expect=0)),
    'aihoea': ('Oea', dict(gate=_OOT.format(p='true', r='ALLIES'), miner=True, expect=0)),
    'aihoes': ('Oes', dict(gate=_OOT.format(p='true', r='ALLIES'), ai_miner=True)),
}
for _k, (_tail, _kw) in HEUR.items():
    MISSION[_k] = (lambda tail, kw: lambda: mission('CampAIPAdv' + tail, 4, 0, **kw))(_tail, _kw)
