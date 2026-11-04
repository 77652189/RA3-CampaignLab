"""K6 team probe (missions/team_bench.py): what the engine does with a map's own team that a script orders as one. The
convoy trucks are ordered to `far` by MOVE_TEAM_TO only (never by name); counters read who got there.

Bench 2026-11-04 (K6 go): a placed unit joins the team and the order reaches every member; a member made after the
order does NOT follow it (once: late 0) but the next order does (tick: late 1); the survivors of a killed member both
move (tick: 2 of 2); with every member dead the team reads 0 members, no units, TEAM_DESTROYED, and a unit made on it
afterwards is a member again and takes the next order (dead).

once: one order at 1 s, nothing after. Placed trucks 1-3 are on the team: do all three go? Late 1 is made on the team
  at 8 s, after the order: does it go too? Counters: trucks in `far`, late 1 in `far`, team members, team has units.
tick: the order again every 3 s (the convoy's tick); late 1 made at 8 s; truck 1 killed at 12 s. The survivors (trucks
  2, 3) and late 1: all in `far`?
dead: the order every 3 s; all three trucks killed at 10 s, a late member made at 16 s. Members and HasUnits while the
  team is empty, TEAM_DESTROYED, and whether the member made after it went.
"""
from parts import Script, Test, square

LATE_AT, KILL_AT = 8.0, 12.0
FAR = 'Test Far Area'
LABELS = ('在终点的车', '后来的车到终点', '队里几个', '队里有人吗')


def _sum(t, counter, names):
    """counter = how many of `names` are inside FAR (zeroed and counted every frame)."""
    t.scripts.append(Script(f'Test - {counter} zero', [], [('SET_COUNTER', counter, 0)], once=False))
    t.scripts += [Script(f'Test - {counter} {k}', [('NAMED_INSIDE_AREA', n, FAR)], [('INCREMENT_COUNTER', 1, counter)],
                         once=False) for k, n in enumerate(names)]


def _team_counters(t, team, members, has):
    t.scripts += [Script(f'Test - {members} {n}', [('TEAM_COMPARE_NUM_MEMBERS', team, 2, n)],
                         [('SET_COUNTER', members, n)], once=False) for n in range(6)]
    t.scripts += [Script(f'Test - {has} zero', [], [('SET_COUNTER', has, 0)], once=False),
                  Script(f'Test - {has} one', [('TEAM_HAS_UNITS', team)], [('SET_COUNTER', has, 1)], once=False)]


def _setup(m, t, tick, order=None):
    team = m.teams.get('Probe')
    order = order or [('MOVE_TEAM_TO', team, m.mark('far'))]
    t.areas[FAR] = square(*m.point('far'), 60.0)
    t.scripts.append(Script('Test - order start', [], [('SET_MILLISECOND_TIMER', 'Test Order Timer', 1.0),
                                                       ('SET_MILLISECOND_TIMER', 'Test Late Timer', LATE_AT)]))
    if tick:
        t.scripts.append(Script('Test - order', [('TIMER_EXPIRED', 'Test Order Timer')],
                                order + [('SET_MILLISECOND_TIMER', 'Test Order Timer', 3.0)],
                                once=False))
    else:
        t.scripts.append(Script('Test - order', [('TIMER_EXPIRED', 'Test Order Timer')],
                                order))
    return team


def _late(m, t, team, at_timer, name='UNIT - CNV Probe Late 1'):
    t.scripts.append(Script('Test - late', [('TIMER_EXPIRED', at_timer)],
                            [('CREATE_NAMED_ON_TEAM_AT_WAYPOINT_WITH_ORIENTATION', name, m.role('truck 1').template,
                              team, m.mark('late'), 0.0)]))
    return name


def once(m):
    t = Test()
    team = _setup(m, t, tick=False)
    late = _late(m, t, team, 'Test Late Timer')
    names = [m.role(f'truck {k}').name for k in (1, 2, 3)]
    _sum(t, 'Test Far', names)
    _sum(t, 'Test Late', [late])
    _team_counters(t, team, 'Test Members', 'Test Has')
    t.counters += list(zip(('Test Far', 'Test Late', 'Test Members', 'Test Has'), LABELS))
    t.expect += [(LABELS[0], 0, 'ever==', 3), (LABELS[1], 0, '==', 0)]      # a member made after the order does not follow
    t.bench = [('bench_watch', dict(seconds=60, every=4, sheet=False, lines=4))]
    return t


