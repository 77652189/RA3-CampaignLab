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
"""
import math

from parts import Script, Test, counted, square

from missions import aitower_bench as tb

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
        counted(f'CNV_AT_B{int(comp * 100)}', label, t, template=tb.TURRET, area=area, player=s1)
        if comp == m.cnv_compactness:
            pick = label
    x, y = m.site('east base')
    t.areas[ANY] = square(x, y, 1500.0)
    t.counters.append(('CNV_AT_First', '落塔帧'))
    t.scripts += [Script('Test - a tower', [('PLAYER_HAS_COMPARISON_UNIT_TYPE_IN_TRIGGER_AREA', s1, 3, 1, tb.TURRET,
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
        counted(f'CNV_AT_Y{int(r)}', label, t, template=tb.TURRET, area=area, player=s1)
    t.areas[ANY] = square(x, y, 1500.0)
    t.counters.append(('CNV_AT_First', '落塔帧'))
    t.scripts += [Script('Test - a tower', [('PLAYER_HAS_COMPARISON_UNIT_TYPE_IN_TRIGGER_AREA', s1, 3, 1, tb.TURRET,
                                             ANY)], [('SET_FLAG', 'Test Tower', 1)]),
                  Script('Test - no tower yet', [('FLAG', 'Test Tower', 0)],
                         [('INCREMENT_COUNTER', 1, 'CNV_AT_First')], once=False)]
    end = m.facts['wake at'] + AFTER
    # centre = the yard (no enemy found, bench a); 0.5 -> within 350; 1.0 -> 560-700 (bench 11-07)
    ring = '塔距场 350 内' if m.cnv_compactness < 0.6 else '塔距场 700 内'
    t.expect += [(ring, 1, 'ever>=', 1, end)]
    t.bench = [('bench_watch', dict(seconds=end + LAG, every=2, sheet=False, lines=len(t.counters)))]
    return t


CHECKS = {k: {'a': a, 'b': b} for k in tb.MISSION}
