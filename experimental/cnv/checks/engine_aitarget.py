"""Engine probe: which of the player's structures an AI attack team goes for first (missions/aitarget_bench.py).

  a  步兵在家 / 到近厂 / 到远厂   Peacekeepers of s1 within 450 of the AI's base, within 300 of the near (defended)
                                  power plant, within 300 of the far (undefended) one -- once a second for 60 s
                                  after the wake

The first of 到近厂 / 到远厂 to go above 0 is the reading (afterwards RAMPAGE may take the team on to the other).
The model (RA3-EngineModel ra3model/ai/targets.py): aitargetsafe (SafestToGroundStructureHeuristic, ThreatToGround)
-> far; aitargetnear (ClosestStructureHeuristic, Distance) -> near. The expectation says the model's pick; a FAIL
is a reading too.

读数
Bench 2026-11-06 aitargetsafe a (CampAISafeA, one run): PASS 2 of 2. 步兵在家 4 -> 2 @ s28, 0 @ s30; 到远厂 3 @ s35,
  4 s36-s60, 2 / 1 / 0 @ s61-63 (the plant down, RAMPAGE on); 到近厂 1 @ s69, 4 @ s72. The safest structure first,
  as the model; the team left ~15 s later than with SimpleAttack (not modelled: DefenseAvoidanceAttack's start).
Bench 2026-11-06 aitargetnear a (CampAINearestA): PASS 2 of 2. 到近厂 2 @ s13 (步兵在家 still 4: the two squares
  touch), 4 @ s14-21, shot down 3 / 2 / 1 / 0 by s35 (the turrets); 到远厂 0 all 76 s. The nearest first, as the
  model.
Bench 2026-11-06 aitargetidle5 a (CampAIIdle5A): PASS 2 of 2. DefenseAvoidanceAttack with MaxTeamIdleTime 5s (a
  flattened copy of StandardMicroManager_MEDIUM; the type cannot be inherited from). 步兵在家 4 -> 3 @ s17, 0 @ s21;
  到远厂 1 @ s22, 4 s26-s41, 3 @ s42, 0 from s43; 到近厂 1 @ s51 (RAMPAGE on). The far plant first, as aitargetsafe,
  ~11 s earlier (s28 -> s17 leaving, s35 -> s22 arriving).
Bench 2026-11-06 aitargetidle30 a (CampAIIdle30A): PASS 2 of 2. Same with MaxTeamIdleTime 30s. 步兵在家 4 -> 3 @ s28,
  0 @ s30; 到远厂 3 @ s35, 4 s36-s60, 2 @ s61, 0 from s63; 到近厂 2 @ s70, 4 @ s73. Identical to aitargetsafe (15 s
  default): 15 s -> 30 s changes nothing, so the wait is not (only) the idle release.
Bench 2026-11-06 aitargetflank a (CampAIFlankA): PASS 2 of 2. SafestToGroundStructureHeuristic + FlankAttack, default
  micro manager. 步兵在家 4 -> 3 @ s25, 0 @ s26; 到远厂 1 @ s58, 3 @ s59, 4 from s61; 到近厂 0 all 76 s. The far plant
  first, but ~23 s later than DefenseAvoidanceAttack (s35) -- a longer way round, or a later start.
Bench 2026-11-07 b (frames from frame 0; 出发帧 = 1000 x last out of the start box + first out):
  aitargetidle5 (two runs)   出发帧 197170, 到达帧 355, 离家帧 280 (the first run had no 离家帧)
  aitargetsafe (two runs)    出发帧 192175, 到达帧 548, 离家帧 443 -- the two runs alike to the frame
  aitargetstill              出发帧 192175, 到达帧 548, 离家帧 443 -- MaxTeamIdleTime and MaxUnitIdleTime 600 s,
                             to the frame as 15 s: neither idle time lets the team go
  Every team leaves the start box 20-25 frames after the wake (frame 150): the first leg goes at once (members with
  no order are idle, 0x8d4e90); the 5 s team then sends the rest at once (straight), the others walk leg by leg.
  The 193 frames at the plant are the DA route's extra walk (RA3-EngineModel tests/test_ai_tactics.py, strict xfail).
"""
from parts import Script, Test, counted, square

LAG = 4.0
AFTER = 60.0
HOME = 'CNV AI Base Area'
NEAR = 'CNV AI Near Plant Area'
FAR = 'CNV AI Far Plant Area'


