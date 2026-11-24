"""Engine probe: three protocols' effects cast by a player's script (missions/super_bench.py with p1's Soviet and Japanese
construction yards; A342, the XML chain and the predictions in the engine line's notes). PLAYER_FIRE_SPECIAL_POWER_AT_
WAYPOINT(Player_1, power, spot) 75 frames after Go; every target NO_ATTACK, s1's (an enemy without AI).
  o1 / o3  SpecialPowerOrbitalRefuse_Rank1 / _Rank3 at 'Test Psi Spot': health % of the base defenses (AlliedBaseDefense,
           1000 hp) at 0 / 150 / 250 / 350 from it: 血0 血150 血250 血350. [R1: 300 EXPLOSIVE radius 75 -> 0 only;
           R3: 1500 radius 175 -> 0 dies, 150 hit, 7 small random debris]
  d3 / dn  SpecialPower_DesolatorBomb_Level3 at 'Test Protocol Spot' (on foe 0): 帧数 (frames since the cast) and the
           health % of the enemy tanks (480 hp) at 0 / 150 / 200: 血0 血150 血200. [bombs ~10 s on, radius 150 fields
           for 30 s, 20 RADIATION a 0.1 s; dn: p1's Soviet yard deleted -- the bombers start from it, maybe no cast]
  f3 / fn  SpecialPowerFinalSquadron_L3 at the same spot, same counters. [~15 s on (3000 at speed 200), each enemy
           non-infantry within 100 up to 4 x 100 EXPLOSIVE; fn: p1's Japanese yard deleted]
No bench yet.
"""
from parts import Script, Test

CAST_FRAME = 75
POWERS = {'o': 'SpecialPowerOrbitalRefuse_Rank', 'd': 'SpecialPower_DesolatorBomb_Level', 'f': 'SpecialPowerFinalSquadron_L'}
RUN = {'o': 40.0, 'd': 45.0, 'f': 40.0}
YARD = {'o': 'syard', 'd': 'syard', 'f': 'jyard'}          # the yard each protocol's side builds; 'n' deletes it too


def protofx(m, which):
    t, p1 = Test(), m.player('p1')
    kind, level = which
    power = POWERS[kind] + ('3' if level == 'n' else level)
    if kind == 'o':
        spot, shown = 'Test Psi Spot', [(f'dtarget {d}', f'血{d}') for d in (0, 150, 250, 350)]
    else:
        spot, shown = 'Test Protocol Spot', [(f'foe {d}', f'血{d}') for d in (0, 150, 200)]
        t.counters.append(('CNV_Proto_Frames', '帧数'))
    keep = {'yard', 'power'} | {r for r, _ in shown} | ({YARD[kind]} if level != 'n' else set())
    start = [('MAP_REVEAL_ALL_PERM', p1), ('SET_MILLISECOND_TIMER', 'Test Go', 1.0)]
    start += [('UNIT_CHANGE_OBJECT_STATUS', m.role(r).name, 'NO_ATTACK', 1) for r, _ in shown]
    start += [('NAMED_DELETE', r.name) for k, r in m.cast.items() if k not in keep and r.name]
    t.scripts.append(Script('Test - start', [], start))
    t.scripts.append(Script('Test - go', [('TIMER_EXPIRED', 'Test Go')], [('SET_FLAG', 'Test Going', 1)]))
    going = ('FLAG', 'Test Going', 1)
    t.scripts.append(Script('Test - tick', [going], [('INCREMENT_COUNTER', 1, 'CNV_Proto_Tick')], once=False))
    t.scripts.append(Script('Test - cast', [going, ('COUNTER', 'CNV_Proto_Tick', 2, CAST_FRAME)],
                            [('PLAYER_FIRE_SPECIAL_POWER_AT_WAYPOINT', p1, power, spot), ('SET_FLAG', 'Test Cast', 1)]))
    cast_on = ('FLAG', 'Test Cast', 1)
    t.scripts.append(Script('Test - frames', [cast_on], [('INCREMENT_COUNTER', 1, 'CNV_Proto_Frames')], once=False))
    for k, (role, label) in enumerate(shown):
        t.counters.append((f'CNV_Proto_H{k}', label))
        t.scripts.append(Script(f'Test - health {k}', [cast_on],
                                [('SET_UNIT_HEALTH_PERCENTAGE_TO_COUNTER', m.role(role).name, f'CNV_Proto_H{k}')],
                                once=False))
    t.expect = []
    t.bench = [('bench_watch', dict(every=0.5, sheet=False, lines=len(t.counters), seconds=RUN[kind] + 8.0))]
    return t


CHECKS = {'engine_protofx': {w: (lambda m, w=w: protofx(m, w)) for w in ('o1', 'o3', 'd3', 'dn', 'f3', 'fn')}}
