"""WallBuilderBehavior startup, not a construction or connection acceptance.

Data prediction: StartInSecondaryModel=true sets WALL_SEGMENT; false and the
identical no-module control do not. Rows encode alive*10 + WALL_SEGMENT.
The no-module control inherits BaseWallPiece, whose effective modules contain
no WallBuilderBehavior. Custom names are outside the retail ConnectingObjectFilter.
"""
from parts import Script, Test, status


def check(m):
    t = Test()
    t.scripts.append(Script('Test - reveal', [], [('MAP_REVEAL_ALL_PERM', m.player('p1'))]))
    for role in ('hub', 'segment', 'none'):
        counter = 'Wall ' + role
        name = m.role(role).name
        t.counters.append((counter, role))
        t.scripts += [
            Script('Test - reset ' + role, [], [('SET_COUNTER', counter, 0)], once=False),
            Script('Test - alive ' + role, [('NAMED_NOT_DESTROYED', name)],
                   [('INCREMENT_COUNTER', 10, counter)], once=False),
            Script('Test - segment ' + role, [('UNIT_HAS_OBJECT_STATUS', name, status('WALL_SEGMENT'))],
                   [('INCREMENT_COUNTER', 1, counter)], once=False)]
    t.expect = [('hub', 2, '==', 10), ('segment', 2, '==', 11), ('none', 2, '==', 10)]
    t.bench = [('bench_watch', dict(seconds=12, every=1, sheet=False, lines=3))]
    return t


CHECKS = {'engine_wallinit': {'a': check}}
