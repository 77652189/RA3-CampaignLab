"""Engine probe: where a skirmish AI puts its base defence tower (missions/aitower_bench.py; l4_defense2.md section 7,
items 2-3).

  a  塔近 0.5 / 0.75 / 1.0   s1's Multigunner turrets in three bands south of the AI's power plant (the AI building
                              nearest the enemy): 250 / 375 / 475-500 from it (the radius for BaseCompactness 0.5 /
                              0.75 / 1.0), x within 180 of the plant's (the first try's angle, straight south)
     落塔帧                   frames from frame 0 until s1 has a turret anywhere near its base (stops then; a turret
                              outside every band is "elsewhere": around the yard, or another angle)

The model (RA3-EngineModel ra3model/ai/defense.py tower_centre / tower_site / tower_spots): centre = the AI plant,
angle = base centre -> nearest enemy (south), radius (BaseCompactness +- 0.05) x 500 clamped to 500. The expectation
says the build's band; a FAIL is a reading too (a turret elsewhere: 落塔帧 stops with every band 0).

读数 (bench 2026-11-07)
aitowerstate a (the probe's own budget PRODUCTION 50 / DEFENSE 50, AlliedDefenseBuildState only, money 1700 at the
  wake; two runs, 0.5 and 0.75): no turret in 70 s (落塔帧 never stops). The always-on build state alone does not build.
aitower50 a (the opener: deposit 1000 PRODUCTION + one AlliedBaseDefense; retail budgets): 落塔帧 451 (the wake is
  frame 150: 20 s, the build time), every band 0. Looked (keep=true, one run): the turret at ~(4092, 3570) -- ~296 from
  the yard at +35 deg (north-east, away from the enemy), nowhere near the AI plant; two refineries by the east ore.
  So the opener's turret is centred on the base anchor at an angle of k x 36 deg: the model's "no enemy found" branch
  (centre = base anchor, angle = random 0..9 x 36 deg) -- the player's plant 1250 south was not found (fog? the AI's
  vision?), or the opener places by another path.
aitower50 b: 落塔帧 451, 塔距场 350 内 1 from s33 (560 内 1). aitower100 b (two runs): 落塔帧 451, 350 / 560 内 0, 700 内
  1 from s29. Radius 0.5 -> ~296, 1.0 -> 560-700: r = BaseCompactness x ~600, not x 500 (the model's R when the
  radius table is empty, l4_defense2.md 2.1) -- the table is not empty, or the default is not 500.
Round 70 (bench 2026-11-07, all 落塔帧 451):
aitower100 c (two runs): 560 / 590 内 0, 620 / 650 内 1 from s31 -> r in (590, 620]. aitower75 c: 420 内 0, 442 内 1
  from s30 -> r in (420, 442]. aitower75 b: 350 内 0, 560 / 700 内 1. So R in [590, 631]: ~600 (the model's
  TOWER_LIST_R, INFERRED: who fills the radius list is not read).
aitower50 d (two runs), aitower100 d (one): FAIL -- 塔在厂南 and 塔在厂南带 0 throughout; 0.5's 塔距场 350 内 1 (s29 /
  s31), 1.0's 0 (its r ~600). Revealed for the AI too, the turret still stands round the yard, not by the plant:
  not the fog (the fog routine reads none either, work/re/l4_tower_r.md Q3). The model's centre / angle is a strict xfail.
Round 71 (bench 2026-11-07):
aitowerfoe e (own budget 50 / 50, only AlliedDefenseBuildState, 4 Guardians 600 south of the AI plant, revealed for
  both; 120 s): FAIL -- no turret anywhere (塔在基地 0 to s139, 落塔帧 never stops). An enemy army does not wake the
  build state either.
aitowerdep e (as aitowerfoe, but an opener that only deposits 1000 to DEFENSE, no Build order; retail budgets): PASS
  -- 落塔帧 451 (as the opener's), 塔距场 350 内 1 from s29, 塔在厂南带 0 throughout. So the build state builds once
  the DEFENSE account has money (PLAYER_SET_MONEY never reaches the accounts: aitowerstate / aitowerfoe were broke),
  and its turret stands round the yard just as the opener's, the enemy tanks 600 south of the plant notwithstanding.
Round 133 (bench 2026-11-11, work/logs/b136_bench.log; which of handoff-b section 125's hypotheses):
aitowerinc e (as aitowerstate, + an AI refinery on the east ore and a miner): PASS -- 落塔帧 451, 塔距场 350 内 1 from
  s29, 2 from s49, 3 from s69, 4 from s89, 5 at s128 (塔在厂南带 0 throughout): one turret a build time.
aitoweropen e (as aitowerstate, + an opener of one empty Time 0s order, own budget kept): FAIL -- no turret to s143.
  So the share pays nothing without income; an unfinished opening is not the reason. Money at the wake was the same
  1700 in both.
Round 135 (bench 2026-11-11, work/logs/b138_bench.log; handoff-b section 137's table):
aitowerinc10 e (as aitowerinc, DEFENSE 10 % / PRODUCTION 90 %, watched to s466): PASS -- 落塔帧 451 (ordered at the
  wake, as at 50 %), 塔距场 350 内 1 from s29, and NO second turret to s466. 10 % x 1700 = 170 < 800 bought the first:
  "share x the money now" is out (it waits for 8000 in the bank, ~s330); the share borrows against something at once,
  and then stops for 7+ minutes -- what it owes after the first is not paid back by the income in that time.
aitowerinc10 f (= e + AI钱, work/logs/b138_bench2.log): PASS, the same -- 落塔帧 451, one turret to s477. AI钱 1700 at
  the wake, paid down to 1189 by s27 (the turret paid as it builds), then +250 every ~12.3 s (one miner: ~20.4/s;
  the simulator's miner ~14.7/s): 5400 at s235, 10400 at s477 -- 10 % of it is 1040 and still no second turret.
aitowerinc5 f (DEFENSE 5 %): FAIL -- no turret to s454; AI钱 1700 never paid down, 10700 at s454.
  Reading (handoff-b section 138): the money in the bank does not decide; the first turret at 10 % and none at 5 %
  fit "share x income rate x build time x window, less what the share has paid (never paid back)": R(10 %) in
  [800, 1600), so R(5 %) < 800 and R(50 %) in [4000, 8000) (aitowerinc's 5, money-limited). INFERRED.
Round 136 (bench 2026-11-11, work/logs/b139_bench.log):
aitowerinc10r f (as aitowerinc10, 20000 at the wake; mod CampAITowRich): PASS -- 塔在基地 1 from s29, 2 from s49, no
  third to s174 (AI钱 ~19150 after the two, 21600 at s174). So the bank does count: 10 % x 20000 = 2000 buys two
  (a third needs 2400). With aitowerinc10 / 5: the share spends the larger of share x the bank and share x income
  rate x build time x W, less what it has paid (handoff-b section 139: tried, not merged -- with the simulator's
  miners it buys aiskirmlow a tower the bench never built, so the rate there must be smaller: net cash flow?).
"""
import math

