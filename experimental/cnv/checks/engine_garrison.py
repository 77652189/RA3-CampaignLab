"""Engine unit test: garrisons (ADR 0019 layer 2; docs/engine/garrison.md) -- who gets into a civilian building, who
owns it, what happens to the passengers when it is hurt, destroyed or contested. Script actions only (the walk to
the door is the AI's: NAMED_GARRISON_SPECIFIC_BUILDING_INSTANTLY).

On the range probe map, six of retail's AM_Apartments_01 (ContestableGarrisonContain, ContainMax 5, infantry only,
neutral and own-player units allowed, enemies and allies not; RequiredClearingObjectStatus CAN_CONTEST_GARRISON;
3000 health), one per lane at '<lane> gun', all the civilians'. Conscripts (SovietAntiInfantryInfantry) in a row
south of each. At IN, ACT and ACT2:

  base     cap      6 of the player's ordered in at IN; ACT one ordered out; ACT2 the rest ordered out
  high     blast    3 in; ACT NAMED_DAMAGE 5000 (the building dies from a hit)
  order    killed   3 in; ACT NAMED_KILL
  removed  worn     3 in; ACT NAMED_DAMAGE 2600 (13 % left); ACT2 NAMED_DAMAGE 200 (under 10 %)
  switch   contest  2 in; ACT an enemy conscript ordered in; ACT2 another enemy conscript, given
                    CAN_CONTEST_GARRISON at the start, ordered in
  low      enemy    1 enemy conscript in at IN; ACT one of the player's ordered in

Counters (four lines fit; "inside" = the lane's conscripts carrying ENCLOSED, ObjectStatusOfContained):
  驻满     cap: inside + 10 if the player owns the building
  伤争敌    worn inside (ones) + contest inside (tens) + enemy-lane inside (hundreds) + 1000 if the enemy owns
           that building
  炸杀     blast inside (ones) + killed inside (tens)
  存活     the blast lane's conscripts alive (ones) + the killed lane's (tens)

The model's answer (RA3-EngineModel ra3model/objects/contain.py, read in RA3 1.13): 驻满 15 / 14 / 0 (five places,
the owner the first passenger's, empty -> the civilians'); 伤争敌 1123 after IN (the enemy refused at ACT, the
player's refused by the enemy's building), 1110 after ACT2 (worn: out under 10 % (REALLYDAMAGED), still in at 13 %;
the contesting one bounces the first passenger and stays out); 炸杀 33 -> 0; 存活 33 -> 3 (a hit that kills ejects
them alive, a script kill kills them).

Bench 11-05 (round 39; the bench's seconds ~1 s ahead of the timers):
  in  CampGarrisonIn_mcp_1105_183705: 驻满 16 (s2-s7), 15 (s8-s13), 0 (s14-); 伤争敌 1123 / 1230 / 1220; 炸杀 33 / 0;
      存活 33 throughout.
  hp  CampGarrisonHp_mcp_1105_183510: 炸楼血 100 -> 0 at s8, 伤楼血 100 -> 13 -> 6; 炸杀, 存活 as above.
So, against the model's first answer: the script's _INSTANTLY entry ignores ContainMax and the relation (six in;
an enemy into the player's building, the player's into the enemy's); the passengers leave at 13 % (ActiveBody's
MaxHealthReallyDamagedPercentage, default 33.3 %, not Generals' 10 %); NAMED_KILL ejects them alive; only the
unit with CAN_CONTEST_GARRISON bounces anyone (the plain enemy stayed beside the player's two; the contesting one
took one out and stayed out). The model was corrected to all of it (RA3-EngineModel contain.py, round 39;
tests/test_objects_bench.py). NAMED_DAMAGE's amount must be an integer: 5000.0 did nothing (health 100 throughout,
run CampGarrisonHp_mcp_1105_183303).
"""
from maps import probe_range
from model import status
from parts import Mission, Script, Test, counted

HOUSE, MAN = 'AM_Apartments_01', 'SovietAntiInfantryInfantry'
IN, ACT, ACT2, RUN = 3.0, 9.0, 15.0, 24.0
# lane -> (the player's conscripts, the enemy's conscripts)
LANES = {'base': (6, 0), 'high': (3, 0), 'order': (3, 0), 'removed': (3, 0), 'switch': (2, 2), 'low': (1, 1)}


def _house(lane):
    return f'UNIT - CNV Garrison {lane.title()} House'


def _man(lane, side, k):
    return f'UNIT - CNV Garrison {lane.title()} {side.upper()} {k}'


def mission():
    m = Mission(name='CampGarrison', map=probe_range, units=[], facts={})
    for lane, (ours, theirs) in LANES.items():
        site = f'{lane} gun'
        m.put(HOUSE, site, side='civ', role=f'{lane} house', name=_house(lane))
        for side, n, row in (('p1', ours, -220.0), ('s1', theirs, -300.0)):
            for k in range(n):
                m.put(MAN, site, -150.0 + 60.0 * k, row, side=side, role=f'{lane} {side} {k}',
                      name=_man(lane, side, k))
    return m


