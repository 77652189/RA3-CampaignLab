"""Liberty tests: the mission does the clicking (scripts), counters report what is checked, the bench only watches.
They ask the mission for everything (its cast, the carrier's published jump, the map's sites) -- no coordinates.

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
JUMP_BY = (300.0, -60.0)                # from the west field: open grass 300 east of the carrier, away from the Hammers
LANDING = 150.0                         # half-side of the landing area around the jump target (the start is 300 west)
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


def jump(m, by=JUMP_BY):
    t = Test()
    to = m.site('west field', *by)
    jumps(t, m.role('carrier').name, m.ability('carrier', 'jump'), 'Test Jump Target', to)
    crew = m.role('crew').template
    counted('Test Crew', '乘员存活', t, template=crew)
    t.areas['Test Landing'] = square(*to, LANDING)
    counted('Test Landed', '乘员到落点', t, template=crew, area='Test Landing')
    if any(u.id == crew for u in m.units):      # our riders, not the retail Guardian
        counted('Test Deck', '乘员在甲板', t, status=lib.ATTACHED)
        t.expect += [('乘员在甲板', 5, '>=', 3), ('乘员在甲板', JUMP_AT + 4, '>=', 3)]
    t.expect += [('乘员存活', JUMP_AT + 4, '>=', 4), ('乘员到落点', 0, '==', 0, JUMP_AT - EARLY),
                 ('乘员到落点', JUMP_AT + 4, '>=', 3)]
    t.bench = [('bench_watch', dict(seconds=JUMP_AT + 12, every=3, sheet=False))]
    return t


OPEN_BY = (300.0, -225.0)               # JUMP_BY moved 165 south: 210+ from our power plant at (1550, 2360)


def jump_open(m):
    """jump with the landing point clear of our own buildings. JUMP_BY's target is ~46 from the power plant for the
    Guardian carried 60 east of the carrier; the deck's Telefrag (INSTANT_DEATH_TELEPORTER_ONLY, collides with
    STRUCTURE) would kill it there -- the suspect for the one Guardian liberty jump loses at the jump (2026-10-21)."""
    t = jump(m, OPEN_BY)
    t.expect.append(('乘员存活', JUMP_AT + 4, '==', 6))
    return t


def ride_ab():
    """A: the riders stick to the carrier (the default flags); B: no STICK_TO_PARENT (on the ground, still attached).
    B's riders mark themselves with another status so the two counts stay apart."""
    a = liberty_bench.mission(riders=True, tag='A', name='CampLibertyAB')
    b = liberty_bench.mission(riders=True, tag='B', ride_flags=lib.RIDE_FLAGS.replace('STICK_TO_PARENT ', ''))
    rb = b.units[1]
    marker = 'IS_BEING_HARVESTED'               # a C&C3 leftover RA3 does nothing with
    rb.xml = rb.xml.replace('AttachedObjectStatus="NO_COLLISIONS ATTACHED"', f'AttachedObjectStatus="NO_COLLISIONS {marker}"')
    m = side_by_side(a, b, 500.0, suffix=' B')
    t = Test()
    dx, dy = JUMP_BY
    jumps(t, m.role('carrier').name, m.ability('carrier', 'jump'), 'Test Jump A', m.site('west field', dx, dy - 250),
          tag=' A')
    jumps(t, m.role('carrier B').name, m.ability('carrier B', 'jump'), 'Test Jump B',
          m.site('west field', dx + 500, dy - 250), tag=' B')
    counted('Test A Crew', 'A 存活', t, template=m.role('crew').template)
    counted('Test A Deck', 'A 在甲板', t, status=lib.ATTACHED)
    counted('Test B Crew', 'B 存活', t, template=m.role('crew B').template)
    counted('Test B Deck', 'B 在甲板', t, status=status(marker))
    t.bench = [('bench_watch', dict(seconds=JUMP_AT + 12, every=3, sheet=False))]
    return m, t
