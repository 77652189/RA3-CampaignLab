"""S6 tests (the plan: docs/story/plans/s6.md). Counted: the launch tower's health.

hold: the tower back at full health every frame -- the countdown runs out and the mission is over (won).
lose: the tower starts at 1 % -- the first mechs through raze it and the mission is over (lost) well before.
"""
import plan
from parts import Script, Test, counted


def launch():
    """When the countdown runs out: phase 2's start plus its countdown (normal difficulty)."""
    d = plan.load('s6')
    phase1 = plan.spans(d['段'][0]['结束'].split('+')[1])[1][0]
    count = plan.spans(d['段'][1]['开场'][1]['倒计时'].split('+')[1])[1][0]
    return phase1 + count


def setup(m):
    t = Test()
    t.scripts.append(Script('Test - reveal', [], [('MAP_REVEAL_ALL_PERM', m.player('p1'))]))
    counted('Test Tower', '发射塔血量', t, health=m.role('launch tower').name)
    return t


def hold(m):
    t = setup(m)
    t.scripts.append(Script('Test - keep the tower up', [], [('UNIT_SET_HEALTH', m.role('launch tower').name, 100.0)],
                            once=False))
    end = launch()
    t.expect += [('ENDED', end - 10, '', None)]
    t.bench = [('bench_watch', dict(seconds=end + 30, every=6, sheet=False, lines=len(t.counters)))]
    return t


def lose(m):
    m.find(m.role('launch tower').name).props['objectInitialHealth'] = 1
    t = setup(m)
    end = launch()
    t.expect += [('ENDED', 30, '', None)]
    t.bench = [('bench_watch', dict(seconds=end - 60, every=6, sheet=False, lines=len(t.counters)))]
    return t
