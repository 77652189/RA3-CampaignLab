"""Waypoint helpers shared by the plain and attack path benches."""
from parts import Script

PATH = ('A', 'B', 'C')


def _at(t, key, secs, actions):
    timer = f'Test {key} Timer'
    t.scripts += [Script(f'Test - {key} timer', [], [('SET_MILLISECOND_TIMER', timer, secs)]),
                  Script(f'Test - {key}', [('TIMER_EXPIRED', timer)], actions)]


def _road(t, m, label, loop=False):
    """The check's own waypoints on A, B, C, labelled `label`, linked in order (loop: C back to A)."""
    names = [f'Test Waypath {p}' for p in PATH]
    for n, p in zip(names, PATH):
        t.waypoints[n] = m.point(p)
    t.path(label, *names, loop=loop)