from parts import Script, Test, counted, square

LAG = 4.0
AFTER = 60.0
HALF_X = 180.0
BANDS = ((0.5, '塔近 0.5', 'CNV AT Band 50', 170.0, 310.0), (0.75, '塔近 0.75', 'CNV AT Band 75', 310.0, 435.0),
         (1.0, '塔近 1.0', 'CNV AT Band 100', 435.0, 570.0))    # (compactness, label, area, r from, r to)
ANY = 'CNV AT Any'


def _band(x, y, near, far):
    """The strip from `near` to `far` south of (x, y), x within HALF_X: the tower's distance r from the plant."""
    return [(x - HALF_X, y - far), (x + HALF_X, y - far), (x + HALF_X, y - near), (x - HALF_X, y - near)]


def a(m):
    t = Test()
    s1 = m.player('s1')
    t.scripts.append(Script('Test - reveal', [], [('MAP_REVEAL_ALL_PERM', m.player('p1'))]))
    o = m.find(m.role('ai plant').name)
    pick = None
    for comp, label, area, near, far in BANDS:
        t.areas[area] = _band(o.x, o.y, near, far)
        counted(f'CNV_AT_B{int(comp * 100)}', label, t, template=m.cnv_turret, area=area, player=s1)
        if comp == m.cnv_compactness:
            pick = label
    x, y = m.site('east base')
    t.areas[ANY] = square(x, y, 1500.0)
    t.counters.append(('CNV_AT_First', '落塔帧'))
    t.scripts += [Script('Test - a tower', [('PLAYER_HAS_COMPARISON_UNIT_TYPE_IN_TRIGGER_AREA', s1, 3, 1, m.cnv_turret,
                                             ANY)], [('SET_FLAG', 'Test Tower', 1)]),
                  Script('Test - no tower yet', [('FLAG', 'Test Tower', 0)],
                         [('INCREMENT_COUNTER', 1, 'CNV_AT_First')], once=False)]
    end = m.facts['wake at'] + AFTER
    t.expect += [(pick, 1, 'ever>=', 1, end)]
    t.bench = [('bench_watch', dict(seconds=end + LAG, every=2, sheet=False, lines=len(t.counters)))]
    return t


