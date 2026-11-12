"""Base-distance IgnoreTargets gate contrast with unarmed, stationary engineers.

INFERRED prediction from the field name and retail 700/0 values: radius 0
ignores the engineers; radius 2000 allows attacks near the base. Both cases
have identical geometry, Hunt recruitment and disabled powers/pullback/dodge.
Engineers appear only after 26 s and two warriors are owned: the rejected
initial probe let the first warrior attack before a two-member team existed.
The hit latch uses game frames; capture seconds are only an observation window.
Damage alone cannot distinguish a micro pick from a Hunt/weapon target pick.
An equal outcome leaves that dispatch boundary unresolved; never tune the model
to this indirect measurement. See work/re/c_ignore_distance_report.md.

MEASURED: delayed targets, radius 0 first hurt frame 397; radius 2000 frame
396. Both own two warriors and pass the pre-target no-damage check. Radius 0
keeps its original diagnostic FAIL; radius 2000 PASS. Named replay asserts
the observed damage in both, not the rejected filtering prediction. The model
consumer and exact base/distance/dispatch rules remain gaps.
"""
from model import Script, Test, counted


def probe(m):
    t = Test()
    t.scripts += [Script('Ignore - reveal', [], [('MAP_REVEAL_ALL_PERM', m.player('p1'))]),
                  Script('Ignore - frame', [], [('INCREMENT_COUNTER', 1, 'CNV_I_Frame')], once=False)]
    t.counters.append(('CNV_I_Frame', '帧数'))
    counted('CNV_I_Own', '造出', t, template=m.cnv_units[0], player=m.player('s1'))
    t.counters += [('CNV_I_Hit', '受伤'), ('CNV_I_First', '首伤')]
    for role, target in sorted(m.cnv_named.items()):
        t.scripts.append(Script('Ignore - hit ' + role,
                                [('NAMED_NOT_DESTROYED', target), ('UNIT_HEALTH', target, 0, 100),
                                 ('COUNTER', 'CNV_I_Hit', 2, 0)],
                                [('SET_COUNTER', 'CNV_I_Hit', 1),
                                 ('SET_COUNTER_TO_COUNTER', 'CNV_I_First', 'CNV_I_Frame')]))
    t.expect = [('造出', 20, 'ever>=', 2, 50), ('受伤', 1, '==', 0, 24),
                ('受伤', 28, 'ever>=' if m.facts['ignore base distance'] else '==',
                 1 if m.facts['ignore base distance'] else 0, 50)]
    t.bench = [('bench_watch', dict(seconds=52, every=3, sheet=False, lines=4))]
    return t


CHECKS = {name: {'r': probe} for name in ('aiignzero', 'aiignnear')}


def observe(m):
    """Separate CNVTeams diagnostics; coverage is checked on the game clock.

    The carrier's equivalence to the original pair is unresolved. Preserve the
    rejected filtering prediction and do not promote these runs as coverage.
    Evidence: work/re/c_ignore_state_report.md.
    """
    t = probe(m)
    t.expect = [('帧数', 1, 'ever>=', 600, 240),
                ('造出', 1, 'ever>=', 2, 240),
                ('受伤', 1, '==', 0, 24),
                ('受伤', 28, 'ever>=' if m.facts['ignore base distance'] else '==',
                 1 if m.facts['ignore base distance'] else 0, 240)]
    t.bench = [('bench_watch', dict(seconds=242, every=5, sheet=False, lines=4))]
    return t


CHECKS.update({name: {'r': observe} for name in ('aiignzt', 'aiignnt')})
