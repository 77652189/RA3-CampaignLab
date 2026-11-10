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
                                  'aiom1', 'aiom2', 'aiom3', 'aiom4', 'aiom5')}
