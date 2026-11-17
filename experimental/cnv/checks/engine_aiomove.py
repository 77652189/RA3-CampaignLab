"""Engine probe: which opening is drawn, and OpeningMoveHeuristic (missions/aiomove_bench.py).

  a  电厂 / 兵营   power plants / barracks s1 owns, once a second
     坦克在家     (aiohc*) Guardians of s1 inside the base area (450 around the east base)

Expected (the model, private ai/opening.py choose: the lines of the difficulty, drawn by Weight; ai/states.py
OpeningMoveHeuristic: Complete == the opening done): the mission's plants / barracks at s40; aiohc* all Guardians
home at 'home until', fewer by 'out by'.

读数
Bench 2026-11-09 (B round 83, one run each):
  aiowt / aiowt2 / aiodf / aiodf2 FAIL: 电厂 0 兵营 0 to s80 -- nothing built at all (two OpeningMove lines, each one
    Build order, no Time). Not found why: aiotime / aiohc* (one line, the 5-order opening) build. Next: one line of
    CNVOpenP alone; then two lines both 100%; then a Time order after the Build.
  aiohc1 (Complete true): 坦克在家 4 to s42, 2 @ s43, 0 from s44; 电厂 1 s19, 2 s49 -- the opening counts as done
    at s40 (wake + Time 30s: the orders after it are builds and Time points already passed), not when the last
    plant stands (s59). simai gives the same (out s44-45). Expectation set to the reading afterwards.
  aiohc0 (Complete false): PASS, out s14-15.
Bench 2026-11-09 (B round 84, narrowing aiowt*'s nothing; one run each, 电厂 兵营):
  aiom1  one line, opening = Build plant:                0 0 to s80 -- nothing
  aiom2  two lines P / B both 100%:                      0 0 to s80 -- nothing
  aiom3  T 100% + B 0%:                                  PASS (plants s19 / s49 / s59 as aiotime): a 0% line is harmless
  aiom4  one line, Build barracks then Time 5s:          0 0 to s81 -- nothing
  aiom5  one line, Build plant, Build plant (no Time):   1 plant from s19, never a second
Not found why: one Build -> none, two Builds -> one, T (plant / Time / plant / Time / plant) -> all three.
Bench 2026-11-09 (B round 85, one run each, 电厂 兵营):
  aiom6  P P P:              1 0 (s19) -- one of three
  aiom7  P, Time 5s:         0 0 -- a trailing Time does not save the lone Build
  aiom8  Time 5s, P:         0 0 -- nor does issuing it after the wake frame
  aiom9  B, P:               1 0 -- the LAST Build of the batch is the one built
  aiom10 P, B:               0 1 -- the same the other way round (so the barracks is buildable: aiom4 is not that)
Read: several Builds issued in one go -> only the last is built; a Build alone in its batch (aiom1 / 4 / 7 / 8) ->
nothing; yet T's first plant (alone at the wake, 30 s before the next order) is built, and its two at s40 both are.
Guesses not tried: the build orders share one slot and a newer one replaces an unstarted older one (but then the
lone one should stand); the opening's done-ness or how long before the next order matters (P + Time 30s untried).
Round 86: aiom11 (P, Time 30s), aiom12 (P, Time 15s), aiom13 (P, P, Time 30s), aiom14 (Time 30s, P) written; the
first run (17:22) all ERROR -- the game's DirectX error box at start (another game, gamemd, held the screen), not read.
Guess they test: the plant takes ~9 s; a lone Build survives only if the opening is not over before it stands.
Bench 2026-11-09 (B round 88, run_queue --jobs 2, the bench free again; counters 电厂 兵营, wake s10):
  aiom11 (P, Time 30s) PASS: plant s19.   aiom12 (P, Time 15s) PASS: plant s19.   (aiom7, P + Time 5s: none)
  aiom13 (P, P, Time 30s) PASS: plants s19 and s29 -- both, where P, P with no Time (aiom5) gave one.
  aiom14 (Time 30s, P) FAIL by timing only: the plant stands at s49 (ordered at s40, the opening's last order) --
    where Time 5s, P (aiom8) gave none.
  aiom15 (P, P, Time 30s Account PRODUCTION Deposit 2000) PASS: plants s23 and s33 -- both, 4 s later than aiom13.
  aiom16 (one P, the money given before SKIRMISH_AI_MAKE_BASE) FAIL: nothing, as aiom1 -- not the money at the wake.
Not settled; what the eight lone-Build readings fit: a Build stands if a Time >= 15 s follows it, or if it is
issued >= 30 s after the wake; a Build alone in the first seconds with the opening ending within ~5 s is dropped.
Bench 2026-11-09 (B round 89): the whole opening's end decides, not each Build's own wait --
  aiom17 (B, Time 3s, P, Time 30s) PASS: barracks s19, plant s29 -- both (the barracks' own wait is 3 s).
  aiom18 (B, P, Time 5s) PASS: plant s19, no barracks -- the last Build, begun at the wake.
  aiom19 (P, P, Time 8s) one plant s19 (guessed 2; the expectation is the bench's now).
  aiom20 (P, Time 10s) PASS: plant s19.
Rule fitted to aiom1-20, aiotime T and aiopen AlliedStandard (private ai/opening.py kept_orders, mechanism not
read): the last Time point >= X s after the wake (8 < X <= 10; the model takes 10) keeps every order; a shorter
opening keeps only its last Build, worked as if alone, and none when it has one Build.
Bench 2026-11-09 (B round 90, the two lines now Build + Time 30s, CNVOpenPT30 / CNVOpenBT30; all PASS):
  aiowt  (P 0%, B 100%): barracks s19, no plant.     aiowt2 (P 100%, B 0%): plant s20, no barracks.
  aiodf  (P EASY, B MEDIUM HARD BRUTAL): barracks s19.  aiodf2 (P MEDIUM HARD BRUTAL, B EASY): plant s19.
Read: a 0% line is never drawn, either order (not "the first / last line"); lines are kept by Difficulty and the
bench plays MEDIUM (as aidiff). The round-83 nothing was the lone-Build rule, not the draw.
"""
from parts import Script, Test, counted, square

