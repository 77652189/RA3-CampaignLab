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


GHOST_BORN = 40.0                               # ghost: the Ghost King appears (the walls have stood since ~20)
GHOST_ORDER = 60.0                              # ghost: from here the script orders it, by the wall nearest to it
GHOST_AREA = 90.0                               # half-side of the area round a wall's spot
REF = 'UNITRef - CNV Nearest Wall'


def ghost_north(m):
    """ghost, but the Ghost King is made at the far north of the walls (150, 600), nearest to B: a nearest-first walk
    from there goes B, A, C, D (300, 640, 900, 985); from the map's origin it would go D, C, A, B."""
    return ghost(m, start=m.site('west field', 150, 600), first=2, order=(2, 1, 3, 4))


def ghost(m, start=None, first=3, order=None):
    """Three questions of A4's last stretch (docs/design/cards/a4-layer3.md), one scene. Four walls built by four
    engineers (unnamed objects, as in play); a Ghost King appears by wall C at GHOST_BORN, left alone until GHOST_ORDER:
    1. does it smash a wall on its own (the wall's health at the nearest one, GHOST_BORN .. GHOST_ORDER)?
    2. a wall in an area is countable (the player's wall count in each wall's area);
    3. from GHOST_ORDER, each frame: if the name REF points at no live object and a wall stands, point REF at the
       nearest unnamed wall to the enemy's team, the Ghost King's (SET_REF_TO_NEREST_...) and order the Ghost King at REF (every frame).
       Read: which area REF is in, the health of REF -- the visits should go C, A, B, D (nearest first)."""
    t = Test()
    p1 = m.player('p1')
    far = m.role('ghost')                       # placed far off, to give the cast an object; killed, a fresh one is made
    gk = 'UNIT - CNV Ghost King 2'
    t.waypoints['Test Ghost Start'] = start or m.point('ghost')
    wall = m.role('wall').template
    t.scripts += [Script('Test - start', [], [('MAP_REVEAL_ALL_PERM', p1),
                                              ('SET_MILLISECOND_TIMER', 'Test - born timer', GHOST_BORN),
                                              ('SET_MILLISECOND_TIMER', 'Test - order timer', GHOST_ORDER)] +
                          [('NAMED_FIRE_SPECIAL_POWER_AT_WAYPOINT', m.role(f'engineer {k}').name,
                            m.ability(f'engineer {k}', 'freeze'), m.mark(f'spot {k}')) for k in 'ABCD']),
                  Script('Test - born', [('TIMER_EXPIRED', 'Test - born timer')],
                         [('NAMED_KILL', m.role(f'engineer {k}').name) for k in 'ABCD'] +
                         [('NAMED_KILL', far.name),
                          ('CREATE_NAMED_ON_TEAM_AT_WAYPOINT', gk, far.template, m.team('s1'), 'Test Ghost Start'),
                          ('SET_FLAG', 'Test Picking', 1)]),
                  Script('Test - order on', [('TIMER_EXPIRED', 'Test - order timer')], [('SET_FLAG', 'Test Ordering', 1)])]
    # a name nobody has had reads as neither destroyed nor standing (sim: destroyed unborn): a flag says whether REF
    # points at something yet; once what it pointed at is destroyed, the flag drops and the next one is picked
    t.scripts += [Script('Test - pick', [('FLAG', 'Test Picking', 1), ('FLAG', 'Test Picked', 0),
                                         ('COUNTER', 'Test Walls', 3, 1)],
                         [('SET_REF_TO_NEREST_TEAM_OF_UNNAMED_TYPE_OWNED_BY_PLAYER', wall, p1, m.team('s1'), REF),
                          ('SET_FLAG', 'Test Picked', 1)], once=False),
                  Script('Test - dropped', [('FLAG', 'Test Picked', 1), ('NAMED_DESTROYED', REF)],
                         [('SET_FLAG', 'Test Picked', 0)], once=False),
                  Script('Test - smash', [('FLAG', 'Test Ordering', 1), ('NAMED_NOT_DESTROYED', REF),
                                          ('NAMED_NOT_DESTROYED', gk)],
                         [('NAMED_ATTACK_NAMED', gk, REF)], once=False)]
    counted('Test Walls', '墙总数', t, template=wall)
    # only four counter lines fit (the fourth reads wrong in the digit strip: the least needed goes there): areas
    # holding a wall (0-4), where the pointed wall is (1-4 = A-D, 0 nowhere), the pointed wall's health
    t.counters += [('Test Areas', '有墙的区域数'), ('Test Where', '选中的墙是')]
    counted('Test Ref Health', '目标墙血量', t, health=REF)
    t.scripts += [Script('Test - areas zero', [], [('SET_COUNTER', 'Test Areas', 0)], once=False),
                  Script('Test - where zero', [], [('SET_COUNTER', 'Test Where', 0)], once=False)]
    for i, k in enumerate('ABCD', 1):
        t.areas[f'Test Spot {k}'] = square(*m.point(f'spot {k}'), GHOST_AREA)
        t.scripts += [Script(f'Test - area {k}', [('PLAYER_HAS_COMPARISON_UNIT_TYPE_IN_TRIGGER_AREA', p1, 3, 1, wall,
                                                   f'Test Spot {k}')], [('INCREMENT_COUNTER', 1, 'Test Areas')],
                             once=False),
                      Script(f'Test - where {k}', [('NAMED_INSIDE_AREA', REF, f'Test Spot {k}')],
                             [('SET_COUNTER', 'Test Where', i)], once=False)]
    # bench 2026-10-31: made by wall C it left it (the nearest) at 100 % for the 20 s it stood beside it, then once ordered
    # smashed C, A, D, B (distance from where it was made: C 150, A 300, D 550, B 620) in ~16-24 s a wall
    t.expect += [('墙总数', 30, 'ever==', 4), ('有墙的区域数', 30, 'ever==', 4),
                 ('选中的墙是', GHOST_BORN + 2, '==', first, GHOST_ORDER - 2),
                 ('目标墙血量', GHOST_BORN + 2, '==', 100, GHOST_ORDER - 2),
                 ('选中的墙是', GHOST_ORDER, 'ever==', (order or (3, 1, 4, 2))[1], GHOST_ORDER + 60),
                 ('墙总数', GHOST_ORDER, 'ever==', 0)]
    t.bench = [('bench_watch', dict(seconds=GHOST_ORDER + 150, every=4, sheet=False, lines=len(t.counters)))]
    return t