def _disc(x, y, r, n=24):
    return [(x + r * math.cos(2 * math.pi * k / n), y + r * math.sin(2 * math.pi * k / n)) for k in range(n)]


RINGS = ((350.0, '塔距场 350 内', 'CNV AT Yard 350'), (560.0, '塔距场 560 内', 'CNV AT Yard 560'),
         (700.0, '塔距场 700 内', 'CNV AT Yard 700'))


def b(m):
    """Bench 11-07 a: the opener's turret stood ~300 from the yard, not by the plant. So count round the yard:

      塔距场 350 / 560 内   s1's turrets within 350 / 560 of the yard (24-gons): BaseCompactness 0.5 -> 225-275 x
                           something, 1.0 -> 475-500 (radius (BaseCompactness +- 0.05) x 500 clamped to 500)
      塔距厂 300 内         within 300 of the AI plant (the read centre when an enemy is found)
      落塔帧                as a"""
    t = Test()
    s1 = m.player('s1')
    t.scripts.append(Script('Test - reveal', [], [('MAP_REVEAL_ALL_PERM', m.player('p1'))]))
    x, y = m.site('east base')
    for r, label, area in RINGS:
        t.areas[area] = _disc(x, y, r)
        counted(f'CNV_AT_Y{int(r)}', label, t, template=m.cnv_turret, area=area, player=s1)
    t.areas[ANY] = square(x, y, 1500.0)
    t.counters.append(('CNV_AT_First', '落塔帧'))
    t.scripts += [Script('Test - a tower', [('PLAYER_HAS_COMPARISON_UNIT_TYPE_IN_TRIGGER_AREA', s1, 3, 1, m.cnv_turret,
                                             ANY)], [('SET_FLAG', 'Test Tower', 1)]),
                  Script('Test - no tower yet', [('FLAG', 'Test Tower', 0)],
                         [('INCREMENT_COUNTER', 1, 'CNV_AT_First')], once=False)]
    end = m.facts['wake at'] + AFTER
    # centre = the yard (no enemy found, bench a); 0.5 -> within 350; 1.0 -> 560-700 (bench 11-07)
    ring = '塔距场 350 内' if m.cnv_compactness < 0.6 else '塔距场 700 内'
    t.expect += [(ring, 1, 'ever>=', 1, end)]
    t.bench = [('bench_watch', dict(seconds=end + LAG, every=2, sheet=False, lines=len(t.counters)))]
    return t


FINE = (560.0, 590.0, 620.0, 650.0)         # x BaseCompactness: R's candidates round 600


def c(m):
    """Round 70: pin R. Four rings round the yard at BaseCompactness x 560 / 590 / 620 / 650 (no 落塔帧: the turret is
    down by frame 451 in every run so far). Read r = (BaseCompactness +- 0.05) x R clamped to R (l4_defense2.md 2.2):
    at 1.0, r is in [0.95 R, R] -- the first ring that counts the turret bounds R from above, the one before from
    below (R >= that / 1.05 at 1.0). The expectation: the outer ring (bench b put 1.0 inside 700)."""
    t = Test()
    s1 = m.player('s1')
    t.scripts.append(Script('Test - reveal', [], [('MAP_REVEAL_ALL_PERM', m.player('p1'))]))
    x, y = m.site('east base')
    k = m.cnv_compactness
    labels = []
    for f in FINE:
        r = k * f
        label, area = f'塔距场 {int(r)} 内', f'CNV AT Fine {int(f)}'
        t.areas[area] = _disc(x, y, r, n=48)
        counted(f'CNV_AT_F{int(f)}', label, t, template=m.cnv_turret, area=area, player=s1)
        labels.append(label)
    end = m.facts['wake at'] + AFTER
    t.expect += [(labels[-1], 1, 'ever>=', 1, end)]
    t.bench = [('bench_watch', dict(seconds=end + LAG, every=2, sheet=False, lines=len(t.counters)))]
    return t


AIM = 296.0                                 # bench a/b: the 0.5 turret ~296 from its centre


