"""Distance 250/2000: retained StaticDefense Guardian displaced 1200 south.

Only Distance differs in the original pair. The 2000 build now also carries
CNVTeams (15-frame samples); named square occupancy alone does not observe
dynamic team membership or exact radial geometry. The per-frame displacement latch
proves teleport success independently of screenshot timing. Predictions are
recorded before bench execution in work/re/c_distance_report.md.

RESULTS: both builds PASS (five endpoint checks each). Small returns to the
900 square at s33, 300 at s41. Large leaves 300 at s15 before the teleport,
returns inside 900 at s34, then leaves 900 again at s56. Both remain alive.
The model matches endpoints but misses the large group's excursion: strict
xfail in test_simai_bench_c.py. No inventory promotion; aesthetics remains gap.

E92: the initial Guardian's ID persists across 68 position samples. Its
(300, 900) square occupancy changes at frames 166/256/451/541/871:
11 -> 01 -> 00 -> 01 -> 00. The model only reproduces 11 -> 00.
One extra member appears only at frame 391; its identity remains a gap.
Raw log, trajectory assertions and same-frame comparison: work/re/e_distance_e92.md.
"""
from model import Script, Test, counted, square


def a(m):
    t = Test()
    name = m.role('ai guardian 1').name
    for radius in (300, 900):
        area = f'CNV Distance Ring {radius}'
        t.areas[area] = square(*m.site('east base'), radius)
        counted(f'CNV_D_R{radius}', f'圈{radius}', t, named=name, area=area)
    t.counters += [('CNV_D_Pushed', '曾出圈')]
    t.scripts += [Script('Distance - reveal', [], [('MAP_REVEAL_ALL_PERM', m.player('p1'))]),
                  Script('Distance - displacement', [('NAMED_OUTSIDE_AREA', name, 'CNV Distance Ring 900')],
                         [('SET_COUNTER', 'CNV_D_Pushed', 1)])]
    counted('CNV_D_Alive', '坦克总数', t, template=m.cnv_units[0], player=m.player('s1'))
    home = int(m.facts['distance'] == 250)
    t.expect = [('圈900', 20, '==', 1, 21), ('曾出圈', 65, '==', 1, 66),
                ('坦克总数', 65, '==', 1, 66), ('圈300', 65, '==', home, 66),
                ('圈900', 65, '==', home, 66)]
    t.bench = [('bench_watch', dict(seconds=74, every=1, sheet=False, lines=4))]
    return t


CHECKS = {name: {'a': a} for name in ('aidist250', 'aidist2000')}
