"""Engine probe for sim.HOLD_SPOTS (Sim.claims: every move's goal kept off the spots other units hold): mission
missions/spots_bench.py, three trucks on teams of their own sent to one point (MOVE_TEAM_TO each team).

  same    all three sent at 1 s. 环k = how many of the nested squares (half-sides RINGS) round the point truck k
          stands in: 4 within 10, 3 within 25, 2 within 45, 1 within 80, 0 farther. [HOLD_SPOTS: one truck 4, the
          other two 1-3 (moved off by about two radii); without it all three 4, or pushed about]
  late    truck k sent at 1 + STAGGER (k - 1) s: each arrives after the one before stands on the point.

读数
Bench 2026-11-09 (one run each; sim pairs in tests/test_simbench.py test_spots_*):
  same    环1 环2 环3: s9 0 1 1 | s10 1 4 1 | s11 3 2 1 | s12-s36 4 2 1 -- they stand apart: truck 1 (ordered first) on
          the point, truck 2 25-45 off (it passed over the point at s10 on its way), truck 3 45-80 off. sim.HOLD_SPOTS
          on: 4 2 2 (0 / 50 / 44.7 off); off: 4 4 4 (all three on the point).
  late    s9 1 0 0 | s11-s27 4 0 0 | s29 4 1 0 | s31-s47 4 2 0 | s49-s75 4 2 1 -- the same: each one sent later stops
          off the spots already held.
(A first build had them at -250 / +300: in the sea, nobody moved.)
"""
from parts import Script, Test, square

RINGS = (80.0, 45.0, 25.0, 10.0)
STAGGER = 20.0
RUN = {'same': 35.0, 'late': 75.0}


def _at(t, key, secs, actions):
    timer = f'Test {key} Timer'
    t.scripts += [Script(f'Test - {key} timer', [], [('SET_MILLISECOND_TIMER', timer, secs)]),
                  Script(f'Test - {key}', [('TIMER_EXPIRED', timer)], actions)]


def _rings(t, m):
    spot = m.point('spot')
    for r in RINGS:
        t.areas[f'Test Spot {r:g}'] = square(*spot, r)
    for k in (1, 2, 3):
        name, counter = m.role(f'truck {k}').name, f'CNV_Spots_Ring{k}'
        t.counters.append((counter, f'环{k}'))
        t.scripts.append(Script(f'Test - {counter} zero', [], [('SET_COUNTER', counter, 0)], once=False))
        t.scripts += [Script(f'Test - {counter} {r:g}', [('NAMED_INSIDE_AREA', name, f'Test Spot {r:g}')],
                             [('INCREMENT_COUNTER', 1, counter)], once=False) for r in RINGS]


def _send(m, k):
    return m.order('move', [m.role(f'truck {k}').name], m.mark('spot'), crew=f'T{k}')


def _watch(t, run, every=1.0):
    t.bench = [('bench_watch', dict(seconds=run, every=every, sheet=False, lines=len(t.counters)))]


def same(m):
    t = Test()
    _at(t, 'go', 1.0, sum((_send(m, k) for k in (1, 2, 3)), []))
    _rings(t, m)
    _watch(t, RUN['same'])
    return t


def late(m):
    t = Test()
    for k in (1, 2, 3):
        _at(t, f'go{k}', 1.0 + STAGGER * (k - 1), _send(m, k))
    _rings(t, m)
    _watch(t, RUN['late'], 2.0)
    return t


CHECKS = {'engine_spots': {'same': same, 'late': late}}     # (a mod name over 15 characters crashes: not 'stagger')