def d(m):
    """Round 70: is "no enemy found" the AI's fog? As b, but the map is revealed for s1 too (MAP_REVEAL_ALL_PERM s1).
    Read: centre = the AI building nearest an enemy (the AI plant), first angle = base centre -> nearest enemy (south).

      塔在厂南        s1's turret within 120 of the AI plant + (0, -BaseCompactness x 592) (the enemy-found spot)
      塔在厂南带      south of the AI plant by 100 or more, x within 400 (any of the 5 tries' angles round south)
      塔距场 350 内   round the yard as b (the no-enemy spot at 0.5)
      落塔帧          as a
    Revealed and still round the yard -> the fog is not why (the opener's own placement path, or the fog routine's filter, work/re/l4_tower_r.md Q3)."""
    t = Test()
    s1 = m.player('s1')
    t.scripts += [Script('Test - reveal', [], [('MAP_REVEAL_ALL_PERM', m.player('p1'))]),
                  Script('Test - reveal for the AI', [], [('MAP_REVEAL_ALL_PERM', s1)])]
    o = m.find(m.role('ai plant').name)
    r = m.cnv_compactness * 2 * AIM
    t.areas['CNV AT Spot'] = _disc(o.x, o.y - r, 120.0)
    counted('CNV_AT_Spot', '塔在厂南', t, template=m.cnv_turret, area='CNV AT Spot', player=s1)
    t.areas['CNV AT South'] = [(o.x - 400, o.y - 900), (o.x + 400, o.y - 900), (o.x + 400, o.y - 100),
                               (o.x - 400, o.y - 100)]
    counted('CNV_AT_South', '塔在厂南带', t, template=m.cnv_turret, area='CNV AT South', player=s1)
    x, y = m.site('east base')
    t.areas['CNV AT Yard 350'] = _disc(x, y, 350.0)
    counted('CNV_AT_Y350', '塔距场 350 内', t, template=m.cnv_turret, area='CNV AT Yard 350', player=s1)
    t.areas[ANY] = square(x, y, 1500.0)
    t.counters.append(('CNV_AT_First', '落塔帧'))
    t.scripts += [Script('Test - a tower', [('PLAYER_HAS_COMPARISON_UNIT_TYPE_IN_TRIGGER_AREA', s1, 3, 1, m.cnv_turret,
                                             ANY)], [('SET_FLAG', 'Test Tower', 1)]),
                  Script('Test - no tower yet', [('FLAG', 'Test Tower', 0)],
                         [('INCREMENT_COUNTER', 1, 'CNV_AT_First')], once=False)]
    end = m.facts['wake at'] + AFTER
    t.expect += [('塔在厂南带', 1, 'ever>=', 1, end)]      # the read rule; a FAIL is the reading "still the yard"
    t.bench = [('bench_watch', dict(seconds=end + LAG, every=2, sheet=False, lines=len(t.counters)))]
    return t


LONG = 120.0                                # the build state is not timed like the opener: give it two minutes


def e(m):
    """Round 71 (aitowerfoe): the regular build state, not the opener. As aitowerstate (own budget, only
    AlliedDefenseBuildState) plus the player's tanks 600 south of the AI plant (HOLD_FIRE), map revealed for both.
    Does BEST_UNIT_EXPECTED build a turret once there is an enemy army, and round which building?

      塔在厂南带      s1's turret south of the AI plant by 100-900, x within 400 (read: centre = the AI building nearest
                      an enemy = the plant, first angle south, r 0.5 x 600 = 300)
      塔距场 350 内   round the yard (the opener's spot at 0.5, bench round 69 / 70)
      塔在基地        anywhere in the 1500 square round the yard (built at all)
      落塔帧          as a
    The expectation: built at all (a FAIL is the reading "the build state builds nothing even with an enemy army")."""
    t = Test()
    s1 = m.player('s1')
    t.scripts += [Script('Test - reveal', [], [('MAP_REVEAL_ALL_PERM', m.player('p1'))]),
                  Script('Test - reveal for the AI', [], [('MAP_REVEAL_ALL_PERM', s1)])]
    o = m.find(m.role('ai plant').name)
    t.areas['CNV AT South'] = [(o.x - 400, o.y - 900), (o.x + 400, o.y - 900), (o.x + 400, o.y - 100),
                               (o.x - 400, o.y - 100)]
    counted('CNV_AT_South', '塔在厂南带', t, template=m.cnv_turret, area='CNV AT South', player=s1)
    x, y = m.site('east base')
    t.areas['CNV AT Yard 350'] = _disc(x, y, 350.0)
    counted('CNV_AT_Y350', '塔距场 350 内', t, template=m.cnv_turret, area='CNV AT Yard 350', player=s1)
    t.areas[ANY] = square(x, y, 1500.0)
    counted('CNV_AT_Any', '塔在基地', t, template=m.cnv_turret, area=ANY, player=s1)
    t.counters.append(('CNV_AT_First', '落塔帧'))
    t.scripts += [Script('Test - a tower', [('PLAYER_HAS_COMPARISON_UNIT_TYPE_IN_TRIGGER_AREA', s1, 3, 1, m.cnv_turret,
                                             ANY)], [('SET_FLAG', 'Test Tower', 1)]),
                  Script('Test - no tower yet', [('FLAG', 'Test Tower', 0)],
                         [('INCREMENT_COUNTER', 1, 'CNV_AT_First')], once=False)]
    end = m.facts['wake at'] + m.facts.get('watch', LONG)
    t.expect += [('塔在基地', 1, 'ever>=', 1, end)]
    t.bench = [('bench_watch', dict(seconds=end + LAG, every=2, sheet=False, lines=len(t.counters)))]
    return t


