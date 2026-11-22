"""NeutralGarrison/native named-slot selection; evidence work/re/c_garrison_report.md.

Counter verifies the placed control survives through the selection window.
Only target_picks establishes the native heuristic's selection verdict.
"""
from parts import Test, Script


def a(m):
    t = Test()
    names = [m.role(r).name for r in ('plant', 'barracks', 'tank')]
    names += [m.role(f'ai guardian {i}').name for i in range(1, 5)]
    t.scripts.append(Script('Garr keep', [],
        [('UNIT_SET_HEALTH', n, 100.0) for n in names], once=False))
    t.scripts.append(Script('Garr reveal', [],
        [('MAP_REVEAL_ALL_PERM', m.player('p1'))]))
    t.counters.append(('GarrControl', 'control alive'))
    control = m.role('garr control').name
    t.scripts.append(Script('Garr alive reset', [], [('SET_COUNTER', 'GarrControl', 0)], once=False))
    t.scripts.append(Script('Garr alive', [('NAMED_NOT_DESTROYED', control)],
        [('SET_COUNTER', 'GarrControl', 1)], once=False))
    # Original off capture missed every sample in s2-s3; keep that FAIL in
    # private evidence. Check the whole selection window, with the same value.
    t.expect = [('control alive', 1, '==', 1, 15)]
    t.bench = [('bench_watch', dict(seconds=15, every=1, sheet=False, lines=1))]
    return t


def b(m, health=False):
    """aigarrbld: the Garrison state's team -- Peacekeepers at home / in all, the player's plant standing, the shop the
    AI's; c (health): the plant's health % in place of the Peacekeepers' count (how fast they take it down)."""
    from checks import engine_aitarget as at
    from parts import counted, square
    INF = m.role('ai inf 1').template
    t = Test()
    s1 = m.player('s1')
    t.scripts.append(Script('Garr reveal', [], [('MAP_REVEAL_ALL_PERM', m.player('p1'))]))
    t.areas[at.HOME] = square(*m.site('east base'), 450.0)
    counted('CNV_GB_Home', '步兵在家', t, template=INF, area=at.HOME, player=s1)
    if health:
        counted('CNV_GB_Count', '电厂血', t, health=m.role('plant').name)
    else:
        counted('CNV_GB_Count', '步兵数', t, template=INF, player=s1)
    counted('CNV_GB_Plant', '电厂在', t, template='AlliedPowerPlant', player=m.player('p1'))  # the team state's fight
    counted('CNV_GB_Shop', '商店归AI', t, template='HV_Shop01', player=s1)
    t.scripts.append(Script('Test - count CNV_GB_Row', [], [('SET_PLAYER_OWNERSHIP_OF_TYPE_COUNTER', 'AM_RowHouse01', s1,
                                                            'CNV_GB_Row')], once=False))   # off screen (OCR reads 4)
    end = m.facts['wake at'] + 60.0
    t.expect = [('步兵在家', m.facts['wake at'] + 5, 'ever==', 0, end)]      # the model: the team leaves for a house
    t.bench = [('bench_watch', dict(seconds=end + at.LAG, every=1, sheet=False, lines=len(t.counters)))]
    return t


CHECKS = {build: {'a': a} for build in ('aigarron', 'aigarroff')}
CHECKS['aigarrbld'] = {'b': b, 'c': lambda m: b(m, health=True)}
