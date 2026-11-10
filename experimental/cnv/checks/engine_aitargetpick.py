"""Engine probe: which target a team picks (missions/aitargetpick_bench.py) -- AITargetingHeuristic VitalKindOf /
ForbiddenKindOf / HeuristicType EnemyUnit, the TargetHeuristic Priority order, MaxTargets.

  a  到电厂  s1's Guardians within 340 of the player's power plant (FS_POWER), once a second
     到兵营  within 340 of the player's barracks (FS_BARRACKS)
     到坦克  within 340 of the player's Guardian's start spot (a VEHICLE unit)
     在家    in the AI's base (x +-300, y -400..+450 round its centre: every start spot)
All three targets are set to full health every frame, so a team stays at its first pick.

Expected (the mission's facts, the model's guess): the picked target's counter reaches 3 or more by s40 (one of four
may be lost to the player's tank), the others are 0 at s40, 在家 == expect home at s40.

读数
Bench 2026-11-09 (B round 80, run_queue --jobs 2, one run each, all PASS; counters 到电厂 到兵营 到坦克 在家):
  aitpnear  ClosestStructureHeuristic: 到电厂 1 @ s13, 4 from s15 to s55; the rest 0.
  aitpvk    VitalKindOf FS_BARRACKS: 在家 0 from s19, 到兵营 1 @ s22, 4 from s23 to s55; 到电厂 0 throughout.
  aitpfk    VitalKindOf STRUCTURE, ForbiddenKindOf FS_POWER: the same to the second (到兵营 4 from s23).
  aitpunit  HeuristicType EnemyUnit, VitalKindOf VEHICLE: 到坦克 3 @ s14, 4 s15-29, then 3 / 2 (lost to the tank).
  aitpphi   CNVHBarracks Priority 20 + Closest 10: barracks, as aitpvk to the second -- the higher Priority first.
  aitpplo   CNVHBarracks Priority 5 + Closest 10: plant, as aitpnear to the second.
  aitpmt1   MaxTargets 1, 8 Guardians: 到电厂 4 from s13, 在家 4 to s55 -- one team.
  aitpmt2   MaxTargets 2: 到电厂 4 from s13, 到兵营 4 from s26 (the second team left s19-21), 在家 0 -- a team per
            slot, the second slot's unique nearest = the barracks (the plant is the first slot's).
(aitpmt1's first run read 在家 2: the home area was then a 300 square that held 6 of the 8 start spots; widened.)
The simulator (simai) gives the same eight (tests/test_simai.py test_target_pick_as_on_the_bench).
Bench 2026-11-09 (B round 82, TeamTemplate.Priority: two always-on states over the same 4 Guardians, P = the plant
(ClosestStructure), B = the barracks (CNVHBarracks); one run each, run first with the model's guess plant 4 for all):
  aitpprs   P STANDARD / B STANDARD: 在家 4 to s16, 3/2/1/0 s17-s20; 到兵营 2 @ s21, 4 s23-s55; 到电厂 0 throughout.
  aitpprh   P STANDARD / B HIGH: the same to the second.
  aitpprl   P LOW / B STANDARD: the same (到兵营 3 @ s22).
  aitpprp   P HIGH / B STANDARD: 在家 2 @ s12, 0 @ s14; 到电厂 4 s15-s56; 到兵营 0 -- the plant, a second earlier than
            aitpnear alone.
Read: the higher team Priority takes the units; on a tie the barracks' state (listed second) wins, though its target
is found later (s19 in aitpvk) -- nobody went to the plant first. Not split: a tie by list order or by state draw.
simai sends all four to the plant (strict xfail, tests/test_simai.py test_team_priority_as_on_the_bench).
Bench 2026-11-09 (B round 85, EndBehavior, the check script kills the plant at s35; one run each; 到电厂 到兵营 到坦克 在家):
  all four: out s13-s14, 到电厂 4 s15-s34 (the Guardians did not kill it by s32 as the simulator has).
  aiendd   DISBAND:                 到电厂 2 @ s37, 0 s38-s39, 到兵营 2 @ s40, 4 from s42 -- PASS (as the model)
  aiendh   RETURN_HOME_AND_DISBAND: the same, 到兵营 4 from s41, never home -- PASS (as the model)
  aiendr   RAMPAGE: 到电厂 0 @ s37, 到兵营 1 @ s38, 4 from s40; 到坦克 0 -- FAIL: the barracks, not the nearest
           enemy unit (the model's tank); RAMPAGE here looks like DISBAND (a nearer structure? the tank parked further?)
  aiendp   PICK_NEW_TARGET: 到电厂 4 to s85 -- FAIL: they stay where the plant was; the model sends them to the
           barracks (the slot re-picked). Not yet a strict xfail in tests/test_simai.py.
"""
from parts import Test, counted, square, Script

