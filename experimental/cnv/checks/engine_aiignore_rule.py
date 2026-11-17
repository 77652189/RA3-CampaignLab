"""IgnoreTargets.Rule ANY/ALL with the retail EASY inclusion mask.

Prediction: ANY permits the engineers, ALL filters their micro target slots.
Damage is latched separately because ordinary attacks can bypass that slot.
Read CNVTeams state/target/members on the same run's game clock; a damage PASS
alone never establishes Rule coverage. See work/re/e118_ignore_rule.md.

MEASURED: ANY first hurt f396 and state 0/nonempty target at f406/421;
ALL first hurt f397 and state 8/empty target at those frames. Both have two
members at f376/391 and prerequisite bad=0. ALL retains diagnostic FAIL:
the wall-clock s22..24 owned count is still 1, although game-frame recruitment
preconditions pass. Do not change that window to fit this run. Model ALL state
replays; ANY candidate/Alpha eligibility remains a strict xfail, no promotion.
"""
from model import Script
from checks.engine_aiignore import probe as distance_probe


def probe(m):
    t = distance_probe(m)
    frame, own, hit, first, bad = ('CNV_I_Frame', 'CNV_I_Own', 'CNV_I_Hit',
                                   'CNV_I_First', 'CNV_IR_Bad')
    # A target cannot contaminate the two-member recruitment window. Latch any
    # violated prerequisite rather than hiding it between HUD samples.
    for counter, op, value in ((own, 0, 2), (own, 4, 2), (hit, 4, 0)):
        t.scripts.append(Script(f'Rule - prerequisite {counter} {op}',
            [('COUNTER', frame, 3, 375), ('COUNTER', frame, 0, 390),
             ('COUNTER', counter, op, value)], [('SET_COUNTER', bad, 1)]))
    t.counters = [(frame, '帧数'), (own, '造出'), (first, '首伤'), (bad, '失配')]
    t.expect = [('帧数', 1, 'ever>=', 600, 50), ('造出', 22, '==', 2, 50),
                ('首伤', 1, 'ever>=', 390, 50), ('失配', 1, '==', 0, 50)]
    t.bench = [('bench_watch', dict(seconds=52, every=2, sheet=False, lines=4))]
    return t


CHECKS = {name: {'r': probe} for name in ('aiignrany', 'aiignrall')}
