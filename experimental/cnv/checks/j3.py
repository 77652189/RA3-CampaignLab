"""J3 tests (the plan: docs/story/plans/j3.md). Counted: Yuriko's health; in run, which leg of the way she is on.

run: Yuriko kept at full health, sent by test script round the castle hill's north side and up the back way to the
  archive (leg by leg, once a second, to the next point she has not reached), then back to the extraction once the escape starts -- the mission is over
  (won).
lose: Yuriko starts at 1 % and is sent straight up the main gate -- shot down, the mission is over (lost).
"""
from parts import Script, Test, counted, square

GO_AT, RUN = 3.0, 480.0
# (point, by site, offset): round the castle hill's north side first -- left to the pathfinder she went by the town
# and the main gate's foot and was run over there (bench 2026-10-27)
WAY = (('north road', 'west road', 0.0, 1600.0), ('north field', 'back foot', -1300.0, 250.0),
       ('back foot', 'back foot', 0.0, 0.0), ('back top', 'back top', 0.0, 0.0),
       ('archive yard', 'archive yard', 0.0, 0.0))


def setup(m):
    t = Test()
    t.scripts.append(Script('Test - reveal', [], [('MAP_REVEAL_ALL_PERM', m.player('p1'))]))
    counted('Test Yuriko', '百合子血量', t, health=m.role('yuriko').name)
    return t


def run(m):
    t = setup(m)
    yuriko = m.role('yuriko').name
    t.scripts.append(Script('Test - keep her up', [], [('UNIT_SET_HEALTH', yuriko, 100.0)], once=False))
    stage = 'Test Leg'
    t.counters.append((stage, '第几段'))
    t.scripts.append(Script('Test - go', [], [('SET_MILLISECOND_TIMER', 'Test - leg', GO_AT)]))
    for k, (point, site, dx, dy) in enumerate(WAY):
        m.waypoint(f'test {point}', f'Test {point}', site, dx, dy)
        t.areas[f'Test {point}'] = square(*m.point(f'test {point}'), m.where(site).r or 150.0)
        t.scripts.append(Script(f'Test - leg {k + 1}', [('TIMER_EXPIRED', 'Test - leg'), ('COUNTER', stage, 2, k)],
                                [('MOVE_NAMED_UNIT_TO', yuriko, m.mark(f'test {point}'))], once=False))
        t.scripts.append(Script(f'Test - at {k + 1}', [('COUNTER', stage, 2, k),
                                                       ('NAMED_INSIDE_AREA', yuriko, f'Test {point}')],
                                [('SET_COUNTER', stage, k + 1)]))
    m.waypoint('test extraction', 'Test extraction', 'extraction')
    t.scripts.append(Script('Test - home', [('FLAG', 'CNV_J3_Phase_2', 1), ('TIMER_EXPIRED', 'Test - leg')],
                            [('MOVE_NAMED_UNIT_TO', yuriko, m.mark('test extraction'))], once=False))
    t.scripts.append(Script('Test - leg again', [('TIMER_EXPIRED', 'Test - leg')],
                            [('SET_MILLISECOND_TIMER', 'Test - leg', 1.0)], once=False))
    t.expect += [('第几段', GO_AT, 'ever==', len(WAY)), ('ENDED', 30, '', None)]
    t.bench = [('bench_watch', dict(seconds=RUN, every=5, sheet=False, lines=len(t.counters)))]
    return t


def lose(m):
    m.find(m.role('yuriko').name).props['objectInitialHealth'] = 1
    t = setup(m)
    m.waypoint('test gate', 'Test gate', 'main gate')
    t.scripts.append(Script('Test - charge', [], [('MOVE_NAMED_UNIT_TO', m.role('yuriko').name, m.mark('test gate'))]))
    t.expect += [('ENDED', 5, '', None)]
    t.bench = [('bench_watch', dict(seconds=120, every=4, sheet=False, lines=len(t.counters)))]
    return t
