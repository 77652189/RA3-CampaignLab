"""C unpack placement: raw core, total plant, local plant and host counts.

Predictions remain hypotheses until the named bench runs have been read.
See work/re/c_placement_report.md for evidence and unresolved eligibility.
"""
from parts import Test, counted, square


def a(m):
    t = Test()
    s1 = m.player('s1')
    core = m.find(m.role('core').name)
    t.areas['CNV Placement Local'] = square(core.x, core.y, 250)
    for key, label, template, area in (
        ('Core', '核心', 'JapanPowerPlantEgg', None),
        ('Plant', '电厂', 'JapanPowerPlant', None),
        ('Local', '近处电厂', 'JapanPowerPlant', 'CNV Placement Local'),
        ('Host', '宿主', 'CNVTeamsHost', None),
    ):
        counted('CNV_Placement_' + key, label, t, template=template, player=s1, area=area)
    plant = int(m.facts['placement distance'] == 200)
    t.expect += [('核心', 35, '==', 1 - plant, 40), ('电厂', 35, '==', plant, 40),
                 ('近处电厂', 35, '==', plant, 40), ('宿主', 35, '==', 1, 40)]
    t.bench = [('bench_watch', dict(seconds=45, every=1, sheet=False, lines=4))]
    return t


CHECKS = {key: {'a': a} for key in ('aiplace1', 'aiplace200', 'aiplacej200')}
