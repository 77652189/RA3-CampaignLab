"""Retail-campaign actions, batch 8 (round 218): what TEAM_HUNT goes for, which switch gates it, NAMED_HUNT on a woken
AI -- round 216's three hypotheses (engine_acts6 hunt). Mission on maps/probe_border.py as checks/engine_acts6.py
('stop row' offsets). What the simulator predicts is in brackets.

Why. Round 216's crew (Soviet_4, both switches 255) went for the tank ~870 east, not the barracks ~1650 west -- the
two were already on opposite sides, but the tank shot back and killed the crew, so it never said whether the hunt
re-picks when its target dies, nor (engine line B, work/re/b186_hunt.md) whether the crew went for the nearest
*object* or for the nearest *structure* and met the tank by auto-acquire. Here the targets are engineers (no weapon)
and every reading is a place: H1 'the nearest hostile object, units too' sends the crew east to e1; H2 'the nearest
structure' west to pb (e1 out of sight behind it); after e1 dies, re-picking the nearest from there goes to e2.

  pick  s4's crew H4 (two conscripts) at (1500, 4400): the player's engineer e1 at (2200, 4400) (700 east), engineer e2
        at (2600, 4800) (1166 from home, 566 from e1), barracks pb at (500, 4400) (1000 west).
  gate  s5's crew H5 at (4600, 4000), set aiTeamBuilder 240 / aiTactical 255 (m.sides); s6's H6 at (4600, 4800), 255 /
        240. Each its own bait 600 west (b5 (4000, 4000), b6 (4000, 4800)): whichever switch gates the hunt, one moves.
  named s3's conscript n3 at (3400, 4400) (the container hands Soviet_3 to its AI at the start) NAMED_HUNT; c3 at
        (3400, 4700), no order (does the woken AI move it anyway).
        2 s: TEAM_ALLOW_AI_AUTOACQUIRE + TEAM_HUNT on H4 / H5 / H6, NAMED_HUNT on n3.
          家 (every frame) = men within 250 of home: H4 (ones) + H5 (tens) + H6 (hundreds) + n3 1000 + c3 10000
          到 (every frame) = H4's men within 300 of pb (ones), of e1's spot (tens), of e2's (hundreds)
          活 (every frame) = alive: e1 1, e2 2, pb 4; attacked by a conscript: e1 8, e2 16, pb 32
          饵 (every frame) = b5 alive 1, b6 alive 2, b5 attacked 4, b6 attacked 8, n3 alive 16, c3 alive 32
  [simulator before the bench: 家 11222 -> 11200 at 8 s (H4 and H5 leave: Sim.tactical reads aiTactical), 到 0 ->
   20 at 11 s (H4 by e1, one order, no re-pick), 活 7 -> 15 at 14 s -> 6 at 16 s (e1 attacked, killed; a dead
   unit's 'attacked' reads false), 饵 51 -> 55 at 12 s -> 50 at 14 s (b5 attacked, killed); n3 never moves]
  BENCH 11-14 (round 218, run_queue once, CampActsYHunt; tests/test_simbench.py test_acts_y_hunt_as_the_bench):
    家 / 到 / 活 / 饵  s1-s5 11222 0 7 51 | s6-s8 11200 0 7 51 | s9-s10 11200 20 7 51 | s11-s12 11200 20 7 55 |
    s13-s14 11200 20 15 54 | s15-s19 11200 20 14 54 | s20 11200 20 14 50 | s21 11200 220 14 50 | s22-s25 11200 220 6
    50 | s26-s28 11200 210 22 50 | s29-s30 11200 200 20 58 | s31-s35 11200 200 20 56 | s36-s37 11200 200 4 56 | s38
    11200 100 4 48 | s39-s42 11200 0 4 48 | s43-s44 11200 10 4 48 | s45 11200 20 4 48 | s46 11200 10 4 48 | s47-s48
    11200 0 4 48 | s49-s50 11201 0 4 48 | s51-s58 11202 0 4 48 | s59 11201 0 4 48 | s60-s61 11200 0 4 48.
    Gate: H4 and H5 left at s6, H6 (aiTactical 240) never -- aiTactical. Pick: H4 by e1 at s9 (east, the nearest
    object, a unit), e1 attacked s13, dead s15; by e2 at s21 (the two areas overlap: 220), e2 attacked s26, dead s29;
    out of e2's at s38-s39, by e1's spot s43-s46, past home s49-s59 westwards (pb the one left). H5: b5 attacked s11,
    dead s13, then b6 (800 on) attacked s29, dead s31. NAMED_HUNT: Soviet_3's n3 (its AI woken by the container)
    never left home, nor c3. New: a dead engineer's NAMED_ATTACKED_BY_OBJECTTYPE stays true 7 s (s15-s21, s13-s19,
    s29-s35, s31-s37) while NAMED_NOT_DESTROYED is false at once -- its body lingers (the simulator's linger for it
    is shorter: not fixed here, a unit-data matter). After the bench the simulator (Sim.hunt_due, HUNT_REPICK 45)
    reads each step a second later: 11200 at 8, 220 at 22, e2 attacked 27, dead 30, b6 attacked 30, 0 at 39, home
    50 / 52 / 60 / 61.
"""
from maps import probe_border
from parts import Mission, Test, square
import checks.engine_scripts8 as s8

