"""Engine line D round 148: three team / tactic fields the retail campaign uses and no bench had (work/re
d130_untouched_census.md section 2; read back by checks/engine_aiteamfields.py). Each pair differs in that one field;
every build carries a passive CNVTeams host (aiteams_bench.host_unit; airelease's own in aihot*) for the team states and members.

Tactic.GatherWaypoint (SimpleAttack only; 22 retail tactics in 7 levels) -- ainamed_bench's ainmfar (2-4 Peacekeepers
by SimpleAttack at the far power plant, south of the AI base) with the tactic's GatherWaypoint:
  aigathwp   GatherWaypoint "CNV AI WP Target" (ainamed's waypoint at 'route 2', ~550 north of the team): the program
             (work/re d130) sends the team to the waypoint first, to the target once every team is still -> the model:
             at the waypoint, then the far plant
  aigathno   no GatherWaypoint (the same waypoint on the map): straight to the far plant
  aigathbad  GatherWaypoint "CNV AI WP Nowhere" (no such waypoint): the lookup fails -> as aigathno

TeamTemplate.MaxTypesOfUnits (58 uses) -- aiteamfilter_bench's SimpleAttack team (no ObjectFilter, CAN_ATTACK,
MinUnits 1, MaxUnits 8) over 2 Guardians, 2 Peacekeepers and 2 Javelins at home:
  aimaxty1   MaxTypesOfUnits 1: the team takes the first type it meets only, the other two stay home
  aimaxty3   MaxTypesOfUnits 3: all six go

TeamTemplate.Priority=HOTSPOT (47 uses, the highest, 8) -- airelease_bench's airelprio (2 Guardians held by a
StaticDefense team, ReleaseType RELEASE_TO_PRIORITY; a SimpleAttack state from 35 s wants the same 2), with the
defender's Priority and the attacker's set here (release: the holder's priority strictly below the recruiter's):
  aihotstd   defender STANDARD, attacker HOTSPOT -> released: the tanks go to the player's plant
  aihotdef   defender STANDARD, attacker DEFAULT -> kept home
  aihotscr   defender SCRIPTED (7), attacker HOTSPOT -> released (only HOTSPOT outranks SCRIPTED)
TeamTemplate.Priority=COOP (12 uses, 6: the co-op commander's beacon states), the same pair:
  aicoophi   defender HIGH (5), attacker COOP -> released;  aicoopsc   defender SCRIPTED (7), attacker COOP -> kept
Facts: wake at (+ airelease's attack at).
"""
from missions import ainamed_bench as an
from missions import aiteamfilter_bench as tf
from missions import airelease_bench as rel
from missions.aiteams_bench import HOST, host_unit

JAV = 'AlliedAntiVehicleInfantry'
NOWHERE = 'CNV AI WP Nowhere'
# the model's order (ra3model/ai/teams.py PRIORITY; work/re d130: HOTSPOT 8 the highest)
PRIORITY = ('DEFAULT', 'DEFENSE', 'LOW', 'STANDARD', 'DEFENSE_HIGH', 'HIGH', 'COOP', 'SCRIPTED', 'HOTSPOT')


def _host(m):
    if HOST not in {u.name for u in m.units}:
        m.units.append(host_unit())
        m.put(HOST, 'east base', 250.0, 400.0, side='s1', role='teams host')
    m.ext = True
    return m


def gather(mod, name=None):
    m = an.mission(mod, 'NamedObject', an.FAR_NAME)
    if name:
        (fname, xml, asset), = m.assets
        tac = 'Tactic="SimpleAttack" EndBehavior="RAMPAGE">'
        assert xml.count(tac) == 1
        m.assets = [(fname, xml.replace(tac, f'Tactic="SimpleAttack" EndBehavior="RAMPAGE" GatherWaypoint="{name}">'),
                     asset)]
    m.facts['gather waypoint'] = int(name == an.WP)     # 1: the named waypoint is on the map
    return _host(m)


def max_types(mod, n):
    m = tf.mission(mod, tanks=2, inf=2)
    (fname, xml, asset), = m.assets
    head = '<TeamTemplate MinUnits="1"'
    assert xml.count(head) == 1
    m.assets = [(fname, xml.replace(head, f'<TeamTemplate MaxTypesOfUnits="{n}" MinUnits="1"'), asset)]
    for k in range(2):
        m.put(JAV, 'east base', -200.0, -310.0 - 50.0 * k, side='s1', angle=3.1416,
              name=f'UNIT - CNV AI Javelin {k + 1}', role=f'ai javelin {k + 1}')
    m.spawns |= {JAV}
    m.cnv_units = (tf.TANK, tf.INF, JAV)
    m.facts['max types'] = n
    return _host(m)


def hotspot(mod, holder, recruiter):
    m = rel.mission(False)
    m.name = mod
    (fname, xml, asset), = m.assets
    head, sep, attack = xml.partition('<AIStrategicStateDefinition id="CNVReleaseAttack"')
    assert sep and head.count('Priority="DEFENSE"') == 1 and attack.count('Priority="STANDARD"') == 1
    xml = head.replace('Priority="DEFENSE"', f'Priority="{holder}"') + sep + \
        attack.replace('Priority="STANDARD"', f'Priority="{recruiter}"')
    m.assets = [(fname, xml, asset)]
    m.facts['released'] = int(PRIORITY.index(recruiter) > PRIORITY.index(holder))
    return m                        # airelease's own CNVTeams host (CNVReleaseHost) logs the teams


MISSION = {
    'aigathwp': lambda: gather('CampAIGathWp', an.WP),
    'aigathno': lambda: gather('CampAIGathNo'),
    'aigathbad': lambda: gather('CampAIGathBad', NOWHERE),
    'aimaxty1': lambda: max_types('CampAIMaxTy1', 1),
    'aimaxty3': lambda: max_types('CampAIMaxTy3', 3),
    'aihotstd': lambda: hotspot('CampAIHotStd', 'STANDARD', 'HOTSPOT'),
    'aihotdef': lambda: hotspot('CampAIHotDef', 'STANDARD', 'DEFAULT'),
    'aihotscr': lambda: hotspot('CampAIHotScr', 'SCRIPTED', 'HOTSPOT'),
    'aicoophi': lambda: hotspot('CampAICoopHi', 'HIGH', 'COOP'),
    'aicoopsc': lambda: hotspot('CampAICoopSc', 'SCRIPTED', 'COOP'),
}
