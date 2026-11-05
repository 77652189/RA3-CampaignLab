"""Engine unit tests: how the game finds a way for units a script orders (docs/engine/pathing.md; engine line
round 10, ADR 0017). On the probe map (maps/probe_paths.py) every order is a whole-team order (Mission.order, as the
missions give them).

detour: an IFV each in the far / mid / near boxes, ordered to the goal on the other side of a wall whose only gap
  is about 8 200 / 3 400 / 1 100 of way round (600 straight); a tank ordered into the closed ring 'shut'. Counters:
  1 by the gap (it went the way round), 10 at the goal; shut: 1 outside the ring on its own side, 10 still at the
  start, 100 outside the ring's far side.
group: 'team' -- an IFV (fast) and an engineer (slow) ordered as one team (move); 'attack team' the same pair by
  attack-move: 1 the IFV at the goal, 10 the engineer (does the fast one wait?). 'narrow' / 'wide': six tanks as one
  team through a gap 50 / 150 across: how many at the goal.
stuck / alive / where: detour's far and mid IFVs read again -- at the start, under the goal, by the gap; alive and
  in which half; then by strips.

Read (测, 2026-11-04, runs CampPaths*_mcp_1104_*; docs/engine/pathing.md): near got there by s9; far and mid, alive,
never reached their gap -- they drove a few hundred east and stopped south of the wall (x 700..1500); shut stopped
outside the ring on its own side; team / attack team: the IFV at s7, the engineer at s25 (nobody waits); narrow 3 at
s9 and 6 at s11, wide 6 at s9. limit: 1 400 there by s10, 1 800 and 2 600 never at their gap in 90 s.
"""
from maps import probe_paths
from parts import Mission, Script, Test, counted, square

IFV = 'AlliedAntiAirVehicleTech1'
TANK = 'AlliedAntiVehicleVehicleTech1'
ENGINEER = 'AlliedEngineer'
CHOKE = 6
LABEL = {'far': '远绕', 'mid': '中绕', 'near': '近绕', 'shut': '围死', 'team': '同队移动', 'attack team': '同队攻移',
         'narrow': '窄口', 'wide': '宽口', 'd1400': '绕1400', 'd1800': '绕1800', 'd2600': '绕2600'}
LIMIT = ('near', 'd1400', 'd1800')   # limit: the way round about 1 100 (control) / 1 400 / 1 800 (2 600: the first run, no)


def _key(s):
    return s.title().replace(' ', '')


def mission():
    m = Mission(name='CampPaths', map=probe_paths, facts={})
    for lane in ('far', 'mid', 'near', 'd1400', 'd1800', 'd2600'):
        m.put(IFV, f'{lane} start', role=f'{lane} ifv', name=f'UNIT - CNV Paths {_key(lane)} Ifv')
    m.put(TANK, 'shut start', role='shut tank', name='UNIT - CNV Paths Shut Tank')
    for lane in ('team', 'attack team'):
        m.put(IFV, f'{lane} start', -40.0, 0, role=f'{lane} ifv', name=f'UNIT - CNV Paths {_key(lane)} Ifv')
        m.put(ENGINEER, f'{lane} start', 40.0, 0, role=f'{lane} engineer',
              name=f'UNIT - CNV Paths {_key(lane)} Engineer')
    for lane in ('narrow', 'wide'):
        for k in range(CHOKE):
            m.put(TANK, f'{lane} start', -125.0 + 50.0 * k, 0, role=f'{lane} tank {k + 1}',
                  name=f'UNIT - CNV Paths {_key(lane)} Tank {k + 1}')
    return m


def _go(m, t, lane, parts, kind='move'):
    wp = f'Test Paths {_key(lane)} Goal'
    t.waypoints[wp] = m.site(f'{lane} goal')
    return m.order(kind, [m.role(p).name for p in parts], wp, crew=f'Paths{_key(lane)}')


