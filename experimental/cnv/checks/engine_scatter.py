"""Engine unit test: the scatter (ADR 0019 layer 3, queue 3; docs/engine/weapons.md) -- how often a scattering shot
still hits its victim, by ScatterRadius.

Four of engine_shot's shell V4s (retail's Hammer shell, its warhead one radius-0 DamageNugget of HIT: 1 % of
engine_missile's 10 000-health Hammer, from the front), each with its own ScatterRadius (RADII) and a reload of
RELOAD s instead of 4.5-5.5, each at its own Hammer AT north (the Hammer faces south, the map's default for s1).
Ordered at ORDER (every clip loaded), they fire for RUN - ORDER s. Counter per lane: percent lost (one per hit, the
step counted once begun). Lane 0 (no scatter) hits every shot, so it counts the shots for all four (same timers).

What it tells apart (the shot aims at a point within R of the Hammer's centre):
  the radius uniform in [0, R] (Generals Weapon.cpp 1004-1010)  hit share falls like 1 / R
  uniform over the disc                                         like 1 / R^2
  the shell detonating on the Hammer on its way to a point beyond it (collision) raises the share on every lane.

Bench 11-05 (round 34, CampScatterHits_mcp_1105_170642): 51 shots in the run; R 0 / 30 / 60 / 120 hit 51 / 34 / 19 /
4, and CampScatterHits_mcp_1105_171950 the same to the second (the game's draws are fixed). The counter is one more
than the hits (the first step is true at full health): 50 shots, 66 / 36 / 6 %. Held against the model (round 35,
RA3-EngineModel tests/test_scatter.py): the radius uniform in [0, R] on the shooter's half, the point inside the
Hammer's 20 x 14 box -- expected 62 / 31 / 16 %, within 3 sigma of all three.
"""
from maps import probe_range
from parts import Mission, Script, Test
from checks.engine_missile import LOST_MAX, TARGET_ID, target
from checks.engine_shot import shell_v4

ORDER, RUN = 6.0, 30.0
RADII = (0.0, 30.0, 60.0, 120.0)
HIT, RELOAD, AT = 100.0, 0.5, 250.0
LANES = ('base', 'high', 'removed', 'switch')


def _id(r):
    return f'CNV_Scat{r:g}'


def units():
    return [shell_v4(_id(r), damage=HIT, scatter=r, reload=RELOAD,
                     what=f'散布 V4（探针）：锤子炮弹、弹头半径 0、{HIT:g} 伤害，ScatterRadius {r:g}，'
                          f'装填 {RELOAD:g} 秒，无预瞄、无开火持续')
            for r in RADII] + [target()]


def mission():
    m = Mission(name='CampScatter', map=probe_range, units=units(), facts={})
    for r, lane in zip(RADII, LANES):
        m.put(_id(r), f'{lane} gun', side='p1', role=f'scatter {r:g} shooter', name=f'UNIT - CNV Scat {r:g} Shooter')
        m.put(TARGET_ID, f'{lane} gun', 0, AT, side='s1', role=f'scatter {r:g} target',
              name=f'UNIT - CNV Scat {r:g} Target')
    m.spawns |= {_id(r) + 'Projectile' for r in RADII}
    return m


def scatter_test(m):
    t = Test()
    pairs = [(m.role(f'scatter {r:g} shooter').name, m.role(f'scatter {r:g} target').name) for r in RADII]
    start = [('MAP_REVEAL_ALL_PERM', m.player('p1'))]
    start += [('UNIT_CHANGE_OBJECT_STATUS', x, 'NO_ATTACK', 1) for p in pairs for x in p]
    start += [('SET_MILLISECOND_TIMER', 'Test Order', ORDER)]
    t.scripts.append(Script('Test - start', [], start))
    t.scripts.append(Script('Test - order', [('TIMER_EXPIRED', 'Test Order')],
                            [('UNIT_CHANGE_OBJECT_STATUS', s, 'NO_ATTACK', 0) for s, _ in pairs]
                            + [('NAMED_ATTACK_NAMED', s, tg) for s, tg in pairs]))
    for k, (r, (_, tg)) in enumerate(zip(RADII, pairs)):
        c = f'CNV_Scat_{k}'
        t.counters.append((c, f'r{r:g}'))
        t.scripts += [Script(f'Test - {c} lost {j}', [('UNIT_HEALTH', tg, 0, 100 - j + 1)],
                             [('INCREMENT_COUNTER', 1, c)]) for j in range(1, LOST_MAX + 1)]
    t.expect = [('r0', 0, 'ever>=', 10, RUN - 1)]
    t.bench = [('bench_watch', dict(seconds=RUN, every=1, sheet=False, lines=6))]
    return t


