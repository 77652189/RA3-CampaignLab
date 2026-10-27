"""Ice-wall engineer tests.

block (A against B): both runners are sent north to their goals at GO_AT; lane A has a wall across it. A must go
  round: it never crosses the strip right behind the wall's middle (a latch: a pass through takes under a second,
  between frames) and still arrives; B drives straight through its own strip.
freeze: the engineer is sent to raise a wall at the spot; it stands, then melts after its lifetime.
smash: enemy Hammers next to a wall, ordered to attack it, shoot it down before it melts.
"""
from parts import Script, Test, counted, square

GO_AT = 10.0
BUILT_LATER = 10.0                              # turns: a core's wall goes up as a building does (bench 2026-10-23:
                                                # scaffolding at s11, whole at s14)
FREEZE_AT = 10.0
ATTACK_AT = 10.0
STRIP = 50.0                                    # half-side of the strip area behind the wall's middle
GOAL = 100.0
CLEAR_FIRE = 8.0                                # clear: told to freeze then, from the away point (~220 off at 40)
CLEAR_STANDS = 20.0                             # clear: the block whole by then (172 back at 40, 5.5 s building)
CLEAR_SIZE = 10.0                               # clear: the engineer's own radius, round the block's square
CLEAR_AWAY = 300.0                              # clear: sent this far south of the spot
CLEAR_OUT = 12.0                                # clear: out within this


def latched(t, counter, label, who, area):
    """A counter that turns 1 the first time `who` is inside `area` and stays 1."""
    t.counters.append((counter, label))
    t.scripts.append(Script(f'Test - latch {counter}', [('NAMED_INSIDE_AREA', who, area)],
                            [('SET_COUNTER', counter, 1)]))


def block(m):
    t = Test()
    go = GO_AT
    t.scripts.append(Script('Test - start', [], [('MAP_REVEAL_ALL_PERM', m.player('p1')),
                                                 ('SET_MILLISECOND_TIMER', 'Test - go timer', go)]))
    t.scripts.append(Script('Test - go', [('TIMER_EXPIRED', 'Test - go timer')],
                            [('MOVE_NAMED_UNIT_TO', m.role(f'runner {k}').name, m.mark(f'goal {k}')) for k in 'AB']))
    for k in 'AB':
        who = m.role(f'runner {k}').name
        t.areas[f'Test Strip {k}'] = square(*m.point(f'behind {k}'), STRIP)
        t.areas[f'Test Goal {k}'] = square(*m.point(f'goal {k}'), GOAL)
        latched(t, f'Test {k} Crossed', f'{k} 穿过', who, f'Test Strip {k}')
        counted(f'Test {k} There', f'{k} 到达', t, named=who, area=f'Test Goal {k}')
    t.expect += [('A 穿过', 0, '==', 0), ('B 穿过', go, 'ever==', 1), ('A 到达', go, 'ever==', 1),
                 ('B 到达', go, 'ever==', 1)]
    t.bench = [('bench_watch', dict(seconds=40, every=3, sheet=False, lines=len(t.counters)))]
    return t


def turns(m):
    """Which built wall holds a lane: each engineer builds at his spot at once, the runners go GO_AT + BUILT_LATER
    later; a runner that never crosses the strip behind its spot was held. Bench 2026-10-23: the square held, both
    bars (asked for 0 and for 90 degrees) let theirs by -- the core's angle does nothing (units/icewall.py seed)."""
    t = Test()
    go = GO_AT + BUILT_LATER
    t.scripts.append(Script('Test - start', [], [('MAP_REVEAL_ALL_PERM', m.player('p1')),
                                                 ('SET_MILLISECOND_TIMER', 'Test - go timer', go)] +
                            [('NAMED_FIRE_SPECIAL_POWER_AT_WAYPOINT', m.role(f'engineer {k}').name,
                              m.ability(f'engineer {k}', 'freeze'), m.mark(f'spot {k}')) for k in 'ABC']))
    t.scripts.append(Script('Test - go', [('TIMER_EXPIRED', 'Test - go timer')],
                            [('MOVE_NAMED_UNIT_TO', m.role(f'runner {k}').name, m.mark(f'goal {k}')) for k in 'ABC']))
    for k in 'ABC':
        t.areas[f'Test Strip {k}'] = square(*m.point(f'behind {k}'), STRIP)
        latched(t, f'Test {k} Crossed', f'{k} 穿过', m.role(f'runner {k}').name, f'Test Strip {k}')
    t.expect += [('C 穿过', 0, '==', 0), ('A 穿过', go, 'ever==', 1), ('B 穿过', go, 'ever==', 1)]
    t.bench = [('bench_watch', dict(seconds=go + 20, every=3, sheet=False, lines=len(t.counters)))]
    return t


