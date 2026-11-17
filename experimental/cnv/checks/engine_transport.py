"""Engine line A round 152: a whole team put into a transport or a house by the script, carried, cannoned out, killed
inside. Retail loads its waves this way (a01's Bullfrog and transport waves: CREATE_REINFORCEMENT_TEAM, then the team
put instantly into the vehicle, then the vehicle moves and empties at a waypoint) -- the house is the rarer target.

The data: the Bullfrog (SovietAntiAirShip) has a TransportContain (ContainMax 5, PassengerFilter INFANTRY,
AllowEnemiesInside false, ObjectStatusOfContained UNSELECTABLE ENCLOSED, KillPassengersOnDeath true) and a
targeted eject (Command_ActivateEjectPassengersSpecialPower: SpecialPower_EjectPassengers, TargetType LOCATION,
EjectPassengersSpecialAbilityUpdate StartAbilityRange 1000, TimePerPassenger 0.5 s -- the man cannon throws them at
the spot). The house is retail's AM_Apartments_01 (engine_garrison).

Mission on maps/probe_border.py (level ground), rows west to east from x 700, everyone holding fire (NO_ATTACK).
At LOAD (2 s) every row's team is put into its own object by TEAM_GARRISON_SPECIFIC_BUILDING_INSTANTLY:
  L  the player's Bullfrog + the player's crew TL of six conscripts (one more than ContainMax)
  E  the player's Bullfrog + Soviet_4's crew TE of two (an enemy; Soviet_4 has no script library, its AI asleep)
  H  the civilians' AM_Apartments_01 + the player's crew TH of three
  R  the player's Bullfrog + crew TR of three; at GO (4 s) MOVE_NAMED_UNIT_TO the Bullfrog 1000 east ('far R')
  J  the player's Bullfrog + crew TJ of three; at GO NAMED_USE_COMMANDBUTTON_ABILITY_AT_WAYPOINT eject at 'far J'
     (500 east of the Bullfrog)
  K  the player's Bullfrog + crew TK of three; at GO NAMED_KILL the Bullfrog
Counters ("in" = carrying ENCLOSED):
  装 = L in (ones) + E in (tens) + H in (hundreds)
  乘 = R in (ones) + R's men inside the far R square (tens) + the R Bullfrog there (hundreds)
  跳 = J in (ones) + J's men inside the far J square (tens)
  存 = K alive (ones) + K in (tens)
The prediction (simgarrison's rule for the named action: the script skips the room and the relation; a contained
unit at the container's spot): 装 326, 乘 3 -> 133, 跳 3 -> 30, 存 33 -> 0 (KillPassengersOnDeath).
The simulator before round 152 (the action unknown): 装 0, 乘 0 -> 100, 跳 0, 存 3.

BENCH 11-10 (round 152) `CampTransLoad_mcp_1110_215316` (the bench's seconds ~2 s behind the mission's):
  装 326 from s1: the team's every member in, the room and the relation skipped (six into five places, an enemy's
     two into the player's Bullfrog), the house too.
  乘 3 to s11, 133 from s12: the men ride -- inside the far square with the Bullfrog, ENCLOSED all along.
  跳 3 3 1 0 20 30 at s1-s6: the man cannon throws one every 0.5 s from the press (500 away, inside its reach),
     each out of ENCLOSED at once and down on the spot ~2 s later.
  存 33 to s2, 0 from s3: NAMED_KILL on the Bullfrog kills its passengers (KillPassengersOnDeath) -- unlike a
     house's, who come out alive (engine_garrison).
The simulator (simgarrison's transports, round 152) reads the same, 2 s later: 跳 1 at 5, 20 at 7, 乘 133 at 14,
存 0 at 4. tests/test_simbench.py test_transport_*.
"""
from maps import probe_border
from parts import Mission, Test, square, status
import checks.engine_scripts8 as s8

FROG, MAN, HOUSE = 'SovietAntiAirShip', 'SovietAntiInfantryInfantry', 'AM_Apartments_01'
O = (1300.0, 4300.0)                            # probe_border's 'stop row'
X0 = 700.0
# row -> (the crew's side, its size, the row's y, the container)
ROWS = {'L': ('p1', 6, 3900.0, FROG), 'E': ('s4', 2, 4100.0, FROG), 'R': ('p1', 3, 4300.0, FROG),
        'J': ('p1', 3, 4500.0, FROG), 'K': ('p1', 3, 4700.0, FROG), 'H': ('p1', 3, 3650.0, HOUSE)}
