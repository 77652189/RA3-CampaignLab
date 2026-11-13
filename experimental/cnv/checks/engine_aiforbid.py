"""Native status and target-area counters; work/re/c_forbid_report.md.

Read the named plant's original status every frame alongside area counts.
No candidate-eligibility interface: any ambiguous outcome remains a gap.
"""
from model import Test, Script, counted, square, status


def a(m):
    t = Test()
    plant = m.role('plant').name
    t.counters.append(('CNV_Forbid_Status', '状态'))
    condition = ('UNIT_HAS_OBJECT_STATUS', plant, status('UNDER_IRON_CURTAIN'))
    t.scripts.append(Script('Test - forbid reset', [],
                           [('SET_COUNTER', 'CNV_Forbid_Status', 0)], once=False))
    t.scripts.append(Script('Test - forbid on', [condition],
                           [('SET_COUNTER', 'CNV_Forbid_Status', 1)], once=False))
    if m.facts.get('read unattackable'):
        t.scripts.append(Script('Test - unattackable on',
            [('UNIT_HAS_OBJECT_STATUS', plant, status('UNATTACKABLE'))],
            [('INCREMENT_COUNTER', 2, 'CNV_Forbid_Status')], once=False))
    keep = [m.role(r).name for r in ('plant', 'barracks', 'tank')]
    keep += [m.role(f'ai guardian {i}').name for i in range(1, 5)]
    t.scripts.append(Script('Test - forbid keep', [],
        [('UNIT_SET_HEALTH', n, 100.0) for n in keep], once=False))
    t.scripts.append(Script('Test - forbid reveal', [], [('MAP_REVEAL_ALL_PERM', m.player('p1'))]))
    for role, label in [('plant', '近处'), ('barracks', '远处')]:
        o = m.find(m.role(role).name)
        area = 'CNV Forbid ' + role
        t.areas[area] = square(o.x, o.y, 340)
        counted('CNV_Forbid_' + role, label, t, template=m.cnv_units[0], area=area, player=m.player('s1'))
        t.expect.append((label, 40, '==', m.facts['expect ' + role], 41))
    x, y = m.site('east base')
    t.areas['CNV Forbid Home'] = [(x-300,y-400),(x+300,y-400),(x+300,y+450),(x-300,y+450)]
    counted('CNV_Forbid_Home', '在家', t, template=m.cnv_units[0], area='CNV Forbid Home', player=m.player('s1'))
    t.expect += [('在家', 40, '==', 0, 41), ('状态', 5, '==', m.facts['status set'], 41)]
    t.bench = [('bench_watch', dict(seconds=54, every=1, sheet=False, lines=len(t.counters)))]
    return t


CHECKS = {k: {'a': a} for k in ('aiforbidnone', 'aiforbidset', 'aiforbidclear',
                              'aifmasknone', 'aifmaskiron', 'aifmaskboth',
                              'aifunanone', 'aifunasingle', 'aifunaboth')}
