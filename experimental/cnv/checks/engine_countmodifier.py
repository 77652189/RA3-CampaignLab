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


def b(m):
    """B round 206: who else spends the opening's PRODUCTION Deposit 2000. The model (simai, before bench) has the
    retail barracks buy 3 dogs + 1 Javelin + 1 Peacekeeper = 1100 in both, the copied one 3 Javelins = 900 (aicmhalf,
    the Deposit spent: stops at 4/5 as the bench) and 5 Peacekeepers = 1000 (aicmfour, the last paid 100; the bench
    stops at 7/2). Prediction: the bench's retail barracks spends 1400 in aicmfour (one more unit than the model), so
    both groups stop with the Deposit gone. Counters: the copied unit the state builds, retail dogs, Javelins,
    Peacekeepers (four lines)."""
    t = Test()
    t.scripts.append(Script('CM reveal', [], [('MAP_REVEAL_ALL_PERM', m.player('p1'))]))
    new = ('CNVNewPK', 'PK', '新维和') if m.facts['count modifier'] > 1 else ('CNVNewJav', 'JAV', '新标枪')
    for template, suffix, label in [new, ('AlliedScoutInfantry', 'DOG', '狗'),
                                    ('AlliedAntiVehicleInfantry', 'RJ', '原标枪'),
                                    ('AlliedAntiInfantryInfantry', 'RP', '原维和')]:
        m.spawns.add(template)           # published for the contract: the AI makes it, the check counts it
        counted('CNV_CM_' + suffix, label, t, template=template, player=m.player('s1'))
    t.bench = [('bench_watch', dict(seconds=65, every=1, sheet=False, lines=2))]
    return t


CHECKS = {build: {'a': a, 'b': b} for build in ('aicmhalf', 'aicmfour')}