AREA = 'CNV AI Base Area'
LAG = 4.0
AT, SECONDS = 40.0, 75.0


def a(m):
    t = Test()
    s1 = m.player('s1')
    t.scripts.append(Script('Test - reveal', [], [('MAP_REVEAL_ALL_PERM', m.player('p1'))]))
    counted('CNV_OM_Plants', '电厂', t, template='AlliedPowerPlant', player=s1)
    counted('CNV_OM_Barracks', '兵营', t, template='AlliedBarracks', player=s1)
    t.expect += [('电厂', AT, '==', m.facts['plants'], AT + 1), ('兵营', AT, '==', m.facts['barracks'], AT + 1)]
    if 'ai tanks' in m.facts:
        t.areas[AREA] = square(*m.site('east base'), 450.0)
        tank, = m.cnv_units
        counted('CNV_OM_Home', '坦克在家', t, template=tank, area=AREA, player=s1)
        n = m.facts['ai tanks']
        if 'home until' in m.facts:
            hu = m.facts['home until']
            t.expect += [('坦克在家', hu, '==', n, hu + 1)]
        by = m.facts['out by']
        t.expect += [('坦克在家', by, '<', n, by + 1)]
    t.bench = [('bench_watch', dict(seconds=SECONDS + LAG, every=1, sheet=False, lines=len(t.counters)))]
    return t


CHECKS = {k: {'a': a} for k in ('aiowt', 'aiowt2', 'aiodf', 'aiodf2', 'aiohc1', 'aiohc0',
                                  'aiom1', 'aiom2', 'aiom3', 'aiom4', 'aiom5',
                                  'aiom6', 'aiom7', 'aiom8', 'aiom9', 'aiom10',
                                  'aiom11', 'aiom12', 'aiom13', 'aiom14', 'aiom15', 'aiom16',
                                  'aiom17', 'aiom18', 'aiom19', 'aiom20')}
