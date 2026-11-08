"""Engine unit tests: does a unit go round a way that structures or enemies block (docs/engine/pathing.md 6, 7;
engine line round 10, ADR 0017). Map: maps/probe_block.py, every way round about 950 (probe_paths' 1 100 goes
round). Whole-team orders (Mission.order), as the missions give them.

wall: an IFV each in 'bits' (the wall on field 0, the control), 'built' (a row of the player's own structures across
  the way, there from the start) and 'late' (the same row made LATE s after the order). Counters: 1 by the far gap
  (it went round), 10 at the goal.
enemy: the wall has a straight gap plugged by two enemy MCVs (unarmed), the far gap open; a tank ordered by move in
  'enemy move', by attack-move in 'enemy attack'. Counters as wall's, and the attack lane's front MCV's health.

Read (测, 2026-11-04, docs/engine/pathing.md 6, 7): wall -- bits and built 11 (round, s7), late 10 at s4 (through
the row, made by s1: `made` reads 8 and 8); enemy -- move 10 at s25 (through the plug; `plugs` again: not by s41),
attack never there, the MCV 98 -> 24 in 90 s.
foot (测, 2026-11-08): the row made at the start, the IFV and a peacekeeper ordered at s4 -- both 11 (round): the IFV
by the gap s7, at the goal s13; the soldier s10 / s22. A made structure is in a new order's way, infantry's too.
"""
from maps import probe_block
from parts import Mission, Script, Test, counted, square

IFV = 'AlliedAntiAirVehicleTech1'
TANK = 'AlliedAntiVehicleVehicleTech1'
WALL = 'SovietBunker'              # the ice wall is a structure; a retail one stands in (G5: no units/ imports)
PLUG = 'AlliedMCV'
FOOT = 'AlliedAntiInfantryInfantry'
LATE = 1.0
AFTER = 4.0                        # foot: the order, 3 s after the late row is made
LABEL = {'bits': '位图墙', 'built': '建筑墙', 'late': '后建墙', 'enemy move': '敌堵移动', 'enemy attack': '敌堵攻移'}


def _key(s):
    return s.title().replace(' ', '')


def mission():
    m = Mission(name='CampBlock', map=probe_block, facts={})
    for lane in ('bits', 'built', 'late'):
        m.put(IFV, f'{lane} start', role=f'{lane} unit', name=f'UNIT - CNV Block {_key(lane)} Unit')
    m.put(FOOT, 'late start', 80.0, 0.0, role='late foot', name='UNIT - CNV Block Late Foot')    # foot's soldier
    x0, y0 = m.site('built wall')
    for k, (x, y) in enumerate(probe_block.ROW['built']):
        m.put(WALL, 'built wall', x - x0, y - y0, name=f'UNIT - CNV Block Built Wall {k}',
              role='built wall' if k == 0 else '')                  # a role publishes the template (counted)
    for lane in ('enemy move', 'enemy attack'):
        m.put(TANK, f'{lane} start', role=f'{lane} unit', name=f'UNIT - CNV Block {_key(lane)} Unit')
        for k, dy in enumerate((-30.0, 30.0)):
            m.put(PLUG, f'{lane} plug', 0, dy, side='s1', angle=90.0, role=f'{lane} plug {k + 1}',
                  name=f'UNIT - CNV Block {_key(lane)} Plug {k + 1}')
    return m


def _go(m, t, lane, kind='move'):
    wp = f'Test Block {_key(lane)} Goal'
    t.waypoints[wp] = m.site(f'{lane} goal')
    return m.order(kind, [m.role(f'{lane} unit').name], wp, crew=f'Block{_key(lane)}')


def _scored(m, t, lane):
    """Latched (sampling misses a pass): 1 once the lane's unit has been by the far gap, 10 once it has been at the
    goal -- 11 went round, 10 went straight through."""
    counter, unit = f'CNV_Block_{_key(lane)}', m.role(f'{lane} unit').name
    t.counters.append((counter, LABEL[lane]))
    for k, (site, half, n) in enumerate(((f'{lane} gap', 140.0, 1), (f'{lane} goal', 100.0, 10))):
        area = f'Test Block {_key(site)}'
        t.areas[area] = square(*m.site(site), half)
        t.scripts.append(Script(f'Test - {counter} {k}', [('NAMED_INSIDE_AREA', unit, area)],
                                [('INCREMENT_COUNTER', n, counter)], once=True))


