"""A7 tests, for the plan-driven level (docs/story/plans/a7.md, devices/carrier.py). Counters say where the enemy
carrier is -- inside a trigger area around its home, a landing point, the station -- and whether the station stands;
all asked of the mission (its marks, cast and facts), nothing of its own.

Every test but win settles the outposts at once (the two loyal ones handed over, the traitor's killed), so the
first phase ends as soon as its objective shows (READY) and the carrier's jumps start `jump delay` later.

jumps: home, warned, at the base edge (the first landing point: the player's army stands elsewhere), home again.
pick: four of the player's tanks at the base edge: it lands at the second point, the ore, instead.
defend: the station down to 40 % before any jump: the carrier jumps to it at once.
power: the station killed after the first jump: no jump home; grounded, the next phase sends it off its point.
win: the carrier at 1 % health jumps (by test script) to the base edge at 5 s, the player's IFVs shoot it down,
  Mission Won ends the mission.
"""
import plan
from parts import Obj, Script, Test, counted, square
from checks.liberty import EARLY, jumps as fire_jump

AREA = 300.0                                    # half-side of the areas counted around the carrier's places
READY = plan.REVEAL_FIRST + plan.REVEAL_GAP + 3.0   # the outposts' objective shows (2nd of phase 1), then done
KILL_AFTER = 8.0                                # power: the station dies this long after the first jump
HURT_AT = 15.0                                  # defend: the station's health drops then


def settle(t, m):
    """The outposts settled at once by test script: the loyal ones the player's, the traitor's gone. No endings:
    nobody deploys the MCV, and the opening raid kills it (bench 2026-10-25: lost at s90, "no yard, no MCV")."""
    m.drop_endings()
    p1 = m.player('p1')
    t.scripts.append(Script('Test - outposts', [], [('NAMED_TRANSFER_OWNERSHIP_PLAYER', r.name, p1)
                                                    for g in ('loyal 1', 'loyal 1 troops', 'loyal 2', 'loyal 2 troops')
                                                    for r in m.roles(g) or [m.role(g)]] +
                            [('NAMED_KILL', m.role('traitor').name)]))


def where(m, places=('carrier home', 'base edge')):
    t = Test()
    t.scripts.append(Script('Test - reveal', [], [('MAP_REVEAL_ALL_PERM', m.player('p1'))]))
    enemy, carrier = m.player('s1'), m.role('carrier')
    labels = {'carrier home': '在家', 'base edge': '在基地边', 'base ore': '在矿区', 'station': '在电站'}
    for part in places:
        t.areas[f'Test {part}'] = square(*m.point(part), AREA)
        counted(f'Test At {part}', labels[part], t, named=carrier.name, area=f'Test {part}')
    counted('Test Station', '电站', t, template=m.role('station').template, player=enemy)
    return t


def keep_up(m, t):
    """The carrier back at full health every frame: the test is about where it goes, not whether it survives."""
    t.scripts.append(Script('Test - keep the carrier up', [], [('UNIT_SET_HEALTH', m.role('carrier').name, 100.0)],
                            once=False))


def first_jump(m):
    return READY + m.facts['jump delay'] + m.facts['warning']


def jumps(m):
    first, stay = first_jump(m), m.facts['stay']
    t = where(m)
    settle(t, m)
    keep_up(m, t)
    t.expect += [('在家', 0, '==', 1, first - EARLY - 3), ('在基地边', 0, '==', 0, first - EARLY - 3),
                 ('在基地边', first + 4, 'ever==', 1, first + stay - EARLY),
                 ('在家', first + stay + 4, 'ever==', 1)]
    t.bench = [('bench_watch', dict(seconds=first + stay + 15, every=3, sheet=False, lines=len(t.counters)))]
    return t


def pick(m):
    first = first_jump(m)
    t = where(m, ('carrier home', 'base edge', 'base ore'))
    settle(t, m)
    keep_up(m, t)
    for k, (dx, dy) in enumerate(((-40, -40), (40, -40), (-40, 40), (40, 40))):
        t.objects.append(Obj('AlliedAntiVehicleVehicleTech1', *m.site('base edge', dx, dy), site='base edge'))
    t.expect += [('在矿区', first + 4, 'ever==', 1, first + 20), ('在基地边', 0, '==', 0)]
    t.bench = [('bench_watch', dict(seconds=first + 20, every=3, sheet=False, lines=len(t.counters)))]
    return t


