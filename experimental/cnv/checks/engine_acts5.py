"""Retail-campaign actions, batch 5 (round 215; the gaps of `inventory_retail.py --part 脚本动作`): model conditions by
number, a player's whole hand-over, the player's own auto-acquire, a move to the nearest of a type, a guard from a
point. Mission on maps/probe_border.py as checks/engine_acts4.py ('stop row' offsets, enemies on Soviet_4 / 5, nobody
fires unless told). What the simulator predicts is in brackets.

  mc    the player's conscripts mc1 / mc2. 1 s: UNIT_SET_MODELCONDITION(mc1, 1, 1), (mc2, 2, 1); 8 s: (mc1, 1, 0),
        (mc2, 3, 1). The number read as USER_<n> (ModelState.xsd's USER_1 .. USER_10; a08's saluting conscripts are
        set 2 off, the conscript's STATE_Saluting is USER_2).
          状 (every frame) = UNIT_HAS_MODELCONDITION mc1 USER_1 1, mc1 USER_2 2, mc2 USER_2 4, mc2 USER_1 8,
            mc2 USER_3 16
  own   Soviet_5's tank xt (210 from Soviet_4's plant xplant) and conscript xm. 6 s: PLAYER_TRANSFER_OWNERSHIP_PLAYER(
        Soviet_5, Player_1) (a05's order: from, to).
  aaq   the player's tank paq 210 from Soviet_4's plant pplant. 2 s: PLAYER_ALLOW_AI_AUTOACQUIRE(Player_1, 1). xt joins
        the player at 6 s: does the player's switch reach a unit it gets later?
          旗 (every frame) = NAMED_OWNED_BY_PLAYER(P1, xt) 1 (P1, xm) 2 + NAMED_ATTACKED_BY_OBJECTTYPE(pplant, tank) 4
            (xplant, tank) 8 + NAMED_NOT_DESTROYED(gfoe) 16
  near  crew Mv (two conscripts at N0); the player's barracks nb (450 south of N0) and fb (650 east). 1 s and 12 s:
        TEAM_MOVE_TO_NEAREST_OBJECT_OF_TYPE(Mv, AlliedBarracks); 10 s: NAMED_DELETE nb.
  guard crew Gd (two tanks); area 'Test Act5 Garea' (800 square), waypoint 'gd from' inside it, 100 in from its north
        edge's middle. 1 s: TEAM_GUARD_AREA_FROM_POSITION(Gd, area, 'gd from'); 15 s: Soviet_4's
        conscript gfoe teleported into the area, 600 south of 'gd from'.
          位 (every frame) = Mv's men by nb (ones) by fb (tens) + Gd's tanks by 'gd from' (hundreds) by the area's
            middle (thousands)
          守 (every frame) = Gd's tanks in the area (ones) + gfoe in the area (tens)
  The second run added: 状 +32 / 64 / 128 = NAMED_OWNED_BY_PLAYER(Soviet_5, mc1 / paq / ym), ym Soviet_6's conscript
  with PLAYER_TRANSFER_OWNERSHIP_PLAYER(Soviet_6, Soviet_5) at 20 s; 守 +100 gfoe attacked by a tank, +1000 gfoe within
  300 of 'gd from'.
  [simulator before the bench: 状 0 (UNIT_SET_MODELCONDITION unknown); 旗 16; 位 0 (both moves unknown); 守 0 -> 10]
  BENCH 11-13 (round 215, run_queue twice, CampActsVActs_mcp_1113_232329 and the next; the same readings both times;
  tests/test_simbench.py test_acts_v_as_the_bench):
    状 / 旗 / 位 / 守  s1-s2 5 20 0 0 | s3 5 20 1 0 | s4 5 20 2 0 | s5 5 20 102 0 | s6 5 20 202 2 | s7-s13 20 20 202 2 |
    s14 20 20 202 12 | s15-s18 20 20 200 12 | s19-s32 20 20 220 12 | s33-s41 20 16 220 12. The bench's seconds run ~1
    behind the scripts' (the 15 s teleport at s14).
    Model condition: n is USER_n (1, 2, 3), 0 clears. Auto-acquire: paq fired on pplant (4). Nearest: Mv to nb, after
    nb's delete and the second order to fb. Guard from position: both tanks to 'gd from' and there to the end, never
    the area's middle; gfoe in the area 600 off was never hit by a tank nor came near, and was dead at s33 (the
    simulator: dead at 36 s, not chased). Hand-over: NOTHING changed hands -- Soviet_5 -> Player_1, Soviet_6 ->
    Soviet_5, nor the other way (Player_1's units never Soviet_5's), so xt's late auto-acquire was never asked
    (handoff hypothesis: Soviet_5 / 6 have no team on this map, TEAMS has p1 / s1 / s4 only).
"""
from maps import probe_border
from parts import Mission, Script, Test, square
import checks.engine_scripts8 as s8

