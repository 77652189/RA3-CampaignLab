"""SkirmishOpeningMove.Side: explicit opening on a fixed Allied player.

Only the opening's Side changes Allies/Soviet. Three consecutive power-plant
orders make its execution visible independently of infantry production.
Pre-bench default model prediction: at s55 three plants, zero barracks in
both builds. E82 bench: Allies PASS (3/0), Soviet FAIL (2/1), [s55,s60).
The original failed prediction stays here; the replay uses engine readings,
with strict xfail for Soviet. Side selection/fallback remains a model gap.
Evidence: work/re/e_openside_e82.md.
"""
from parts import Script, Test, counted


def a(m):
    t = Test()
    t.scripts.append(Script('Side reveal', [], [('MAP_REVEAL_ALL_PERM', m.player('p1'))]))
    for key, label, template in (('Power', '电厂数', 'AlliedPowerPlant'),
                                 ('Barracks', '兵营数', 'AlliedBarracks')):
        m.spawns.add(template)
        counted('Side' + key, label, t, template=template, player=m.player('s1'))
    t.expect = [('电厂数', 55, '==', 3, 60), ('兵营数', 55, '==', 0, 60)]
    t.bench = [('bench_watch', dict(seconds=64, every=1, sheet=False, lines=2))]
    return t


CHECKS = {name: {'a': a} for name in ('aiosallies', 'aiossoviet')}