MAN, ENGINEER, BARRACKS = 'SovietAntiInfantryInfantry', 'AlliedEngineer', 'AlliedBarracks'
O = (1300.0, 4300.0)                            # probe_border's 'stop row'
RUN = 60.0
HOME = {'H4': (1500.0, 4400.0), 'H5': (4600.0, 4000.0), 'H6': (4600.0, 4800.0), 'n3': (3400.0, 4400.0),
        'c3': (3400.0, 4700.0)}
PLAYER = {'e1': (ENGINEER, 2200.0, 4400.0), 'e2': (ENGINEER, 2600.0, 4800.0), 'pb': (BARRACKS, 500.0, 4400.0),
          'b5': (ENGINEER, 4000.0, 4000.0), 'b6': (ENGINEER, 4000.0, 4800.0)}
SIDES = {'s5': {'aiTeamBuilder': 240, 'aiTactical': 255}, 's6': {'aiTeamBuilder': 255, 'aiTactical': 240}}


def _n(part):
    return f'UNIT - CNV Act8 {part.title()}'


def _put(m, role, side, template, x, y, crew=None):
    props = {'originalOwner': m.crew(crew, side=side)} if crew else {}
    m.put(template, 'stop row', x - O[0], y - O[1], side=side, angle=0.0 if side == 'p1' else 3.1416,
          name=_n(role), role=role, props=props)


def mission():
    m = Mission(name='CampActsY', map=probe_border, units=[], facts={})
    m.spawns |= {MAN, ENGINEER, BARRACKS}
    for side, props in SIDES.items():
        m.sides[side] = dict(m.sides.get(side, {}), **props)
    for key, (x, y) in HOME.items():
        if key.startswith('H'):
            for k in range(2):
                _put(m, f'{key} {k}', 's' + key[1], MAN, x, y - 30.0 + 60.0 * k, crew=key)
        else:
            _put(m, key, 's3', MAN, x, y)
    for role, (template, x, y) in PLAYER.items():
        _put(m, role, 'p1', template, x, y)
    return m


def men(key):
    return [_n(f'{key} {k}') for k in range(2)] if key.startswith('H') else [_n(key)]


def hunt(m):
    t = Test()
    for key, at in HOME.items():
        t.areas[f'Test Act8 Home {key}'] = square(*at, 250.0)
    for role in ('pb', 'e1', 'e2'):
        t.areas[f'Test Act8 By {role}'] = square(*PLAYER[role][1:], 300.0)
    s8.at(t, 'h2', 2.0, [a for crew in ('H4', 'H5', 'H6') for a in (('TEAM_ALLOW_AI_AUTOACQUIRE', m.teams[crew], 1),
                                                                  ('TEAM_HUNT', m.teams[crew]))]
          + [('NAMED_HUNT', _n('n3'))])
    weight = {'H4': 1, 'H5': 10, 'H6': 100, 'n3': 1000, 'c3': 10000}
    s8.total(t, 'CNV_Act8_Home', '家', [(w, ('NAMED_INSIDE_AREA', u, f'Test Act8 Home {k}'))
                                        for k, w in weight.items() for u in men(k)])
    s8.total(t, 'CNV_Act8_At', '到', [(w, ('NAMED_INSIDE_AREA', u, f'Test Act8 By {role}'))
                                      for role, w in (('pb', 1), ('e1', 10), ('e2', 100)) for u in men('H4')])
    s8.total(t, 'CNV_Act8_Alive', '活', [(w, ('NAMED_NOT_DESTROYED', _n(r))) for r, w in (('e1', 1), ('e2', 2), ('pb', 4))]
             + [(w, ('NAMED_ATTACKED_BY_OBJECTTYPE', _n(r), MAN)) for r, w in (('e1', 8), ('e2', 16), ('pb', 32))])
    s8.total(t, 'CNV_Act8_Bait', '饵', [(1, ('NAMED_NOT_DESTROYED', _n('b5'))), (2, ('NAMED_NOT_DESTROYED', _n('b6'))),
                                        (4, ('NAMED_ATTACKED_BY_OBJECTTYPE', _n('b5'), MAN)),
                                        (8, ('NAMED_ATTACKED_BY_OBJECTTYPE', _n('b6'), MAN)),
                                        (16, ('NAMED_NOT_DESTROYED', _n('n3'))), (32, ('NAMED_NOT_DESTROYED', _n('c3')))])
    s8.watch(t, RUN)
    return t


MISSION = {'engine_acts_y': mission}
CHECKS = {'engine_acts_y': {'hunt': hunt}}
