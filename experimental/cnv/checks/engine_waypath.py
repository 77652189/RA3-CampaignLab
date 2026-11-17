"""Engine probe for the waypoint paths (Sim.order_follow: *_FOLLOW_WAYPOINTS): mission missions/waypath_bench.py,
convoy trucks (speed 50) in the west field and an L of waypoints A (+150, -150) -> B (+450, -150) -> C (+450, +150).
Each check writes its own waypoints on A, B, C (the check layer may not put the mission's on a path) and labels them.

Counters: 段k = the last of truck k's boxes (40 half-side) it was in: 1 A, 2 B, 3 C (0 none yet); 近B = how near
truck 1 came to B: 4 within 10, 3 within 25, 2 within 50, 1 within 100 (nested squares; the highest it reached).

  line   NAMED_FOLLOW_WAYPOINTS truck 1 'CNVRoad' (A -> B -> C) at 1 s. [sim: 段1 1 -> 2 -> 3, then stays; 近B 4 --
         it walks to each waypoint, no corner cut (INFERRED)]
  exact  the same with NAMED_FOLLOW_WAYPOINTS_EXACT. [sim: as line; the two differ on the bench by 近B, if at all]
  near   truck 1 first sent to N (by B, MOVE_TEAM_TO), the path at 15 s. [sim: B nearest -- 段1 2 -> 3, A never]
  loop   the path linked C -> A as well (a ring), truck 1 at 1 s. [sim: 段1 1 2 3 1 2 3 ... round and round]
  team   TEAM_FOLLOW_WAYPOINTS team W23 (trucks 2, 3) 'CNVRoad' asTeam=1 at 1 s; boxes 100 half-side here. [sim:
         joined at A (nearest the team's middle), group legs: both 1 -> 2 -> 3]
  start  NAMED_FOLLOW_WAYPOINTS_STARTING_AT_WAYPOINT truck 2 'CNVRoad' from B at 1 s (A is nearest it, 250 off; its
         straight run to B passes 50 north of A's box). [sim: 段2 0 -> 2 -> 3, A never]
  texact TEAM_FOLLOW_WAYPOINTS_EXACT team W23 'CNVRoad' asTeam=1 at 1 s; boxes 100. [sim: as team]

Simulator 11-10 (round 143, work/logs/a143_waypath_sim.log; 段 boxes 40): line / exact s5 段1 1, s11 2 (近B 4), s17 3;
near s5 1 (passing A on the way to N), s17 2, s23 3 (A never again: joined at B); loop 1 2 3 every ~20 s, round and
round; team (boxes 40 then) truck 3 never in A's or B's box -- its group legs ran 100 aside: boxes 100 since.

读数 (bench 2026-11-10, after package._drop_dangling_links -- the first line / exact runs had the container's stale
links on our waypoint ids, 10 -> 9, 8 -> 7 ...: line went C -> B -> C ..., exact forked at A to N -- the same fork,
the two runs took different links: random -- and on through unlabelled waypoints N, C, B, A to the camera's)
  line   段1 s3 1, s9 2 (近B 4), s15 3, stays.             exact  the same, second by second: no corner cut either.
  near   段1 s3 1 (on the way to N), s15 2 (近B 3, s16 4), s21 3; A never again: joined at B.
  loop   段1 1 2 3 at s3 9 15, s23 29 35, s43 49 55, s63 70 76, s84 90: a lap 20-21 s, round and round.
  team   段2 s3 1, s10 2, s17 3; 段3 s5 1, s10 2, s14 3: both within 100 of every waypoint (each to the waypoint plus
         its offset from the team's middle, ±75), the one ahead on the last leg (truck 3) there 3 s first.
  start  (round 151) CampPathStart_mcp_1110_211156: 段2 0 s1-s8, 2 s9, 3 s15 on: straight to B, A never.
  texact (round 151) CampPathTexact_mcp_1110_211438: 段2 s3 1, s10 2, s17 3; 段3 s5 1, s10 2, s14 3 -- team's
         readings second by second: _EXACT changes nothing here either.
Simulator after the round-144 fix (Generals m_moveAsGroup offsets, the first there moves the team on): every reading
LAG 2 s later (loop drifts to 3 s by the third lap); tests/test_simbench.py test_waypath_*.
"""
from parts import Script, Test, square

PATH = ('A', 'B', 'C')
RINGS = (100.0, 50.0, 25.0, 10.0)
RUN = {'line': 40.0, 'exact': 40.0, 'near': 50.0, 'loop': 90.0, 'team': 45.0, 'start': 45.0, 'texact': 45.0}


