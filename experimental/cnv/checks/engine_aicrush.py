"""Engine probe: the skirmish AI team's Crush / CrushPreference (missions/aicrush_bench.py; docs/engine/aiteamstate.md).

  a  守军数     Peacekeepers the player (p1) owns (12 at the start; the guards)
     坦克数     Hammers s1 owns
     到远厂     Hammers of s1 within 300 of the far power plant
     once a second, AFTER seconds after the wake

Expectations are the model's (l4_micro_engage.md 1.5); a FAIL is a reading too: read the speed the guards die at --
a crush kills at once on contact, a gun takes many seconds.
  aicrush1   the guards fall below 8 within 25 s of the wake (aicrush1t too: aicrush1 with the CNVTeams carrier)
  aicrush0 / aicrushlo   the guards are still 8 or more at 25 s of the wake

Readings (11-09, all PASS; counters 守军数 坦克数 到远厂; the AI's 4 Hammers SovietAntiVehicleVehicleTech1, the player's 12
Peacekeepers; tanks reach the plant s15):
  aicrush1   s1-s18 12 4 4 | s19 11 | s20 9 | s21 7 | s22 4 | s23 3 | s24-25 2 | s26-27 1 | s28-s33 0 (4 tanks alive all
             along, 9 s for 12 men); then 1 @ s34-35 and s71-74 (a stray guard counted again), tanks 4 to s79
  aicrush0   s15-s22 12 4 4 | s23-s30 12 3 3 | s31-37 11 2 2 | s38-s85 11 0 0 (the guards win: shot down, 1 guard lost)
  aicrushlo  s15-s22 12 4 4 | s23-s30 12 3 3 | s31-36 11 2 2 | s37 11 1 1 | s38-s85 11 0 0 (as aicrush0)
"""
from checks import engine_aitarget as at
from parts import Script, Test, counted, square

AFTER = 70.0
SOON = 25.0


def a(m, build):
    t = Test()
    s1, p1 = m.player('s1'), m.player('p1')
    t.scripts.append(Script('Test - reveal', [], [('MAP_REVEAL_ALL_PERM', p1)]))
    o = m.find(m.role('far plant').name)
    t.areas[at.FAR] = square(o.x, o.y, 300.0)
    inf, tank = m.cnv_units
    counted('CNV_CR_Guards', '守军数', t, template=inf, player=p1, most=13)
    counted('CNV_CR_Tanks', '坦克数', t, template=tank, player=s1)
    counted('CNV_CR_Far', '到远厂', t, template=tank, area=at.FAR, player=s1)
    wake = m.facts['wake at']
    end = wake + AFTER
    if build in ('aicrush1', 'aicrush1t'):
        t.expect += [('守军数', wake + SOON, '<', 8)]
    else:
        t.expect += [('守军数', wake + SOON, '>=', 8)]
    t.bench = [('bench_watch', dict(seconds=end + at.LAG, every=1, sheet=False, lines=len(t.counters)))]
    return t


CHECKS = {k: {'a': (lambda m, k=k: a(m, k))} for k in ('aicrush1', 'aicrush0', 'aicrushlo', 'aicrush1t')}
