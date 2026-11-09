"""Engine probe: how SET_REF_TO_NEREST_TEAM_OF_UNNAMED_TYPE_OWNED_BY_PLAYER (type, player, team, ref) picks
(missions/ref_bench.py; A4's Ghost King pick, devices/horn.py).

Members are made by script at 1 s (order M1, M2; ref_a2 M2, M1); at PICK s the action runs on the wall type; at
DEL s the ref is deleted (NAMED_DELETE) -- the area whose wall count falls from 1 to 0 is the wall it pointed at.
  墙A 墙B 墙C  walls of the type standing in the square round each wall (1 / 0)
  引用血  SET_UNIT_HEALTH_PERCENTAGE_TO_COUNTER of the ref, every frame (0 before the pick)
ref_c (no area counts; the three walls unnamed): pick at 3 s; at 5 s pick a type nobody owns; at 7 s the wall type
again; at 8 s the members are deleted; at 10 s the wall type with an EMPTY team; at 12 s the ref is deleted. 引用血
tells whether a failed pick leaves the ref or clears it; 墙A 墙B 墙C when the delete at 12 s hits.
Readings: see RESULTS below.
RESULTS (bench 2026-11-07; bench s = script s - ~1; counters 墙A 墙B 墙C 引用血):
  ref_a / ref_a2 (members made M1,M2 / M2,M1; walls unnamed): s2-s4 1 1 1 100 -> s5+ 1 1 0 100: the ref pointed at C, the
    wall nearest the CENTRE of the members (150 from it; A 472, B 412), not the first / last / any-member nearest;
    the swapped order changes nothing.
  ref_b (C named, A B unnamed): s4+ 1 0 1 100: C skipped, the ref took B (next nearest the centre) -- a NAMED object is
    skipped, "UNNAMED" means the wall has no script name.
  ref_c (pick wall at 3, pick a type nobody owns at 5, wall at 7, members deleted at 8, wall with an EMPTY team at 10,
    ref deleted at 12): s11+ 0 1 1: the ref then pointed at A, the wall nearest the map's (0,0) (A 2183, C 2713, B 2977
    from it: inference), so an empty team's centre reads (0,0) and the pick still sets the ref. 引用血 read 100 all
    the time, also after a NAMED_DELETE of the ref (a_a: s5+ still 100): it is no sign of a cleared ref. The no-such-type
    pick (s5) left no trace in these readings.
  ref_d (bench 2026-11-09, CampRefDFrames_mcp_1109_061813; counters 造了 坦克 墙A 墙B; the members made by ONE script
    run twice, CREATE_UNNAMED_ON_TEAM_AT_WAYPOINT at M2; the tank type picked at 8 s, deleted at 10 s): s1-s3 2 2 1 1,
    s4-s7 2 2 1 0, s8+ 2 1 1 0 -- two objects, both on the team (the wall pick took B, nearest M2; an empty team takes
    A), and an unnamed made one is picked by the type's pick.
  a4/smash: see the coordinator's note (冰墙 1 at s58, 鬼王上岸 1 at s58, 血量 100 s58-s67, 76 s70, 53 s73, 41 s76,
    18 s79, 6 s82-s106; 冰墙 0 from s82).
"""
from parts import Script, Test, counted, square

PICK, DEL, RUN = 3.0, 6.0, 16.0
REF = 'UNITRef - CNV Ref Nearest'
TANK_PICK, TANK_DEL, TANK_REF = 8.0, 10.0, 'UNITRef - CNV Ref Tank'     # ref_d
MEMBER = 'AlliedAntiVehicleVehicleTech1'


