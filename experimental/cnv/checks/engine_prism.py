"""Engine unit test: why does the mirage tank fire ONE shot and stop (engine line C round 12; docs/engine/weaponset.md 4).
Bench 11-09: a mirage tank told to attack a held Tsunami tank (380 hp, NO_ATTACK) hit it once (200 -> 47 % left) and never
fired again for 40 s, though its cannon is a single shot (1.5 s firing, 0.1 s reload, auto) that should repeat every 1.6 s.
The simulator fires on. Candidates: the cannon's OCL nugget makes a prism node object at the target that blocks the
line of sight; the one attack order is spent by a clip (ReAcquireDetailType PER_CLIP); a Tsunami target in particular.

On the range probe map, four lanes (the lane names are the map's; the counter bar holds four lines), each an attacker of
the player's at '<lane> gun' and a Tsunami tank 100 north (the enemy's, NO_ATTACK, never answers):
  base     mirage    one attack order at ORDER        (the control: one shot expected)
  high     mirage    no order at all (auto-acquire)
  removed  guardian  one attack order                 (a plain cannon: keeps firing)
  low      mirage    the order given again every 3 s from ORDER (is a fresh order a fresh clip?)
Counters: 基准血 / 自动血 / 守护血 / 重令血 -- the Tsunami's health in percent, every second.

Bench 2026-11-09: 基准 / 自动 / 守护 / 重令 = s1 47 47 84 47, s2-3 47 47 68 47, s4-5 .. 52, s6-7 .. 36, s8-9 .. 21, s10-31
47 47 5 47. The mirage tank fires once however it is aimed (an order, auto-acquire, a fresh order every 3 s), the guardian's
plain cannon keeps firing at the same tank: the cause is in the prism cannon itself (docs/engine/weaponset.md 4).
"""
from maps import probe_range
from parts import Mission, Script, Test, counted

CONSCRIPT, MIRAGE, GUARD, TANK = ('SovietAntiInfantryInfantry', 'AlliedAntiVehicleVehicleTech3',
                                  'AlliedAntiVehicleVehicleTech1', 'JapanAntiVehicleVehicleTech1')
LANES = {'base': (MIRAGE, TANK), 'high': (MIRAGE, TANK), 'removed': (GUARD, TANK), 'low': (MIRAGE, TANK)}
ORDERED = ('base', 'removed')                   # one attack order; low: repeated; high: none
ORDER, AGAIN, RUN = 3.0, 3.0, 30.0
LABELS = (('Base', '基准血'), ('High', '自动血'), ('Removed', '守护血'), ('Low', '重令血'))


def _n(lane, part):
    return f'UNIT - CNV Prism {lane.title()} {part}'


def mission():
    m = Mission(name='CampPrism', map=probe_range, units=[], facts={})
    for lane, (gun, target) in LANES.items():
        m.put(gun, f'{lane} gun', side='p1', role=f'{lane} attacker', name=_n(lane, 'Man'))
        m.put(target, f'{lane} gun', 0.0, 100.0, side='s1', role=f'{lane} target', name=_n(lane, 'Tank'))
    return m


def prism_test(m):
    t = Test()
    p1 = m.player('p1')
    targets = [_n(lane, 'Tank') for lane in LANES]
    t.scripts.append(Script('Test - start', [], [('UNIT_CHANGE_OBJECT_STATUS', u, 'NO_ATTACK', 1) for u in targets] + [
        ('MAP_REVEAL_ALL_PERM', p1), ('SET_MILLISECOND_TIMER', 'Test Order', ORDER)]))
    hit = lambda lane: ('NAMED_ATTACK_NAMED', _n(lane, 'Man'), _n(lane, 'Tank'))
    t.scripts.append(Script('Test - order', [('TIMER_EXPIRED', 'Test Order')],
                            [hit(lane) for lane in ORDERED] + [hit('low'), ('SET_MILLISECOND_TIMER', 'Test Again', AGAIN)]))
    t.scripts.append(Script('Test - again', [('TIMER_EXPIRED', 'Test Again')],
                            [hit('low'), ('SET_MILLISECOND_TIMER', 'Test Again', AGAIN)], once=False))
    for key, label in LABELS:
        counted(f'CNV_Prism_{key}Hp', label, t, health=_n(key, 'Tank'))
    t.expect = [('基准血', 0, 'ever<=', 99, RUN)]
    t.bench = [('bench_watch', dict(seconds=RUN, every=1, sheet=False, lines=len(t.counters)))]
    return t


MISSION = {'engine_prism': mission}
CHECKS = {'engine_prism': {'a': prism_test}}