def garrison_test(m, hp=False):
    t = Test()
    p1, s1 = m.player('p1'), m.player('s1')
    enclosed = status('ENCLOSED')
    hold = [('UNIT_CHANGE_OBJECT_STATUS', _man(lane, side, k), 'NO_ATTACK', 1)     # no fighting across the lane
            for lane, (ours, theirs) in LANES.items() for side, n in (('p1', ours), ('s1', theirs)) for k in range(n)]
    t.scripts.append(Script('Test - start', [], hold + [
        ('MAP_REVEAL_ALL_PERM', p1),
        ('UNIT_CHANGE_OBJECT_STATUS', _man('switch', 's1', 1), 'CAN_CONTEST_GARRISON', 1),
        ('SET_MILLISECOND_TIMER', 'Test In', IN), ('SET_MILLISECOND_TIMER', 'Test Act', ACT),
        ('SET_MILLISECOND_TIMER', 'Test Act2', ACT2)]))
    go = lambda u, lane: ('NAMED_GARRISON_SPECIFIC_BUILDING_INSTANTLY', u, _house(lane))   # noqa: E731
    out = lambda u: ('NAMED_EXIT_BUILDING', u)                                              # noqa: E731
    at_in = [go(_man(lane, 'p1', k), lane) for lane in ('base', 'high', 'order', 'removed', 'switch')
             for k in range(LANES[lane][0])] + [go(_man('low', 's1', 0), 'low')]
    at_act = [out(_man('base', 'p1', 0)), ('NAMED_DAMAGE', _house('high'), 5000), ('NAMED_KILL', _house('order')),
              ('NAMED_DAMAGE', _house('removed'), 2600), go(_man('switch', 's1', 0), 'switch'),
              go(_man('low', 'p1', 0), 'low')]
    at_act2 = [out(_man('base', 'p1', k)) for k in range(1, 6)] + [
        ('NAMED_DAMAGE', _house('removed'), 200), go(_man('switch', 's1', 1), 'switch')]
    t.scripts += [Script('Test - in', [('TIMER_EXPIRED', 'Test In')], at_in),
                  Script('Test - act', [('TIMER_EXPIRED', 'Test Act')], at_act),
                  Script('Test - act2', [('TIMER_EXPIRED', 'Test Act2')], at_act2)]
    def lane_rows(lane, step, owner=None):
        ours, theirs = LANES[lane]
        rows = [(step, ('UNIT_HAS_OBJECT_STATUS', _man(lane, side, k), enclosed))
                for side, n in (('p1', ours), ('s1', theirs)) for k in range(n)]
        if owner:
            rows.append((step * 10, ('NAMED_OWNED_BY_PLAYER', owner, _house(lane))))
        return rows

    if hp:                              # the hp check: the blast and worn buildings' health instead
        counted('CNV_Garrison_HighHp', '炸楼血', t, health=_house('high'))
        counted('CNV_Garrison_WornHp', '伤楼血', t, health=_house('removed'))
    lines = [] if hp else [('CNV_Garrison_Cap', '驻满', lane_rows('base', 1, p1)),
                           ('CNV_Garrison_Mix', '伤争敌', lane_rows('removed', 1) + lane_rows('switch', 10)
                            + lane_rows('low', 100, s1))]
    for c, label, rows in lines + [('CNV_Garrison_Die', '炸杀', lane_rows('high', 1) + lane_rows('order', 10))]:
        t.counters.append((c, label))
        t.scripts.append(Script(f'Test - {c} zero', [], [('SET_COUNTER', c, 0)], once=False))
        t.scripts += [Script(f'Test - {c} {i}', [cond], [('INCREMENT_COUNTER', step, c)], once=False)
                      for i, (step, cond) in enumerate(rows)]
    c = 'CNV_Garrison_Alive'
    t.counters.append((c, '存活'))
    t.scripts.append(Script(f'Test - {c} zero', [], [('SET_COUNTER', c, 0)], once=False))
    t.scripts += [Script(f'Test - {c} {lane} {k}', [('NAMED_NOT_DESTROYED', _man(lane, 'p1', k))],
                         [('INCREMENT_COUNTER', step, c)], once=False)
                  for lane, step in (('high', 1), ('order', 10)) for k in range(3)]
    # judged loosely here (the bench's seconds run ~1 s ahead of the timers); the side-by-side test holds the rest
    t.expect = [('炸杀' if hp else '驻满', 0, 'ever>=', 11, ACT - 1), ('存活', 0, 'ever>=', 33, IN + 2)]
    t.bench = [('bench_watch', dict(seconds=RUN, every=1, sheet=False, lines=len(t.counters)))]
    return t


MISSION = {'engine_garrison': mission}
CHECKS = {'engine_garrison': {'in': garrison_test,      # the mod's name CampGarrisonIn: 15 characters at most
                              'hp': lambda m: garrison_test(m, hp=True)}}