def defend(m):
    t = where(m, ('carrier home', 'station'))
    keep_up(m, t)
    timer = 'Test - hurt timer'
    t.scripts += [Script('Test - hurt set', [], [('SET_MILLISECOND_TIMER', timer, HURT_AT)]),
                  Script('Test - hurt station', [('TIMER_EXPIRED', timer)],
                         [('UNIT_SET_HEALTH', m.role('station').name, 40.0)])]
    t.expect += [('在电站', 0, '==', 0, HURT_AT - EARLY), ('在电站', HURT_AT + 4, 'ever==', 1, HURT_AT + 15)]
    t.bench = [('bench_watch', dict(seconds=HURT_AT + 18, every=2, sheet=False, lines=len(t.counters)))]
    return t


def power(m):
    first, stay = first_jump(m), m.facts['stay']
    t = where(m)
    settle(t, m)
    keep_up(m, t)
    timer = 'Test - kill timer'
    t.scripts += [Script('Test - kill set', [], [('SET_MILLISECOND_TIMER', timer, first + KILL_AFTER)]),
                  Script('Test - kill station', [('TIMER_EXPIRED', timer)], [('NAMED_KILL', m.role('station').name)])]
    t.expect += [('电站', 0, '==', 1, first + KILL_AFTER - EARLY), ('电站', first + KILL_AFTER + 2, '==', 0),
                 ('在基地边', first, 'ever==', 1, first + KILL_AFTER),       # wide enough for a reading every 4 s
                 ('在家', first + KILL_AFTER, '==', 0),                                  # no jump home, ever
                 ('在基地边', first + stay + 30, '==', 0)]                               # flown off its point
    t.bench = [('bench_watch', dict(seconds=first + stay + 35, every=4, sheet=False, lines=len(t.counters)))]
    return t


def east(m):
    """The east bank given to the skirmish AI (敌方AI, a player of its own beside the enemy): asleep and broke
    through phase 1; woken (phase 2 + its time, normal difficulty) it is given the east bank's construction yard,
    power plant, barracks, factory and airfield and spends its money on troops from them; the carrier stays home till its first jump (the enemy's, not
    the AI's -- bench 2026-10-25: with the enemy itself the AI, it left home at 18 s). Its barracks stand the whole
    run: bench 2026-10-25, with no construction yard it sank its money into an MCV it never finished, sold its
    buildings when broke -- and the bonus objective (destroy them) was done for the player."""
    t = Test()
    t.scripts.append(Script('Test - reveal', [], [('MAP_REVEAL_ALL_PERM', m.player('p1'))]))
    t.areas['Test carrier home'] = square(*m.point('carrier home'), AREA)
    counted('Test At carrier home', '在家', t, named=m.role('carrier').name, area='Test carrier home')
    settle(t, m)
    keep_up(m, t)
    ai = m.ai_player()
    counted('Test AI Barracks', 'AI的兵营', t, template=m.role('east barracks').template, player=ai)
    t.counters.append(('Test AI Money', '敌方资金'))
    t.scripts.append(Script('Test - AI money', [], [('SET_PLAYER_MONEY_TO_COUNTER', ai, 'Test AI Money')], once=False))
    counted('Test AI Guardians', 'AI的守护者', t, template='AlliedAntiVehicleVehicleTech1', player=ai)
    wake = READY + plan.spans(plan.load('a7')['敌方AI']['唤醒']['任一'][0].split('+')[1])[1][0]
    money = plan.counts(plan.load('a7')['敌方AI']['资金'])[1]
    # bench 2026-10-25: woken at s36 it had spent 1000 of its 5000 by s44 -- the money is read rising, not as given
    t.expect += [('敌方资金', 1, '==', 0, wake - 4), ('敌方资金', wake - 4, 'ever>', 0, wake + 12),
                 ('敌方资金', wake, 'ever<', money - 1000, wake + 150),
                 ('AI的守护者', 1, '==', 0, wake - 4), ('AI的守护者', wake, 'ever>', 0, wake + 180),
                 ('AI的兵营', wake + 8, '>=', 1),
                 ('在家', 0, '==', 1, READY + m.facts['jump delay'] - EARLY)]
    t.bench = [('bench_watch', dict(seconds=wake + 180, every=4, sheet=False, lines=len(t.counters)))]
    return t


def win(m):
    m.find(m.role('carrier').name).props['objectInitialHealth'] = 1
    t = where(m)
    fire_jump(t, m.role('carrier').name, m.ability('carrier', 'jump'), 'Test Strike', m.point('base edge'), at=5.0)
    t.expect += [('ENDED', 5, '', None)]
    t.bench = [('bench_watch', dict(seconds=25, every=1, sheet=False))]
    return t
