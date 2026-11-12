"""CreateUnits.UnitName / MinUnits isolated slot probe (C line).

aicr1:a / aicr3:a: the same opener produces three Guardians, no placed tanks.
Four unrelated Peacekeepers start at home. Prediction: only the named Guardians
join the attack team; minimum 3 waits for the third, minimum 1 can leave earlier.
TeamTemplate.MinUnits=1 and CreateUnits.MaxUnits=3 in both variants. Production
itself is supplied by the opener: this does not claim CreateUnits creates units.
No exact timing, replacement, multiple slots or MaxUnits rule is established.
Evidence and model gaps: work/re/c_create_report.md.

RESULTS (2026-11-11; owned / home Guardians, home Peacekeepers, named team):
aicr1:a FAIL: s19 first Guardian, s29 1/0/2/99; s41-85 3/2/2/99.
aicr3:a PASS: s19 1/1/4/99, s30 2/2/4/99, s41 3/3/4/99,
s48 3/2/4/99, s49-85 3/0/4/99. Named-team membership is NOT established.
The original aicr1 all-tanks-out / no-infantry-out expectations are retained
as a failed prediction, not widened to PASS. Model replay is strict xfail;
neither field is promoted. INFERRED: slot minimum plus general recruitment
can explain the mixed departure at minimum 1; exact members are still a gap.
"""
from parts import Test, Script, counted, square


def a(m):
    t = Test()
    tank, infantry = m.cnv_units
    s1 = m.player('s1')
    area = 'CNV Create Home'
    t.areas[area] = square(*m.site('east base'), m.facts['home radius'])
    t.scripts.append(Script('Test - reveal', [], [('MAP_REVEAL_ALL_PERM', m.player('p1'))]))
    counted('CNV_CR_Total', '坦克总数', t, template=tank, player=s1)
    counted('CNV_CR_Home', '坦克在家', t, template=tank, player=s1, area=area)
    counted('CNV_CR_Inf', '步兵在家', t, template=infantry, player=s1, area=area)
    team = m.team('create team')
    t.counters.append(('CNV_CR_Team', '招人队员'))
    t.scripts.append(Script('Test - unknown', [], [('SET_COUNTER', 'CNV_CR_Team', 99)], once=False))
    for n in range(9):
        t.scripts.append(Script(f'Test - members {n}', [('TEAM_COMPARE_NUM_MEMBERS', team, 2, n)],
                                [('SET_COUNTER', 'CNV_CR_Team', n)], once=False))
    t.expect = [('坦克总数', 70.0, '==', 3, 71.0), ('步兵在家', 70.0, '==', 4, 71.0),
                ('坦克在家', 70.0, '==', 0, 71.0)]
    t.bench = [('bench_watch', dict(seconds=84.0, every=1, sheet=False, lines=4))]
    return t


CHECKS = {'aicr1': {'a': a}, 'aicr3': {'a': a}}
