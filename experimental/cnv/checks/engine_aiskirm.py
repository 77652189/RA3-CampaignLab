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
"""
from parts import Script, Test, counted, square

AREA = 'CNV AI Base Area'
RIPTIDE = 'AlliedAntiInfantryVehicle_Ground'     # the one a Riptide on land is (aiopen b counts both alike)
YOURS = ('AlliedConstructionYard', 'AlliedWarFactory', 'AlliedPowerPlant')
SECONDS = 310.0                      # after the wake


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


CHECKS = {'aiskirm': {'a': a}}
