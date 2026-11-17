"""Retail-campaign actions, batch 7 (round 217): PLAYER_TRANSFER_OWNERSHIP_PLAYER (a05 a09 ...). Mission on
maps/probe_border.py as checks/engine_acts5.py ('stop row' offsets, engine_acts.SLOT spots). What the simulator
predicts is in brackets.

Why again. Round 215's bench (engine_acts_v) saw nothing change hands and guessed Soviet_5 / 6 had no team. They do:
the container's Teams has teamSoviet_5 and teamSoviet_6 (read 11-14 off the container map, mapxml.teams), and a
bare object placed for s5 is on teamSoviet_5 (island.like). Round 215 never asked whether its units were Soviet_5's
before the order. The program (work/re/a217_transfer.md): the handler calls the second player's method with the first
(retail a05 ('Japan_04_Scripted', 'Japan_03') then wakes Japan_03: from, to); it returns at once when the receiver has
no default team, else walks a list of the giver's (read as its teams, members of one kind skipped), moves
them onto the receiver and adds one of the giver's counters to it. Predicted: units on teams move, ones on no team --
Soviet_2's, the container's start-up UNIT_AI_TRANSFER_ALL takes them off every team (sim.skirmish_setup) -- stay.
The bench read the opposite (below): the list is not the map's teams (which list it is: not read further).

  own   xt5 Soviet_5's tank (bare: teamSoviet_5), xc5 Soviet_5's conscript on a crew of its own (C5), xm6 Soviet_6's
        conscript (bare), xm2 Soviet_2's (bare, off its team after the start), xm4 Soviet_4's (bare, never handed).
        1 s: PLAYER_SET_MONEY Player_1 1000, Soviet_5 5000. 4 s: TRANSFER(Soviet_5, Player_1), TRANSFER(Soviet_6,
        Soviet_4). 12 s: TRANSFER(Soviet_2, Player_1).
          主 (every frame) = NAMED_OWNED_BY_PLAYER xt5 s5 1 / p1 2, xc5 s5 4 / p1 8, xm6 s6 16 / s4 32,
            xm2 s2 64 / p1 128, xm4 s4 256
          钱 (every frame) = PLAYER_HAS_CREDITS p1 >= 5000 1, s5 >= 4000 2, s5 < 100 4, p1 >= 1000 8
  [simulator before the bench: 主 341 throughout (no hand-over), 钱 10 from 1 s]
  BENCH 11-14 run 1 (round 217, run_queue): 主 / 钱 s1-s2 341 10 | s3-s10 341 13 | s11-s31 405 13 -- nothing of
    Soviet_5 / 6 changed hands at 4 s, Soviet_2's conscript (off its team) went to Player_1 at 12 s; the money moved
    whole at 4 s (Player_1 >= 5000, Soviet_5 < 100). So the team, not the AI: the second run added xb2 (Soviet_2's,
    put on crew B2 at 2 s), UNIT_AI_TRANSFER(xc5, 1) at 2 s (off its crew, Soviet_5 not woken), 主 512 / 1024 for
    xb2 / xm4 (xm4 was 256) and 钱 16 / 32 / 64 = p1 >= 5900 / 6100, s5 >= 4900.
  BENCH 11-14 run 2 (CampActsXOwn; tests/test_simbench.py test_acts_x_own_as_the_bench): 主 / 钱 s1 1365 74 |
    s2-s9 1369 29 | s10-s31 1433 61. At 4 s xc5 (off its crew) went to Player_1, xt5 (teamSoviet_5) and xm6 stayed;
    at 12 s xm2 went, xb2 (on B2) stayed; Player_1 1000 + 5000 (>= 5900, < 6100), Soviet_5 < 100; at 12 s Soviet_2's
    money too (>= 6100; its starting money not simulated). The simulator after: 1365 / 74 at 1 s, 1369 / 29 at 4 s,
    1433 / 29 at 12 s (sim.Sim.act PLAYER_TRANSFER_OWNERSHIP_PLAYER: owner and money; units with no team only).
"""
from maps import probe_border
from parts import Mission, Test
import checks.engine_scripts8 as s8

TANK, MAN = 'AlliedAntiVehicleVehicleTech1', 'SovietAntiInfantryInfantry'
O = (1300.0, 4300.0)                            # probe_border's 'stop row'
RUN = 30.0
AT = {'xt5': (600.0, 4000.0), 'xc5': (2200.0, 4000.0), 'xm6': (3800.0, 4000.0), 'xm2': (600.0, 4700.0),
      'xb2': (2200.0, 4700.0), 'xm4': (3800.0, 4700.0)}
GE, LT = 3, 0                                   # comparisons (sim.CMP): >=, <


def _n(part):
    return f'UNIT - CNV Act7 {part.title()}'


def mission():
    m = Mission(name='CampActsX', map=probe_border, units=[], facts={})
    m.spawns |= {TANK, MAN}
    m.crew('B2', side='s2')                     # xb2 joins it at 2 s (after the container's start-up hand-over)
    for role, (x, y) in AT.items():
        side = 's' + role[-1]
        props = {'originalOwner': m.crew('C5', side='s5')} if role == 'xc5' else {}
        m.put(TANK if role == 'xt5' else MAN, 'stop row', x - O[0], y - O[1], side=side, angle=3.1416,
              name=_n(role), role=role, props=props)
    return m


def own(m):
    t = Test()
    p1, s2, s4, s5, s6 = (m.player(s) for s in ('p1', 's2', 's4', 's5', 's6'))
    s8.at(t, 'o1', 1.0, [('PLAYER_SET_MONEY', p1, 1000), ('PLAYER_SET_MONEY', s5, 5000)])
    s8.at(t, 'o2', 2.0, [('UNIT_AI_TRANSFER', _n('xc5'), 1), ('UNIT_SET_TEAM', _n('xb2'), m.teams['B2'])])
    s8.at(t, 'o4', 4.0, [('PLAYER_TRANSFER_OWNERSHIP_PLAYER', s5, p1), ('PLAYER_TRANSFER_OWNERSHIP_PLAYER', s6, s4)])
    s8.at(t, 'o12', 12.0, [('PLAYER_TRANSFER_OWNERSHIP_PLAYER', s2, p1)])
    s8.total(t, 'CNV_Act7_Own', '主', [(w, ('NAMED_OWNED_BY_PLAYER', who, _n(u))) for w, who, u in (
        (1, s5, 'xt5'), (2, p1, 'xt5'), (4, s5, 'xc5'), (8, p1, 'xc5'), (16, s6, 'xm6'), (32, s4, 'xm6'),
        (64, s2, 'xm2'), (128, p1, 'xm2'), (256, s2, 'xb2'), (512, p1, 'xb2'), (1024, s4, 'xm4'))])
    s8.total(t, 'CNV_Act7_Cash', '钱', [(w, ('PLAYER_HAS_CREDITS', who, c, n)) for w, who, c, n in (
        (1, p1, GE, 5000), (2, s5, GE, 4000), (4, s5, LT, 100), (8, p1, GE, 1000), (16, p1, GE, 5900), (32, p1, GE, 6100),
        (64, s5, GE, 4900))])
    s8.watch(t, RUN)
    return t


MISSION = {'engine_acts_x': mission}
CHECKS = {'engine_acts_x': {'own': own}}