CYCLES = 40


def cycle_test(m):
    """The 0.5 s reload's shot-to-shot cycle, by the game's own frames (the watch's seconds are wall clock x rate,
    so a count at 's30' is not at the mission's 30 s): R 0's target loses 1 % a hit, and 帧数 counts the frames
    from the first hit (health below 100 %) to the (CYCLES + 1)th (below 100 - CYCLES %) = CYCLES cycles."""
    t = Test()
    s, tg = m.role('scatter 0 shooter').name, m.role('scatter 0 target').name
    others = [m.role(f'scatter {r:g} shooter').name for r in RADII[1:]]
    start = [('MAP_REVEAL_ALL_PERM', m.player('p1'))]
    start += [('UNIT_CHANGE_OBJECT_STATUS', x, 'NO_ATTACK', 1) for x in [s, tg] + others]
    start += [('SET_MILLISECOND_TIMER', 'Test Order', ORDER)]
    t.scripts.append(Script('Test - start', [], start))
    t.scripts.append(Script('Test - order', [('TIMER_EXPIRED', 'Test Order')],
                            [('UNIT_CHANGE_OBJECT_STATUS', s, 'NO_ATTACK', 0), ('NAMED_ATTACK_NAMED', s, tg)]))
    t.counters.append(('CNV_Scat_0', 'r0'))
    t.scripts += [Script(f'Test - CNV_Scat_0 lost {j}', [('UNIT_HEALTH', tg, 0, 100 - j + 1)],
                         [('INCREMENT_COUNTER', 1, 'CNV_Scat_0')]) for j in range(1, LOST_MAX + 1)]
    t.counters.append(('CNV_Scat_F', '帧数'))
    t.scripts.append(Script('Test - CNV_Scat_F', [('UNIT_HEALTH', tg, 0, 100), ('UNIT_HEALTH', tg, 3, 100 - CYCLES)],
                            [('INCREMENT_COUNTER', 1, 'CNV_Scat_F')], once=False))
    t.expect = [('帧数', 0, 'ever>=', CYCLES * 6, RUN - 1)]
    t.bench = [('bench_watch', dict(seconds=RUN, every=1, sheet=False, lines=2))]
    return t


SPANS = ((1, 5), (5, 11), (11, 21), (21, 41))


def spans_test(m):
    """cycle_test's frames cut into SPANS: counter k counts the frames from hit a to hit b (health in
    [100 - b + 1, 100 - a] %), i.e. b - a cycles -- where the shorter cycles fall.

    Read (11-05): cyc CampScatterCyc_mcp_1105_205319 帧数 316 (hits 1 -> 41); span CampScatterSpan_mcp_1105_205644
    28 / 48 / 80 / 160: from hit 5 on every cycle is 8 frames (0.5 s -> ceil 7.5), the first four after the attack
    starts 7. Round 35's '50 shots in 24 s' read the watch's seconds (wall clock x rate) as mission time."""
    t = cycle_test(m)
    t.counters, t.scripts = [], [x for x in t.scripts if not x.name.startswith('Test - CNV_Scat_')]
    tg = m.role('scatter 0 target').name
    for k, (a, b) in enumerate(SPANS):
        c = f'CNV_Scat_S{k}'
        t.counters.append((c, f'{a}-{b}'))
        t.scripts.append(Script(f'Test - {c}', [('UNIT_HEALTH', tg, 0, 100 - a + 1), ('UNIT_HEALTH', tg, 3, 100 - b + 1)],
                                [('INCREMENT_COUNTER', 1, c)], once=False))
    t.expect = [(f'{a}-{b}', 0, 'ever>=', (b - a) * 6, RUN - 1) for a, b in SPANS]
    t.bench = [('bench_watch', dict(seconds=RUN, every=1, sheet=False, lines=len(SPANS)))]
    return t


MISSION = {'engine_scatter': mission}
CHECKS = {'engine_scatter': {'hits': scatter_test, 'cyc': cycle_test, 'span': spans_test}}
