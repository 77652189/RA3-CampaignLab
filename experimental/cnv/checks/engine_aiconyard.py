"""C conyard minimum-distance diagnostic, not distance acceptance.

Observe core / total plant / local plant / host before and after 15s. Read
teamlog.target_picks and team membership from the same run; no movement proxy
can establish the real conyard exit or a placement candidate's eligibility.
Evidence and gate: work/re/c_conyard_report.md.
"""
from parts import Test, counted, square


def a(m):
    t = Test()
    core = m.find(m.role('core').name)
    t.areas['CNV Yard Local'] = square(core.x, core.y, 250)
    for key, label, template, area in (
        ('Core', '核心', 'JapanPowerPlantEgg', None),
        ('Plant', '电厂', 'JapanPowerPlant', None),
        ('Local', '近处电厂', 'JapanPowerPlant', 'CNV Yard Local'),
        ('Host', '宿主', 'CNVTeamsHost', None),
    ):
        counted('CNV_Yard_' + key, label, t, template=template, player=m.player('s1'), area=area)
    # Readings only: no distance verdict before eligibility and exit facts.
    t.bench = [('bench_watch', dict(seconds=40, every=1, sheet=False, lines=4))]
    return t


CHECKS = {key: {'a': a} for key in ('aicyard0', 'aicyard300')}