def _scored(t, lane, worth):
    """A counter for `lane`: 0 every frame, then each (named, area, worth) adds `worth` while that unit is inside."""
    counter = f'CNV_Paths_{_key(lane)}'
    t.counters.append((counter, LABEL[lane]))
    t.scripts.append(Script(f'Test - {counter} zero', [], [('SET_COUNTER', counter, 0)], once=False))
    for k, (name, area, n) in enumerate(worth):
        t.scripts.append(Script(f'Test - {counter} {k}', [('NAMED_INSIDE_AREA', name, area)],
                                [('INCREMENT_COUNTER', n, counter)], once=False))


def _area(m, t, site, half):
    name = f'Test Paths {_key(site)}'
    t.areas[name] = square(*m.site(site), half)
    return name


def detour(m):
    t = Test()
    order = [('MAP_REVEAL_ALL_PERM', m.player('p1'))]
    for lane in ('far', 'mid', 'near'):
        order += _go(m, t, lane, [f'{lane} ifv'])
        ifv = m.role(f'{lane} ifv').name
        _scored(t, lane, [(ifv, _area(m, t, f'{lane} gap', 140.0), 1), (ifv, _area(m, t, f'{lane} goal', 100.0), 10)])
    order += _go(m, t, 'shut', ['shut tank'])
    tank = m.role('shut tank').name
    _scored(t, 'shut', [(tank, _area(m, t, 'shut near', 60.0), 1), (tank, _area(m, t, 'shut start', 60.0), 10),
                        (tank, _area(m, t, 'shut far', 60.0), 100)])
    t.scripts.insert(0, Script('Test - go', [], order))
    t.bench = [('bench_watch', dict(seconds=200, every=4, sheet=False, lines=4))]
    t.expect = [('近绕', 0, 'ever==', 10, 200)]          # the near one gets there: the rest are read, not judged
    return t


def limit(m, lanes=LIMIT):
    """Between near (gets there) and mid (stops): IFVs whose way round is about 1 400 / 1 800, near as the control.
    Counters as detour's: 1 by the gap, 10 at the goal."""
    t = Test()
    order = [('MAP_REVEAL_ALL_PERM', m.player('p1'))]
    for lane in lanes:
        order += _go(m, t, lane, [f'{lane} ifv'])
        ifv = m.role(f'{lane} ifv').name
        _scored(t, lane, [(ifv, _area(m, t, f'{lane} gap', 140.0), 1), (ifv, _area(m, t, f'{lane} goal', 100.0), 10)])
    t.scripts.insert(0, Script('Test - go', [], order))
    t.bench = [('bench_watch', dict(seconds=90, every=3, sheet=False, lines=3))]
    t.expect = [('近绕', 0, 'ever==', 10, 90)]
    return t


def stuck(m):
    """detour's three IFVs again, read for where they stop: 1 still at the start, 10 against the wall right under
    the goal (the nearest point to it), 100 by the gap; every second."""
    t = Test()
    order = [('MAP_REVEAL_ALL_PERM', m.player('p1'))]
    for lane in ('far', 'mid', 'near'):
        order += _go(m, t, lane, [f'{lane} ifv'])
        ifv = m.role(f'{lane} ifv').name
        gx, _ = m.site(f'{lane} goal')
        wy = probe_paths.BOXES[lane][1]
        under = f'Test Paths {_key(lane)} Under'
        t.areas[under] = square(gx, wy - 70.0, 70.0)
        _scored(t, lane, [(ifv, _area(m, t, f'{lane} start', 60.0), 1), (ifv, under, 10),
                          (ifv, _area(m, t, f'{lane} gap', 140.0), 100)])
    t.scripts.insert(0, Script('Test - go', [], order))
    t.bench = [('bench_watch', dict(seconds=60, every=1, sheet=False, lines=3))]
    t.expect = [('近绕', 0, 'ever==', 100, 60)]
    return t


