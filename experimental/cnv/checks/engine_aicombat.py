"""AllowRecruitUnitsInCombat: does a team take a unit that is shooting at an enemy in range?

missions/aicombat_bench.py: fighter (inserted first, in a held fight until `fight ends`) and idle (out of sight).
First departure identity: 0 none, 1 fighter, 2 idle, 3 both in the same frame. 80-unit square per candidate.
Prediction (recruit gate read rule): off -> idle goes first, the fighter stays even after the fight (the team is
full at one); on -> the fighter is taken, the idle one stays home throughout.

RESULTS (2026-11-16, run_queue, both PASS): aicombat0 -- s1-s10 1 1 0 0, s11-s55 1 0 2 184 (idle leaves f184, the
fighter stays). aicombat1 -- s1-s28 1 1 0 0, s29-s55 0 1 1 462: the fighter is taken but shoots on where it stands
until its foe is deleted (s30), leaves f462; the idle one never leaves. Readings: engine_aicombat.readings.toml.
"""
from model import Script, Test, counted, square


def a(m):
    t = Test()
    t.scripts += [Script('Combat - reveal', [], [('MAP_REVEAL_ALL_PERM', m.player('p1'))]),
                  Script('Combat - clock', [], [('INCREMENT_COUNTER', 1, 'CNV_RC_Clock')], once=False)]
    outside = []
    for identity, name, pos in m.cnv_candidates:
        area = f'CNV Combat {identity}'
        t.areas[area] = square(*pos, m.facts['departure radius'])
        counted(f'CNV_RC_{identity}', '战者在原位' if identity == 'fighter' else '闲者在原位',
                t, named=name, area=area)
        outside.append(('NAMED_OUTSIDE_AREA', name, area))
    t.counters += [('CNV_RC_First', '首离身份'), ('CNV_RC_Frame', '首离帧')]
    for identity, conditions in ((3, outside), (1, outside[:1]), (2, outside[1:])):
        t.scripts.append(Script(f'Combat - first {identity}',
                                [('COUNTER', 'CNV_RC_First', 2, 0), *conditions],
                                [('SET_COUNTER', 'CNV_RC_First', identity),
                                 ('SET_COUNTER_TO_COUNTER', 'CNV_RC_Frame', 'CNV_RC_Clock')]))
    allow = m.facts['allow in combat']
    if allow:
        t.expect = [('闲者在原位', 1, '==', 1, 9), ('闲者在原位', 25, '==', 1, 26),
                    ('闲者在原位', 50, '==', 1, 51), ('战者在原位', 50, '==', 0, 51)]
    else:
        t.expect = [('闲者在原位', 1, '==', 1, 9), ('首离身份', 25, '==', 2, 26),
                    ('战者在原位', 25, '==', 1, 26), ('战者在原位', 50, '==', 1, 51)]
    t.bench = [('bench_watch', dict(seconds=54, every=1, sheet=False, lines=4))]
    return t


CHECKS = {name: {'a': a} for name in ('aicombat0', 'aicombat1')}
