"""A1 (coord 11-28; docs/design/flow/mechanics.md 占点计数 / 燃烧瓶清楼): two design promises, on the range probe map with
retail's civilian AM_Apartments_01 (ContestableGarrisonContain, 5 infantry, the owner its first passenger's, empty ->
the civilians': engine_garrison in).

  pts  seven houses ('Plant 1'..'Plant 7'), each a man south of it, everyone NO_ATTACK. A script total each frame
       (zero, then +1 per house NAMED_OWNED_BY_PLAYER) for the player and s1; at 3 s the player's into 1 2 3, 6 s
       s1's into 6 7, 9 s the player's into 4, 12 s the player's out of 1 (NAMED_EXIT_BUILDING), 15 s s1's in 7
       killed inside (NAMED_KILL), 18 s the player's into 5.
         我占 / 敌占   the totals;  到四   a once script on 我占 >= 4;  够数帧   frames with 我占 >= 4.
       Predicted (engine_garrison: the owner follows the first passenger, the house the civilians' when empty):
       3 0 / 3 2 / 4 2 1 / 3 2 1 (45 frames) / 3 1 / 4 1 1.
  mol  five lanes, a house with three of the player's Peacekeepers put in at the start (NO_ATTACK; 150 health), one
       conscript (SovietAntiInfantryInfantry) 170 south of it, healed back every frame:
         base     s1's, Molotov toggled at 1 s (Command_ToggleMolotovCocktailSpecialPower), NAMED_ATTACK_NAMED at 4 s
         high     s1's, no toggle, the same order (the AK47)
         order    s1's, toggled, no order
         removed  s1's, nothing (does Soviet_1 toggle it itself?)
         switch   Soviet_2's (no AI), nothing
       Digits base 1, high 10, order 100, removed 1000, switch 10000:
         屋内 passengers ENCLOSED;  存活 passengers alive;  切换 the conscript has ANTI_GARRISON;  归属 the house is
         the player's.
       Predicted from the data: the Molotov (AttackRange 200, PreAttackDelay 0.25 s, ClipReloadTime 1.0-1.2 s) lands
       a DamageContainedNugget 50 EXPLOSIVE BURNED on ONE infantry passenger (MaxUnitsToDamage 1), and 15 in a radius
       15 on the house: the passengers die inside one at a time (not thrown out alive: 屋内 == 存活), the house the
       civilians' when the last dies; the AK47 has no contained damage (high stays 3). The toggle's SkirmishAiInfo
       ToggleHint TOGGLE_WEAPON is the AI micro manager's (work/re/l4_toggle.md): a unit in no AI team is not
       toggled (removed / switch stay 0) -- INFERRED, the run tells. Bench: as predicted, see AI below.
"""
from maps import probe_range
from model import status
from parts import Mission, Script, Test

HOUSE, ALLY, SOV = 'AM_Apartments_01', 'AlliedAntiInfantryInfantry', 'SovietAntiInfantryInfantry'
MOLOTOV = 'Command_ToggleMolotovCocktailSpecialPower'
SPOTS = [('base', 0), ('high', 0), ('order', 0), ('removed', 0), ('switch', 0), ('low', 0), ('base', 600)]
P_STEPS = ((3, 'in', 'p1', (1, 2, 3)), (6, 'in', 's1', (6, 7)), (9, 'in', 'p1', (4,)), (12, 'out', 'p1', (1,)),
           (15, 'kill', 's1', (7,)), (18, 'in', 'p1', (5,)))
M_LANES = {'base': ('s1', True, True), 'high': ('s1', False, True), 'order': ('s1', True, False),
           'removed': ('s1', False, False), 'switch': ('s2', False, False)}
RUN = {'pts': 24.0, 'mol': 45.0}


def _plant(k):
    return f'UNIT - CNV A1Hold Plant {k}'


def _house(lane):
    return f'UNIT - CNV A1Hold House {lane}'


