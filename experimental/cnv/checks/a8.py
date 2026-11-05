"""A8 checks (the plan's, docs/story/plans/a8.md; the old rough's are checks/a8_rough.py).

beat: the swell's wiring, read as counters (no pictures): the three platform groups turn on one after another, each on
  for 25 s of every 60, 20 s apart, starting 10 s in (devices/rhythm.py: the flag each group sets while it is on).
  Reads from the mission's own scripts, so it proves the beat is wired and paced, not what the upgrade does to a
  turret's reach (that is `swell`, still to write on the bench: it needs a unit in range to measure).
"""
from devices import rhythm
from parts import Script, Test

START, PERIOD, ON, PHASES = 10.0, 60.0, 25.0, (0.0, 20.0, 40.0)
GROUPS = ('北', '中', '南')                     # gun north / mid / south
SLACK = 3.0                                    # the bench's seconds start some seconds after the mission's


def beat(m):
    t = Test()
    for k, label in enumerate(GROUPS):
        counter = f'Test Swell {k}'
        t.counters.append((counter, f'浪高{label}'))
        t.scripts += [Script(f'Test - {counter} zero', [], [('SET_COUNTER', counter, 0)], once=False),
                      Script(f'Test - {counter} on', [('FLAG', rhythm.on_flag('A8', '浪', k), 1)],
                             [('SET_COUNTER', counter, 1)], once=False)]
    # sample well inside each group's on and off stretches (after the bench's start slack)
    for k, label in enumerate(GROUPS):
        on_from = START + PHASES[k]
        mid_on = on_from + ON / 2
        mid_off = on_from + ON + (PERIOD - ON) / 2
        t.expect += [(f'浪高{label}', mid_on + SLACK, '==', 1, mid_on + SLACK + 2),
                     (f'浪高{label}', mid_off + SLACK, '==', 0, mid_off + SLACK + 2)]
    t.bench = [('bench_watch', dict(seconds=START + PERIOD + 25, every=3, sheet=False, lines=len(t.counters)))]
    return t


# the checks per build (cnv/registry.py): build name -> {check name: check(mission) -> Test}
CHECKS = {
    'a8': {'beat': beat},
}
