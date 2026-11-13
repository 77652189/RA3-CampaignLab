"""CountModifier 0.5/4 contrast, identical seeded counts 4/2 and one copied factory.

Prediction before bench: FEWEST_UNIT scores at 4/2 are 11.11/33.33 for
0.5 and 50/33.33 for 4, so the higher modifier should favour Peacekeepers.
This is a model prediction, not a measured engine score. Record 65 seconds;
candidate eligibility and per-factory choice remain gaps without direct readings.
"""
from parts import Test, Script, counted


def a(m):
    t = Test()
    t.scripts.append(Script('CM reveal', [], [('MAP_REVEAL_ALL_PERM', m.player('p1'))]))
    for template, suffix, label in [('CNVNewPK', 'PK', '新维和'), ('CNVNewJav', 'JAV', '新标枪')]:
        counted('CNV_CM_' + suffix, label, t, template=template, player=m.player('s1'))
    t.bench = [('bench_watch', dict(seconds=65, every=1, sheet=False, lines=2))]
    return t


CHECKS = {build: {'a': a} for build in ('aicmhalf', 'aicmfour')}
