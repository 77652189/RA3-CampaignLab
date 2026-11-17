"""Engine probe: the opening a PathToTargetHeuristic picks (missions/aiopath_bench.py). s1 (Allied, woken at 10 s,
50000 money) has two openings only, AlliedStandard (PathExists true: barracks, then power plant at +10 s) and
AlliedIsland (PathExists false: power plant, refinery x2, power plant, naval yard; no barracks), both tested with the
mission's ObjectTypeToUseForTest. Counted once a second for 90 s after the wake: 兵营 电厂 精炼厂 船坞 (s1's own).

  p  aiopath1 (AlliedPowerPlant tests: no locomotor = no path)  -> Island: a power plant by wake+15, never a barracks
  s  aiopath0 (SovietAntiInfantryInfantry, the stock tester)    -> Standard: a barracks by wake+15, no power plant yet
  p  aiopathi (one line, Island with PathExists true)           -> the probe's personality takes at all
  p  aiopathr (aiopath1, Island listed first)                   -> both lines held? then the first (Island) is drawn

读数
Bench 2026-11-09 (one run each, 105 frames s1-s105; counters 兵营 电厂 精炼厂 船坞; mods CampAIPath1P / IP / RP):
  aiopath1  兵营 s19, 电厂 s29, 精炼厂 s49 / s69, 电厂2 s79, 船坞 never   FAIL: the Standard opening (= engine_aiopen a)
  aiopathi  电厂 s19, 精炼厂 s39 / s59, 电厂2 s69, 船坞 s89, 兵营 never     PASS: the Island list, the personality takes
  aiopathr  兵营 s19, 电厂 s29, ... the same as aiopath1                   FAIL: Standard again, though listed second
So with a tester that has no locomotor the heuristic says "a way": PathExists="true" holds, "false" fails (not
"both hold, the first is drawn"). The program read (work/re l4_states.md 3, "no locomotor -> no way") is wrong or
misread. aiopath0 not run (the infantry tester on land is aiopen's own opening). A true "no way" (an island map)
not measured. Simulator: simai.Brain.path_to_target no locomotor -> True; tests/test_simai.py holds the three.
"""
from parts import Script, Test, counted

LAG = 4.0
AFTER = 90.0


def _run(m, island):
    t = Test()
    s1 = m.player('s1')
    t.scripts.append(Script('Test - reveal', [], [('MAP_REVEAL_ALL_PERM', m.player('p1'))]))
    for c, lab, tpl in (('CNV_AP_Barracks', '兵营', 'AlliedBarracks'), ('CNV_AP_Power', '电厂', 'AlliedPowerPlant'),
                        ('CNV_AP_Refinery', '精炼厂', 'AlliedRefinery'), ('CNV_AP_Naval', '船坞', 'AlliedNavalYard')):
        counted(c, lab, t, template=tpl, player=s1)
    w = m.facts['wake at']
    if island:
        t.expect += [('电厂', w + LAG, 'ever>=', 1, w + 15.0), ('兵营', 2, '==', 0, w + AFTER)]
    else:
        t.expect += [('兵营', w + LAG, 'ever>=', 1, w + 15.0), ('电厂', 2, '==', 0, w + 15.0)]
    t.bench = [('bench_watch', dict(seconds=w + AFTER + LAG, every=1, sheet=False, lines=len(t.counters)))]
    return t


CHECKS = {'aiopath1': {'p': lambda m: _run(m, True)}, 'aiopath0': {'s': lambda m: _run(m, False)},
          'aiopathi': {'p': lambda m: _run(m, True)}, 'aiopathr': {'p': lambda m: _run(m, True)}}