def mission():
    m = Mission(name='CampA1Hold', map=probe_range, units=[], facts={})
    for k, (lane, dx) in enumerate(SPOTS, 1):              # pts
        m.put(HOUSE, lane + ' gun', dx, 1200.0, side='civ', role=f'plant {k}', name=_plant(k))
        for side, x in (('p1', -40.0), ('s1', 40.0)):
            m.put(ALLY if side == 'p1' else SOV, lane + ' gun', dx + x, 1000.0, side=side, role=f'pman {side} {k}',
                  name=f'{_plant(k)} {side}')
    for lane, (side, _, _) in M_LANES.items():             # mol
        m.put(HOUSE, lane + ' gun', 0.0, 300.0, side='civ', role=f'house {lane}', name=_house(lane))
        for j in range(3):
            m.put(ALLY, lane + ' gun', -60.0 + 60.0 * j, 520.0, role=f'pk {lane} {j}', name=f'{_house(lane)} PK {j}')
        m.put(SOV, lane + ' gun', 0.0, 130.0, side=side, role=f'thrower {lane}', name=f'{_house(lane)} Thrower')
    return m


def _total(t, counter, label, rows):
    """counter = sum of the steps whose condition holds this frame (zeroed first)."""
    t.counters.append((counter, label))
    t.scripts.append(Script(f'Test - {counter} zero', [], [('SET_COUNTER', counter, 0)], once=False))
    t.scripts += [Script(f'Test - {counter} {i}', [c], [('INCREMENT_COUNTER', n, counter)], once=False)
                  for i, (n, c) in enumerate(rows)]


def _drop(m, names):
    return [('NAMED_DELETE', n) for n in names]


def pts_test(m):
    t = Test()
    p1, s1 = m.player('p1'), m.player('s1')
    men = [f'{_plant(k)} {s}' for k in range(1, 8) for s in ('p1', 's1')]
    mol = [n for lane in M_LANES for n in [_house(lane), f'{_house(lane)} Thrower']
           + [f'{_house(lane)} PK {j}' for j in range(3)]]
    start = [('MAP_REVEAL_ALL_PERM', p1)] + [('UNIT_CHANGE_OBJECT_STATUS', n, 'NO_ATTACK', 1) for n in men]
    start += _drop(m, mol) + [('SET_MILLISECOND_TIMER', f'Test At {s}', float(s)) for s, *_ in P_STEPS]
    t.scripts.append(Script('Test - start', [], start))
    for s, what, side, ks in P_STEPS:
        do = {'in': lambda k: ('NAMED_GARRISON_SPECIFIC_BUILDING_INSTANTLY', f'{_plant(k)} {side}', _plant(k)),
              'out': lambda k: ('NAMED_EXIT_BUILDING', f'{_plant(k)} {side}'),
              'kill': lambda k: ('NAMED_KILL', f'{_plant(k)} {side}')}[what]
        t.scripts.append(Script(f'Test - at {s}', [('TIMER_EXPIRED', f'Test At {s}')], [do(k) for k in ks]))
    for counter, label, who in (('CNV_A1H_Ours', '我占', p1), ('CNV_A1H_Theirs', '敌占', s1)):
        _total(t, counter, label, [(1, ('NAMED_OWNED_BY_PLAYER', who, _plant(k))) for k in range(1, 8)])
    four = ('COUNTER', 'CNV_A1H_Ours', 3, 4)
    t.counters += [('CNV_A1H_Four', '到四'), ('CNV_A1H_Held', '够数帧')]
    t.scripts += [Script('Test - four', [four], [('INCREMENT_COUNTER', 1, 'CNV_A1H_Four')]),
                  Script('Test - held', [four], [('INCREMENT_COUNTER', 1, 'CNV_A1H_Held')], once=False)]
    t.expect = [('我占', 0, 'ever>=', 4, RUN['pts'])]
    t.bench = [('bench_watch', dict(seconds=RUN['pts'], every=1, sheet=False, lines=4))]
    return t