TANK, PLANT, MAN, BARRACKS = 'AlliedAntiVehicleVehicleTech1', 'SovietPowerPlant', 'SovietAntiInfantryInfantry', \
    'AlliedBarracks'
O = (1300.0, 4300.0)                            # probe_border's 'stop row'
RUN = 40.0
MC = {'mc1': (600.0, 4000.0), 'mc2': (600.0, 4700.0)}
PAQ, XT, XM, YM = (1400.0, 4000.0), (3800.0, 4000.0), (3800.0, 4700.0), (4600.0, 4350.0)
N0 = (2800.0, 2100.0)
NB, FB = (N0[0], N0[1] + 450.0), (N0[0] + 650.0, N0[1])
GD, GAREA, GFROM = (3700.0, 2000.0), (4200.0, 2700.0), (4200.0, 2400.0)
GFOE, GFOE_TO = (3000.0, 4350.0), (4200.0, 3000.0)
AREA = 'Test Act5 Garea'


def _n(part):
    return f'UNIT - CNV Act5 {part.title()}'


def _unit(m, role, side, template, x, y, crew=None):
    props = {'originalOwner': m.crew(crew, side=side)} if crew else {}
    m.put(template, 'stop row', x - O[0], y - O[1], side=side, angle=0.0 if side == 'p1' else 3.1416,
          name=_n(role), role=role, props=props)


def mission():
    m = Mission(name='CampActsV', map=probe_border, units=[], facts={})
    m.spawns |= {TANK, PLANT, MAN, BARRACKS}
    for role, at in MC.items():
        _unit(m, role, 'p1', MAN, *at)
    _unit(m, 'paq', 'p1', TANK, *PAQ)
    _unit(m, 'pplant', 's4', PLANT, PAQ[0] + 210.0, PAQ[1])
    _unit(m, 'xt', 's5', TANK, *XT)
    _unit(m, 'xplant', 's4', PLANT, XT[0] + 210.0, XT[1])
    _unit(m, 'xm', 's5', MAN, *XM)
    _unit(m, 'ym', 's6', MAN, *YM)
    for k in range(2):
        _unit(m, f'mv {k}', 'p1', MAN, N0[0], N0[1] - 30.0 + 60.0 * k, crew='Mv')
        _unit(m, f'gd {k}', 'p1', TANK, GD[0], GD[1] - 40.0 + 80.0 * k, crew='Gd')
    _unit(m, 'nb', 'p1', BARRACKS, *NB)
    _unit(m, 'fb', 'p1', BARRACKS, *FB)
    _unit(m, 'gfoe', 's4', MAN, *GFOE)
    for spot, at in (('gd from', GFROM), ('gfoe to', GFOE_TO)):
        m.waypoint(spot, f'Test Act5 {spot.title()}', 'stop row', at[0] - O[0], at[1] - O[1])
    return m


