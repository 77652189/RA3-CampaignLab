"""Engine probe for the ATTACK versions of the waypoint paths (Sim.order_follow attacking=True: an attack-move each
leg): mission missions/waypath_bench.py engine_wayatk -- the player's Guardian tanks (weapon 150, vision 200; both
tanks' bounding circle 23.3: the weapon reaches 196.6 centre to centre, an idle one goes after an enemy within 223.3,
checks/engine_acquire.py) in the west field, the L of waypoints A (+150, -150) -> B (+450, -150) -> C (+450, +150).
Each check writes its own waypoints on A, B, C labelled 'CNVRoad' (checks/engine_waypath.py's _road) and makes, in
the first frame, an enemy Guardian (s1, NO_ATTACK: it never fires back) at F, d beside the middle of the A -> B leg
(+300, -150 - d); the orders at 2 s.

Counters: 段k = the last of tank k's boxes (40 half-side; team 100) it was in: 1 A, 2 B, 3 C; 敌血 = the enemy's
health (percent); 近敌 = 1 while tank 1 (team: tank 2) is within 100 of F (it turned aside to it).

  atk    NAMED_ATTACK_FOLLOW_WAYPOINTS tank 1 'CNVRoad', F 150 off the leg (within the weapon's reach from the path).
  plain  NAMED_FOLLOW_WAYPOINTS the same: does a plain path walker fire on the way, stop, or pass it by?
  atk2   NAMED_ATTACK_FOLLOW_WAYPOINTS, F 220 off (beyond the weapon from the path, within an idle unit's acquire).
  team   TEAM_ATTACK_MOVE_FOLLOW_WAYPOINTS W23 (tanks 2, 3; asTeam 1), F 150 off (tank 2 runs 75 from it).
  amove  ATTACK_MOVE_TEAM_TO W1 (tank 1) to B, F 150 off: the one-leg attack-move, beside atk.

Simulator 11-10 (round 145, work/logs/a145_wayatk_sim.log): atk / amove 段1 1 s4, 敌血 from s6 6.25 %/s, 0 s21, B
s24 (atk C s28); plain B s8, C s12 (81 at the end); atk2 passes by (B s8, C s12, 敌血 100); team tank 3 on to B s9 /
C s12 while tank 2 fights, tank 2 B s27.

读数 (bench 2026-11-10; 敌血 stays at a dead unit's last value: SET_UNIT_HEALTH_PERCENTAGE_TO_COUNTER of the dead)
  atk    段1 s3 1; 敌血 86 s4, a shot every 2 s (13.9 %): 72 58 45 31 17, 3 at s16 (the 8th kills ~s18); B s21, C s25.
         It stops to fight (stays in A's box) and goes on once its target is dead.
  amove  the same, second by second (B s21).
  plain  段1 s3 1, s7 2, s10 3; 敌血 86 s4, 73 s6: fires on the way, does not stop.
  atk2   F 220 off (beyond the weapon from the path): it goes for it all the same -- 敌血 86 s6 (2 s after atk's), 13
         a shot to 8 at s18; B s22, C s26; 近敌 0 (a step aside, not within 100). Generals AIAttackFollowWaypointPathState
         ::update (and AIAttackMoveToState) takes getNextMoodTarget every idle frame: the mood scan, an idle unit's
         reach (VisionRange + the target's radius, engine_acquire: 223.3 here). The simulator's attack-move only takes
         what its weapon reaches from where it is: GAP (round 146: an attack-mover's own chase, as idle_chase, then on).
  team   敌血 86 s4, 73 s6, 59 s7, 32 s8 (both firing), 5 at s11 (dead ~s12); 段2 1 s2, 段3 1 s4; then B 段3 s14 /
         段2 s15, C s18 / s19: the team waits while one fights (tank 3 at A did not move the team on). GAP: the
         simulator's first-there rule moves tank 3 on (round 146: a member fighting holds the team's waypoint? or tank 3
         took the target too -- the mood scan of a team member: read AIUpdate::getNextMoodTarget).
Tested (tests/test_simbench.py test_wayatk_*): plain, atk, amove; atk2 and team not yet (inventory NOTES keeps
TEAM_ATTACK_MOVE_FOLLOW_WAYPOINTS 推断).
"""
from parts import Script, Test, counted, square
from checks.engine_waypath import PATH, _at, _road

