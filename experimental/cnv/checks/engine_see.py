"""Engine unit test: a tower on high ground, an Athena cannon below it (A6, docs/story/plans/a6.md 待做 1).

Two questions: does a unit on the low ground see a tower up on the outer ring, and can it hit it then; and once a
spotter of ours on the ring sees the tower, does the cannon below -- which still cannot see it itself -- fire when
it is ordered to (know-how.md: a unit picks targets only inside its own vision; this asks about the player's order).

The map is A6's stonehenge (imported only: outer ring tier 2, ~115 elevation above the low ground). The probe places
its own cast, retail units; the enemy has no power plant (its towers may well be offline: they do not matter as
shooters here). Three arms, each a tower of the enemy's (AlliedBaseDefense: range 300, vision 300) and a cannon of
the player's (AlliedAntiStructureVehicle: weapon range 500, minimum 200, vision 500), 400 apart:
  W  blind   tower on the ring's west rim, the cannon below to the west; nobody of ours on the ring
  E  spotter tower on the ring's east side, the cannon below to the east; Tanya (vision 200) on the ring 150 from it
  S  level   tower and cannon both on the ring's south side (the control: the cannon sees and hits at 400)
No orders before ORDER (does anything fire by itself?). At ORDER the script orders cannon W and S to attack their
towers; cannon E: check `order` orders it by script too, check `click` leaves it to the bench -- select it with a
left click, right click the tower (the player's own order, as a player gives it).

Counters: 看见 = W 1 + E 10 + S 100, each added once the player has discovered that tower (NAMED_DISCOVERED), + 1000
once Tanya is below full health (does the tower shoot?); 血西/东/南 the tower's health in percent.
"""
from maps import stonehenge
from parts import Mission, Script, Test, counted
from checks.probe_view import open_in_view

TOWER, CANNON, TANYA = 'AlliedBaseDefense', 'AlliedAntiStructureVehicle', 'AlliedCommandoTech1'
ORDER, RUN = 8.0, 40.0
# arm: (tower x, y), (cannon x, y) -- the ring is the circle r 720 about (1900, 1350) less the inner platform's r 380
ARMS = {'W': ((1280.0, 1350.0), (880.0, 1350.0)),
        'E': ((2420.0, 1250.0), (2820.0, 1250.0)),
        'S': ((1700.0, 800.0), (2100.0, 800.0))}
SPOTTER = (2420.0, 1100.0)                       # on the ring (r ~577), 150 south of tower E
LABELS = {'W': '西', 'E': '东', 'S': '南'}


def mission():
    m = Mission(name='CampSee', map=stonehenge, facts={})
    cx, cy = m.site('start')
    for k, ((tx, ty), (ax, ay)) in ARMS.items():
        m.put(TOWER, 'start', tx - cx, ty - cy, side='s1', name=f'UNIT - CNV See Tower {k}', role=f'tower {k}')
        m.put(CANNON, 'start', ax - cx, ay - cy, name=f'UNIT - CNV See Cannon {k}', role=f'cannon {k}',
              angle=3.1416 if k == 'W' else 0.0)
    m.put(TANYA, 'start', SPOTTER[0] - cx, SPOTTER[1] - cy, name='UNIT - CNV See Tanya', role='tanya', angle=1.5708)
    return open_in_view(m, 'See')      # K5: the start is too near the map's edge


def _test(m, clicked=None):
    """clicked: the arm whose cannon the bench orders by hand (the rest by script at ORDER); None: all by script."""
    t = Test()
    p1 = m.player('p1')
    arms = [k for k in ARMS if k != clicked]
    # bench 2026-11-04: left alone, Tanya ran up and blew tower E with her C4 by s2 -- she is the eyes only here:
    # hold fire (stance 3, Stance.xsd's order) and no auto-acquire
    tanya = m.role('tanya').name
    t.scripts += [Script('Test - start', [], [('UNIT_SET_STANCE', tanya, 3), ('UNIT_ALLOW_AI_AUTOACQUIRE', tanya, 0),
                                              ('SET_MILLISECOND_TIMER', 'Test Order', ORDER)]),
                  Script('Test - order', [('TIMER_EXPIRED', 'Test Order')],
                         [('NAMED_ATTACK_NAMED', m.role(f'cannon {k}').name, m.role(f'tower {k}').name)
                          for k in arms])]
    # one line for what is seen (only four counter lines fit): W 1, E 10, S 100 once discovered; 1000 once Tanya hurts
    c = 'Test See'
    t.counters.append((c, '看见'))
    t.scripts.append(Script('Test - see zero', [], [('SET_COUNTER', c, 0)]))
    for i, k in enumerate(ARMS):
        t.scripts.append(Script(f'Test - see {k}', [('NAMED_DISCOVERED', p1, m.role(f'tower {k}').name)],
                                [('INCREMENT_COUNTER', 10 ** i, c)]))
    t.scripts.append(Script('Test - tanya hurt', [('UNIT_HEALTH', m.role('tanya').name, 0, 100)],
                            [('INCREMENT_COUNTER', 1000, c)]))
    for k, zh in LABELS.items():
        counted(f'Test Hp {k}', f'血{zh}', t, health=m.role(f'tower {k}').name)
    # the controls: the level cannon sees its tower and hurts it once ordered; Tanya sees tower E
    t.expect += [('看见', 0, 'ever>=', 110), ('血南', ORDER, 'ever<', 100)]
    lines = len(t.counters)
    if clicked is None:
        t.bench = [('bench_watch', dict(seconds=RUN, every=2, sheet=False, lines=lines))]
    else:
        # the camera put by script, exactly (bench 2026-11-04: after bench_camera's minimap click the left click
        # missed the cannon by ~70 px and nothing was selected)
        (tx, ty), (ax, ay) = ARMS[clicked]
        eye = ((tx + ax) / 2, ty)
        t.waypoints['Test Eye'] = eye
        t.scripts.append(Script('Test - camera', [], [('MOVE_CAMERA_TO', 'Test Eye', 0.1, 0.0, 0.0, 0.0)]))
        t.bench = [('bench_watch', dict(seconds=ORDER, every=2, sheet=False, lines=lines)),
                   ('bench_view', dict(x=eye[0], y=eye[1], look=False)),
                   ('bench_click', dict(x=ax, y=ay, look=False)),
                   # the ring stands higher than the ground the bench maps clicks on: the tower is drawn ~22 px left
                   # and ~24 px up of its ground point (bench 2026-11-04: a right click there was a move order)
                   ('bench_click', dict(x=tx - 14.0, y=ty + 20.0, right=True, look=True)),
                   ('bench_watch', dict(seconds=RUN - ORDER, every=2, sheet=False, lines=lines))]
    return t


def order(m):
    return _test(m)


def click(m):
    return _test(m, clicked='E')


def blind(m):
    """The player's right click on tower W, which nobody of ours has seen (the shroud over it)."""
    return _test(m, clicked='W')


# the builds this module makes and their checks (cnv/registry.py)
MISSION = {'engine_see': mission}
CHECKS = {'engine_see': {'order': order, 'click': click, 'blind': blind}}