def alive(m):
    """Are the far and mid IFVs there at all (health), and in which half of the far box (south / north of the wall)."""
    t = stuck(m)
    t.counters.clear()
    t.scripts = [s for s in t.scripts if not s.name.startswith('Test - CNV_Paths')]
    for lane in ('far', 'mid'):
        counted(f'Test Paths {_key(lane)} Hp', f'{LABEL[lane]}血量', t, health=m.role(f'{lane} ifv').name)
    (x0, y0, x1, y1), wy, _ = probe_paths.BOXES['far']
    ifv = m.role('far ifv').name
    for half, (a, b) in (('south', (y0, wy)), ('north', (wy, y1))):
        t.areas[f'Test Paths Far {half}'] = [(x0, a), (x1, a), (x1, b), (x0, b)]
        counted(f'Test Paths Far {half.title()}', f'远绕{"南" if half == "south" else "北"}', t, named=ifv,
                area=f'Test Paths Far {half}')
    t.bench = [('bench_watch', dict(seconds=30, every=2, sheet=False, lines=4))]
    t.expect = []
    return t


BANDS_X = ((300.0, 700.0), (700.0, 1500.0), (1500.0, 3000.0), (3000.0, 4700.0))   # 1 / 10 / 100 / 1000
BANDS_Y = 4                         # south of the wall in 4 strips from the fence up to the wall: 1 / 10 / 100 / 1000


def where(m):
    """Where the far and mid IFVs stop south of the wall: an x counter and a y counter each (the strip's worth)."""
    t = Test()
    order = [('MAP_REVEAL_ALL_PERM', m.player('p1'))]
    for lane in ('far', 'mid'):
        order += _go(m, t, lane, [f'{lane} ifv'])
        ifv = m.role(f'{lane} ifv').name
        (x0, y0, x1, _), wy, _ = probe_paths.BOXES[lane]
        xs, ys = [], []
        for k, (a, b) in enumerate(BANDS_X):
            n = f'Test Paths {_key(lane)} X{k}'
            t.areas[n] = [(a, y0), (b, y0), (b, wy), (a, wy)]
            xs.append((ifv, n, 10 ** k))
        step = (wy - y0) / BANDS_Y
        for k in range(BANDS_Y):
            n = f'Test Paths {_key(lane)} Y{k}'
            t.areas[n] = [(x0, y0 + k * step), (x1, y0 + k * step), (x1, y0 + (k + 1) * step), (x0, y0 + (k + 1) * step)]
            ys.append((ifv, n, 10 ** k))
        LABEL[f'{lane} x'], LABEL[f'{lane} y'] = f'{LABEL[lane]}X', f'{LABEL[lane]}Y'
        _scored(t, f'{lane} x', xs)
        _scored(t, f'{lane} y', ys)
    t.scripts.insert(0, Script('Test - go', [], order))
    t.bench = [('bench_watch', dict(seconds=40, every=2, sheet=False, lines=4))]
    return t


def group(m):
    t = Test()
    order = [('MAP_REVEAL_ALL_PERM', m.player('p1'))]
    for lane, kind in (('team', 'move'), ('attack team', 'attack_move')):
        order += _go(m, t, lane, [f'{lane} ifv', f'{lane} engineer'], kind)
        goal = _area(m, t, f'{lane} goal', 100.0)
        _scored(t, lane, [(m.role(f'{lane} ifv').name, goal, 1), (m.role(f'{lane} engineer').name, goal, 10)])
    for lane in ('narrow', 'wide'):
        order += _go(m, t, lane, [f'{lane} tank {k + 1}' for k in range(CHOKE)])
        counted(f'CNV_Paths_{_key(lane)}', LABEL[lane], t, template=TANK, area=_area(m, t, f'{lane} goal', 200.0))
    t.scripts.insert(0, Script('Test - go', [], order))
    t.bench = [('bench_watch', dict(seconds=90, every=2, sheet=False, lines=4))]
    t.expect = [('宽口', 0, 'ever>', 0, 90)]
    return t


# the builds this module makes and their checks (cnv/registry.py)
MISSION = {'engine_paths': mission}
CHECKS = {'engine_paths': {'detour': detour, 'limit': limit, 'stuck': stuck, 'alive': alive, 'where': where, 'group': group}}
