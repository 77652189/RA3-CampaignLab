"""Engine probe: when the skirmish AI's first attack team leaves its base (missions/aiskirm_bench.py: s1 AlliedBalanced
with a yard, woken at 10 s with 50000 money; the player has a yard, a war factory and a power plant on the west bank),
read for the plan simulator (simai.py: first team BalancedAttackGround = 4 Riptides + 4 dogs leaves ~157 s after the
wake; the player's 3 buildings die 232-261 s after).

  a  激流总数 / 激流在家   Riptides (AlliedAntiInfantryVehicle) s1 owns / of them inside 600 around the east base
     出门帧             frames from the wake until the first Riptide stands outside the area (stops there; never
                        out = counts the whole run). 15 frames a second.
     我方建筑           how many of the player's yard / war factory / power plant are still alive (0-3)

The units counted are the Riptides only (the team's dogs are not read: the Riptides are the first to be built and the
ones that leave with the team). Four lines a check. Once the first leaves, the other readings are the timeline.

读数
RESULTS (bench 2026-11-07; bench s; counters 激流总数 激流在家 出门帧 我方建筑; the check logs 1-s rows; PASS):
  wake: 出门帧 starts counting at ~s8.1 bench (the check's wake = timer 10 s + 30 ticks; bench s runs ~2 s ahead of
    the mission clock), 15 frames a second. Seconds below are bench s; "after wake" = minus ~8.1.
  first Riptide: 激流总数 1 at s111 (~103 s after wake), 2 at s123, 3 at s131, 4 at s142, 5 s174, 6 s185, 7 s248,
    8 s259, 9 s269, 10 s280, 11 s291, 12 s317, 13 s325 (total counts all Riptides, the AI keeps building).
  leaves: 出门帧 stops at 1992 (= 132.8 s) at s139: 激流在家 3 at s138, 1 at s139 (two out at once) = first team
    leaves ~131-133 s after the wake (sim said ~157 s: the sim is ~25 s late).
  player buildings 我方建筑: 3 until s202, 2 from s203, 1 from s221, 0 from s223 = first dies ~195 s after the wake,
    the last (all three gone) ~215 s after (sim said 232-261 s: the sim is ~35-45 s late).
  Reading: the first attack team leaves ~132 s after the wake, 20 s after the first Riptide stands (s111), and the
  player's 3 buildings are gone ~83 s after it leaves; the sim's 157 s / 232-261 s are too late.

  b  激流在家 / 警犬总数 / 警犬在家 / 出圈帧   (dogs = AlliedScoutInfantry; 出圈帧 stops at the first dog out)
RESULTS b (bench 2026-11-07; PASS; wake = ~s8.1 bench, so after-wake seconds = bench s minus 8.1):
  dogs: total 1 at s23, 2 at s26 (built before the first Riptide); 出圈帧 stops at 661 (= 44 s after wake) at s52:
    警犬在家 2 -> 1 at s52 -> 0 at s55; back 2 at s68-86; 0 again from s87 on (the whole 120-170 window). So the dogs
    scout on their own, they are NOT in the team that leaves with the Riptides.
  Riptides: 在家 1 at s111, 2 at s123, 3 at s131-138, 1 at s139, 0 at s140-141 (the two leave at s139).
  120-145 s after wake (s128-153), 激流在家/警犬总数/警犬在家: s128-130 2/2/0; s131-138 3/2/0; s139 1/2/0;
    s140-141 0/2/0; s142 1/2/0; s143-150 2/2/0; s151-153 1/2/0. Dogs stay at 0 home, so no dog leaves with them.
  145-170 s after wake (s153-178): 激流在家 1 (to s158; the 4th, built s142, left at s151), 0 (s159-173; the 2nd team
    out), 1 from s174, 2 from s185 -- these are the new builds of a's total (5th at s174, 6th at s185); no dog or
    Riptide is seen coming home (home count only rises at build seconds).
  Reading: the first team's two Riptides leave without dogs; the dogs left earlier (~44 s after wake) and are away.

  c  维和总数 / 维和在家 / 标枪总数 / 工程师总数   (Peacekeeper AlliedAntiInfantryInfantry, Javelin soldier
     AlliedAntiVehicleInfantry, AlliedEngineer; home = inside 600 around the east base; runs to ~s188)
RESULTS c (bench 2026-11-07; PASS; after-wake seconds = bench s minus 8.1; templates all exist in the SDK):
  Peacekeepers total: 1 at s43 (35 s after wake), 2 s49 (41), 3 s54 (46), 4 s133 (125), 5 s150 (142), 6 s162 (154),
    7 s168 (160), 8 s179 (171). Javelin: 1 s32 (24), 2 s37 (29), 3 s60 (52), 4 s156 (148), 5 s173 (165), 6 s185 (177).
    Engineer: 1 at s144 (136), only one in the whole run. So the barracks never stops: ~1 infantry per 5-25 s, a long
    gap 52-125 s (nothing built; 3 Peacekeepers + 3 Javelins stand home s69-132).
  Peacekeepers at home 125-145 s after wake (s133-153): 4 (s133-140), 1 at s141 (= 132.9 s after wake: THREE leave
    in the same second, the same moment the first Riptide team leaves), 0 s142-144, 3 at s145 (the 3 back or new ones:
    total stays 4, so they return), 4 at s150, 1 at s152 (3 out again). Engineer built s144 (136 s).
  Reading: the first attack team leaves ~133 s after wake with 3 Peacekeepers (plus the Riptides); the barracks'
    4th Peacekeeper (125 s) is built just before and stays or comes back.
"""
from parts import Script, Test, counted, square