def wall(m):
    t = Test()
    order = [('MAP_REVEAL_ALL_PERM', m.player('p1')), ('SET_MILLISECOND_TIMER', 'Test Block Late', LATE)]
    for lane in ('bits', 'built', 'late'):
        order += _go(m, t, lane)
        _scored(m, t, lane)
    make = []
    for k, xy in enumerate(probe_block.ROW['late']):
        wp = f'Test Block Late {k}'
        t.waypoints[wp] = xy
        make.append(('CREATE_NAMED_ON_TEAM_AT_WAYPOINT', f'UNIT - CNV Block Late Wall {k}', WALL, m.team('p1'), wp))
    t.scripts.insert(0, Script('Test - go', [], order))
    t.scripts.append(Script('Test - late wall', [('TIMER_EXPIRED', 'Test Block Late')], make))
    t.bench = [('bench_watch', dict(seconds=60, every=3, sheet=False, lines=3))]
    t.expect = [('位图墙', 0, 'ever==', 11, 60)]          # the control goes round: the rest are read, not judged
    return t


def made(m):
    """wall's late lane again, with how many of its structures stand (does the script make them; capped at 8), and
    the built row's count for the same reading."""
    t = wall(m)
    t.counters = [c for c in t.counters if c[1] == LABEL['late']]
    t.scripts = [s for s in t.scripts if 'Bits' not in s.name and 'Built' not in s.name]
    for lane in ('late', 'built'):
        xs = [x for x, _ in probe_block.ROW[lane]]
        y = probe_block.ROW[lane][0][1]
        area = f'Test Block {_key(lane)} Row'
        t.areas[area] = [(xs[0] - 20, y - 40), (xs[-1] + 20, y - 40), (xs[-1] + 20, y + 40), (xs[0] - 20, y + 40)]
        counted(f'Test Block {_key(lane)} Walls', f'{LABEL[lane]}座数', t, template=WALL, area=area)
    t.expect = []
    return t


def foot(m):
    """The late row made first (LATE), then -- AFTER -- the late lane's IFV and a soldier beside it ordered to the
    goal: is a structure made in the run in a new order's way, for a vehicle and for infantry (docs/engine/pathing.md
    6). Counters as wall's: 11 went round by the gap, 10 straight through."""
    t = Test()
    make = []
    for k, xy in enumerate(probe_block.ROW['late']):
        wp = f'Test Block Late {k}'
        t.waypoints[wp] = xy
        make.append(('CREATE_NAMED_ON_TEAM_AT_WAYPOINT', f'UNIT - CNV Block Late Wall {k}', WALL, m.team('p1'), wp))
    t.scripts.append(Script('Test - late wall', [], [('MAP_REVEAL_ALL_PERM', m.player('p1'))] + make))
    t.scripts.append(Script('Test - wait', [], [('SET_MILLISECOND_TIMER', 'Test Block After', AFTER)]))
    wp = 'Test Block Late Goal'
    t.waypoints[wp] = m.site('late goal')
    order = m.order('move', [m.role('late unit').name], wp, crew='BlockLate') + \
        m.order('move', [m.role('late foot').name], wp, crew='BlockFoot')
    t.scripts.append(Script('Test - go', [('TIMER_EXPIRED', 'Test Block After')], order))
    _scored(m, t, 'late')
    counter = 'CNV_Block_Foot'
    t.counters.append((counter, '后建墙步兵'))
    for k, (site, half, n) in enumerate((('late gap', 140.0, 1), ('late goal', 100.0, 10))):
        t.scripts.append(Script(f'Test - {counter} {k}', [('NAMED_INSIDE_AREA', m.role('late foot').name,
                                                           f'Test Block {_key(site)}')],
                                [('INCREMENT_COUNTER', n, counter)], once=True))
    t.bench = [('bench_watch', dict(seconds=60, every=3, sheet=False, lines=2))]
    t.expect = []
    return t


def enemy(m):
    t = Test()
    order = [('MAP_REVEAL_ALL_PERM', m.player('p1'))]
    for lane, kind in (('enemy move', 'move'), ('enemy attack', 'attack_move')):
        order += _go(m, t, lane, kind)
        _scored(m, t, lane)
    counted('Test Block Plug Hp', '敌车血量', t, health=m.role('enemy attack plug 1').name)
    t.scripts.insert(0, Script('Test - go', [], order))
    t.bench = [('bench_watch', dict(seconds=90, every=3, sheet=False, lines=3))]
    t.expect = []
    return t


def plugs(m):
    """How the move lane's tank got through the plug: its counter and both its MCVs' health."""
    t = Test()
    order = [('MAP_REVEAL_ALL_PERM', m.player('p1'))] + _go(m, t, 'enemy move')
    _scored(m, t, 'enemy move')
    for k in (1, 2):
        counted(f'Test Block Move Plug {k} Hp', f'敌车{k}血量', t, health=m.role(f'enemy move plug {k}').name)
    t.scripts.insert(0, Script('Test - go', [], order))
    t.bench = [('bench_watch', dict(seconds=40, every=2, sheet=False, lines=3))]
    t.expect = []
    return t


# the builds this module makes and their checks (cnv/registry.py)
MISSION = {'engine_block': mission}
CHECKS = {'engine_block': {'wall': wall, 'made': made, 'foot': foot, 'enemy': enemy, 'plugs': plugs}}
