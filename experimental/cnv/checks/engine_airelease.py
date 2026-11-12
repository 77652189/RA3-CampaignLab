"""Direct named-team release observation; 99 means the instance is absent.

Prediction (INFERRED until measured): both defense teams first hold two;
after the timed STANDARD consumer starts, priority releases two to attack,
NEVER_RELEASE keeps them. No production, deaths or other candidate units.

RESULTS (2026-11-12): both diagnostic checks FAIL. Defense/attack remain
99/99, live tanks 2, initial-hold latch 0 throughout (never s1-70,
priority s1-73). Recruitment is unobserved; no release conclusion follows.
Model reads 0/0 instead; strict xfails retain the observation gap.
See work/re/c_never_release_report.md; B/D team/member interface needed.
"""
from model import Script, Test, counted


def a(m):
    t = Test()
    t.scripts.append(Script('Release - reveal', [], [('MAP_REVEAL_ALL_PERM', m.player('p1'))]))
    for key, counter, label in [('release defense', 'CNV_R_Def', '防御人数'),
                                 ('release attack', 'CNV_R_Atk', '进攻人数')]:
        team = m.map.TEAMS[key]
        t.counters.append((counter, label))
        t.scripts.append(Script(f'Release - {key} absent', [], [('SET_COUNTER', counter, 99)], once=False))
        for n in range(3):
            t.scripts.append(Script(f'Release - {key} below {n}',
                                    [('TEAM_COMPARE_NUM_MEMBERS', team, 2, n)],
                                    [('SET_COUNTER', counter, n)], once=False))
    counted('CNV_R_Live', '坦克总数', t, player=m.player('s1'), template=m.cnv_units[0])
    t.counters.append(('CNV_R_Held', '曾防御量'))
    t.scripts.append(Script('Release - held', [('COUNTER', 'CNV_R_Def', 2, 2)],
                            [('SET_COUNTER', 'CNV_R_Held', 2)]))
    never = m.facts['never release']
    t.expect = [('防御人数', 25, '==', 2, 29), ('曾防御量', 25, '==', 2),
                ('坦克总数', 1, '==', 2),
                ('防御人数', 55, '==', 2, 65)] if never else [
                    ('防御人数', 25, '==', 2, 29), ('曾防御量', 25, '==', 2),
                    ('坦克总数', 1, '==', 2), ('进攻人数', 55, '==', 2, 65)]
    t.bench = [('bench_watch', dict(seconds=69, every=1, sheet=False, lines=4))]
    return t


CHECKS = {name: {'a': a} for name in ('airelnever', 'airelprio')}