AREA = 'CNV AI Base Area'
RIPTIDE = 'AlliedAntiInfantryVehicle_Ground'     # the one a Riptide on land is (aiopen b counts both alike)
YOURS = ('AlliedConstructionYard', 'AlliedWarFactory', 'AlliedPowerPlant')
DOG = 'AlliedScoutInfantry'
SECONDS = 310.0                     # after the wake


def a(m):
    t = Test()
    m.spawns.add(RIPTIDE)               # published for the contract: the AI makes it, the check counts it
    s1 = m.player('s1')
    t.scripts.append(Script('Test - reveal', [], [('MAP_REVEAL_ALL_PERM', m.player('p1'))]))
    t.areas[AREA] = square(*m.site('east base'), 600.0)
    counted('CNV_AK_Total', '激流总数', t, template=RIPTIDE, player=s1)
    counted('CNV_AK_Home', '激流在家', t, template=RIPTIDE, area=AREA, player=s1)
    t.counters.append(('CNV_AK_OutFrames', '出门帧'))
    t.counters.append(('CNV_AK_Built', '我方建筑'))
    p1 = m.player('p1')
    t.scripts.append(Script('Test - built zero', [], [('SET_COUNTER', 'CNV_AK_Built', 0)], once=False))
    for i, tpl in enumerate(YOURS):
        m.spawns.add(tpl)
        t.scripts += [Script(f'Test - own {i}', [], [('SET_PLAYER_OWNERSHIP_OF_TYPE_COUNTER', tpl, p1, f'CNV_AK_Own{i}')],
                             once=False),
                      Script(f'Test - built {i}', [('COUNTER', f'CNV_AK_Own{i}', 3, 1)],
                             [('INCREMENT_COUNTER', 1, 'CNV_AK_Built')], once=False)]
    t.scripts += [Script('Test - tick', [], [('INCREMENT_COUNTER', 1, 'CNV_AK_Tick')], once=False),
                  Script('Test - woke', [('TIMER_EXPIRED', 'CNV AI Wake'), ('COUNTER', 'CNV_AK_Tick', 3, 30)],
                         [('SET_FLAG', 'Test Woke', 1)])]
    for n in range(1, 9):                # more of them owned than at home = one is out
        t.scripts.append(Script(f'Test - out {n}', [('COUNTER', 'CNV_AK_Total', 2, n), ('COUNTER', 'CNV_AK_Home', 0, n)],
                                [('SET_FLAG', 'Test Out', 1)], once=False))
    t.scripts.append(Script('Test - wait out', [('FLAG', 'Test Woke', 1), ('FLAG', 'Test Out', 0)],
                            [('INCREMENT_COUNTER', 1, 'CNV_AK_OutFrames')], once=False))
    w = m.facts['wake at']
    t.expect += [('激流总数', w + 150.0, 'ever>=', 1, w + SECONDS)]
    t.bench = [('bench_watch', dict(seconds=w + SECONDS + 4.0, every=1, sheet=False, lines=len(t.counters)))]
    return t


