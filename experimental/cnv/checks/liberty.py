"""Liberty tests: the mission does the clicking (scripts), counters report what is checked, the bench only watches.

jump: at JUMP_AT the carrier jumps (NAMED_FIRE_SPECIAL_POWER_AT_WAYPOINT) to open grass east of the start; counters
  count the crew alive, the crew inside the landing area (a trigger area: none before the jump, the carried ones
  after) and, with riders, the riders on the deck (ATTACHED). Before the fix (2026-10-21) the deck's store / send
  detached the riders on the jump; after it, 6 alive / 5 on deck before and after.
ride_ab: two carriers side by side, riders that stick to the carrier (A) and riders that do not (B), one jump each.
"""
from parts import Script, Test, counted, side_by_side, square, status
from missions import liberty_bench
from units import liberty as lib

JUMP_AT = 15.0
JUMP_TO = (1480.0, 2315.0)              # open grass 300 east of the carrier, away from the Hammers
LANDING = 150.0                         # half-side of the landing area around JUMP_TO (the start is 300 west)
EARLY = 2.0                             # mission timers run ahead of the bench's seconds (counted from when the bench
                                        # sees the mission; bench 2026-10-21: the s15 jump had landed by s14.2)


def jumps(t, carrier, power, wp, to, at=JUMP_AT, tag=''):
    """Scripts: the map revealed, a timer, the carrier fires its jump at waypoint wp, a caption marks it."""
    t.waypoints[wp] = to
    timer = f'Test - jump timer{tag}'
    t.scripts += [Script(f'Test - start{tag}', [], [('MAP_REVEAL_ALL_PERM', 'Player_1'), ('SET_MILLISECOND_TIMER', timer, at)]),
                  Script(f'Test - jump{tag}', [('TIMER_EXPIRED', timer)],
                         [('NAMED_FIRE_SPECIAL_POWER_AT_WAYPOINT', carrier, power, wp),
                          ('SHOW_MILITARY_CAPTION', 'SCRIPT:CNVTEST_JUMP', 5.0)])]
    t.strings['SCRIPT:CNVTEST_JUMP'] = 'TEST：自由号跃迁'


def jump(m):
    t = Test()
    jumps(t, liberty_bench.CARRIER, m.names['power'], 'Test Jump Target', JUMP_TO)
    counted('Test Crew', '乘员存活', t, template=m.names['crew'])
    t.areas['Test Landing'] = square(*JUMP_TO, LANDING)
    counted('Test Landed', '乘员到落点', t, template=m.names['crew'], area='Test Landing')
    if m.names['crew'] != 'AlliedAntiVehicleVehicleTech1':
        counted('Test Deck', '乘员在甲板', t, status=lib.ATTACHED)
        t.expect += [('乘员在甲板', 5, '>=', 3), ('乘员在甲板', JUMP_AT + 4, '>=', 3)]
    t.expect += [('乘员存活', JUMP_AT + 4, '>=', 4), ('乘员到落点', 0, '==', 0, JUMP_AT - EARLY),
                 ('乘员到落点', JUMP_AT + 4, '>=', 3)]
    t.bench = [('bench_watch', dict(seconds=JUMP_AT + 12, every=3, sheet=False))]
    return t


def ride_ab():
    """A: the riders stick to the carrier (the default flags); B: no STICK_TO_PARENT (on the ground, still attached).
    B's riders mark themselves with another status so the two counts stay apart."""
    a = liberty_bench.mission(riders=True, tag='A', name='CampLibertyAB')
    b = liberty_bench.mission(riders=True, tag='B', ride_flags=lib.RIDE_FLAGS.replace('STICK_TO_PARENT ', ''))
    rb = b.units[1]
    marker = 'IS_BEING_HARVESTED'               # a C&C3 leftover RA3 does nothing with
    rb.xml = rb.xml.replace('AttachedObjectStatus="NO_COLLISIONS ATTACHED"', f'AttachedObjectStatus="NO_COLLISIONS {marker}"')
    m = side_by_side(a, b, 500.0)
    t = Test()
    jumps(t, liberty_bench.CARRIER, a.names['power'], 'Test Jump A', (JUMP_TO[0], JUMP_TO[1] - 250), tag=' A')
    b_carrier = 'UNIT - CNV Liberty B'
    next(o for o in m.objects[len(a.objects):] if o.name == liberty_bench.CARRIER).name = b_carrier
    jumps(t, b_carrier, b.names['power'], 'Test Jump B', (JUMP_TO[0] + 500, JUMP_TO[1] - 250), tag=' B')
    counted('Test A Crew', 'A 存活', t, template=a.names['crew'])
    counted('Test A Deck', 'A 在甲板', t, status=lib.ATTACHED)
    counted('Test B Crew', 'B 存活', t, template=b.names['crew'])
    counted('Test B Deck', 'B 在甲板', t, status=status(marker))
    t.bench = [('bench_watch', dict(seconds=JUMP_AT + 12, every=3, sheet=False))]
    return m, t
