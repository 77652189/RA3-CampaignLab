"""S2 tests (the plan: docs/story/plans/s2.md). Counted: which stop each train last reached (the device's own stop
counters), both trains kept at full health -- the test is about where they go.

catch: when the cryo train reaches the river station, test script destroys it -- the mission is over (won); both
  trains got there by the route.
escape: nothing is done -- the cryo train runs its route to the end and the mission is over (lost).
"""
from parts import Script, Test

RUN = 420.0


def setup(m):
    t = Test()
    t.scripts.append(Script('Test - reveal', [], [('MAP_REVEAL_ALL_PERM', m.player('p1'))]))
    for part in ('armoured', 'cryo'):
        t.scripts.append(Script(f'Test - keep {part} up', [], [('UNIT_SET_HEALTH', m.role(part).name, 100.0)],
                                once=False))
    # the device's stop counters, shown (S2's tag: CNV_S2_<Role>)
    t.counters += [('CNV_S2_Cryo Stop', '冷冻列车到站'), ('CNV_S2_Armoured Stop', '装甲列车到站')]
    return t


def catch(m):
    t = setup(m)
    t.scripts = [s for s in t.scripts if s.name != 'Test - keep cryo up']
    t.scripts.append(Script('Test - catch', [('COUNTER', 'CNV_S2_Cryo Stop', 3, 3)],
                            [('NAMED_KILL', m.role('cryo').name)]))
    t.expect += [('冷冻列车到站', 5, 'ever>=', 1), ('装甲列车到站', 5, 'ever>=', 2), ('ENDED', 30, '', None)]
    t.bench = [('bench_watch', dict(seconds=RUN, every=5, sheet=False, lines=len(t.counters)))]
    return t


def escape(m):
    t = setup(m)
    t.expect += [('冷冻列车到站', 5, 'ever>=', 4), ('ENDED', 60, '', None)]
    t.bench = [('bench_watch', dict(seconds=RUN, every=5, sheet=False, lines=len(t.counters)))]
    return t
