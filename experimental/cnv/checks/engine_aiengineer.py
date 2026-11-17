"""Engineer tactic isolation: named target ownership, approach and survival.

INFERRED competing prediction: Engineer captures the enemy plant and consumes
the engineer; SimpleAttack only approaches it. CaptureAnything micro and
CreateUnits are intentionally absent in both lanes. A failure narrows this
prediction, rather than establishing that Engineer cannot capture in retail.
Four direct counters avoid uncallable dynamic team names. See
work/re/c_engineer_report.md for pre-run model prediction and measured scope.

MEASURED (2026-11-12): Engineer s1-63 and control s1-74 both read
owner0/near0/live1/HP100. Both retain the original diagnostic FAIL.
The model replays these counters, but neither lane establishes recruitment
or a target dispatch. Engineer stays a gap; no tactic rule is promoted.
"""
from model import Script, Test, counted, square


def a(m):
    t = Test()
    engineer, target = m.cnv_named['engineer'], m.cnv_named['target']
    t.areas['Engineer target'] = square(*m.point('engineer target'), 180)
    t.scripts.append(Script('Engineer - reveal', [], [('MAP_REVEAL_ALL_PERM', m.player('p1'))]))
    counted('CNV_E_Owner', '目标归属', t, owner=target, player=m.player('s1'))
    counted('CNV_E_Near', '到目标量', t, named=engineer, area='Engineer target')
    counted('CNV_E_Live', '工程师量', t, template='AlliedEngineer', player=m.player('s1'))
    counted('CNV_E_HP', '目标血量', t, health=target)
    t.expect = [('目标归属', 1, '==', 0, 7), ('工程师量', 1, '==', 1, 7),
                ('到目标量', 12, 'ever==', 1, 50), ('目标血量', 1, '==', 100)]
    if m.facts['engineer tactic']:
        t.expect += [('目标归属', 20, 'ever==', 1, 60), ('工程师量', 20, 'ever==', 0, 60)]
    else:
        t.expect += [('目标归属', 1, '==', 0), ('工程师量', 1, '==', 1)]
    t.bench = [('bench_watch', dict(seconds=62, every=2, sheet=False, lines=4))]
    return t


CHECKS = {name: {'a': a} for name in ('aieng', 'aiengctl')}
