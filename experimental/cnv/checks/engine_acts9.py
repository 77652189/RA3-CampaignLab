"""Retail-campaign actions, batch 9 (round 219): SKIRMISH_AI_TRANSFER_ALL (a01 a05 ... 35 uses). Mission on
maps/probe_border.py as checks/engine_acts7.py ('stop row' offsets, engine_acts.SLOT spots). What the simulator
predicts is in brackets.
The program (work/re/a219_skirmish_transfer.md): the handler runs, for each player named, the same step as
UNIT_AI_TRANSFER_ALL's -- minus the AI wake UNIT_AI_TRANSFER_ALL does after it. That step, switch 1: the members of
the player's map default team (teamSoviet_N) and of every other map team go to the AI's defaultSkirmishTeam; switch
0: the members of defaultSkirmishTeam and the AI's other teams go to the map default team (not back to the crew they
came from). Predicted: 1 empties teamSoviet_5 and the crew C5; 0 puts all three onto teamSoviet_5, Soviet_2's two
(taken off at the start by the container's UNIT_AI_TRANSFER_ALL, sim.skirmish_setup) onto teamSoviet_2; Soviet_6's
(never handed) stays where it is.
  all   s5: a5 b5 (bare: teamSoviet_5), c5 (crew C5); s2: a2 b2 (bare); s6: a6 (bare). 2 s: TRANSFER_ALL(Soviet_5, 1).
        6 s: TRANSFER_ALL(Soviet_5, 0), (Soviet_2, 0), (Soviet_6, 0). Counters = TEAM_COMPARE_NUM_MEMBERS == n:
        队5 teamSoviet_5, 队C5 the crew, 队2 teamSoviet_2, 队6 teamSoviet_6.
  [predicted: 队5 / 队C5 / 队2 / 队6 = 2 1 0 1 at s1, 0 0 0 1 from 2 s, 3 0 2 1 from 6 s]
  BENCH 11-14 (round 219, run_queue; tests/test_simbench.py test_acts_z_all_as_the_bench): s1-s4 0 0 0 1 | s5-s13
    4 0 3 2. Switch 1 as predicted (the bench's s1 is past the 2 s timer). Switch 0: every default team one member
    more than the units sent back -- Soviet_6's too (1 -> 2), never handed: a hidden object each player has on
    defaultSkirmishTeam from the start goes over with them (its PlayerSpellBook, INFERRED: which object not read).
    The simulator after: 2 1 0 1 at 1 s, 0 0 0 1 from 2 s, 4 0 3 2 from 6 s (Sim.hidden_home).
"""
from maps import probe_border
from parts import Mission, Script, Test
import checks.engine_scripts8 as s8

MAN = 'SovietAntiInfantryInfantry'
O = (1300.0, 4300.0)                            # probe_border's 'stop row'
RUN = 12.0
AT = {'a5': (600.0, 4000.0), 'b5': (1400.0, 4000.0), 'c5': (2200.0, 4000.0), 'a2': (600.0, 4700.0),
      'b2': (1400.0, 4700.0), 'a6': (3800.0, 4000.0)}
EQ = 2                                          # TEAM_COMPARE_NUM_MEMBERS' ==


def _n(part):
    return f'UNIT - CNV Act9 {part.title()}'


def mission():
    m = Mission(name='CampActsZ', map=probe_border, units=[], facts={})
    m.spawns |= {MAN}
    for role, (x, y) in AT.items():
        side = 's' + role[-1]
        props = {'originalOwner': m.crew('C5', side='s5')} if role == 'c5' else {}
        m.put(MAN, 'stop row', x - O[0], y - O[1], side=side, angle=3.1416, name=_n(role), role=role, props=props)
    return m


def _members(t, counter, label, team):
    t.counters.append((counter, label))
    t.scripts += [Script(f'Test - {counter} {n}', [('TEAM_COMPARE_NUM_MEMBERS', team, EQ, n)],
                         [('SET_COUNTER', counter, n)], once=False) for n in range(5)]


def all_(m):
    t = Test()
    s2, s5, s6 = (m.player(s) for s in ('s2', 's5', 's6'))
    s8.at(t, 'z2', 2.0, [('SKIRMISH_AI_TRANSFER_ALL', s5, 1)])
    s8.at(t, 'z6', 6.0, [('SKIRMISH_AI_TRANSFER_ALL', p, 0) for p in (s5, s2, s6)])
    for counter, label, team in (('CNV_Act9_T5', '队5', m.team('s5')), ('CNV_Act9_C5', '队C5', m.teams['C5']),
                                 ('CNV_Act9_T2', '队2', m.team('s2')), ('CNV_Act9_T6', '队6', m.team('s6'))):
        _members(t, counter, label, team)
    s8.watch(t, RUN)
    return t


MISSION = {'engine_acts_z': mission}
CHECKS = {'engine_acts_z': {'all': all_}}