def tick(m):
    t = Test()
    team = _setup(m, t, tick=True)
    late = _late(m, t, team, 'Test Late Timer')
    names = [m.role(f'truck {k}').name for k in (1, 2, 3)]
    t.scripts += [Script('Test - kill start', [('TIMER_EXPIRED', 'Test Late Timer')],
                         [('SET_MILLISECOND_TIMER', 'Test Kill Timer', KILL_AT - LATE_AT)]),
                  Script('Test - kill', [('TIMER_EXPIRED', 'Test Kill Timer')], [('NAMED_KILL', names[0])])]
    _sum(t, 'Test Far', names[1:])
    _sum(t, 'Test Late', [late])
    _team_counters(t, team, 'Test Members', 'Test Has')
    t.counters += list(zip(('Test Far', 'Test Late', 'Test Members', 'Test Has'), LABELS))
    t.expect += [(LABELS[0], 0, 'ever==', 2), (LABELS[1], 0, 'ever==', 1)]
    t.bench = [('bench_watch', dict(seconds=60, every=4, sheet=False, lines=4))]
    return t


def dead(m):
    t = Test()
    team = _setup(m, t, tick=True)
    names = [m.role(f'truck {k}').name for k in (1, 2, 3)]
    t.scripts += [Script('Test - kill timer', [], [('SET_MILLISECOND_TIMER', 'Test Kill Timer', 10.0),
                                                    ('SET_MILLISECOND_TIMER', 'Test Late Timer', 16.0)]),
                  Script('Test - kill', [('TIMER_EXPIRED', 'Test Kill Timer')], [('NAMED_KILL', n) for n in names])]
    late = _late(m, t, team, 'Test Late Timer')
    _sum(t, 'Test Late', [late])
    _team_counters(t, team, 'Test Members', 'Test Has')
    t.scripts += [Script('Test - gone', [('TEAM_DESTROYED', team)], [('SET_COUNTER', 'Test Gone', 1)], once=False)]
    t.counters += list(zip(('Test Late', 'Test Members', 'Test Has', 'Test Gone'),
                           ('后来的车到终点', '队里几个', '队里有人吗', '队被判毁了')))
    t.expect += [('后来的车到终点', 0, 'ever==', 1), ('队里几个', 9, '==', 0, 15), ('队里几个', 17, '==', 1)]
    t.bench = [('bench_watch', dict(seconds=60, every=4, sheet=False, lines=4))]
    return t


def _control(order):
    """The trucks ordered every 3 s by `order(m, team, names)`; counters as in once."""
    def check(m):
        t = Test()
        team = m.teams.get('Probe')
        names = [m.role(f'truck {k}').name for k in (1, 2, 3)]
        _setup(m, t, tick=True, order=order(m, team, names))
        _sum(t, 'Test Far', names)
        t.counters += [('Test Far', LABELS[0])]
        if team:
            _team_counters(t, team, 'Test Members', 'Test Has')
            t.counters += [('Test Members', LABELS[2])]
        t.expect += [(LABELS[0], 0, 'ever==', 3)]
        t.bench = [('bench_watch', dict(seconds=45, every=4, sheet=False, lines=2))]
        return t
    return check


# named: each truck by name (what A4 does today); attack: ATTACK_MOVE_TEAM_TO
named =_control(lambda m, team, names: [('MOVE_NAMED_UNIT_TO', n, m.mark('far')) for n in names])
attack = _control(lambda m, team, names: [('ATTACK_MOVE_TEAM_TO', team, m.mark('far'))])