HOME = 'CNV TP Home'
AREAS = (('CNV TP Plant Area', 'plant', 'CNV_TP_Plant', '到电厂'),
         ('CNV TP Barracks Area', 'barracks', 'CNV_TP_Barracks', '到兵营'),
         ('CNV TP Tank Area', 'tank', 'CNV_TP_Tank', '到坦克'))
LAG = 4.0
AT, SECONDS = 40.0, 50.0
END = 75.0                    # the EndBehavior variants (aiend*): where they stand at s75 (the plant dies at s35)


def a(m):
    t = Test()
    s1 = m.player('s1')
    t.scripts.append(Script('Test - reveal', [], [('MAP_REVEAL_ALL_PERM', m.player('p1'))]))
    kill = m.facts.get('kill plant at')
    keep = [m.role(r).name for _, r, _, _ in AREAS if not (kill is not None and r == 'plant')]
    t.scripts.append(Script('Test - targets keep', [], [('UNIT_SET_HEALTH', n, 100.0) for n in keep], once=False))
    if kill is not None:          # EndBehavior variants: the plant dies, where do they stand at the end
        t.scripts += [Script('Test - kill set', [], [('SET_MILLISECOND_TIMER', 'Test Kill Plant', kill)]),
                      Script('Test - kill', [('TIMER_EXPIRED', 'Test Kill Plant')],
                             [('NAMED_KILL', m.role('plant').name)])]
    end = END if kill is not None else AT
    (tank,) = m.cnv_units
    for area, role, counter, label in AREAS:
        o = m.find(m.role(role).name)
        t.areas[area] = square(o.x, o.y, 340.0)
        counted(counter, label, t, template=tank, area=area, player=s1)
        want = m.facts['expect ' + role]
        if kill is not None:
            t.expect.append((label, end, '>=', 3, end + 1) if want else (label, end, '==', 0, end + 1))
        else:
            t.expect.append((label, 1, 'ever>=', 3, AT) if want else (label, AT, '==', 0, AT + 1))
    x, y = m.site('east base')        # every start spot (x -280..-200, y +160..+370), clear of the plant's square
    t.areas[HOME] = [(x - 300, y - 400), (x + 300, y - 400), (x + 300, y + 450), (x - 300, y + 450)]
    counted('CNV_TP_Home', '在家', t, template=tank, area=HOME, player=s1)
    t.expect.append(('在家', end, '==', m.facts['expect home'], end + 1))
    secs = END + 5.0 if kill is not None else SECONDS
    t.bench = [('bench_watch', dict(seconds=secs + LAG, every=1, sheet=False, lines=len(t.counters)))]
    return t


CHECKS = {k: {'a': a} for k in ('aitpnear', 'aitpvk', 'aitpfk', 'aitpunit', 'aitpphi', 'aitpplo', 'aitpmt1',
                                 'aitpmt2', 'aitpprs', 'aitpprh', 'aitpprp', 'aitpprl',
                                 'aiendr', 'aiendd', 'aiendh', 'aiendp')}
