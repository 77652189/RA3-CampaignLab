"""Engine unit test: does a moving tank's hull turn to where it drives, and how soon -- read by the side / rear
scalar a hit takes (engine_shot flank: BaseTankArmor Side 105 beyond 45 degrees, Rear 110 beyond 135, by where
the shooter stands against the victim's facing; docs/engine/weapons.md 4).

Every pair: engine_shot's flank V4 (one 4000 EXPLOSIVE instant hit, no pre-attack, no scatter; the next hit >= 4.5 s
later) HULL_REACH south of engine_missile's 10 000-health Hammer, which faces south (the map's default for s1: the
shooter is in front of it). Both keep NO_ATTACK until the fire order. At MOVE the check's Hammers are sent (PAIRS:
east, north of where they stand); each V4 is told to fire the pair's seconds after that. Counter per Hammer:
percent lost (1 per percent; a front hit 40, a side 42, a rear 44).

  turn   still  not sent (the control)                    front 40
         north  north 600, fire 2.5 s after               turned: the shooter behind it, rear 44; not: front 40
         east   east 600, fire 2.5 s after                turned: the shooter ~110 off its facing, side 42
         short  north 120 (behind it, short), 2.5 s after turned and arrived: rear 44; reversed: front 40
  rate   r15 / r30 / r50 / r80: north 600, fire 0.15 / 0.3 / 0.5 / 0.8 s after -- the turn under way (front 40
         below 45 degrees off, side 42 to 135, rear 44 past it)

Prediction from the data (round 187, before the bench): the Hammer's locomotor turns (TurnTimeSeconds 1.25,
ClampOrientationToPathTangent true), so north 44, east 42; short may reverse (CanReverseMove true, the goal 120
behind) -- not predicted; the rate pairs mid-turn. The model before this round never turned a moving hull: 40 on
every pair.

Bench 11-12 (round 187, run_queue at c2a4fde5, both PASS):

  turn   40 / 44 / 42 / 44 (s5-s9; still's second hit at s10)   the hull faces the way it drives; no reversing
  rate   44 / 44 / 44 / 44 (s5-s12)                              already turned 0.15 s after the order: faster
                                                                 than 180 degrees in ~0.3 s, whatever 1.25 s means

Model (sim.Sim.move): a body that moved this step faces its step's direction at once (INFERRED: instant; the
true rate is only known to be above that).
"""
from maps import probe_range
from parts import Mission, Script, Test
from checks.engine_missile import LOST_MAX, TARGET_ID, target
from checks.engine_shot import FLANK_DAMAGE, DAMAGE, _nuggets, shot_v4

SHOOTER = 'CNV_HullV4'
HULL_AT, HULL_REACH = 300.0, 250.0          # the Hammer this far north of its spot, the V4 this far south of it
MOVE = 4.0                                   # every clip is loaded by 6 s; the fire orders all come after it
# pair: (lane gun pad, east offset of the pair on it, where the Hammer is sent from where it stands or None,
# seconds from the move order to the fire order); four pairs a check (four counter lines fit)
PAIRS = {
    'still': ('base', 0.0, None, 2.5), 'north': ('high', 0.0, (0.0, 600.0), 2.5),
    'east': ('removed', -300.0, (600.0, 0.0), 2.5), 'short': ('switch', 0.0, (0.0, 120.0), 2.5),
    'r15': ('order', -300.0, (0.0, 600.0), 0.15), 'r30': ('order', 300.0, (0.0, 600.0), 0.3),
    'r50': ('low', -300.0, (0.0, 600.0), 0.5), 'r80': ('low', 300.0, (0.0, 600.0), 0.8),
}
GROUPS = {'turn': ('still', 'north', 'east', 'short'), 'rate': ('r15', 'r30', 'r50', 'r80')}
RUN = MOVE + 2.5 + 3.0                       # the last fire order and its first hit, not the second


def _n(pair, part):
    return f'UNIT - CNV Hull {pair.title()} {part}'


def mission():
    units = [shot_v4(SHOOTER, _nuggets(DAMAGE.format(d=FLANK_DAMAGE, r=0, extra='')),
                     what=f'车体朝向 V4（探针）：{FLANK_DAMAGE:g} 伤害（EXPLOSIVE），无预瞄、无开火持续、无散布'),
             target()]
    m = Mission(name='CampHull', map=probe_range, units=units, facts={})
    for pair, (lane, dx, _, _) in PAIRS.items():
        site = f'{lane} gun'
        m.put(SHOOTER, site, dx, HULL_AT - HULL_REACH, side='p1', role=f'{pair} shooter', name=_n(pair, 'Shooter'),
              angle=1.5707963267948966)          # facing north, at its Hammer
        m.put(TARGET_ID, site, dx, HULL_AT, side='s1', role=f'{pair} target', name=_n(pair, 'Target'))
    return m


def hull_test(m, group):
    t = Test()
    start = [('MAP_REVEAL_ALL_PERM', m.player('p1'))]
    start += [('UNIT_CHANGE_OBJECT_STATUS', _n(pair, part), 'NO_ATTACK', 1) for pair in PAIRS
              for part in ('Shooter', 'Target')]
    start += [('SET_MILLISECOND_TIMER', 'Test Move', MOVE)]
    t.scripts.append(Script('Test - start', [], start))
    moves = []
    for pair in GROUPS[group]:
        lane, dx, go, fire = PAIRS[pair]
        if go is not None:
            x, y = m.site(f'{lane} gun')[:2]
            spot = f'Test Hull {pair.title()} Goal'
            t.waypoints[spot] = (x + dx + go[0], y + HULL_AT + go[1])
            moves.append(('MOVE_NAMED_UNIT_TO', _n(pair, 'Target'), spot))
        moves.append(('SET_MILLISECOND_TIMER', f'Test Fire {pair.title()}', fire))
    t.scripts.append(Script('Test - move', [('TIMER_EXPIRED', 'Test Move')], moves))
    for k, pair in enumerate(GROUPS[group]):
        s, tg = _n(pair, 'Shooter'), _n(pair, 'Target')
        t.scripts.append(Script(f'Test - fire {pair}', [('TIMER_EXPIRED', f'Test Fire {pair.title()}')],
                                [('UNIT_CHANGE_OBJECT_STATUS', s, 'NO_ATTACK', 0), ('NAMED_ATTACK_NAMED', s, tg)]))
        c = f'CNV_Hull_{group[0].upper()}{k}'
        t.counters.append((c, pair))
        t.scripts += [Script(f'Test - {c} lost {j}', [('UNIT_HEALTH', tg, 0, 100 - j + 1)],
                             [('INCREMENT_COUNTER', 1, c)]) for j in range(1, LOST_MAX + 1)]
    t.expect = [(GROUPS[group][0], 0, 'ever>=', 1, RUN - 1)]
    t.bench = [('bench_watch', dict(seconds=RUN, every=1, sheet=False, lines=6))]
    return t


MISSION = {'engine_hull': mission}
CHECKS = {'engine_hull': {g: (lambda m, g=g: hull_test(m, g)) for g in GROUPS}}
