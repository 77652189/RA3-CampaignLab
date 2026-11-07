"""Level-line probe: does A4's Ghost King shoot a wall it is re-ordered against every frame (missions/kingref_bench.py)?
Background: checks/a4.py smev (bench 2026-11-07) reproduced the old behaviour on the real map -- the King walks from the
shore to the bridge either way, but with the attack order re-given every frame the wall's health stays 100; with it given
once the King fires from the same spot. A's engine_reorder tank fires under every-frame orders, so what differs is the
unit (King = JapanAntiVehicleVehicleTech3, a heavy tank) or the target (a SET_REF pick, not a name).

The enemy (s1) King is made at 1 s at S; the wall W stands 900 north. Orders from 2 s:
  kone    named wall, the order once                         (control)
  kevery  named wall, the whole order every frame
  rone    unnamed wall picked with SET_REF at 1.5 s, the order once
  revery  unnamed wall, SET_REF once, the order every frame  (what A4 did)
  aref    like revery but the attacker is the Athena tank of A's probe (separates unit from target kind)
Counters: 近墙 (the King in the square of half-side 170 round (0, 330)), 墙血 (the wall's health in percent: by name, or
by the reference). bench_watch 45 s, every 2 s.
"""
from parts import Script, Test, counted, square

VARIANTS = ('kone', 'kevery', 'rone', 'revery', 'aref')
ATK, WALL = 'UNIT - CNV Reo Atk', 'UNIT - CNV Reo Wall'
REF = 'UNITRef - CNV Reo Nearest Wall'
KING, ATHENA = 'JapanAntiVehicleVehicleTech3', 'AlliedAntiVehicleVehicleTech1'
RUN = 45.0


def frames(m):
    t = Test()
    v = VARIANTS[m.facts['variant']]
    p1 = m.player('p1')
    team = m.teams['Reo']
    named = v in ('kone', 'kevery')
    t.areas['Test Mid'] = square(*m.point('mid'), 150.0)
    t.areas['Test Near'] = square(*m.point('near'), 170.0)
    target = WALL if named else REF
    order = m.order('attack', [ATK], target, 's1', crew='Reo')
    timers = [('SET_MILLISECOND_TIMER', 'Test Make', 1.0), ('SET_MILLISECOND_TIMER', 'Test Pick', 1.5),
              ('SET_MILLISECOND_TIMER', 'Test Go', 2.0)]
    t.scripts.append(Script('Test - start', [], [('MAP_REVEAL_ALL_PERM', p1)] + timers))
    t.scripts.append(Script('Test - make', [('TIMER_EXPIRED', 'Test Make')],
                            [('CREATE_NAMED_ON_TEAM_AT_WAYPOINT', ATK, ATHENA if v == 'aref' else KING,
                              m.team('s1'), m.mark('s')), ('UNIT_SET_TEAM', ATK, team)]))
    if not named:
        t.scripts.append(Script('Test - pick', [('TIMER_EXPIRED', 'Test Pick')],
                                [('SET_REF_TO_NEREST_TEAM_OF_UNNAMED_TYPE_OWNED_BY_PLAYER', 'CNV_ReoWall', p1,
                                  m.team('s1'), REF)]))
    t.scripts.append(Script('Test - order', [('TIMER_EXPIRED', 'Test Go')], order, once=v in ('kone', 'rone')))
    counted('CNV_Reo_N', '近墙', t, named=ATK, area='Test Near')
    counted('CNV_Reo_H', '墙血', t, health=WALL if named else REF)
    t.bench = [('bench_watch', dict(seconds=RUN, every=2, sheet=False, lines=len(t.counters)))]
    return t


CHECKS = {f'kingref_{v}': {'frames': frames} for v in VARIANTS}
