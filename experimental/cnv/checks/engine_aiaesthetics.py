"""UseAestheticsManager true/false at fixed Distance=2000.

Named square occupancy, a post-timer displacement latch and survival separate
movement from loss or failed teleport. No dynamic membership or exact circle
geometry is claimed. Predictions/evidence: work/re/c_aesthetics_report.md.

RESULTS: both builds PASS (5/5). Enabled leaves 300 before displacement,
returns inside 900, then leaves again. Disabled returns inside both squares.
Both survive and latch displacement. Model location replays strict xfail;
stand-point/readiness consumers need B investigation, no inventory promotion.
"""
from model import Script, Test, counted, square


def a(m):
    t = Test()
    name = m.role('ai guardian 1').name
    for radius in (300, 900):
        area = f'CNV Aes Ring {radius}'
        t.areas[area] = square(*m.site('east base'), radius)
        counted(f'CNV_Aes_R{radius}', f'圈{radius}', t, named=name, area=area)
    t.counters += [('CNV_Aes_Pushed', '传送出圈')]
    t.scripts += [Script('Aesthetics - reveal', [], [('MAP_REVEAL_ALL_PERM', m.player('p1'))]),
                  Script('Aesthetics - displacement',
                         [('TIMER_EXPIRED', 'CNV Distance Push'),
                          ('NAMED_OUTSIDE_AREA', name, 'CNV Aes Ring 900')],
                         [('SET_COUNTER', 'CNV_Aes_Pushed', 1)])]
    counted('CNV_Aes_Alive', '坦克总数', t, template=m.cnv_units[0], player=m.player('s1'))
    home = 1 - m.facts['aesthetics enabled']
    t.expect = [('圈900', 20, '==', 1, 21), ('传送出圈', 65, '==', 1, 66),
                ('坦克总数', 65, '==', 1, 66), ('圈300', 65, '==', home, 66),
                ('圈900', 65, '==', home, 66)]
    t.bench = [('bench_watch', dict(seconds=74, every=1, sheet=False, lines=4))]
    return t


CHECKS = {name: {'a': a} for name in ('aiaeson', 'aiaesoff')}
