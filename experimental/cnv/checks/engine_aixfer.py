"""Engine line A round 150: TEAM_AI_TRANSFER / UNIT_AI_TRANSFER (the program read in work/re/l2_scripts1.md 7: a
computer player's units into its AI's hands -- each set onto the player's AI team and logged in the AI's unit list,
no order cleared; a human player's units: nothing). Retail (a01's wave 3) gives the order and the hand-over in one
script: ATTACK_MOVE_NAMED_UNIT_TO then UNIT_AI_TRANSFER(unit, 1); this probe does the same with a plain move.

Mission on maps/probe_border.py (level ground), rows west to east from x 700 to `far` x 1900 (1200 run):
  A  Soviet_4's crew XA, two Guardians at y 4150 / 4250 (row 4200): MOVE_TEAM_TO(XA, far A) + TEAM_AI_TRANSFER(XA, 1)
  B  Soviet_4's crew XB, one Guardian at y 4700: MOVE_NAMED_UNIT_TO(it, far B) + UNIT_AI_TRANSFER(it, 1)
  C  the player's crew XC, one Guardian at y 4450: MOVE_TEAM_TO(XC, far C) + TEAM_AI_TRANSFER(XC, 1) +
     UNIT_AI_TRANSFER(it, 1)
  D  Soviet_4's crew XD, one Guardian at y 3950: the control (late only): MOVE_TEAM_TO(XD, far D), no hand-over
Soviet_4 has no script library (engine_scripts9 memb4: its placed crews keep their members) and its AI is never
woken (no UNIT_AI_TRANSFER_ALL). Everyone holds fire (NO_ATTACK).
  xfer  all at 1 s, in one script, order first (as retail). D stands (not counted).
          到 = in its row's far square: A's each x1 (0-2), B x4, C x8          [simulator: all kept, 14 at ~s15]
          队 = members: XA's (0-2), XB's x4, XC's x8                         [the notes: A / B onto the AI team -> 8]
          默 = teamSoviet_4's members (Soviet_4's default team)              [0; the AI team being the default one: 3]
  late  the orders at 1 s, the hand-overs at LATE_AT (4 s); D counted (x16 in 到 / 队).
          离 = how many of A's (x1) / B (x4) are out of the 150 square round where they stood
          [simulator before round 150: 离 6 from ~s4, 到 30 at ~s15, 队 30 all along]

BENCH 11-10 (round 150):
  xfer `CampAiXferXfer_mcp_1110_200631`: 到 0 to s13, 8 from s14 (C alone arrives); 队 8 from s1 (the bench's s1 is
    past the 1 s hand-over); 默 0 all 26 s. A computer player's units handed over leave their crew (onto none the
    scripts can name) and drop the order; the player's own: nothing.
  late `CampAiXferLate_mcp_1110_200927`: 离 6 from s1 (A and B had set off), 队 30 to s2, 24 from s3 (A / B off
    their crews at the 4 s hand-over), 到 0 to s13, 24 from s14 (C and the control D arrive; A / B never), 默 0.
    The order is dropped at the hand-over, not refused at the start. sim.py UNIT_AI_TRANSFER branch: off the team
    and Sim.stand; tests/test_simbench.py test_aixfer_*.
"""
from maps import probe_border
from parts import Mission, Script, Test, square, status
import checks.engine_scripts8 as s8

TANK = 'AlliedAntiVehicleVehicleTech1'
O = (1300.0, 4300.0)                            # probe_border's 'stop row'
X0, X1 = 700.0, 1900.0
ROWS = {'A': ('s4', (4150.0, 4250.0)), 'B': ('s4', (4700.0,)), 'C': ('p1', (4450.0,)), 'D': ('s4', (3950.0,))}
FAR_R = {'A': 120.0, 'B': 80.0, 'C': 80.0, 'D': 80.0}
WEIGHT = {'A': 1, 'B': 4, 'C': 8, 'D': 16}
AT, LATE_AT, RUN = 1.0, 4.0, 25.0


def _n(part):
    return f'UNIT - CNV AX {part}'