FOE, FOE_TEMPLATE = 'UNIT - CNV Wayatk Foe', 'AlliedAntiVehicleVehicleTech1'
RUN = 50.0
LEG_MIDDLE = (300.0, -150.0)            # offsets from 'west field': the A -> B leg's middle


def _legs(t, m, tanks, half=40.0):
    for k in tanks:
        name, counter = m.role(f'tank {k}').name, f'CNV_Wayatk_Leg{k}'
        t.counters.append((counter, f'段{k}'))
        for i, p in enumerate(PATH, 1):
            area = f'Test Wayatk Box {p}'
            t.areas[area] = square(*m.point(p), half)
            t.scripts.append(Script(f'Test - {counter} {p}', [('NAMED_INSIDE_AREA', name, area)],
                                    [('SET_COUNTER', counter, i)], once=False))


def _foe(t, m, d, near):
    """The enemy at F (d beside the A -> B leg's middle), NO_ATTACK, made in the first frame; 敌血 and 近敌."""
    ax, ay = m.point('A')                           # A is (+150, -150) from the field: F from A
    fx, fy = ax + (LEG_MIDDLE[0] - 150.0), ay - d
    t.waypoints['Test Wayatk F'] = (fx, fy)
    t.areas['Test Wayatk Near'] = square(fx, fy, 100.0)
    t.scripts.append(Script('Test - foe', [], [('CREATE_NAMED_ON_TEAM_AT_WAYPOINT', FOE, FOE_TEMPLATE, m.team('s1'),
                                                'Test Wayatk F'),
                                               ('UNIT_CHANGE_OBJECT_STATUS', FOE, 'NO_ATTACK', 1)]))
    counted('CNV_Wayatk_Hp', '敌血', t, health=FOE)
    counted('CNV_Wayatk_Near', '近敌', t, named=m.role(f'tank {near}').name, area='Test Wayatk Near')


def _probe(m, d, actions, tanks=(1,), half=40.0):
    t = Test()
    t.scripts.append(Script('Test - reveal', [], [('MAP_REVEAL_ALL_PERM', m.player('p1'))]))
    _road(t, m, 'CNVRoad')
    _foe(t, m, d, tanks[0])
    _at(t, 'go', 2.0, actions)
    _legs(t, m, tanks, half)
    t.bench = [('bench_watch', dict(seconds=RUN, every=1.0, sheet=False, lines=len(t.counters)))]
    return t


def atk(m):
    return _probe(m, 150.0, [('NAMED_ATTACK_FOLLOW_WAYPOINTS', m.role('tank 1').name, 'CNVRoad')])


def plain(m):
    return _probe(m, 150.0, [('NAMED_FOLLOW_WAYPOINTS', m.role('tank 1').name, 'CNVRoad')])


def atk2(m):
    return _probe(m, 220.0, [('NAMED_ATTACK_FOLLOW_WAYPOINTS', m.role('tank 1').name, 'CNVRoad')])


def team(m):
    return _probe(m, 150.0, [('TEAM_ATTACK_MOVE_FOLLOW_WAYPOINTS', m.crew('W23'), 'CNVRoad', 1, 0)], (2, 3), 100.0)


def amove(m):
    return _probe(m, 150.0, m.order('attack_move', [m.role('tank 1').name], m.mark('B'), crew='W1'))


CHECKS = {'engine_wayatk': {'atk': atk, 'plain': plain, 'atk2': atk2, 'team': team, 'amove': amove}}