def acts(m):
    t = Test()
    p1, s5, s6 = m.player(), m.player('s5'), m.player('s6')
    t.areas['Test Act5 Close'] = square(*GFROM, 300.0)
    t.areas[AREA] = square(*GAREA, 400.0)
    t.areas['Test Act5 Nb'] = square(*NB, 250.0)
    t.areas['Test Act5 Fb'] = square(*FB, 250.0)
    t.areas['Test Act5 From'] = square(*GFROM, 150.0)
    t.areas['Test Act5 Mid'] = square(*GAREA, 150.0)
    near = ('TEAM_MOVE_TO_NEAREST_OBJECT_OF_TYPE', m.teams['Mv'], BARRACKS)
    s8.at(t, 'a1', 1.0, [('UNIT_SET_MODELCONDITION', _n('mc1'), 1, 1), ('UNIT_SET_MODELCONDITION', _n('mc2'), 2, 1),
                         near, ('TEAM_GUARD_AREA_FROM_POSITION', m.teams['Gd'], AREA, m.mark('gd from'))])
    s8.at(t, 'a2', 2.0, [('PLAYER_ALLOW_AI_AUTOACQUIRE', p1, 1)])
    s8.at(t, 'a6', 6.0, [('PLAYER_TRANSFER_OWNERSHIP_PLAYER', s5, p1)])
    s8.at(t, 'a8', 8.0, [('UNIT_SET_MODELCONDITION', _n('mc1'), 1, 0), ('UNIT_SET_MODELCONDITION', _n('mc2'), 3, 1)])
    s8.at(t, 'a10', 10.0, [('NAMED_DELETE', _n('nb'))])
    s8.at(t, 'a12', 12.0, [near])
    s8.at(t, 'a20', 20.0, [('PLAYER_TRANSFER_OWNERSHIP_PLAYER', s6, s5)])
    s8.at(t, 'a15', 15.0, [('UNIT_TELEPORT_TO_WAYPOINT', _n('gfoe'), m.mark('gfoe to'))])
    s8.total(t, 'CNV_Act5_Mc', '状', [(w, ('UNIT_HAS_MODELCONDITION', _n(u), c)) for w, u, c in (
        (1, 'mc1', 'USER_1'), (2, 'mc1', 'USER_2'), (4, 'mc2', 'USER_2'), (8, 'mc2', 'USER_1'), (16, 'mc2', 'USER_3'))]
        + [(w, ('NAMED_OWNED_BY_PLAYER', s5, _n(u))) for w, u in ((32, 'mc1'), (64, 'paq'), (128, 'ym'))])
    s8.total(t, 'CNV_Act5_Flags', '旗', [
        (1, ('NAMED_OWNED_BY_PLAYER', p1, _n('xt'))), (2, ('NAMED_OWNED_BY_PLAYER', p1, _n('xm'))),
        (4, ('NAMED_ATTACKED_BY_OBJECTTYPE', _n('pplant'), TANK)),
        (8, ('NAMED_ATTACKED_BY_OBJECTTYPE', _n('xplant'), TANK)),
        (16, ('NAMED_NOT_DESTROYED', _n('gfoe')))])
    mv, gd = [_n(f'mv {k}') for k in range(2)], [_n(f'gd {k}') for k in range(2)]
    s8.total(t, 'CNV_Act5_Where', '位', [(1, ('NAMED_INSIDE_AREA', u, 'Test Act5 Nb')) for u in mv]
             + [(10, ('NAMED_INSIDE_AREA', u, 'Test Act5 Fb')) for u in mv]
             + [(100, ('NAMED_INSIDE_AREA', u, 'Test Act5 From')) for u in gd]
             + [(1000, ('NAMED_INSIDE_AREA', u, 'Test Act5 Mid')) for u in gd])
    s8.total(t, 'CNV_Act5_Guard', '守', [(1, ('NAMED_INSIDE_AREA', u, AREA)) for u in gd]
             + [(10, ('NAMED_INSIDE_AREA', _n('gfoe'), AREA)),
                (100, ('NAMED_ATTACKED_BY_OBJECTTYPE', _n('gfoe'), TANK)),
                (1000, ('NAMED_INSIDE_AREA', _n('gfoe'), 'Test Act5 Close'))])
    s8.watch(t, RUN)
    return t


# Round 280: ATTACK_MOVE_TEAM_TO_NEAREST_OBJECT_OF_TYPE_OF_PLAYER (team, type, player; j04 / j05). s4's crew Am (tanks
# m0 / m1, 1600 apart) to the player's plants: X is nearest their middle, Y m0's, Z m1's, D (s4's own) nearest of all.
# s4's tank TA (crew Ae) to the player's engineer EN, teleported 1560 off a second after the order: followed?
NEAR = {'m0': (1800.0, 1500.0), 'm1': (3400.0, 1500.0), 'X': (2600.0, 2700.0), 'Y': (1800.0, 2700.0),
        'Z': (3600.0, 2800.0), 'D': (2600.0, 1700.0), 'TA': (4400.0, 4000.0), 'EN': (4400.0, 3400.0)}
