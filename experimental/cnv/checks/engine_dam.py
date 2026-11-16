"""The dolphin's jump told apart from swimming (round 252), and where a bear stands in the opening 0.1 s -- one run.
Mission on maps/probe_dam.py: probe_air with a dry dam across its sea trench (y 3220..3280), so the trench is a south
and a north pool. Everyone holds fire (NO_ATTACK at 0.1 s). What the data predicts in brackets (15 logic frames a
second).
  DJ  AlliedAntiNavalScout (dolphin) in the south pool, NAMED_USE_COMMANDBUTTON_ABILITY_AT_WAYPOINT
      Command_ActivateJumpSpecialPower 250 north at PRESS (3 s), into the north pool over the dam (engine_acts_wet's
      DJ, which a swimmer matched: round 249). WeaponFireSpecialAbilityUpdate, UnpackTime 0, StartAbilityRange 300,
      weapon AlliedAntiNavalScoutJumpWeapon ProjectileSelf at 160 a second (Sim.leap_press). [DJ in the north pool
      ~1.6 s after the press (24 frames)]
  DQ  another dolphin beside it told to MOVE the same 250 north: it cannot swim there. [stays in the south pool]
  BR  SovietScoutInfantry (bear) and CS, an enemy conscript (s4) 60 north of it on the flat at 'air B' -- engine_acts_mix
      RN / C2's pair, no button pressed: does the bear walk up in the frame before NO_ATTACK holds it (round 251: the
      simulator's idle chase walks it to the conscript's feet by frame 15, which put the fitted NONE_TARGET_LAG)?
      [simulator: out of its start square from frame 1, at y >= 1445 by frame 15]
Counters:
  跳 = DJ in its jump square + 10 x DJ in the south pool + 100 x DQ in its jump square + 1000 x DQ in the south pool
  帧 = frames DJ in its jump square (only added to: the reading minus this is the frame it came in)
  熊 = BR in its start square (half 8) + 10 x BR 20..45 north of it + 100 x BR 45..90 north of it (x within 30)
  走 = frames BR out of its start square (only added to)
  BENCH 11-15 (round 252, run_queue; CampDamAll_mcp_1115_204351; tests/test_simbench.py test_dam_all_as_the_bench,
    test_dam_bear_stands_in_the_opening): readings 1-4 1010 0 1 0 | 5-6 1000 0 1 0 | 7 1001 8 1 0 | 8 1001 17 |
    9 1001 25 | 10 1001 34 | 11 1001 44 (熊 1, 走 0 throughout).
    DJ jumped over the dam (two readings in the air: out of the south pool, not yet in its square), DQ stayed in the
    south pool. 帧 grew 8-10 a reading, not 15 (not explained), so the landing frame is not compared. The bear never
    moved: no idle chase in the opening frame (the simulator's walks it up: strict xfail).
"""
from maps import probe_dam
from parts import Mission, Test, square, status
import checks.engine_scripts8 as s8

MAN = 'SovietAntiInfantryInfantry'
BEAR = 'SovietScoutInfantry'
DOLPHIN = 'AlliedAntiNavalScout'
JUMP = 'Command_ActivateJumpSpecialPower'
LAND, SEA = 'air B', 'air sea S'
# row -> (template, x, y, side, site)
ROWS = {'DJ': (DOLPHIN, 2350.0, 3120.0, 'p1', SEA), 'DQ': (DOLPHIN, 2250.0, 3120.0, 'p1', SEA),
        'BR': (BEAR, 4000.0, 1400.0, 'p1', LAND), 'CS': (MAN, 4000.0, 1460.0, 's4', LAND)}
JUMPS = {'DJ': 250.0, 'DQ': 250.0}                 # north
PRESS, RUN = 3.0, 10.0
SQUARE = 30.0                                      # a jump square's half side


def _n(part):
    return f'UNIT - CNV Dam {part}'


def _rect(x0, x1, y0, y1):
    return [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]


def mission():
    m = Mission(name='CampDam', map=probe_dam, units=[], facts={})
    m.spawns |= {r[0] for r in ROWS.values()}
    for row, (tmpl, x, y, side, site) in ROWS.items():
        o = probe_dam.SITES[site]
        m.put(tmpl, site, x - o.x, y - o.y, side=side, angle=0.0, name=_n(row), role=row.lower())
        if row in JUMPS:
            m.waypoint(f'jump {row}', f'CNV Dam Jump {row}', site, x - o.x, y + JUMPS[row] - o.y)
    return m


def all_(m):
    t = Test()
    s8.at(t, 'hold', 0.1, [('UNIT_CHANGE_OBJECT_STATUS', _n(r), status('NO_ATTACK'), 1) for r in ROWS]
          + [('MAP_REVEAL_ALL_PERM', m.player('p1'))])
    s8.at(t, 'press', PRESS, [
        ('NAMED_USE_COMMANDBUTTON_ABILITY_AT_WAYPOINT', _n('DJ'), JUMP, m.mark('jump DJ')),
        ('MOVE_NAMED_UNIT_TO', _n('DQ'), m.mark('jump DQ'))])
    # the by-name areas first (know-how: an object is counted in its first few areas only)
    for row in JUMPS:
        t.areas[f'Test Dam Jump {row}'] = square(*m.point(f'jump {row}'), SQUARE)
    t.areas['Test Dam Pool S'] = _rect(*probe_dam.POOL_S)
    bx, by = ROWS['BR'][1], ROWS['BR'][2]
    t.areas['Test Dam Bear Start'] = square(bx, by, 8.0)
    t.areas['Test Dam Bear Near'] = _rect(bx - 30.0, bx + 30.0, by + 20.0, by + 45.0)
    t.areas['Test Dam Bear Far'] = _rect(bx - 30.0, bx + 30.0, by + 45.0, by + 90.0)
    inside = lambda row, a: ('NAMED_INSIDE_AREA', _n(row), f'Test Dam {a}')  # noqa: E731
    s8.total(t, 'CNV_Dam_Jump', '跳', [(1, inside('DJ', 'Jump DJ')), (10, inside('DJ', 'Pool S')),
                                       (100, inside('DQ', 'Jump DQ')), (1000, inside('DQ', 'Pool S'))])
    s8.frames(t, 'CNV_Dam_Frames', '帧', [inside('DJ', 'Jump DJ')])
    s8.total(t, 'CNV_Dam_Bear', '熊', [(1, inside('BR', 'Bear Start')), (10, inside('BR', 'Bear Near')),
                                       (100, inside('BR', 'Bear Far'))])
    s8.frames(t, 'CNV_Dam_Walk', '走', [('NAMED_OUTSIDE_AREA', _n('BR'), 'Test Dam Bear Start')])
    s8.watch(t, RUN)
    return t


MISSION = {'engine_dam': mission}
CHECKS = {'engine_dam': {'all': all_}}