FAR = {'R': 1000.0, 'J': 500.0}
FAR_R = 150.0
LOAD, GO, RUN = 2.0, 4.0, 30.0


def _n(part):
    return f'UNIT - CNV TR {part}'


def mission(name='CampTrans'):
    m = Mission(name=name, map=probe_border, units=[], facts={})
    m.spawns |= {FROG, MAN}
    for row, (side, n, y, box) in ROWS.items():
        kw = {'side': side} if side != 'p1' else {}
        m.put(box, 'stop row', X0 - O[0], y - O[1], angle=0.0, name=_n(f'{row} Box'), role=f'{row} box',
              **({'side': 'civ'} if box == HOUSE else {}))
        c = m.crew(f'T{row}', side=side)
        for k in range(n):
            m.put(MAN, 'stop row', X0 - 100.0 + 40.0 * k - O[0], y - 90.0 - O[1], angle=0.0, name=_n(f'{row} {k}'),
                  role=f'{row} {k}', props={'originalOwner': c}, **kw)
        if row in FAR:
            m.waypoint(f'far {row}', f'CNV TR Far {row}', 'stop row', X0 + FAR[row] - O[0], y - O[1])
    return m


def _men(row):
    return [_n(f'{row} {k}') for k in range(ROWS[row][1])]


def load(m):
    t = Test()
    hold = [('UNIT_CHANGE_OBJECT_STATUS', u, status('NO_ATTACK'), 1)
            for row in ROWS for u in _men(row) + ([_n(f'{row} Box')] if ROWS[row][3] == FROG else [])]
    s8.at(t, 'hold', 0.1, hold + [('MAP_REVEAL_ALL_PERM', m.player('p1'))])
    s8.at(t, 'load', LOAD, [('TEAM_GARRISON_SPECIFIC_BUILDING_INSTANTLY', m.teams[f'T{row}'], _n(f'{row} Box'))
                            for row in ROWS])
    s8.at(t, 'go', GO, [('MOVE_NAMED_UNIT_TO', _n('R Box'), m.mark('far R')),
                        ('NAMED_USE_COMMANDBUTTON_ABILITY_AT_WAYPOINT', _n('J Box'),
                         'Command_ActivateEjectPassengersSpecialPower', m.mark('far J')),
                        ('NAMED_KILL', _n('K Box'))])
    for row in FAR:
        t.areas[f'Test TR Far {row}'] = square(*m.point(f'far {row}'), FAR_R)
    inside = lambda row, w: [(w, ('UNIT_HAS_OBJECT_STATUS', u, status('ENCLOSED'))) for u in _men(row)]  # noqa: E731
    there = lambda row, w: [(w, ('NAMED_INSIDE_AREA', u, f'Test TR Far {row}')) for u in _men(row)]     # noqa: E731
    s8.total(t, 'CNV_TR_Load', '装', inside('L', 1) + inside('E', 10) + inside('H', 100))
    s8.total(t, 'CNV_TR_Ride', '乘', inside('R', 1) + there('R', 10)
             + [(100, ('NAMED_INSIDE_AREA', _n('R Box'), 'Test TR Far R'))])
    s8.total(t, 'CNV_TR_Jump', '跳', inside('J', 1) + there('J', 10))
    s8.total(t, 'CNV_TR_Kill', '存', [(1, ('NAMED_NOT_DESTROYED', u)) for u in _men('K')] + inside('K', 10))
    s8.watch(t, RUN)
    t.expect += [('装', 1, '==', 326), ('乘', 1, '==', 3), ('乘', RUN - 2, '==', 133), ('跳', 1, '==', 3),
                 ('跳', 8, '==', 30), ('存', 1, '==', 33), ('存', 6, '==', 0)]      # bench 11-10 round 152
    return t


MISSION = {'engine_transport': mission}
CHECKS = {'engine_transport': {'load': load}}