def mission(name='CampAiXfer'):
    m = Mission(name=name, map=probe_border, units=[], facts={})
    m.spawns |= {TANK}
    for row, (side, ys) in ROWS.items():
        c = m.crew(f'X{row}', side=side)
        kw = {'side': side} if side != 'p1' else {}
        for k, y in enumerate(ys, 1):
            m.put(TANK, 'stop row', X0 - O[0], y - O[1], angle=0.0, name=_n(f'{row} {k}'), role=f'{row} {k}',
                  props={'originalOwner': c}, **kw)
        mid = sum(ys) / len(ys)
        m.waypoint(f'far {row}', f'CNV AX Far {row}', 'stop row', X1 - O[0], mid - O[1])
    return m


def _roles(row):
    return [f'{row} {k}' for k in range(1, len(ROWS[row][1]) + 1)]


def _probe(m, late):
    t = Test()
    rows = list(ROWS) if late else ['A', 'B', 'C']
    every = [r for row in ROWS for r in _roles(row)]
    t.scripts.append(Script('Test - AX hold', [], [('UNIT_CHANGE_OBJECT_STATUS', m.role(r).name, status('NO_ATTACK'), 1)
                                                   for r in every]))
    team = {row: m.teams[f'X{row}'] for row in ROWS}
    ub, uc = m.role('B 1').name, m.role('C 1').name
    orders = [('MOVE_TEAM_TO', team['A'], m.mark('far A')), ('MOVE_NAMED_UNIT_TO', ub, m.mark('far B')),
              ('MOVE_TEAM_TO', team['C'], m.mark('far C'))]
    xfers = [('TEAM_AI_TRANSFER', team['A'], 1), ('UNIT_AI_TRANSFER', ub, 1), ('TEAM_AI_TRANSFER', team['C'], 1),
             ('UNIT_AI_TRANSFER', uc, 1)]
    if late:
        s8.at(t, 'go', AT, orders + [('MOVE_TEAM_TO', team['D'], m.mark('far D'))])
        s8.at(t, 'xfer', LATE_AT, xfers)
    else:                                       # as retail: the order, then the hand-over, in one script
        s8.at(t, 'go', AT, [orders[0], xfers[0], orders[1], xfers[1], orders[2], xfers[2], xfers[3]])
    parts = []
    for row in rows:
        area = f'Test AX Far {row}'
        t.areas[area] = square(*m.point(f'far {row}'), FAR_R[row])
        parts += [(WEIGHT[row], ('NAMED_INSIDE_AREA', m.role(r).name, area)) for r in _roles(row)]
    s8.total(t, 'CNV_AX_Far', '到', parts)
    s8.total(t, 'CNV_AX_Memb', '队', [(WEIGHT[row] * n, ('TEAM_COMPARE_NUM_MEMBERS', team[row], 2, n))
                                     for row in rows for n in range(1, len(ROWS[row][1]) + 1)])
    p4 = m.player('s4')
    t.counters.append(('CNV_AX_Default', '默'))
    t.scripts += [Script(f'Test - AX default {n}', [('TEAM_COMPARE_NUM_MEMBERS', f'{p4}/team{p4}', 2, n)],
                         [('SET_COUNTER', 'CNV_AX_Default', n)], once=False) for n in range(6)]
    if late:
        away = []
        for row in ('A', 'B'):
            for r in _roles(row):
                area = f'Test AX Home {r}'
                b = next(o for o in m.objects if o.name == m.role(r).name)
                t.areas[area] = square(b.x, b.y, 150.0)
                away.append((WEIGHT[row], ('NAMED_OUTSIDE_AREA', m.role(r).name, area)))
        s8.total(t, 'CNV_AX_Away', '离', away)
    s8.watch(t, RUN)
    return t


def xfer(m):
    t = _probe(m, late=False)
    t.expect += [('到', RUN - 2, '==', 8), ('队', 1, '==', 8), ('默', 1, '==', 0)]      # bench 11-10 round 150
    return t


def late(m):
    t = _probe(m, late=True)
    t.expect += [('队', 0, '==', 30, 2),('队', 4, '==', 24), ('离', 2, '==', 6), ('到', RUN - 2, '==', 24),
                 ('默', 1, '==', 0)]           # bench 11-10 round 150
    return t


MISSION = {'engine_aixfer': mission}
CHECKS = {'engine_aixfer': {'xfer': xfer, 'late': late}}
