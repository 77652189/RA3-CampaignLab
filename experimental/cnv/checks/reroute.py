"""Reroute tests (missions/reroute_bench.py): an ice wall is put across the quay between the squad and the middle
bridge at the start; at GO_AT the squad is sent to the west field (again every few seconds, as a wave is). Counted,
latched: one of the squad on the middle bridge's west end (it got over that way), on the north or south bridge (it went round), how many infantry got
to the west field, and the wall's health (it stands).

round: the wall up, none gets over by the middle bridge; some go round by another and get to the west field.
open: no wall -- the control: they cross by the middle bridge (the shortest way).
"""
from missions.reroute_bench import ANGLE, SQUAD, WARRIOR, bridges
from parts import Script, Test, counted, square

GO_AT, RUN = 3.0, 150.0
BRIDGE = 80.0                                   # half-side of the area on a bridge (its middle)


def latch(t, counter, label, when):
    t.counters.append((counter, label))
    t.scripts.append(Script(f'Test - {counter} zero', [], [('SET_COUNTER', counter, 0)]))
    t.scripts += [Script(f'Test - {counter} {k + 1}', w, [('SET_COUNTER', counter, 1)]) for k, w in enumerate(when)]


def trip(m, wall):
    t = Test()
    s1 = m.player('s1')
    squad = [m.role(f'warrior {j}').name for j in range(1, SQUAD + 1)]
    t.scripts.append(Script('Test - start', [], [('MAP_REVEAL_ALL_PERM', m.player('p1')),
                                                 ('SET_MILLISECOND_TIMER', 'Test - go', GO_AT)]))
    t.scripts.append(Script('Test - go', [('TIMER_EXPIRED', 'Test - go')],
                            [('MOVE_NAMED_UNIT_TO', n, m.mark('goal')) for n in squad]
                            + [('SET_MILLISECOND_TIMER', 'Test - go', 4.0)], once=False))
    b = bridges()
    mx, my = b['middle']
    for k in ('north', 'south'):
        t.areas[f'Test {k}'] = square(*b[k], BRIDGE)
    t.areas['Test west end'] = square(mx - 200, my, BRIDGE)
    if wall:
        # up before the squad is sent, across the quay (the mission's wall mark and angle). Bench 2026-10-27: put
        # up once the squad neared the bridge it came too late; on the bridge's deck it stopped nobody
        unit = next(u for u in m.units if u.id == 'CNV_RerouteWall')
        m.spawns.add(unit.id)
        t.scripts.append(Script('Test - close', [], [('CREATE_NAMED_ON_TEAM_AT_WAYPOINT_WITH_ORIENTATION',
                                                      'UNIT - CNV Reroute Wall', unit.id, m.team('p1'),
                                                      m.mark('wall'), ANGLE)]))
        counted('Test Wall', '冰墙血量', t, health='UNIT - CNV Reroute Wall')
    latch(t, 'Test Middle', '走中桥过去', [[('NAMED_INSIDE_AREA', n, 'Test west end')] for n in squad])
    latch(t, 'Test Round', '绕北桥或南桥', [[('NAMED_INSIDE_AREA', n, f'Test {k}')] for n in squad
                                       for k in ('north', 'south')])
    t.areas['Test goal'] = square(*m.point('goal'), 300.0)
    counted('Test Goal W', '到了西边步兵', t, template=WARRIOR, player=s1, area='Test goal', most=4)
    t.bench = [('bench_watch', dict(seconds=RUN, every=4, sheet=False, lines=len(t.counters)))]
    return t


def round_(m):
    t = trip(m, wall=True)
    t.expect += [('冰墙血量', 1, 'ever>=', 90), ('走中桥过去', 1, '==', 0), ('绕北桥或南桥', 1, 'ever==', 1),
                 ('到了西边步兵', 1, 'ever>=', 1)]
    return t


def opened(m):
    t = trip(m, wall=False)
    t.expect += [('走中桥过去', 1, 'ever==', 1), ('到了西边步兵', 1, 'ever>=', 1)]
    return t
