"""A7 tests (were make_campa7.py's CNV_TEST=1 / win). Counters say where the enemy carrier is -- inside a trigger
area around its home mark, around its strike mark -- and whether the station stands; all asked of the mission (its
marks, its cast, its published timings), nothing of its own.

jumps: the mission as played: home until the first jump, at the strike point until the next, then home again.
power: the station killed by script soon after the first jump: the carrier stays at the strike point.
win: the carrier at 1 % health jumps (by test script) to the strike point at 5 s, the player's IFVs shoot it down,
  Mission Won ends the mission.
"""
from parts import Script, Test, counted, square
from checks.liberty import EARLY, jumps as fire_jump

AREA = 300.0                                    # half-side of the areas around home and strike
KILL_AFTER = 8.0                                # power: the station dies this long after the first jump


def where(m):
    """A test counting the carrier (alive, at home, at the strike point) and the station."""
    t = Test()
    t.scripts.append(Script('Test - reveal', [], [('MAP_REVEAL_ALL_PERM', m.player('p1'))]))
    enemy, carrier = m.player('s1'), m.role('carrier')
    counted('Test Carrier', '自由号', t, template=carrier.template, player=enemy)
    for part, label in (('home', '自由号在家'), ('strike', '自由号在我方')):
        t.areas[f'Test {part}'] = square(*m.point(part), AREA)
        counted(f'Test At {part}', label, t, named=carrier.name, area=f'Test {part}')
    counted('Test Station', '电站', t, template=m.role('station').template, player=enemy)
    return t


def keep_up(m, t):
    """The carrier back at full health every frame: the test is about where it goes, not whether it survives."""
    t.scripts.append(Script('Test - keep the carrier up', [], [('UNIT_SET_HEALTH', m.role('carrier').name, 100.0)],
                            once=False))


def jumps(m):
    """The pacing alone: the carrier kept at full health (bench 2026-10-22: as played, the player's four idle IFVs
    shot it down at the strike point ~35 s after the first jump, before the jump home -- a level finding, see
    docs/story/levels.md A7)."""
    first, gap = m.facts['first jump'], m.facts['jump every']
    t = where(m)
    keep_up(m, t)
    t.expect += [('自由号在家', 0, '==', 1, first - EARLY), ('自由号在我方', 0, '==', 0, first - EARLY),
                 ('自由号在我方', first + 4, '==', 1, first + gap - EARLY), ('自由号在家', first + 4, '==', 0, first + gap - EARLY),
                 ('自由号在家', first + gap + 4, '==', 1), ('自由号在我方', first + gap + 4, '==', 0)]
    t.bench = [('bench_watch', dict(seconds=first + gap + 12, every=4, sheet=False, lines=len(t.counters)))]
    return t


def power(m):
    first, gap = m.facts['first jump'], m.facts['jump every']
    t = where(m)
    keep_up(m, t)                               # bench 2026-10-22: without it shot down at ~s77, before the s85 test
    timer = 'Test - kill timer'
    t.scripts += [Script('Test - kill set', [], [('SET_MILLISECOND_TIMER', timer, first + KILL_AFTER)]),
                  Script('Test - kill station', [('TIMER_EXPIRED', timer)], [('NAMED_KILL', m.role('station').name)])]
    t.expect += [('电站', 0, '==', 1, first + KILL_AFTER - EARLY), ('电站', first + KILL_AFTER + 2, '==', 0),
                 ('自由号在我方', first + 4, '==', 1), ('自由号在家', first + 4, '==', 0)]   # past first + gap: no jump home
    t.bench = [('bench_watch', dict(seconds=first + gap + 12, every=4, sheet=False, lines=len(t.counters)))]
    return t


def win(m):
    m.find(m.role('carrier').name).props['objectInitialHealth'] = 1
    t = where(m)
    fire_jump(t, m.role('carrier').name, m.ability('carrier', 'jump'), 'Test Strike', m.point('strike'), at=5.0)
    t.expect += [('自由号', 0, 'ever==', 1), ('ENDED', 5, '', None)]
    t.bench = [('bench_watch', dict(seconds=20, every=1, sheet=False))]
    return t