def mol_test(m, plan=None):
    plan = plan or {lane: (tog, order) for lane, (_, tog, order) in M_LANES.items()}
    t = Test()
    p1 = m.player('p1')
    pts = [n for k in range(1, 8) for n in (_plant(k), f'{_plant(k)} p1', f'{_plant(k)} s1')]
    pks = {lane: [f'{_house(lane)} PK {j}' for j in range(3)] for lane in M_LANES}
    start = [('MAP_REVEAL_ALL_PERM', p1), ('SET_MILLISECOND_TIMER', 'Test Toggle', 1.0),
             ('SET_MILLISECOND_TIMER', 'Test Order', 4.0)] + _drop(m, pts)
    start += [a for lane in M_LANES for n in pks[lane]
              for a in (('UNIT_CHANGE_OBJECT_STATUS', n, 'NO_ATTACK', 1),
                        ('NAMED_GARRISON_SPECIFIC_BUILDING_INSTANTLY', n, _house(lane)))]
    t.scripts.append(Script('Test - start', [], start))
    t.scripts.append(Script('Test - toggle', [('TIMER_EXPIRED', 'Test Toggle')],
                            [('NAMED_USE_COMMANDBUTTON_ABILITY', f'{_house(lane)} Thrower', MOLOTOV)
                             for lane, (tog, _) in plan.items() if tog]))
    t.scripts.append(Script('Test - order', [('TIMER_EXPIRED', 'Test Order')],
                            [('NAMED_ATTACK_NAMED', f'{_house(lane)} Thrower', _house(lane))
                             for lane, (_, order) in plan.items() if order]))
    for lane in M_LANES:
        me = f'{_house(lane)} Thrower'
        t.scripts.append(Script(f'Test - heal {lane}', [('UNIT_HEALTH', me, 0, 100)], [('UNIT_SET_HEALTH', me, 100.0)],
                                once=False))
    step = {lane: 10 ** i for i, lane in enumerate(M_LANES)}
    _total(t, 'CNV_A1H_In', '屋内', [(step[lane], ('UNIT_HAS_OBJECT_STATUS', n, status('ENCLOSED')))
                                    for lane in M_LANES for n in pks[lane]])
    _total(t, 'CNV_A1H_Alive', '存活', [(step[lane], ('NAMED_NOT_DESTROYED', n)) for lane in M_LANES for n in pks[lane]])
    _total(t, 'CNV_A1H_Anti', '切换', [(step[lane], ('UNIT_HAS_OBJECT_STATUS', f'{_house(lane)} Thrower',
                                                     status('ANTI_GARRISON'))) for lane in M_LANES])
    _total(t, 'CNV_A1H_Owner', '归属', [(step[lane], ('NAMED_OWNED_BY_PLAYER', p1, _house(lane))) for lane in M_LANES])
    t.expect = [('屋内', 0, 'ever>=', 1, RUN['mol'])]
    t.bench = [('bench_watch', dict(seconds=RUN['mol'], every=1, sheet=False, lines=4))]
    return t


MISSION = {'engine_a1hold': mission}
# ai: three of s1's untoggled ordered (does Soviet_1's AI pick the Molotov for an order?), Soviet_2's toggled ordered.
# Bench 11-28 (A431; a swapped run too, CampA1HoldSwp: the lane does not matter): mol and ai, every toggled conscript
# (ordered or not, s1's or s2's) burns its house's three out one at a time, a death about every 6 s (3 x 50), all dead
# inside by ~16 s after the order, the house the civilians' then; 屋内 drops ~2 s before 存活 (the dying body). No
# untoggled one does (the AK47 only; s1's AI toggles nobody in 45 s): mol 33030 33030 101 11010, ai 03330 03330 10001
# 01110 from s19. Toggled and idle (mol order) attacks the house by itself. The simulator burns nobody (33333).
AI = {'base': (True, True), 'high': (False, True), 'order': (False, True), 'removed': (False, True),
      'switch': (True, True)}
CHECKS = {'engine_a1hold': {'pts': pts_test, 'mol': mol_test, 'ai': lambda m: mol_test(m, AI)}}
