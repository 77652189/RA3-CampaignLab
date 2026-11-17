"""Engine probe: how many frames an object with a LifetimeUpdate lives, and how long an ice engineer's power takes to
leave a wall (missions/life_bench.py; rules R1 and R5 of docs/story/sim-vs-bench-a4.md: the A4 bench read an ice
wall standing ~28 s of its 30, and a wall ~9 s after the order).

Frame 1 a script creates the named wall at A and the ice core at B; at ORDER s the two engineers are told to freeze
C and D (NAMED_FIRE_SPECIAL_POWER_AT_WAYPOINT; his power reloads 20 s, so it is ready). Each frame (15 a second):
  墙A  1 x frames the named wall is not destroyed  + 1000 x frames a wall stands in the square round A
  墙B  1 x frames a wall stands in the square round B + 1000 x frames the named core is not destroyed
  冰C  from the order: 1 x frames nothing of his stands at C yet + 1000 x frames his core stands there
  冰D  the same at D (engineer 2 walks 400 first)
So 墙A's units digits are the wall's life in frames, its thousands how long its body stands in the area; 墙B's
thousands the core's life, its units the wall it left. 冰C / 冰D: the order to the core (units), the core to the
wall (thousands). Read at the end only (the run outlasts all).
bench 2026-11-07 (frames, R1): 墙A 451451, 墙B 83450 -- a 30 s wall 450 frames, a 5.5 s core 82, its wall at once.
"""
from parts import Script, Test, square

RUN, ORDER = 52.0, 21.0


def frames(m):
    t = Test()
    p1 = m.player('p1')
    wall_a, core_b = 'UNIT - CNV Life Wall A', 'UNIT - CNV Life Core B'
    t.scripts += [Script('Test - start', [], [('MAP_REVEAL_ALL_PERM', p1),
                                              ('CREATE_NAMED_ON_TEAM_AT_WAYPOINT', wall_a, 'CNV_LifeWall', m.team('p1'),
                                               m.mark('life A')),
                                              ('CREATE_NAMED_ON_TEAM_AT_WAYPOINT', core_b, 'CNV_LifeSeed', m.team('p1'),
                                               m.mark('life B')),
                                              ('SET_FLAG', 'Test Made', 1),
                                              ('SET_MILLISECOND_TIMER', 'Test Order', ORDER)]),
                  Script('Test - order', [('TIMER_EXPIRED', 'Test Order')],
                         [('NAMED_FIRE_SPECIAL_POWER_AT_WAYPOINT', m.role(f'engineer {k}').name,
                           m.ability(f'engineer {k}', 'freeze'), m.mark(f'life {s}')) for k, s in ((1, 'C'), (2, 'D'))]
                         + [('SET_FLAG', 'Test Ordered', 1)])]
    for k in 'ABCD':
        t.areas[f'Test Life {k}'] = square(*m.point(f'life {k}'), 100.0)

    def there(template, k, n=1):
        return ('PLAYER_HAS_COMPARISON_UNIT_TYPE_IN_TRIGGER_AREA', p1, 3 if n else 2, n, template, f'Test Life {k}')

    made, ordered = [('FLAG', 'Test Made', 1)], [('FLAG', 'Test Ordered', 1)]
    t.scripts += [
        Script('Test - wall A alive', made + [('NAMED_NOT_DESTROYED', wall_a)],
               [('INCREMENT_COUNTER', 1, 'CNV_Life_A')], once=False),
        Script('Test - wall A there', made + [there('CNV_LifeWall', 'A')],
               [('INCREMENT_COUNTER', 1000, 'CNV_Life_A')], once=False),
        Script('Test - wall B there', made + [there('CNV_LifeWall', 'B')],
               [('INCREMENT_COUNTER', 1, 'CNV_Life_B')], once=False),
        Script('Test - core B alive', made + [('NAMED_NOT_DESTROYED', core_b)],
               [('INCREMENT_COUNTER', 1000, 'CNV_Life_B')], once=False)]
    for k in 'CD':
        t.scripts += [
            Script(f'Test - nothing at {k}', ordered + [there('CNV_LifeSeed', k, 0), there('CNV_LifeWall', k, 0)],
                   [('INCREMENT_COUNTER', 1, f'CNV_Life_{k}')], once=False),
            Script(f'Test - core at {k}', ordered + [there('CNV_LifeSeed', k)],
                   [('INCREMENT_COUNTER', 1000, f'CNV_Life_{k}')], once=False)]
    t.counters += [('CNV_Life_A', '墙A'), ('CNV_Life_B', '墙B'), ('CNV_Life_C', '冰C'), ('CNV_Life_D', '冰D')]
    life = m.facts['life'] * 15
    t.expect += [('墙A', RUN - 2, 'ever>=', life - 60),         # it stood about its lifetime (frames) ...
                 ('墙B', RUN - 2, 'ever>=', 1000),               # ... and the core lived and left a wall
                 ('冰C', RUN - 2, 'ever>=', 1000),               # each engineer's core came
                 ('冰D', RUN - 2, 'ever>=', 1000)]
    t.bench = [('bench_watch', dict(seconds=RUN, every=4, sheet=False, lines=len(t.counters)))]
    return t


CHECKS = {'engine_life': {'frames': frames}}
