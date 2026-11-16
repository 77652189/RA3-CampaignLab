"""Engine unit test: CREATE_REINFORCEMENT_TEAM_AT_UNIT_POSITION(team, unit) (A round 253; 31 uses in the 27 retail
missions: j07 makes a civilian garrison team at each of 15 civilian buildings, s08 a Man Cannon's crew at the cannon).
The simulator makes it as CREATE_REINFORCEMENT_TEAM with the named object's place as the waypoint (Sim.reinforce,
Sim.point: INFERRED until this bench). Three calls of the player's template R (A = AlliedAntiInfantryInfantry, min 2
max 3: three made a call, engine_reinf) on Niagara's west field:
  2 s   at HS, a civilian apartment block (AM_Apartments_01, as j07's buildings) 500 east of the field's middle
  12 s  at MV, a Guardian tank placed at the middle and sent 500 north at 0.5 s (there by ~8 s): its place now, or
        where it was placed?
  19 s  at DK, a Guardian 400 west, killed by NAMED_KILL at 17 s: made at a dead unit's place, or not at all?
Counters: 兵A (how many A the player owns), 楼A (A within 250 of HS), 楼内A (A within 60 of HS: inside its
footprint), 远处A (A within 200 of MV's goal).
What the simulator predicts (Sim.reinforce on a grid of SPREAD round the point): 兵A 3 from s2, 6 from s12, 9 from
s19; 楼A 3 from s2; 楼内A 3 (the grid stands on the house; does the game push them out?); 远处A 3 from s12.
"""
import resources
from maps import niagara
from parts import Mission, Test, counted, square
import checks.engine_scripts8 as s8

A, TANK, HOUSE = 'AlliedAntiInfantryInfantry', 'AlliedAntiVehicleVehicleTech1', 'AM_Apartments_01'
SITE = 'west field'
ROWS = {'HS': (HOUSE, 500.0, 0.0, 'civ'), 'MV': (TANK, 0.0, 0.0, 'p1'), 'DK': (TANK, -400.0, 0.0, 'p1')}
GOAL = (0.0, 500.0)
GO, AT_HOUSE, AT_MOVER, KILL, AT_DEAD, RUN = 0.5, 2.0, 12.0, 17.0, 19.0, 26.0


def _n(row):
    return f'UNIT - CNV ReinfAt {row}'


def mission():
    m = Mission(name='CampReinfAt', map=resources.measured(niagara), units=[], facts={})
    m.reinforcement('ReinfAt', [(A, 2, 3)], 'p1', instances=1)
    m.spawns |= {r[0] for r in ROWS.values()}
    for row, (tmpl, dx, dy, side) in ROWS.items():
        m.put(tmpl, SITE, dx, dy, side=side, angle=0.0, name=_n(row), role=row.lower())
    m.waypoint('goal', 'Test ReinfAt Goal', SITE, *GOAL)
    return m


def go(m):
    t = Test()
    team = m.teams['RReinfAt']
    make = lambda row: [('CREATE_REINFORCEMENT_TEAM_AT_UNIT_POSITION', team, _n(row))]  # noqa: E731
    s8.at(t, 'reveal', 0.1, [('MAP_REVEAL_ALL_PERM', m.player('p1'))])
    s8.at(t, 'go', GO, [('MOVE_NAMED_UNIT_TO', _n('MV'), m.mark('goal'))])
    s8.at(t, 'house', AT_HOUSE, make('HS'))
    s8.at(t, 'mover', AT_MOVER, make('MV'))
    s8.at(t, 'kill', KILL, [('NAMED_KILL', _n('DK'))])
    s8.at(t, 'dead', AT_DEAD, make('DK'))
    hx, hy = _site_point('HS')
    t.areas['Test ReinfAt House In'] = square(hx, hy, 60.0)
    t.areas['Test ReinfAt House'] = square(hx, hy, 250.0)
    t.areas['Test ReinfAt Goal'] = square(*m.point('goal'), 200.0)
    counted('CNV_ReinfAt_A', '兵A', t, template=A)
    counted('CNV_ReinfAt_H', '楼A', t, template=A, area='Test ReinfAt House')
    counted('CNV_ReinfAt_HI', '楼内A', t, template=A, area='Test ReinfAt House In')
    counted('CNV_ReinfAt_G', '远处A', t, template=A, area='Test ReinfAt Goal')
    s8.watch(t, RUN)
    return t


def _site_point(row):
    o = niagara.SITES[SITE]
    return o.x + ROWS[row][1], o.y + ROWS[row][2]


MISSION = {'engine_reinfat': mission}
CHECKS = {'engine_reinfat': {'go': go}}      # mod CampReinfAtGo: 15 characters at most
