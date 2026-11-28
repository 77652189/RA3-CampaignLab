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
  fl       SpecialPowerFinalSquadron_L1, the foes on the line to the yard (super_bench.LINE): 血400 血800 血1400.
           [the guns' first hits time the aircraft: born 3000 out toward the yard (work/re a353 A357) or 1500]
  os / ms  orbital rank 1 / SpecialPowerMagneticSatelliteLvl3 at 'Test Curtain Spot' on the CASTER's own tanks 0 / 150:
           帧数 血0 血150 (A433: does it hurt its own side? XML refuse ALLIES ENEMIES NEUTRALS; the campaign's satellite
           ENEMIES NEUTRAL)
  oz       o1 cast by s1 (no yard, no protocol) on its own base defenses;  or  o1 cast again 300 frames on;  oc  the
           same, PLAYER_SET_SPECIAL_POWER_COUNTDOWN(p1, power, 0) first (血0 血150 血250 + 施放数).  m*: the target at 0 only, + 吸起 (its owner has
           an object SUCKED_UP_HIGH: 1, sticky) and 活着 (it NAMED_NOT_DESTROYED: 1, else 0)
  m1 / m3  SpecialPowerMagneticSatelliteLvl1 / 3 at 'Test Protocol Spot', foes 0 / 150 / 200 as d3 [vehicles within
           40 lifted, die at 450 up; the beam lives 4 / 10 s (CampaignOverrides) or 10 / 20]
Bench 11-23: engine_protofx.readings.toml (o1 and the desolator as predicted but no yard needed; o3 / f3 / fn random).
"""
from parts import Script, Test

CAST_FRAME = 75
POWERS = {'o': 'SpecialPowerOrbitalRefuse_Rank', 'd': 'SpecialPower_DesolatorBomb_Level', 'f': 'SpecialPowerFinalSquadron_L',
          'm': 'SpecialPowerMagneticSatelliteLvl'}
RUN = {'o': 40.0, 'd': 45.0, 'f': 40.0, 'm': 40.0}
YARD = {'o': 'syard', 'd': 'syard', 'f': 'jyard', 'm': 'syard'}   # the yard each protocol's side builds; 'n' deletes it too
LEVEL = {'n': '3', 'x': '3', 'l': '1', 'os': '1', 'oz': '1', 'or': '1', 'oc': '1', 'ms': '3'}


def protofx(m, which):
    t, p1 = Test(), m.player('p1')
    kind, level = which
    power = POWERS[kind] + LEVEL.get(which, LEVEL.get(level, level))
    caster = m.player('s1') if level == 'z' else p1
    if level == 's':
        spot, shown = 'Test Curtain Spot', [(f'tank {d}', f'血{d}') for d in (0, 150)]
        t.counters.append(('CNV_Proto_Frames', '帧数'))
    elif kind == 'o':
        spot, shown = 'Test Psi Spot', [(f'dtarget {d}', f'血{d}') for d in (0, 150, 250, 350)]
    else:
        spot, shown = 'Test Protocol Spot', [(f'foe {d}', f'血{d}') for d in (0, 150, 200)]
        shown = [(r, '血' + r[5:]) for r in m.cast if r.startswith('lfoe ')] if level == 'l' else shown
        t.counters.append(('CNV_Proto_Frames', '帧数'))
    shown = shown[:1] if kind == 'm' else shown[:3] if level in 'rc' else shown
    keep = {'yard', 'power', 'foe 0'} | {r for r, _ in shown} | ({YARD[kind]} if level != 'n' else set())
    keep -= {'dtarget 150'} if level == 'x' else {'foe 0'} if level == 's' else set()   # ox: no 150 (does the centre get it?)
    start = [('MAP_REVEAL_ALL_PERM', p1), ('SET_MILLISECOND_TIMER', 'Test Go', 1.0)]
    start += [('UNIT_CHANGE_OBJECT_STATUS', m.role(r).name, 'NO_ATTACK', 1) for r, _ in shown]
    start += [('NAMED_DELETE', r.name) for k, r in m.cast.items() if k not in keep and r.name]
    t.scripts.append(Script('Test - start', [], start))
    t.scripts.append(Script('Test - go', [('TIMER_EXPIRED', 'Test Go')], [('SET_FLAG', 'Test Going', 1)]))
    going = ('FLAG', 'Test Going', 1)
    t.scripts.append(Script('Test - tick', [going], [('INCREMENT_COUNTER', 1, 'CNV_Proto_Tick')], once=False))
    t.scripts.append(Script('Test - cast', [going, ('COUNTER', 'CNV_Proto_Tick', 2, CAST_FRAME)],
                            [('PLAYER_FIRE_SPECIAL_POWER_AT_WAYPOINT', caster, power, spot), ('SET_FLAG', 'Test Cast', 1)]))
    if level in 'rc':
        zero = [('PLAYER_SET_SPECIAL_POWER_COUNTDOWN', caster, power, 0)] if level == 'c' else []
        t.scripts.append(Script('Test - recast', [going, ('COUNTER', 'CNV_Proto_Tick', 2, CAST_FRAME + 300)],
                                zero + [('PLAYER_FIRE_SPECIAL_POWER_AT_WAYPOINT', caster, power, spot)]))
    cast_on = ('FLAG', 'Test Cast', 1)
    t.scripts.append(Script('Test - frames', [cast_on], [('INCREMENT_COUNTER', 1, 'CNV_Proto_Frames')], once=False))
    for k, (role, label) in enumerate(shown):
        t.counters.append((f'CNV_Proto_H{k}', label))
        t.scripts.append(Script(f'Test - health {k}', [cast_on],
                                [('SET_UNIT_HEALTH_PERCENTAGE_TO_COUNTER', m.role(role).name, f'CNV_Proto_H{k}')],
                                once=False))
    if level in 'rc':       # each cast event once (PLAYER_TRIGGERED_SPECIAL_POWER holds the frame of it)
        t.counters.append(('CNV_Proto_Seen', '施放数'))
        t.scripts.append(Script('Test - seen', [('PLAYER_TRIGGERED_SPECIAL_POWER', caster, power)],
                                [('INCREMENT_COUNTER', 1, 'CNV_Proto_Seen')], once=False))
    if kind == 'm':
        who, name = (p1 if level == 's' else m.player('s1')), m.role(shown[0][0]).name
        t.counters += [('CNV_Proto_Lift', '吸起'), ('CNV_Proto_Live', '活着')]
        t.scripts += [Script('Test - lift', [cast_on, ('PLAYER_HAS_NUMBER_OBJECTS_WITH_MODELCONDITION', who, 3, 1,
                                                       'SUCKED_UP_HIGH')], [('SET_COUNTER', 'CNV_Proto_Lift', 1)]),
                      Script('Test - live 0', [], [('SET_COUNTER', 'CNV_Proto_Live', 0)], once=False),
                      Script('Test - live', [('NAMED_NOT_DESTROYED', name)], [('SET_COUNTER', 'CNV_Proto_Live', 1)],
                             once=False)]
    t.expect = []
    t.bench = [('bench_watch', dict(every=0.5, sheet=False, lines=len(t.counters), seconds=RUN[kind] + 8.0))]
    return t


CHECKS = {'engine_protofx': {w: (lambda m, w=w: protofx(m, w)) for w in ('o1', 'o2', 'o3', 'ox', 'd1', 'd2', 'd3', 'dn', 'f1', 'f2', 'f3', 'fn', 'fl',
                                                                           'os', 'oz', 'or', 'oc', 'ms', 'm1', 'm3')}}