def f(m):
    """Round 135: e + AI钱 (s1's money each frame) -- the miner's income rate and the money when a second turret is
    (not) ordered: which of handoff-b section 138's budget models."""
    t = e(m)
    t.counters = [c for c in t.counters if c[1] != '塔在厂南带']     # four lines fit (never 1 in e's runs)
    t.counters.append(('CNV_AT_Money', 'AI钱'))
    t.scripts.append(Script('Test - money', [], [('SET_PLAYER_MONEY_TO_COUNTER', m.player('s1'), 'CNV_AT_Money')],
                            once=False))
    t.bench = [('bench_watch', dict(seconds=m.facts['wake at'] + m.facts.get('watch', LONG) + LAG, every=2,
                                    sheet=False, lines=len(t.counters)))]
    return t


TRIP = 250                                  # a miner's load (aitowerinc10 f: +250 every ~12.3 s at x1)


def g(m):
    """B round 172 (aicheat2 / aicheat1): ResourceMultiplierCheat. DEFENSE 0 %, so nothing is bought and AI钱 only
    grows by the miner's trips. Read (work/re/l2_mining.md 4): a deposit is the load x the AI's cheat multiplier.

      AI钱    s1's money each second (a step = one trip: 250 x the multiplier)

    The expectation: the MEDIUM line's Percentage is the multiplier (200 % -> 500 a trip; 100 % -> 250, and a line
    for EASY HARD BRUTAL is skipped at MEDIUM). In the 90 s watched ~7 trips: x1 stays under the wake money + 2500,
    x2 passes the wake money + 5 x 500.

    读数 (bench 2026-11-13, B round 172, work/logs/b172_bench.log, one run each, both PASS):
    aicheat1 g (EASY HARD BRUTAL 300 %, MEDIUM 100 %): 1700 at the wake, +250 a trip (1950 s18, 2200 s30, ...
      3450 s92, 3700 s104) -- the 300 % line is skipped at MEDIUM, 100 % = x1.
    aicheat2 g (MEDIUM 200 %): +500 a trip (2200 s18, 2700 s31, ... 5200 s92) -- the Percentage is the factor."""
    t = Test()
    t.counters.append(('CNV_AT_Money', 'AI钱'))
    t.scripts.append(Script('Test - money', [], [('SET_PLAYER_MONEY_TO_COUNTER', m.player('s1'), 'CNV_AT_Money')],
                            once=False))
    wake, end = m.facts['wake at'], m.facts['wake at'] + m.facts.get('watch', LONG)
    if m.cnv_cheat == 1.0:
        t.expect += [('AI钱', wake + 5, '<', m.facts['money'] + 10 * TRIP, end)]
    else:
        t.expect += [('AI钱', wake + 5, 'ever>=', m.facts['money'] + 5 * round(TRIP * m.cnv_cheat), end)]
    t.bench = [('bench_watch', dict(seconds=end + LAG, every=1, sheet=False, lines=1))]
    return t


