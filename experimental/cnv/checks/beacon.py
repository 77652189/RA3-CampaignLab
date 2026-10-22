"""Beacon trooper tests. Counters: the squad alive, the squad inside an area around the trooper (an area the
teleported enter at once; the one they left would keep counting them, see the A7 carrier), the trooper alive.

pull: at PULL_AT the trooper fires pull at the squad's mark: all four come to his side, none lost.
still: nobody fires: no one comes (the control).
The reach is not a check: a script's NAMED_FIRE_SPECIAL_POWER_AT_WAYPOINT ignores it (reach 300, the squad 500 away:
pulled all the same, with and without MaxCastRange + LIMIT_DISTANCE); by hand it holds (bench 2026-10-22, the
still scene kept up, trooper selected, ability at the squad: reach 300 -> nothing, reach 1500 -> all four came).
"""
from parts import Script, Test, counted, square
from checks.liberty import EARLY

# bench 2026-10-22: a pull scripted for s5 was done before the bench's first frame once ('in game at 41 s', the
# others 38 s): how far the mission has run when the bench starts counting varies by a few seconds, so the first
# scripted action waits until well past it
PULL_AT = 10.0
NEAR = 200.0                                    # half-side of the area around the trooper


def watch(m, fire=True):
    """Counters (and with fire, the pull at PULL_AT)."""
    t = Test()
    who = m.role('beacon')
    t.scripts.append(Script('Test - start', [], [('MAP_REVEAL_ALL_PERM', m.player('p1')),
                                                 ('SET_MILLISECOND_TIMER', 'Test - pull timer', PULL_AT)]))
    if fire:
        t.scripts.append(Script('Test - pull', [('TIMER_EXPIRED', 'Test - pull timer')],
                                [('NAMED_FIRE_SPECIAL_POWER_AT_WAYPOINT', who.name, m.ability('beacon', 'pull'),
                                  m.mark('squad'))]))
    t.areas['Test Near Beacon'] = square(*m.point('beacon'), NEAR)
    squad = m.role('squad').template
    counted('Test Squad', '小队', t, template=squad)
    counted('Test Near', '到身边', t, template=squad, area='Test Near Beacon')
    counted('Test Beacon', '信标兵', t, template=who.template)
    t.bench = [('bench_watch', dict(seconds=PULL_AT + 12, every=2, sheet=False, lines=len(t.counters)))]
    return t


def pull(m):
    t = watch(m)
    t.expect += [('到身边', 0, '==', 0, PULL_AT - EARLY), ('到身边', PULL_AT + 4, 'ever>=', 4),
                 ('小队', PULL_AT + 4, '==', 4), ('信标兵', 0, '==', 1)]
    return t


def still(m):
    """The control: nobody fires the pull -- the squad must stay where it is (bench 2026-10-22: it did, so the
    s1 squad at the trooper's side in the first pull run was the pull itself, done before the bench's first frame)."""
    t = watch(m, fire=False)
    t.expect += [('到身边', 0, '==', 0), ('小队', 0, '==', 4)]
    return t