def frames(m):
    t = Test()
    p1, team = m.player('p1'), m.teams['Ref']
    wall = 'CNV_RefWall'
    pts = [('m1', 'UNIT - CNV Ref M1'), ('m2', 'UNIT - CNV Ref M2')]
    if m.facts['swap']:
        pts.reverse()
    make = [('CREATE_NAMED_ON_TEAM_AT_WAYPOINT', n, MEMBER, team, m.mark(k)) for k, n in pts]
    pick = ('SET_REF_TO_NEREST_TEAM_OF_UNNAMED_TYPE_OWNED_BY_PLAYER', wall, p1, team, REF)
    extra = m.facts['extra']
    timers = [('SET_MILLISECOND_TIMER', 'Test Pick', PICK), ('SET_MILLISECOND_TIMER', 'Test Del', DEL)]
    if extra:
        timers = [('SET_MILLISECOND_TIMER', f'Test S{i}', s) for i, s in enumerate((3.0, 5.0, 7.0, 8.0, 10.0, 12.0))]
    unnamed = m.facts.get('unnamed')
    if unnamed:                                 # one script, run twice: two unnamed members at M2
        make = []
        timers += [('SET_MILLISECOND_TIMER', 'Test Tank Pick', TANK_PICK),
                   ('SET_MILLISECOND_TIMER', 'Test Tank Del', TANK_DEL)]
        t.counters.append(('CNV_Ref_Made', '造了'))
        t.scripts.append(Script('Test - make unnamed', [('COUNTER', 'CNV_Ref_Made', 0, 2)],
                                [('CREATE_UNNAMED_ON_TEAM_AT_WAYPOINT', MEMBER, team, m.mark('m2')),
                                 ('INCREMENT_COUNTER', 1, 'CNV_Ref_Made')], once=False))
    t.scripts.append(Script('Test - start', [], [('MAP_REVEAL_ALL_PERM', p1)] + make + timers))
    if unnamed:                                 # then the tank type itself: is an unnamed made one picked?
        t.scripts += [Script('Test - tank pick', [('TIMER_EXPIRED', 'Test Tank Pick')],
                             [('SET_REF_TO_NEREST_TEAM_OF_UNNAMED_TYPE_OWNED_BY_PLAYER', MEMBER, p1, team, TANK_REF)]),
                      Script('Test - tank del', [('TIMER_EXPIRED', 'Test Tank Del')], [('NAMED_DELETE', TANK_REF)])]
        counted('CNV_Ref_T', '坦克', t, template=MEMBER, most=3)
    if not extra:
        t.scripts += [Script('Test - pick', [('TIMER_EXPIRED', 'Test Pick')], [pick]),
                      Script('Test - del', [('TIMER_EXPIRED', 'Test Del')], [('NAMED_DELETE', REF)])]
    else:
        none = ('SET_REF_TO_NEREST_TEAM_OF_UNNAMED_TYPE_OWNED_BY_PLAYER', 'CNV_RefNone', p1, team, REF)
        t.scripts += [Script('Test - S0', [('TIMER_EXPIRED', 'Test S0')], [pick]),
                      Script('Test - S1', [('TIMER_EXPIRED', 'Test S1')], [none]),
                      Script('Test - S2', [('TIMER_EXPIRED', 'Test S2')], [pick]),
                      Script('Test - S3', [('TIMER_EXPIRED', 'Test S3')],
                             [('NAMED_DELETE', n) for _, n in pts]),
                      Script('Test - S4', [('TIMER_EXPIRED', 'Test S4')], [pick]),
                      Script('Test - S5', [('TIMER_EXPIRED', 'Test S5')], [('NAMED_DELETE', REF)])]
    for k in 'AB' if unnamed else 'ABC':        # the mission publishes each wall's spot (four lines fit: d drops C)
        t.areas[f'Test Ref {k}'] = square(*m.point(f'spot {k}'), 100.0)
        counted(f'CNV_Ref_{k}', f'墙{k}', t, template=wall, area=f'Test Ref {k}', most=2)
    if unnamed:
        t.expect += [('造了', 1, 'ever>=', 2)]
    else:
        counted('CNV_Ref_H', '引用血', t, health=REF)
        t.expect += [('引用血', RUN - 1, 'ever>=', 0)]
    t.bench = [('bench_watch', dict(seconds=RUN, every=1, sheet=False, lines=len(t.counters)))]
    return t


CHECKS = {k: {'frames': frames} for k in ('ref_a', 'ref_a2', 'ref_b', 'ref_c', 'ref_d')}