def h(m):
    """B round 173 (aibsprod): BudgetState.State. The personality declares its own budget (DEFENSE 50 %, which buys a
    turret soon after the wake in aitowerinc) but its one BudgetState line names retail ProductionOnlyBudget
    (OpeningMoveHeuristic Complete=true -> PRODUCTION 100 %, DEFENSE 0 %); 20000 at the wake, no opening move.

      塔在基地   s1's turrets in the 1500 square round the yard
      AI钱      s1's money each 2 s

    The expectation: the State is the budget used -- DEFENSE 0 %, so no turret however rich (the own 50 % one, were it
    used, buys one within ~30 s as aitowerinc)."""
    t = Test()
    s1 = m.player('s1')
    t.scripts.append(Script('Test - reveal', [], [('MAP_REVEAL_ALL_PERM', m.player('p1'))]))
    x, y = m.site('east base')
    t.areas[ANY] = square(x, y, 1500.0)
    counted('CNV_AT_Any', '塔在基地', t, template=m.cnv_turret, area=ANY, player=s1)
    t.counters.append(('CNV_AT_Money', 'AI钱'))
    t.scripts.append(Script('Test - money', [], [('SET_PLAYER_MONEY_TO_COUNTER', s1, 'CNV_AT_Money')], once=False))
    wake, end = m.facts['wake at'], m.facts['wake at'] + m.facts.get('watch', LONG)
    t.expect += [('塔在基地', wake + 5, '<=', 0, end)]
    t.bench = [('bench_watch', dict(seconds=end + LAG, every=2, sheet=False, lines=len(t.counters)))]
    return t


def i(m):
    """B round 178 (aibsmax / aibstie / aibszero; work/re d122_ai_rules.md 1, R1-R3): which of two budget states runs.
    The personality's two own states, in list order: DEFENSE 100 % (turrets from the 20000 bank) and PRODUCTION 100 %
    (buys nothing -- no unit build state left). Read: each state's weight is the product of its heuristics; the one
    with the largest weight runs, its shares alone (not mixed); ties go to the earlier line; all 0 -> the first line.

      塔在基地   s1's turrets in the 1500 square round the yard

    aibsmax  DEFENSE 0.4 first, PRODUCTION 0.6: PRODUCTION runs -> no turret (mixed shares or "the first line": turrets)
    aibstie  0.5 and 0.5: the earlier (DEFENSE) runs -> turrets
    aibszero DEFENSE weight 0 first, PRODUCTION while the opening is not done (done 40 s after the wake): no turret
             before, then every weight 0 -> the first line (DEFENSE) -> turrets ("keep the budget it had": none)

    RESULTS i (bench 2026-11-13, B round 178, work/logs/b178_bench.log in the B worktree, all three PASS):
      aibsmax 塔在基地 0 s1-s171; aibstie 0 to s27, 1 from s29, then one every ~20 s (5 from s109);
      aibszero 0 to s67 (the opening done at s50), 1 from s69, 5 from s149. The simulator: none / s32 / s71."""
    t = Test()
    s1 = m.player('s1')
    t.scripts.append(Script('Test - reveal', [], [('MAP_REVEAL_ALL_PERM', m.player('p1'))]))
    x, y = m.site('east base')
    t.areas[ANY] = square(x, y, 1500.0)
    counted('CNV_AT_Any', '塔在基地', t, template=m.cnv_turret, area=ANY, player=s1)
    wake, end = m.facts['wake at'], m.facts['wake at'] + m.facts.get('watch', LONG)
    weights = [w for _, w, _ in m.cnv_bsets]
    if 'opening' in weights:                # aibszero
        done = wake + m.facts['opening']
        t.expect += [('塔在基地', wake + 5, '<=', 0, done), ('塔在基地', done, 'ever>=', 1, end)]
    elif len(weights) < 2:                  # a build without the budget-state pair: readings only
        pass
    elif float(weights[1]) > float(weights[0]):     # aibsmax: the second (PRODUCTION) is larger
        t.expect += [('塔在基地', wake + 5, '<=', 0, end)]
    else:                                   # aibstie: the first (DEFENSE) holds the tie
        t.expect += [('塔在基地', wake + 5, 'ever>=', 1, end)]
    t.bench = [('bench_watch', dict(seconds=end + LAG, every=2, sheet=False, lines=len(t.counters)))]
    return t


CHECKS = {k: {'a': a, 'b': b, 'c': c, 'd': d, 'e': e, 'f': f, 'g': g, 'h': h, 'i': i}
          for k in ('aitower50', 'aitower75', 'aitower100', 'aitowerstate', 'aitowerfoe',
                   'aitowerdep', 'aitowerinc', 'aitoweropen', 'aitowerinc10', 'aitowerinc5', 'aitowerinc10r',
                   'aicheat2', 'aicheat1', 'aibsprod', 'aibsmax', 'aibstie', 'aibszero')}
