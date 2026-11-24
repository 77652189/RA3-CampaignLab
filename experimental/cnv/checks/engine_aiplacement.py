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


def b(m):
    """aiplb*: the AI's own core; the plant counted in squares round the yard (half-sides 450 / 1000). No total plant
    count: the type-ownership counter never counted the unpacked plant (bench 11-24: 0 while both squares read 1)."""
    t = Test()
    s1 = m.player('s1')
    yard = m.find(m.role('ai yard').name)
    for key, label, template, half in (('Core', '核心', 'JapanPowerPlantEgg', 0), ('Near', '近450', 'JapanPowerPlant', 450),
                                       ('Mid', '近1000', 'JapanPowerPlant', 1000)):
        area = f'CNV PlB {key}' if half else None
        if area:
            t.areas[area] = square(yard.x, yard.y, half)
        counted('CNV_PlB_' + key, label, t, template=template, player=s1, area=area)
    near = int(m.facts['placement distance'] < 1000)
    t.expect += [('核心', 55, '==', 0, 60), ('近450', 55, '==', near, 60), ('近1000', 55, '==', 1, 60)]
    t.bench = [('bench_watch', dict(seconds=60, every=1, sheet=False, lines=4))]
    return t


CHECKS = {key: {'a': a} for key in ('aiplace1', 'aiplace200', 'aiplacej200')}
CHECKS |= {key: {'b': b} for key in ('aiplb600', 'aiplb1500')}
