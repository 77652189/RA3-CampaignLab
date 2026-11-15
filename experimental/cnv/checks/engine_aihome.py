"""Engine probe: DefaultTacticHomeBaseCriteria -- which of two AI bases a RETURN_HOME_AND_DISBAND team walks home to
(missions/aihome_bench.py).

  a  家A / 家B / 敌存活 (aihomecl) or 到电厂 (aihmg*)   s1 units inside a square around base A (the first yard,
     half-width 450) / around base B (the second yard, 1350 north, half-width 750) / the player's Peacekeepers within
     2500 of the foe spot (aihomecl) or s1 units within 300 of the plant (aihmg*) -- once a second to wake + 70 s.
     aihmg*: the plant is killed by the check at the mission's 'kill plant at' (35 s).

Model prediction (defense.home_for: pick_base with the personality's criteria, the team centre as PREFER_CLOSEST's
point): first guess aihmgcl -> back to A (wrong, see below); aihmgnw, aihmgno -> to B (家B 4).

读数
Bench 2026-11-14 aihomecl a (run_queue, PASS on the weak expectation): 家A 4 to s7 (s8 3, s9 2, s10 1, s11 0), 家B 1
  @ s11, 2 @ s12, 3 @ s13, 4 from s14 to the end (s95); 敌存活 1 throughout. With two bases and no TargetBaseCriteria
  the ReactiveDefense team walks to B (the newer base: the xsd default sort PREFER_NEWEST) and never chases the foe
  1000 south of A. The same runs with SortOrder PREFER_NEWEST or PreferredNotBaseTypes OLDEST_OF_TYPE in the
  personality's DefaultTacticHomeBaseCriteria (builds aihomenw / aihomeno, retired) read the same to the second:
  ReactiveDefense never ends (the model: no EndBehavior), so those criteria were never asked.
Bench 2026-11-14 (run_queue; 家A 家B 到电厂; the tanks leave s5-s8, 到电厂 4 from s7-s10):
  aihmgnw  PREFER_NEWEST: the tanks kill the plant themselves (到电厂 2 @ s27, 0 @ s28), walk past A (家A 1-2
           s28-s32) to B: 家B 1 @ s34, 2 @ s35, 4 from s36 to the end (s93) -- PASS.
  aihmgno  PREFER_CLOSEST + PreferredNotBaseTypes OLDEST_OF_TYPE: the plant gone s23-s24, 家A 1-2 s24-s27, 家B 2 @ s29,
           4 from s30 to the end (s87) -- PASS: the preferred-not type outweighs the closer base.
  aihmgcl  PREFER_CLOSEST: 到电厂 4 from s7 to the end (s88), 家A 0, 家B 0 -- FAIL against the model's first guess (back
           to A). The closest base is A and the team (firing from range, ~700 from A's yard at the plant) is within
           600 of it: the engine's go-home check says home, disband where they stand, no move order (work/re l4_tactics.md 4). The model
           ordered the move first and disbanded at 600 with the order on; fixed (B round 201), now the same.
"""
from parts import Script, Test, counted, square

LAG = 4.0
AFTER = 70.0
NEAR_A = 450.0
NEAR_B = 750.0
NEAR_PLANT = 300.0
BIG = 2500.0
FOE_DIST = 1000.0   # missions/aihome_bench.py
HOME = {'aihomecl': 'B', 'aihmgnw': 'B', 'aihmgno': 'B'}      # aihmgcl: neither (bench), asserted on 到电厂


def a(m):
    t = Test()
    s1, p1 = m.player('s1'), m.player('p1')
    t.scripts.append(Script('Test - reveal', [], [('MAP_REVEAL_ALL_PERM', p1)]))
    (unit,) = m.cnv_units
    x, y = m.site('east base')
    bx, by = m.site('east base', 0.0, m.facts['north'])
    t.areas['CNV HB A'] = square(x, y, NEAR_A)
    t.areas['CNV HB B'] = square(bx, by, NEAR_B)
    counted('CNV_HB_A', '家A', t, template=unit, area='CNV HB A', player=s1)
    counted('CNV_HB_B', '家B', t, template=unit, area='CNV HB B', player=s1)
    end = m.facts['wake at'] + AFTER
    if m.facts['probe'] == 'reactive':
        fx, fy = m.site('east base', 0.0, -FOE_DIST)
        t.areas['CNV HB FoeBig'] = square(fx, fy, BIG)
        counted('CNV_HB_ALIVE', '敌存活', t, template=unit, area='CNV HB FoeBig', player=p1)
    else:
        px, py = m.site('east gate')
        t.areas['CNV HB Plant'] = square(px, py, NEAR_PLANT)
        counted('CNV_HB_PLANT', '到电厂', t, template=unit, area='CNV HB Plant', player=s1)
        kill = m.facts['kill plant at']
        t.scripts += [Script('Test - kill set', [], [('SET_MILLISECOND_TIMER', 'Test Kill Plant', kill)]),
                      Script('Test - kill', [('TIMER_EXPIRED', 'Test Kill Plant')],
                             [('NAMED_KILL', m.role('plant').name)])]
    home = HOME.get(_key(m))
    t.expect += [('家B' if home == 'B' else '到电厂', end, '==', 4, end + 1)]
    t.bench = [('bench_watch', dict(seconds=end + LAG, every=1, sheet=False, lines=len(t.counters)))]
    return t


def _key(m):
    return next(k for k, n in NAMES.items() if n == m.name)


NAMES = {'aihomecl': 'CampAIHomeCl', 'aihmgcl': 'CampAIHmGCl', 'aihmgnw': 'CampAIHmGNw', 'aihmgno': 'CampAIHmGNo'}
CHECKS = {k: {'a': a} for k in NAMES}