def a(m):
    t = Test()
    s1 = m.player('s1')
    t.scripts.append(Script('Test - reveal', [], [('MAP_REVEAL_ALL_PERM', m.player('p1'))]))
    t.areas[HOME] = square(*m.site('east base'), 450.0)
    for area, role in ((NEAR, 'near plant'), (FAR, 'far plant')):
        o = m.find(m.role(role).name)
        t.areas[area] = square(o.x, o.y, 300.0)
    (inf,) = m.cnv_units
    counted('CNV_AT_Home', '步兵在家', t, template=inf, area=HOME, player=s1)
    counted('CNV_AT_Near', '到近厂', t, template=inf, area=NEAR, player=s1)
    counted('CNV_AT_Far', '到远厂', t, template=inf, area=FAR, player=s1)
    w = m.facts['wake at']
    end = w + AFTER
    pick = '到远厂' if m.cnv_heuristic.startswith('Safest') else '到近厂'
    t.expect += [('步兵在家', end, '<', 4, end + 1), (pick, 1, 'ever>=', 1, end)]
    t.bench = [('bench_watch', dict(seconds=end + LAG, every=1, sheet=False, lines=len(t.counters)))]
    return t


START = 'CNV AI Start Area'


def b(m):
    """Departure / arrival to the frame (for the 5 s vs 15 s MaxTeamIdleTime gap; check a reads once a second).

      出发帧   1 x frames from frame 0 while all four Peacekeepers stand in a tight box round their start spots
               + 1000 x frames while at least one does (first to leave / last to leave)
      到达帧   frames from frame 0 until the first Peacekeeper is inside the far plant's 300 square (stops then)
      在家     Peacekeepers in the box (a sanity readout)
      离家帧   frames from frame 0 until a Peacekeeper is first outside check a's 450 square round the base
    Both builds walk to the far plant first, so the box's exit lag and the way there cancel in the difference."""
    t = Test()
    s1 = m.player('s1')
    (inf,) = m.cnv_units
    t.scripts.append(Script('Test - reveal', [], [('MAP_REVEAL_ALL_PERM', m.player('p1'))]))
    x, y = m.site('east base')
    t.areas[START] = [(x - 280.0, y - 110.0), (x - 240.0, y - 110.0), (x - 240.0, y + 110.0), (x - 280.0, y + 110.0)]
    o = m.find(m.role('far plant').name)
    t.areas[FAR] = square(o.x, o.y, 300.0)
    has = lambda cmp, n, area: ('PLAYER_HAS_COMPARISON_UNIT_TYPE_IN_TRIGGER_AREA', s1, cmp, n, inf, area)
    t.counters.append(('CNV_AT_Leave', '出发帧'))
    t.scripts += [Script('Test - all home', [has(2, 4, START)], [('INCREMENT_COUNTER', 1, 'CNV_AT_Leave')], once=False),
                  Script('Test - any home', [has(3, 1, START)], [('INCREMENT_COUNTER', 1000, 'CNV_AT_Leave')],
                         once=False)]
    t.counters.append(('CNV_AT_Arrive', '到达帧'))
    t.scripts += [Script('Test - arrived', [has(3, 1, FAR)], [('SET_FLAG', 'Test Arrived', 1)]),
                  Script('Test - on the way', [('FLAG', 'Test Arrived', 0)],
                         [('INCREMENT_COUNTER', 1, 'CNV_AT_Arrive')], once=False)]
    counted('CNV_AT_Box', '在家', t, template=inf, area=START, player=s1)
    t.areas[HOME] = square(x, y, 450.0)
    t.counters.append(('CNV_AT_Out', '离家帧'))
    t.scripts += [Script('Test - out', [has(0, 4, HOME)], [('SET_FLAG', 'Test Out', 1)]),
                  Script('Test - not out', [('FLAG', 'Test Out', 0)], [('INCREMENT_COUNTER', 1, 'CNV_AT_Out')],
                         once=False)]
    end = m.facts['wake at'] + AFTER
    t.expect += [('在家', end, '<', 4, end + 2)]
    t.bench = [('bench_watch', dict(seconds=end + LAG, every=2, sheet=False, lines=len(t.counters)))]
    return t


CHECKS = {k: {'a': a, 'b': b} for k in ('aitargetsafe', 'aitargetnear', 'aitargetidle5', 'aitargetidle30',
                                         'aitargetstill', 'aitargetflank')}
