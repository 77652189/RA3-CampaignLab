"""Engine probe: the personality's DefaultTacticHomeBaseCriteria -- which base a RETURN_HOME_AND_DISBAND team walks
home to (read back by checks/engine_aihome.py; engine line B round 201).

Two AI yards, both initial map objects placed one after the other (as C's aibs3 / aibn2 pairs): base A = the first
at 'east base' (OLDEST_OF_TYPE), base B = the second NORTH north of it (MOST_RECENT_OF_TYPE), both MAIN_BASE.

aihmg* (the probe): aitargetpick's aiendh set-up (4 Guardians at A, one always-on SimpleAttack state, EndBehavior
RETURN_HOME_AND_DISBAND, the tactic has no HomeBaseCriteria of its own so the personality's is used, the check kills
the target at KILL_AT) with one target only -- a NamedObject heuristic on the player's power plant at the east gate
(~710 from A, ~1610 from B), no barracks or tank, so once the plant is gone there is no new target (aiendh's team
went straight on to the barracks, never home). Only DefaultTacticHomeBaseCriteria differs:
  aihmgcl  SortOrder PREFER_CLOSEST, PreferredNotBaseTypes CAPTURED (the retail line)       -> A
  aihmgnw  SortOrder PREFER_NEWEST,  PreferredNotBaseTypes CAPTURED                         -> B (SortOrder)
  aihmgno  SortOrder PREFER_CLOSEST, PreferredNotBaseTypes OLDEST_OF_TYPE                   -> B (PreferredNot)

aihomecl (bench 2026-11-14, checks/engine_aihome.py): aireactive_bench's ReactiveDefense team (4 Peacekeepers, the
foe 1000 south of A, radius 1200) with the second yard -- the tactic has no TargetBaseCriteria; it guards B.
"""
import resources
from maps import niagara
from missions import aireactive_bench as rb
from missions import aistate_bench as ab
from missions import aitargetpick_bench as tp
from parts import Mission, Script

WAKE_AT = 10.0
KILL_AT = 35.0
FOE_DIST = rb.FOE_DIST
RADIUS = 1200
NORTH = 1350.0          # base B from base A
PID = 'CNVHomeTest'
PLANT = 'UNIT - CNV TP Plant'
NAMED = (f'  <AITargetingHeuristic id="CNVHPlant" HeuristicType="NamedObject" Name="{PLANT}"'
         ' MinDistanceFromEnemy="0" SearchRange="5000" Location="Land"/>')


def _wrap(states, pid, inherit_attrs, criteria):
    removed = [f'    <StrategicState id="{k}" xai:joinAction="Remove"/>' for k in ab.INHERITED]
    return '\n'.join([
        '<?xml version="1.0" encoding="utf-8"?>',
        '<AssetDeclaration xmlns="uri:ea.com:eala:asset" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"'
        ' xmlns:xai="uri:ea.com:eala:asset:instance">',
        '  <Tags></Tags>',
        '  <Includes>',
        f'    <Include type="instance" source="DATA:SkirmishAI/Personalities/{ab.BASE}.xml" />',
        '  </Includes>',
        *states,
        f'  <AIPersonalityDefinition id="{pid}" PersonalityType="{pid}" inheritFrom="{ab.BASE}"{inherit_attrs}>',
        *removed,
        *criteria,
        '  </AIPersonalityDefinition>',
        '</AssetDeclaration>', ''])


def _yards(m):
    m.put('AlliedConstructionYard', 'east base', 0, 0, side='s1', name='UNIT - CNV AI Yard', role='ai yard')
    m.put('AlliedConstructionYard', 'east base', 0, NORTH, side='s1', name='UNIT - CNV AI Yard B',
          role='second ai yard')
    m.put('AlliedConstructionYard', 'base yard', name='UNIT - CNV AI Player Yard', role='player yard')