EN_TO = (3400.0, 4600.0)
ENGINEER = 'AlliedEngineer'


def near_mission():
    m = Mission(name='CampActsNear', map=probe_border, units=[], facts={})
    m.spawns |= {TANK, PLANT, ENGINEER}
    for role, (x, y) in NEAR.items():
        crew = {'m0': 'Am', 'm1': 'Am', 'TA': 'Ae'}.get(role)
        tmpl = TANK if crew else ENGINEER if role == 'EN' else PLANT
        _unit(m, role, 's4' if crew or role == 'D' else 'p1', tmpl, x, y, crew=crew)
    m.waypoint('en to', 'Test Act5 En To', 'stop row', EN_TO[0] - O[0], EN_TO[1] - O[1])
    return m


def near(m):
    """位 = Am's tanks within 400 of X (ones), Y (tens), Z (hundreds); 打 = X attacked by a tank 1, Y 2, Z 4 + TA within
    400 of EN's first place 10, of its second 100 + EN attacked by a tank 1000."""
    t = Test()
    go = 'ATTACK_MOVE_TEAM_TO_NEAREST_OBJECT_OF_TYPE_OF_PLAYER'
    s8.at(t, 'a1', 1.0, [(go, m.teams['Am'], PLANT, m.player()), (go, m.teams['Ae'], ENGINEER, m.player())])
    s8.at(t, 'a2', 2.0, [('UNIT_TELEPORT_TO_WAYPOINT', _n('EN'), m.mark('en to'))])
    for k, at in (('X', NEAR['X']), ('Y', NEAR['Y']), ('Z', NEAR['Z']), ('En', NEAR['EN']), ('Ento', EN_TO)):
        t.areas[f'Test Act5 By {k}'] = square(*at, 400.0)
    s8.total(t, 'CNV_Act5_Near', '位', [(w, ('NAMED_INSIDE_AREA', _n(u), f'Test Act5 By {k}'))
                                        for k, w in (('X', 1), ('Y', 10), ('Z', 100)) for u in ('m0', 'm1')])
    s8.total(t, 'CNV_Act5_Hit', '打', [(w, ('NAMED_ATTACKED_BY_OBJECTTYPE', _n(k), TANK))
                                       for k, w in (('X', 1), ('Y', 2), ('Z', 4), ('EN', 1000))]
             + [(10, ('NAMED_INSIDE_AREA', _n('TA'), 'Test Act5 By En')),
                (100, ('NAMED_INSIDE_AREA', _n('TA'), 'Test Act5 By Ento'))])
    s8.watch(t, RUN)
    return t


def tow(m):
    """TEAM_ATTACK_MOVE_TOWARDS_NEAREST_OBJECT_TYPE (team, type; a03 / s03): the same handler with no player, so any
    owner's. 位 = Am's tanks within 400 of X (ones), Y (tens), Z (hundreds), s4's own D (thousands); 打 = D attacked
    by a tank 1, Y 2."""
    t = Test()
    s8.at(t, 'a1', 1.0, [('TEAM_ATTACK_MOVE_TOWARDS_NEAREST_OBJECT_TYPE', m.teams['Am'], PLANT)])
    for k in 'XYZD':
        t.areas[f'Test Act5 By {k}'] = square(*NEAR[k], 400.0)
    s8.total(t, 'CNV_Act5_Near', '位', [(w, ('NAMED_INSIDE_AREA', _n(u), f'Test Act5 By {k}'))
                                        for k, w in zip('XYZD', (1, 10, 100, 1000)) for u in ('m0', 'm1')])
    s8.total(t, 'CNV_Act5_Hit', '打', [(w, ('NAMED_ATTACKED_BY_OBJECTTYPE', _n(k), TANK)) for k, w in (('D', 1), ('Y', 2))])
    s8.watch(t, RUN)
    return t


MISSION = {'engine_acts_v': mission, 'engine_acts_near': near_mission}
CHECKS = {'engine_acts_v': {'acts': acts}, 'engine_acts_near': {'all': near, 'tow': tow}}