def clear(m):
    """The engineer is not shut in his own block (A4's: a core that leaves a 160 square): walked up from afar, he
    stops to build far enough off (units/icewall.py stand) that once it stands he is clear of its square, and sent
    off he walks away. Bench 2026-10-26: at stand 30 it came out round him and he could not walk out of it."""
    t = Test()
    who, k = m.role('engineer C').name, 'C'
    x, y = m.point(f'spot {k}')
    t.waypoints['Test Away'] = (x, y - CLEAR_AWAY)
    t.scripts += [Script('Test - start', [], [('MAP_REVEAL_ALL_PERM', m.player('p1')),
                                              ('MOVE_NAMED_UNIT_TO', who, 'Test Away'),
                                              ('SET_MILLISECOND_TIMER', 'Test - freeze timer', CLEAR_FIRE),
                                              ('SET_MILLISECOND_TIMER', 'Test - away timer', CLEAR_STANDS + 4)]),
                  Script('Test - freeze', [('TIMER_EXPIRED', 'Test - freeze timer')],
                         [('NAMED_FIRE_SPECIAL_POWER_AT_WAYPOINT', who, m.ability(f'engineer {k}', 'freeze'),
                           m.mark(f'spot {k}'))]),
                  Script('Test - away', [('TIMER_EXPIRED', 'Test - away timer')],
                         [('MOVE_NAMED_UNIT_TO', who, 'Test Away')])]
    core = next(u for u in m.units if u.id == m.param(f'engineer {k}', 'wall'))
    side = core.params['wall']                  # the block the core leaves
    half = next(u for u in m.units if u.id == side).params['length'] / 2
    t.areas['Test Block'] = square(x, y, half + CLEAR_SIZE)
    counted('Test In Block', '工兵在冰块里', t, named=who, area='Test Block')
    counted('Test Walls', '冰墙', t, template=side)
    t.expect += [('冰墙', 0, 'ever==', 1, CLEAR_STANDS),
                 ('工兵在冰块里', CLEAR_STANDS, '==', 0, CLEAR_STANDS + 4),               # not inside it at all
                 ('工兵在冰块里', CLEAR_STANDS + 4, 'ever==', 0, CLEAR_STANDS + 4 + CLEAR_OUT)]
    t.bench = [('bench_watch', dict(seconds=CLEAR_STANDS + 6 + CLEAR_OUT, every=2, sheet=False,
                                    lines=len(t.counters)))]
    return t


def built(m):
    """Bisect control: the engineer's structure only has to appear (retail's bunker does not melt)."""
    t = Test()
    eng = m.role('engineer').name
    t.scripts.append(Script('Test - start', [], [('MAP_REVEAL_ALL_PERM', m.player('p1')),
                                                 ('NAMED_FIRE_SPECIAL_POWER_AT_WAYPOINT', eng,
                                                  m.ability('engineer', 'freeze'), m.mark('spot'))]))
    counted('Test Walls', '建筑', t, template=m.role('wall').template)
    t.expect += [('建筑', 0, 'ever==', 1)]
    t.bench = [('bench_watch', dict(seconds=30, every=3, sheet=False, lines=len(t.counters), until='c1==1'))]
    return t


def freeze(m):
    t = Test()
    eng = m.role('engineer').name
    t.scripts.append(Script('Test - start', [], [('MAP_REVEAL_ALL_PERM', m.player('p1')),
                                                 ('SET_MILLISECOND_TIMER', 'Test - freeze timer', FREEZE_AT)]))
    t.scripts.append(Script('Test - freeze', [('TIMER_EXPIRED', 'Test - freeze timer')],
                            [('NAMED_FIRE_SPECIAL_POWER_AT_WAYPOINT', eng, m.ability('engineer', 'freeze'),
                              m.mark('spot'))]))
    counted('Test Walls', '冰墙', t, template=m.role('wall').template)
    life = m.param('wall', 'lifetime')
    t.expect += [('冰墙', 0, '==', 0, FREEZE_AT - 2), ('冰墙', FREEZE_AT, 'ever==', 1),
                 ('冰墙', FREEZE_AT + life + 12, 'ever==', 0)]      # he walks there and builds first
    t.bench = [('bench_watch', dict(seconds=FREEZE_AT + life + 22, every=3, sheet=False, lines=len(t.counters)))]
    return t


def smash(m):
    t = Test()
    wall = m.role('wall').name
    t.scripts.append(Script('Test - start', [], [('MAP_REVEAL_ALL_PERM', m.player('p1')),
                                                 ('SET_MILLISECOND_TIMER', 'Test - attack timer', ATTACK_AT)]))
    # left alone the Hammers never shot it (bench 2026-10-22: 100 % for 44 s): ordered, as a player would
    t.scripts.append(Script('Test - attack', [('TIMER_EXPIRED', 'Test - attack timer')],
                            [('NAMED_ATTACK_NAMED', h.name, wall) for h in m.roles('hammer')]))
    counted('Test Walls', '冰墙', t, template=m.role('wall').template)
    counted('Test Wall Health', '冰墙血量', t, health=wall)
    t.expect += [('冰墙血量', 0, '==', 100, ATTACK_AT - 2), ('冰墙血量', ATTACK_AT, 'ever<', 100),
                 ('冰墙', ATTACK_AT, 'ever==', 0)]
    t.bench = [('bench_watch', dict(seconds=70, every=3, sheet=False, lines=len(t.counters), until='c1==0'))]
    return t