def _wake(m):
    s1, base = m.player('s1'), 'CNV AI Base'
    m.waypoint('ai base', base, 'east base')
    m.scripts += [
        Script('CNV AI - Start', [], [('PLAYER_SET_MONEY', s1, 0), ('SET_MILLISECOND_TIMER', 'CNV AI Wake', WAKE_AT)]),
        Script('CNV AI - Wake', [('TIMER_EXPIRED', 'CNV AI Wake')],
               [('UNIT_AI_TRANSFER_ALL', s1, 1), ('SKIRMISH_AI_MAKE_BASE', s1, base),
                ('SKIRMISH_AI_SET_ALL_ENEMY_PLAYERS_PRIORITIES', s1, 20), ('SKIRMISH_AI_USE_REPAIRS', s1, 0),
                ('SKIRMISH_AI_USE_REBUILD_SYSTEM', s1, 0), ('PLAYER_SET_MONEY', s1, 0)])]


def _facts(**kw):
    return {'wake at': WAKE_AT, 'initial dual bases': True, 'north': NORTH, **kw}


def home(name, sort, preferred_not):
    """The probe: a SimpleAttack team on the named plant, killed at KILL_AT, walks home by the criteria."""
    pid = PID + name[-3:]
    m = Mission(name=name, map=resources.measured(niagara),
                facts=_facts(probe='home', **{'home sort': sort, 'home preferred not': preferred_not,
                                              'kill plant at': KILL_AT}))
    state = tp.state_xml('CNVStateTP', [('CNVHPlant', None)], 1, end='RETURN_HOME_AND_DISBAND')
    crit = [f'    <DefaultTacticHomeBaseCriteria SortOrder="{sort}" PreferredNotBaseTypes="{preferred_not}"/>']
    xml = _wrap([NAMED, state], pid, '', ['    <StrategicState id="CNVStateTP" State="CNVStateTP"/>', *crit])
    m.sides['s1'] = {'playerFaction': 'PlayerTemplate:Allies', 'aiPersonality': f'AIPersonalityDefinition:{pid}'}
    m.assets.append((f'{pid}.xml', xml, f'AIPersonalityDefinition:{pid}'))
    m.cnv_units = (tp.TANK,)
    m.spawns |= {tp.TANK}
    _yards(m)
    m.put('AlliedPowerPlant', 'east gate', 0.0, 0.0, name=PLANT, role='plant')
    for k in range(4):
        m.put(tp.TANK, 'east base', -200.0, 160.0 + 70.0 * k, side='s1', angle=3.1416,
              name=f'UNIT - CNV AI Tank {k + 1}', role=f'ai guardian {k + 1}')
    _wake(m)
    return m


def reactive(name):
    """aireact1200 with the second yard and RETURN_HOME_AND_DISBAND: which base ReactiveDefense guards."""
    m = Mission(name=name, map=resources.measured(niagara), facts=_facts(probe='reactive', radius=RADIUS))
    state = rb._state().replace('EndBehavior="DISBAND"', 'EndBehavior="RETURN_HOME_AND_DISBAND"')
    xml = _wrap([state], PID, f' ReactiveDefenseRadius="{RADIUS}"',
                ['    <StrategicState id="CNVStateGo" State="CNVStateGo"/>',
                 '    <DefaultTacticHomeBaseCriteria SortOrder="PREFER_CLOSEST" PreferredNotBaseTypes="CAPTURED"/>'])
    m.sides['s1'] = {'playerFaction': 'PlayerTemplate:Allies', 'aiPersonality': f'AIPersonalityDefinition:{PID}'}
    m.assets.append((f'{PID}.xml', xml, f'AIPersonalityDefinition:{PID}'))
    m.cnv_units = (ab.INF,)
    m.spawns |= {ab.INF}
    _yards(m)
    for k in range(4):
        m.put(ab.INF, 'east base', -100.0, -90.0 + 60.0 * k, side='s1', angle=3.1416,
              name=f'UNIT - CNV AI Inf {k + 1}', role=f'peacekeeper {k + 1}')
    m.put(ab.INF, 'east base', 0.0, -FOE_DIST, angle=1.5708, name='UNIT - CNV RD Foe', role='foe')
    _wake(m)
    return m


MISSION = {'aihomecl': lambda: reactive('CampAIHomeCl'),
           'aihmgcl': lambda: home('CampAIHmGCl', 'PREFER_CLOSEST', 'CAPTURED'),
           'aihmgnw': lambda: home('CampAIHmGNw', 'PREFER_NEWEST', 'CAPTURED'),
           'aihmgno': lambda: home('CampAIHmGNo', 'PREFER_CLOSEST', 'OLDEST_OF_TYPE')}
