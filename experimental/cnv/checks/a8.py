"""A8 checks (the plan's, docs/story/plans/a8.md; the old rough's are checks/a8_rough.py).

beat: the swell's wiring, read as counters (no pictures): the three platform groups turn on one after another, each on
  for 25 s of every 60, 20 s apart, starting 10 s in (devices/rhythm.py: the flag each group sets while it is on).
  Reads from the mission's own scripts, so it proves the beat is wired and paced, not what the upgrade does to a
  turret's reach (that is `swell`, still to write on the bench: it needs a unit in range to measure).
"""
import re

from parts import Obj, Script, Test


def on_flag(m, k):
    """The flag group k of the swell sets while it is on, read off the mission's own scripts (a check asks the mission,
    it does not import the device): the group's `on` script (devices/rhythm.py) sets it to 1."""
    s = next(s for s in m.scripts if re.search(rf' - Beat\w+ {k} on$', s.name))
    return next(a[1] for a in s.do if a[0] == 'SET_FLAG' and a[2] == 1)

START, PERIOD, ON, PHASES = 10.0, 60.0, 25.0, (0.0, 20.0, 40.0)
GROUPS = ('北', '中', '南')                     # gun north / mid / south
SLACK = 3.0                                    # the bench's seconds start some seconds after the mission's


def beat(m):
    t = Test()
    for k, label in enumerate(GROUPS):
        counter = f'Test Swell {k}'
        t.counters.append((counter, f'浪高{label}'))
        t.scripts += [Script(f'Test - {counter} zero', [], [('SET_COUNTER', counter, 0)], once=False),
                      Script(f'Test - {counter} on', [('FLAG', on_flag(m, k), 1)],
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


SHOW_LOW, SHOW_HIGH, RUN = 15.0, 33.0, 55.0
TARGET = 'AlliedEngineer'


def swell(m):
    """The swell on the real mission: what the beat does to a platform's guns (docs/engine/upgrades.md: RANGE moves the
    weapon, VISION the picking; a removed upgrade's modifier goes). Two neutral engineers stand west of the middle
    platform's first gun, 250 and 450 from it (retail's sentry gun: reach 300, sight 310). The middle group is on
    (high: reach x2, sight x2) from 30 s to 55 s of the beat and off (low: reach x0.6 = 180) before.
      SHOW_LOW  s15  the 250 one is handed to the player: the gun sees it but cannot reach it (180) -- not hurt while low
      SHOW_HIGH s33  the 450 one is handed over, the beat is on high: reach 600, sight 600 -- the gun picks it and
                     hurts it; the 250 one, in reach now, is hurt too.
    Counters (a target counts once hurt or dead, latched): 受伤250, 受伤450, and the middle group's high flag."""
    t = Test()
    gun = m.find(m.roles('gun mid')[0].name)
    p1 = m.player('p1')
    site = m.roles('gun mid')[0].site
    names = {}
    for d in (250, 450):
        names[d] = f'UNIT - Test Swell Target {d}'
        t.objects.append(Obj(TARGET, gun.x - d, gun.y, side='neutral', name=names[d], site=site))
    t.scripts += [
        Script('Test - swell start', [], [('MAP_REVEAL_ALL_PERM', p1), ('SET_MILLISECOND_TIMER', 'Test Swell Low', SHOW_LOW),
                                          ('SET_MILLISECOND_TIMER', 'Test Swell High', SHOW_HIGH)]),
        Script('Test - swell hand low', [('TIMER_EXPIRED', 'Test Swell Low')],
               [('NAMED_TRANSFER_OWNERSHIP_PLAYER', names[250], p1)]),
        Script('Test - swell hand high', [('TIMER_EXPIRED', 'Test Swell High')],
               [('NAMED_TRANSFER_OWNERSHIP_PLAYER', names[450], p1)])]
    for d, label in ((250, '受伤250'), (450, '受伤450')):
        counter, flag = f'Test Swell Hurt {d}', f'Test Swell Hit {d}'
        t.counters.append((counter, label))
        t.scripts += [Script(f'Test - swell hurt {d}', [('UNIT_HEALTH', names[d], 0, 100)], [('SET_FLAG', flag, 1)]),
                      Script(f'Test - swell dead {d}', [('NAMED_DESTROYED', names[d])], [('SET_FLAG', flag, 1)]),
                      Script(f'Test - swell zero {d}', [], [('SET_COUNTER', counter, 0)], once=False),
                      Script(f'Test - swell hit {d}', [('FLAG', flag, 1)], [('SET_COUNTER', counter, 1)], once=False)]
    t.counters.append(('Test Swell Mid', '浪高中'))
    t.scripts += [Script('Test - swell mid zero', [], [('SET_COUNTER', 'Test Swell Mid', 0)], once=False),
                  Script('Test - swell mid on', [('FLAG', on_flag(m, 1), 1)],
                         [('SET_COUNTER', 'Test Swell Mid', 1)], once=False)]
    # the bench's seconds start some seconds after the mission's (SLACK): low is judged late in its stretch, high late too
    t.expect += [('受伤250', SHOW_LOW + 8 + SLACK, '==', 0, 28 + SLACK),
                 ('受伤450', 0, '==', 0, SHOW_HIGH - 2),                 # hurt at s34 on the bench: right after the hand-over
                 ('受伤450', SHOW_HIGH + 4 + SLACK, 'ever==', 1, RUN),
                 ('受伤250', SHOW_HIGH + 4 + SLACK, 'ever==', 1, RUN)]
    t.bench = [('bench_watch', dict(seconds=RUN, every=3, sheet=False, lines=len(t.counters)))]
    return t


# the checks per build (cnv/registry.py): build name -> {check name: check(mission) -> Test}
CHECKS = {
    'a8': {'beat': beat, 'swell': swell},
}
