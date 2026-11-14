"""Retail-campaign actions, batch 3 (round 213; the gaps of `inventory_retail.py --part 脚本动作`). Mission on
maps/probe_border.py as checks/engine_acts.py (its SLOT places, clear of probe_range's lanes and start); enemies on
Soviet_4. Nobody here is an enemy unit, so nobody fires unless told. What the simulator predicts is in brackets.

  tel     teleport: crew Tel (three tanks, 60 apart) MOVE_TEAM_TO 'tel go' (400 east) at 1 s, TEAM_TELEPORT_TO_WAYPOINT
               'tel to' (700 south of where they stood) at 2 s.
          garrison: crew Gar (six conscripts) TEAM_GARRISON_SPECIFIC_BUILDING the player's Bullfrog 'gfrog' (five
               places, 300 east) at 2 s.
          ref: crew RefT (one conscript 'refm' at M); the player's tanks 'refb' (named, 250 west of M), crew CA's
               unnamed one (300 east), crew CC's unnamed one (400 south); TEAM_SET_PLAYERS_NEAREST_UNIT_OF_TYPE_TO_
               REFERENCE(tank, RefT, ref) at 3 s and 6 s, NAMED_DELETE(ref) at 4 s and 7 s.
          acquire: the player's 'aaq' and 'aaq0' (tanks) 210 from a Soviet_4 power plant each; UNIT_ALLOW_AI_AUTOACQUIRE
               (aaq, 1) at 2 s.
          cap: PLAYER_SET_MONEY(Player_1, 1000) at the start; PLAYER_SET_MONEY_CAP 3000 at 2 s; PLAYER_GIVE_MONEY 5000 at
               3 s; cap 500 at 5 s; PLAYER_SET_MONEY 10000 at 7 s; cap 0 at 9 s; give 100 at 10 s; set 20000 at 12 s.
          钱 = Player_1's money
          位 (every frame) = Tel's tanks in 'tel to' (ones) + in 'tel go' (tens) + Gar's men ENCLOSED (hundreds)
          旗 (every frame) = 1 refb alive 2 CA has units 4 CC has units 8 NAMED_ATTACKED_BY_OBJECTTYPE(aplant, tank)
            16 (aplant0, tank)
          [simulator, INFERRED: 位 0 -> 3 at 2 s (teleported, the move dropped as UNIT_TELEPORT_TO_WAYPOINT's) -> 503
          (five walk in, the room asked as NAMED_GARRISON_SPECIFIC_BUILDING); 旗 7 -> 6 at 4 s (the nearest of the
          player's tanks to RefT's middle, named or not: refb) -> 4 at 7 s (CA's next) -> +8 from ~3 s (aaq takes the
          plant as TEAM_ALLOW_AI_AUTOACQUIRE's member); 钱 1000 -> 3000 at 3 s (the give capped) -> 500 at 5 s ->
          500 at 7 s -> 20000 at 12 s (cap 0 = none) -- the cap's every step a guess]
  BENCH 11-13 (round 213, run_queue, CampActsTTel_mcp_1113_203544; tests/test_simbench.py test_acts_tel_as_the_bench):
    钱 / 位 / 旗  s1 1000 3 15 | s2 6000 3 15 | s3 6000 3 14 | s4 6000 103 14 | s5 6000 203 14 | s6 10000 303 12 |
    s7 10000 403 12 | s8 10000 503 12 | s9-s10 10100 503 12 | s11-s31 20000 503 12. The bench's seconds run 1-2 s
    ahead. Against the prediction: the money cap holds no script's money (the give over the cap, the cap under the
    money, the set over it: all kept -- simulator: recorded, unused; what it caps not benched, inventory NOTES); the
    walk-in garrison put nobody in on the simulator (a transport was only walked to) -- on the bench five of six went
    in, one a second (fixed: simgarrison walks into a transport as into a house, the room asked; the simulator's
    first one goes in ~2 s later than the bench's, not chased). Teleport (the move dropped), the reference (named
    counted, nearest the team's middle: refb, then CA) and UNIT_ALLOW_AI_AUTOACQUIRE as predicted.
"""
from maps import probe_border
from parts import Mission, Script, Test, square, status
import checks.engine_scripts8 as s8

TANK, PLANT, MAN, FROG = 'AlliedAntiVehicleVehicleTech1', 'SovietPowerPlant', 'SovietAntiInfantryInfantry', \
    'SovietAntiAirShip'
O = (1300.0, 4300.0)                            # probe_border's 'stop row'
RUN = 30.0
TEL, TEL_GO, TEL_TO = (600.0, 4000.0), (1000.0, 4000.0), (600.0, 4700.0)
GAR, FROGAT = (1400.0, 4000.0), (1700.0, 4000.0)
M = (2200.0, 4000.0)
REFB, CA, CC = (M[0] - 250.0, M[1]), (M[0] + 300.0, M[1]), (M[0], M[1] + 400.0)
AAQ = {'aaq': (3000.0, 4000.0), 'aaq0': (3800.0, 4000.0)}
REF = 'UNITRef - CNV Act3 Nearest'