def join(m):
    """The exit's way in (ctx.order): units that were NOT placed on the team join it by UNIT_SET_TEAM in the same script
    that gives the whole-team order, every 3 s. Run on team_plain (the trucks on the player's default team). The order
    names late 1 too, which does not exist till 8 s (a name not made yet: no harm?) and is made then on the default
    team; truck 1 is killed at 12 s (a dead name: no harm?). Do the survivors and late 1 all reach `far`?"""
    t = Test()
    team = m.crew('Probe')
    late = 'UNIT - CNV Probe Late 1'
    names = [m.role(f'truck {k}').name for k in (1, 2, 3)]
    _setup(m, t, tick=True, order=[('UNIT_SET_TEAM', n, team) for n in names + [late]] +
           [('MOVE_TEAM_TO', team, m.mark('far'))])
    t.scripts += [Script('Test - late', [('TIMER_EXPIRED', 'Test Late Timer')],
                         [('CREATE_NAMED_ON_TEAM_AT_WAYPOINT_WITH_ORIENTATION', late, m.role('truck 1').template,
                           m.team('p1'), m.mark('late'), 0.0),
                          ('SET_MILLISECOND_TIMER', 'Test Kill Timer', KILL_AT - LATE_AT)]),
                  Script('Test - kill', [('TIMER_EXPIRED', 'Test Kill Timer')], [('NAMED_KILL', names[0])])]
    _sum(t, 'Test Far', names[1:])
    _sum(t, 'Test Late', [late])
    t.counters += [('Test Far', LABELS[0]), ('Test Late', LABELS[1])]
    t.expect += [(LABELS[0], 0, 'ever==', 2), (LABELS[1], 0, 'ever==', 1)]
    t.bench = [('bench_watch', dict(seconds=60, every=4, sheet=False, lines=2))]
    return t


def made(m):
    """A unit made on the team in the SAME script that gives the order, once, at 1 s (a plan's wave: create, then
    send). Run on team: truck 1-3 are placed on the team, late 1 is made with the order. Does late 1 go?"""
    t = Test()
    team = m.teams.get('Probe')
    late = 'UNIT - CNV Probe Late 1'
    names = [m.role(f'truck {k}').name for k in (1, 2, 3)]
    _setup(m, t, tick=False, order=[('CREATE_NAMED_ON_TEAM_AT_WAYPOINT_WITH_ORIENTATION', late, m.role('truck 1').template,
                                     team, m.mark('late'), 0.0), ('MOVE_TEAM_TO', team, m.mark('far'))])
    _sum(t, 'Test Far', names)
    _sum(t, 'Test Late', [late])
    t.counters += [('Test Far', LABELS[0]), ('Test Late', LABELS[1])]
    t.expect += [(LABELS[0], 0, 'ever==', 3), (LABELS[1], 0, 'ever==', 1)]
    t.bench = [('bench_watch', dict(seconds=45, every=4, sheet=False, lines=2))]
    return t


def guard(m):
    """TEAM_GUARD_AREA (the area `far`) at 1 s: do all three go to the area and stay?"""
    t = Test()
    team = m.teams.get('Probe')
    names = [m.role(f'truck {k}').name for k in (1, 2, 3)]
    _setup(m, t, tick=False, order=[('TEAM_GUARD_AREA', team, FAR)])
    _sum(t, 'Test Far', names)
    t.counters += [('Test Far', LABELS[0])]
    t.expect += [(LABELS[0], 0, 'ever==', 3)]
    t.bench = [('bench_watch', dict(seconds=45, every=4, sheet=False, lines=2))]
    return t


def stop(m):
    """MOVE_TEAM_TO at 1 s, TEAM_STOP at 5 s (the trucks have gone about 125 of the 300 at speed 25): none may ever
    reach `far`."""
    t = Test()
    team = m.teams.get('Probe')
    names = [m.role(f'truck {k}').name for k in (1, 2, 3)]
    _setup(m, t, tick=False)
    t.scripts += [Script('Test - stop arm', [('TIMER_EXPIRED', 'Test Order Timer')],
                         [('SET_MILLISECOND_TIMER', 'Test Stop Timer', 4.0)]),
                  Script('Test - stop', [('TIMER_EXPIRED', 'Test Stop Timer')], [('TEAM_STOP', team)])]
    _sum(t, 'Test Far', names)
    t.counters += [('Test Far', LABELS[0])]
    t.expect += [(LABELS[0], 0, '==', 0)]
    t.bench = [('bench_watch', dict(seconds=45, every=4, sheet=False, lines=2))]
    return t


CHECKS = {'team': {'once': once, 'tick': tick, 'dead': dead, 'named': named, 'attack': attack, 'made': made,
                   'guard': guard, 'stop': stop},
          'team_plain': {'named': named, 'join': join}}
