"""J5 tests (the plan: docs/story/plans/j5.md). Counted: Yuriko's and the observatory's health.

hold: the observatory and Yuriko back at full health every frame -- the countdown runs out and the mission is over
  (won).
lose: Yuriko starts at 1 %, the shikigami not on guard -- the first head-hunters shoot her down and the mission is
  over (lost) well before.
"""
import plan
from parts import Script, Test, counted


def done():
    """When the countdown runs out: phase 2's start plus its countdown (normal difficulty)."""
    d = plan.load('j5')
    phase1 = plan.spans(d['段'][0]['结束'].split('+')[1])[1][0]
    count = plan.spans(d['段'][1]['开场'][1]['倒计时'].split('+')[1])[1][0]
    return phase1 + count


def setup(m):
    t = Test()
    t.scripts.append(Script('Test - reveal', [], [('MAP_REVEAL_ALL_PERM', m.player('p1'))]))
    counted('Test Yuriko', '百合子血量', t, health=m.role('yuriko').name)
    counted('Test Observatory', '观测站血量', t, health=m.role('observatory').name)
    return t


def hold(m):
    t = setup(m)
    for part in ('yuriko', 'observatory'):
        t.scripts.append(Script(f'Test - keep {part} up', [], [('UNIT_SET_HEALTH', m.role(part).name, 100.0)],
                                once=False))
    end = done()
    t.expect += [('ENDED', end - 10, '', None)]
    t.bench = [('bench_watch', dict(seconds=end + 30, every=6, sheet=False, lines=len(t.counters)))]
    return t


def lose(m):
    m.find(m.role('yuriko').name).props['objectInitialHealth'] = 1
    t = setup(m)
    end = done()
    t.expect += [('ENDED', 30, '', None)]
    t.bench = [('bench_watch', dict(seconds=end - 60, every=6, sheet=False, lines=len(t.counters)))]
    return t