def _at(t, key, secs, actions):
    timer = f'Test {key} Timer'
    t.scripts += [Script(f'Test - {key} timer', [], [('SET_MILLISECOND_TIMER', timer, secs)]),
                  Script(f'Test - {key}', [('TIMER_EXPIRED', timer)], actions)]


def _road(t, m, label, loop=False):
    """The check's own waypoints on A, B, C, labelled `label`, linked in order (loop: C back to A)."""
    names = [f'Test Waypath {p}' for p in PATH]
    for n, p in zip(names, PATH):
        t.waypoints[n] = m.point(p)
    t.path(label, *names, loop=loop)


def _legs(t, m, trucks, half=40.0):
    for k in trucks:
        name, counter = m.role(f'truck {k}').name, f'CNV_Waypath_Leg{k}'
        t.counters.append((counter, f'段{k}'))
        for i, p in enumerate(PATH, 1):
            area = f'Test Waypath Box {p}'
            t.areas[area] = square(*m.point(p), half)
            t.scripts.append(Script(f'Test - {counter} {p}', [('NAMED_INSIDE_AREA', name, area)],
                                    [('SET_COUNTER', counter, i)], once=False))


def _near_b(t, m):
    name, counter = m.role('truck 1').name, 'CNV_Waypath_NearB'
    t.counters.append((counter, '近B'))
    for level, r in enumerate(RINGS, 1):
        area = f'Test Waypath B {r:g}'
        t.areas[area] = square(*m.point('B'), r)
        t.scripts.append(Script(f'Test - {counter} {r:g}', [('NAMED_INSIDE_AREA', name, area)],
                                [('SET_COUNTER', counter, level)]))


def _watch(t, run, every=1.0):
    t.bench = [('bench_watch', dict(seconds=run, every=every, sheet=False, lines=len(t.counters)))]


def _one(m, action, run):
    t = Test()
    _road(t, m, 'CNVRoad')
    _at(t, 'go', 1.0, [(action, m.role('truck 1').name, 'CNVRoad')])
    _legs(t, m, (1,))
    _near_b(t, m)
    _watch(t, run)
    return t


def line(m):
    return _one(m, 'NAMED_FOLLOW_WAYPOINTS', RUN['line'])


def exact(m):
    return _one(m, 'NAMED_FOLLOW_WAYPOINTS_EXACT', RUN['exact'])


def near(m):
    t = Test()
    _road(t, m, 'CNVRoad')
    _at(t, 'go', 1.0, m.order('move', [m.role('truck 1').name], m.mark('N'), crew='W1'))
    _at(t, 'path', 15.0, [('NAMED_FOLLOW_WAYPOINTS', m.role('truck 1').name, 'CNVRoad')])
    _legs(t, m, (1,))
    _near_b(t, m)
    _watch(t, RUN['near'])
    return t


def loop(m):
    t = Test()
    _road(t, m, 'CNVRing', loop=True)
    _at(t, 'go', 1.0, [('NAMED_FOLLOW_WAYPOINTS', m.role('truck 1').name, 'CNVRing')])
    _legs(t, m, (1,))
    _watch(t, RUN['loop'])
    return t


def team(m):
    t = Test()
    _road(t, m, 'CNVRoad')
    _at(t, 'go', 1.0, [('TEAM_FOLLOW_WAYPOINTS', m.crew('W23'), 'CNVRoad', 1, 0)])
    _legs(t, m, (2, 3), half=100.0)         # a group's legs end apart (order_group): boxes of 100
    _watch(t, RUN['team'])
    return t


def start(m):
    t = Test()
    _road(t, m, 'CNVRoad')
    _at(t, 'go', 1.0, [('NAMED_FOLLOW_WAYPOINTS_STARTING_AT_WAYPOINT', m.role('truck 2').name, 'CNVRoad',
                        'Test Waypath B')])
    _legs(t, m, (2,))
    _watch(t, RUN['start'])
    return t


def texact(m):
    t = Test()
    _road(t, m, 'CNVRoad')
    _at(t, 'go', 1.0, [('TEAM_FOLLOW_WAYPOINTS_EXACT', m.crew('W23'), 'CNVRoad', 1)])
    _legs(t, m, (2, 3), half=100.0)
    _watch(t, RUN['texact'])
    return t


CHECKS = {'engine_waypath': {'line': line, 'exact': exact, 'near': near, 'loop': loop, 'team': team,
                             'start': start, 'texact': texact}}