def b(m):
    """Same wake and area as a; reads the Riptides together with the dogs (AlliedScoutInfantry): do the dogs leave in
    the same second as the two Riptides?  出圈帧 stops at the first dog out (dogs owned > dogs at home)."""
    t = Test()
    m.spawns.add(RIPTIDE)
    m.spawns.add(DOG)
    s1 = m.player('s1')
    t.scripts.append(Script('Test - reveal', [], [('MAP_REVEAL_ALL_PERM', m.player('p1'))]))
    t.areas[AREA] = square(*m.site('east base'), 600.0)
    counted('CNV_AK_Home', '激流在家', t, template=RIPTIDE, area=AREA, player=s1)
    counted('CNV_AK_DogTotal', '警犬总数', t, template=DOG, player=s1)
    counted('CNV_AK_DogHome', '警犬在家', t, template=DOG, area=AREA, player=s1)
    t.counters.append(('CNV_AK_OutFrames', '出圈帧'))
    t.scripts += [Script('Test - tick', [], [('INCREMENT_COUNTER', 1, 'CNV_AK_Tick')], once=False),
                  Script('Test - woke', [('TIMER_EXPIRED', 'CNV AI Wake'), ('COUNTER', 'CNV_AK_Tick', 3, 30)],
                         [('SET_FLAG', 'Test Woke', 1)])]
    for n in range(1, 9):                # more dogs owned than at home = one is out
        t.scripts.append(Script(f'Test - out {n}', [('COUNTER', 'CNV_AK_DogTotal', 2, n), ('COUNTER', 'CNV_AK_DogHome', 0, n)],
                                [('SET_FLAG', 'Test Out', 1)], once=False))
    t.scripts.append(Script('Test - wait out', [('FLAG', 'Test Woke', 1), ('FLAG', 'Test Out', 0)],
                            [('INCREMENT_COUNTER', 1, 'CNV_AK_OutFrames')], once=False))
    w = m.facts['wake at']
    t.expect += [('警犬总数', w + 150.0, 'ever>=', 1, w + 170.0)]
    t.bench = [('bench_watch', dict(seconds=w + 174.0, every=1, sheet=False, lines=len(t.counters)))]
    return t


def c(m):
    """Same wake and area as a; counts the barracks' infantry: Peacekeepers (AlliedAntiInfantryInfantry) total and at
    home, Javelin soldiers (AlliedAntiVehicleInfantry) total, Engineers (AlliedEngineer) total. Runs to ~170 s after
    the wake. Home = inside 600 around the east base."""
    t = Test()
    PK, JAV, ENG = 'AlliedAntiInfantryInfantry', 'AlliedAntiVehicleInfantry', 'AlliedEngineer'
    for tpl in (PK, JAV, ENG):
        m.spawns.add(tpl)
    s1 = m.player('s1')
    t.scripts.append(Script('Test - reveal', [], [('MAP_REVEAL_ALL_PERM', m.player('p1'))]))
    t.areas[AREA] = square(*m.site('east base'), 600.0)
    counted('CNV_AK_PkTotal', '维和总数', t, template=PK, player=s1)
    counted('CNV_AK_PkHome', '维和在家', t, template=PK, area=AREA, player=s1)
    counted('CNV_AK_JavTotal', '标枪总数', t, template=JAV, player=s1)
    counted('CNV_AK_EngTotal', '工程师总数', t, template=ENG, player=s1)
    w = m.facts['wake at']
    t.expect += [('维和总数', w + 150.0, 'ever>=', 1, w + 170.0)]
    t.bench = [('bench_watch', dict(seconds=w + 174.0, every=1, sheet=False, lines=len(t.counters)))]
    return t


CHECKS = {'aiskirm': {'a': a, 'b': b, 'c': c}}