def _n(part):
    return f'UNIT - CNV Act3 {part.title()}'


def _unit(m, role, side, template, x, y, crew=None, named=True):
    props = {'originalOwner': m.crew(crew, side=side)} if crew else {}
    m.put(template, 'stop row', x - O[0], y - O[1], side=side, angle=0.0 if side == 'p1' else 3.1416,
          name=_n(role) if named else '', role=role, props=props)


def mission():
    m = Mission(name='CampActsT', map=probe_border, units=[], facts={})
    m.spawns |= {TANK, PLANT, MAN, FROG}
    for k in range(3):
        _unit(m, f'tel {k}', 'p1', TANK, TEL[0], TEL[1] - 60.0 + 60.0 * k, crew='Tel')
    for spot, at in (('tel go', TEL_GO), ('tel to', TEL_TO)):
        m.waypoint(spot, f'Test Act3 {spot.title()}', 'stop row', at[0] - O[0], at[1] - O[1])
    for k in range(6):
        _unit(m, f'gar {k}', 'p1', MAN, GAR[0] - 90.0 + 35.0 * k, GAR[1], crew='Gar')
    _unit(m, 'gfrog', 'p1', FROG, *FROGAT)
    _unit(m, 'refm', 'p1', MAN, *M, crew='RefT')
    _unit(m, 'refb', 'p1', TANK, *REFB)
    _unit(m, 'ref a', 'p1', TANK, *CA, crew='CA', named=False)
    _unit(m, 'ref c', 'p1', TANK, *CC, crew='CC', named=False)
    for role, (x, y) in AAQ.items():
        _unit(m, role, 'p1', TANK, x, y)
        _unit(m, 'aplant' + role[3:], 's4', PLANT, x + 210.0, y)
    return m


def tel(m):
    t = Test()
    p1 = m.player()
    t.areas['Test Act3 To'] = square(*TEL_TO, 150.0)
    t.areas['Test Act3 Go'] = square(*TEL_GO, 150.0)
    t.scripts.append(Script('Test - Act3 start', [], [('PLAYER_SET_MONEY', p1, 1000)]))
    pick = ('TEAM_SET_PLAYERS_NEAREST_UNIT_OF_TYPE_TO_REFERENCE', TANK, m.teams['RefT'], REF)
    s8.at(t, 'one', 1.0, [('MOVE_TEAM_TO', m.teams['Tel'], m.mark('tel go'))])
    s8.at(t, 'two', 2.0, [('TEAM_TELEPORT_TO_WAYPOINT', m.teams['Tel'], m.mark('tel to')),
                          ('TEAM_GARRISON_SPECIFIC_BUILDING', m.teams['Gar'], _n('gfrog')),
                          ('UNIT_ALLOW_AI_AUTOACQUIRE', _n('aaq'), 1),
                          ('PLAYER_SET_MONEY_CAP', p1, 3000)])
    s8.at(t, 'three', 3.0, [pick, ('PLAYER_GIVE_MONEY', p1, 5000)])
    s8.at(t, 'four', 4.0, [('NAMED_DELETE', REF)])
    s8.at(t, 'five', 5.0, [('PLAYER_SET_MONEY_CAP', p1, 500)])
    s8.at(t, 'six', 6.0, [pick])
    s8.at(t, 'seven', 7.0, [('NAMED_DELETE', REF), ('PLAYER_SET_MONEY', p1, 10000)])
    s8.at(t, 'nine', 9.0, [('PLAYER_SET_MONEY_CAP', p1, 0)])
    s8.at(t, 'ten', 10.0, [('PLAYER_GIVE_MONEY', p1, 100)])
    s8.at(t, 'twelve', 12.0, [('PLAYER_SET_MONEY', p1, 20000)])
    t.counters.append(('CNV_Act3_M', '钱'))
    t.scripts.append(Script('Test - CNV_Act3_M', [], [('SET_PLAYER_MONEY_TO_COUNTER', p1, 'CNV_Act3_M')], once=False))
    tanks = [_n(f'tel {k}') for k in range(3)]
    s8.total(t, 'CNV_Act3_Where', '位', [(1, ('NAMED_INSIDE_AREA', u, 'Test Act3 To')) for u in tanks]
             + [(10, ('NAMED_INSIDE_AREA', u, 'Test Act3 Go')) for u in tanks]
             + [(100, ('UNIT_HAS_OBJECT_STATUS', _n(f'gar {k}'), status('ENCLOSED'))) for k in range(6)])
    s8.total(t, 'CNV_Act3_Flags', '旗', [
        (1, ('NAMED_NOT_DESTROYED', _n('refb'))), (2, ('TEAM_HAS_UNITS', m.teams['CA'])),
        (4, ('TEAM_HAS_UNITS', m.teams['CC'])),
        (8, ('NAMED_ATTACKED_BY_OBJECTTYPE', _n('aplant'), TANK)),
        (16, ('NAMED_ATTACKED_BY_OBJECTTYPE', _n('aplant0'), TANK))])
    s8.watch(t, RUN)
    return t


MISSION = {'engine_acts_tel': mission}
CHECKS = {'engine_acts_tel': {'tel': tel}}
