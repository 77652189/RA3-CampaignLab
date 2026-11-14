"""Retail-campaign actions, batch 2 (round 212; the gaps of `inventory_retail.py --part 脚本动作`, the program read in
work/re/d115_script_semantics.md 12, 13, 14, 27). Missions on maps/probe_border.py as checks/engine_acts.py (its SLOT
places, clear of probe_range's lanes and start); enemies on Soviet_4. What the simulator predicts is in brackets.

  seq     UNIT_EXECUTE_SEQUENTIAL_SCRIPT at 1 s, the scripts subroutines:
          run: the player's 'runner' with 'Test - Seq Run' = [+1, MOVE <This Object> to P (300 east), +10, MOVE it
               back to R (where it stood), +100]. (The catalog's action takes no loop count: a first build with a
               third argument was refused by the writer.)
          queue: 'queuer' given 'Test - Seq Q1' = [MOVE <This Object> to Q (300 east), +1] and then 'Test - Seq Q2'
               = [+10], in one script.
          sit: 'sitter' with 'Test - Seq Sit' = [+1, UNIT_IDLE_FOR_SECONDS <This Object> 5, +10].
          跑 / 排 / 等 = the three counters; 位 (every frame) = 1 runner in P, 2 runner in R
          [simulator, d115 14: one action a frame once the unit is idle, the queue's second script after the first,
          the idle a wait of 75 frames: 跑 1 -> 11 at P -> 111 back at R and no more; 排 0 -> 11 at Q (10 only after
          the move: not 10 at once); 等 1 -> 11 ~5 s later]
  BENCH 11-13 (round 212, run_queue; tests/test_simbench.py test_acts_seq_as_the_bench): 跑 / 排 / 等 / 位
    s1 1 0 11 0 | s2 1 0 11 1 | s3-s4 11 11 11 1 | s5-s6 11 11 11 0 | s7 11 11 11 2 | s8-s41 111 11 11 2.
    Against the prediction: 等 11 from the first second -- the IDLE_FOR_SECONDS step held the next back not at all
    (d115 14 has IDLE_FOR_* write the record's wait; on a standing unit it did not). The rest as predicted; the
    simulator fixed (sim.Sim.seq_due keeps no wait).
  more    garrison: crew G1 (7 conscripts) and crew Frogs1 (two of the player's Bullfrogs, 5 places each); crew G2 (6)
               and Frogs2 (one); TEAM_GARRISON_TEAM_INSTANTLY(G1, Frogs1), (G2, Frogs2) at 2 s; NAMED_KILL the first
               Bullfrog of Frogs1 at KILL (KillPassengersOnDeath: its passengers die).
          force: the player's 'gunner' and 'gunner b' (conscripts, NO_ATTACK till 2 s) each 100 from a Soviet_4
               conscript 'lure' / 'lure b' (NO_ATTACK); at 2 s NAMED_FORCE_ATTACK_WAYPOINT(gunner, the ground 100
               on its other side), gunner b nothing; NAMED_STOP(gunner) at STOP.
          kill: UNIT_KILL_ALL_IN_AREA(Player_1, K) at KILL; in K the player's tank 'kin' and power plant 'kplant',
               Soviet_4's tank 'kfoe'; the player's 'kout' 250 east, outside.
          move: crew Mover (one tank) ATTACK_MOVE_TEAM_TO_NAMED_OBJECT the player's 'post' (300 east) at 2 s; the
               post moved 400 north at 3 s.
          reveal: Soviet_4's 'hide' (crew Hide) far from the player's eyes; MAP_REVEAL_PERMANENTLY_IN_TRIGGER(its area,
               Player_1, 'CNV Act Rev') at KILL, MAP_UNDO_REVEAL_PERMANENTLY_IN_TRIGGER at UNDO.
          驻 = G1 inside (ones) + G2 inside (tens) + G1 alive (hundreds); 诱血 = lure's health %
          旗 (every frame) = 1 NAMED_ATTACKED_BY_OBJECTTYPE(lure b, conscript) 2 (lure, ...) 4 kin alive 8 kfoe alive
            16 kplant alive 32 kout alive 64 Mover in the post's first place 128 in its second
            256 TEAM_DISCOVERED(Player_1, Hide)
          [simulator, d115 12 / 13 / 27: 驻 700 -> 757 (the room asked: 5 of G2's 6) -> 353 (dealt out 4 + 3, the
          first Bullfrog 4); 诱血 100 till STOP, then falling; 旗 60 -> 61 at 2 s (gunner b fires, gunner busy at the
          ground) -> 40+1 at KILL (kin, kplant dead) + 64 (the post's place at the order) + 256 KILL..UNDO, 2 after
          STOP]
  BENCH 11-13 (round 212, run_queue; tests/test_simbench.py test_acts_more_as_the_bench): 驻 / 诱血 / 旗
    s1-s2 767 100 61 | s3-s4 767 100 125 | s5-s11 363 100 361 | s12 363 85 363 | s13-s19 363 75..15 107 | s20 5 106 |
    s21-s28 0 106 | s29-s31 0 104. The bench's seconds run 1-2 s ahead. Against the prediction: the room is not
    asked (G2's six all in one five-place Bullfrog, as TEAM_GARRISON_SPECIFIC_BUILDING_INSTANTLY: 767, not 757);
    the dealing out confirmed (the first Bullfrog's kill took 4 of G1's 7: 363). The rest as predicted. The
    simulator fixed (sim.Sim.act TEAM_GARRISON_TEAM_INSTANTLY). Bits 1 / 2 stay up ~8 s after lure b's / the lure's
    death on the bench (the simulator drops them at the death; round 210's dying-unit gap, not this batch's).
"""
from maps import probe_border
from parts import Mission, Script, Test, square, status
import checks.engine_scripts8 as s8

TANK, PLANT, MAN, FROG = 'AlliedAntiVehicleVehicleTech1', 'SovietPowerPlant', 'SovietAntiInfantryInfantry', \
    'SovietAntiAirShip'
O = (1300.0, 4300.0)                            # probe_border's 'stop row'
RUN = {'seq': 40.0, 'more': 30.0}
SEQ = {'runner': (600.0, 4000.0), 'queuer': (2200.0, 4000.0), 'sitter': (3800.0, 4000.0)}
LEG = 300.0
G = {'G1': (7, 2, (600.0, 4000.0)), 'G2': (6, 1, (1400.0, 4000.0))}     # crew: men, Bullfrogs, place
GUN = {'gunner': (2200.0, 4000.0), 'gunner b': (3000.0, 4000.0)}
K = (3800.0, 4000.0)
MOVER, POST, POST2 = (600.0, 4700.0), (900.0, 4700.0), (900.0, 4300.0)
HIDE = (4500.0, 3000.0)
KILL, STOP, UNDO = 6.0, 12.0, 14.0


def _n(part):
    return f'UNIT - CNV Act2 {part.title()}'


def _put(m, template, x, y, **kw):
    m.put(template, 'stop row', x - O[0], y - O[1], **kw)


def _unit(m, role, side, template, x, y, crew=None):
    props = {'originalOwner': m.crew(crew, side=side)} if crew else {}
    _put(m, template, x, y, side=side, angle=0.0 if side == 'p1' else 3.1416, name=_n(role), role=role, props=props)


def mission_seq():
    m = Mission(name='CampActsS', map=probe_border, units=[], facts={})
    m.spawns |= {TANK}
    for role, (x, y) in SEQ.items():
        _unit(m, role, 'p1', TANK, x, y)
        m.waypoint(f'{role} to', f'Test Act2 {role.title()} To', 'stop row', x + LEG - O[0], y - O[1])
        m.waypoint(f'{role} back', f'Test Act2 {role.title()} Back', 'stop row', x - O[0], y - O[1])
    return m


def seq(m):
    t = Test()
    me = '<This Object>'
    run, q, sit = 'CNV_Seq_Run', 'CNV_Seq_Q', 'CNV_Seq_Sit'
    t.scripts += [
        Script('Test - Seq Run', [], [('INCREMENT_COUNTER', 1, run), ('MOVE_NAMED_UNIT_TO', me, m.mark('runner to')),
                                      ('INCREMENT_COUNTER', 10, run),
                                      ('MOVE_NAMED_UNIT_TO', me, m.mark('runner back')),
                                      ('INCREMENT_COUNTER', 100, run)], sub=True),
        Script('Test - Seq Q1', [], [('MOVE_NAMED_UNIT_TO', me, m.mark('queuer to')), ('INCREMENT_COUNTER', 1, q)],
               sub=True),
        Script('Test - Seq Q2', [], [('INCREMENT_COUNTER', 10, q)], sub=True),
        Script('Test - Seq Sit', [], [('INCREMENT_COUNTER', 1, sit), ('UNIT_IDLE_FOR_SECONDS', me, 5.0),
                                      ('INCREMENT_COUNTER', 10, sit)], sub=True)]
    s8.at(t, 'seq', 1.0, [('UNIT_EXECUTE_SEQUENTIAL_SCRIPT', _n('runner'), 'Test - Seq Run'),
                          ('UNIT_EXECUTE_SEQUENTIAL_SCRIPT', _n('queuer'), 'Test - Seq Q1'),
                          ('UNIT_EXECUTE_SEQUENTIAL_SCRIPT', _n('queuer'), 'Test - Seq Q2'),
                          ('UNIT_EXECUTE_SEQUENTIAL_SCRIPT', _n('sitter'), 'Test - Seq Sit')])
    for c, label in ((run, '跑'), (q, '排'), (sit, '等')):
        t.counters.append((c, label))
    t.areas['Test Act2 P'] = square(*m.point('runner to'), 80.0)
    t.areas['Test Act2 R'] = square(*m.point('runner back'), 80.0)
    s8.total(t, 'CNV_Seq_Where', '位', [(1, ('NAMED_INSIDE_AREA', _n('runner'), 'Test Act2 P')),
                                       (2, ('NAMED_INSIDE_AREA', _n('runner'), 'Test Act2 R'))])
    s8.watch(t, RUN['seq'])
    return t


def mission_more():
    m = Mission(name='CampActsM', map=probe_border, units=[], facts={})
    m.spawns |= {TANK, PLANT, MAN, FROG}
    for crew, (men, frogs, (x, y)) in G.items():
        for k in range(frogs):
            _unit(m, f'{crew} frog {k}', 'p1', FROG, x + 160.0 * k, y, crew=f'Frogs{crew[1]}')
        for k in range(men):
            _unit(m, f'{crew} man {k}', 'p1', MAN, x - 100.0 + 35.0 * k, y - 90.0, crew=crew)
    for k, (role, (x, y)) in enumerate(GUN.items()):
        _unit(m, role, 'p1', MAN, x, y)
        _unit(m, 'lure' + role[6:], 's4', MAN, x + 100.0, y)
        m.waypoint(f'{role} at', f'Test Act2 {role.title()} At', 'stop row', x - 100.0 - O[0], y - O[1])
    _unit(m, 'kin', 'p1', TANK, K[0] - 60.0, K[1])
    _unit(m, 'kplant', 'p1', PLANT, K[0] + 40.0, K[1] + 60.0)
    _unit(m, 'kfoe', 's4', TANK, K[0], K[1] - 80.0)
    _unit(m, 'kout', 'p1', TANK, K[0] + 250.0, K[1])
    _unit(m, 'mover', 'p1', TANK, *MOVER, crew='Mover')
    _unit(m, 'post', 'p1', TANK, *POST)
    m.waypoint('post to', 'Test Act2 Post To', 'stop row', POST2[0] - O[0], POST2[1] - O[1])
    _unit(m, 'hide', 's4', TANK, *HIDE, crew='Hide')
    return m


def more(m):
    t = Test()
    p1 = m.player()
    na = status('NO_ATTACK')
    men = lambda crew: [_n(f'{crew} man {k}') for k in range(G[crew][0])]                  # noqa: E731
    held = [_n(r) for r in ('gunner', 'gunner b', 'lure', 'lure b', 'kin', 'kfoe', 'kout', 'kplant', 'mover', 'post',
                            'hide', 'G1 frog 0', 'G1 frog 1', 'G2 frog 0')] + men('G1') + men('G2')
    t.areas['Test Act2 K'] = square(*K, 150.0)
    t.areas['Test Act2 Post A'] = square(*POST, 100.0)
    t.areas['Test Act2 Post B'] = square(*POST2, 100.0)
    t.areas['Test Act2 Rev'] = square(*HIDE, 150.0)
    t.scripts.append(Script('Test - Act2 start', [], [('UNIT_CHANGE_OBJECT_STATUS', u, na, 1) for u in held]))
    s8.at(t, 'two', 2.0, [('TEAM_GARRISON_TEAM_INSTANTLY', m.teams['G1'], m.teams['Frogs1']),
                          ('TEAM_GARRISON_TEAM_INSTANTLY', m.teams['G2'], m.teams['Frogs2']),
                          ('UNIT_CHANGE_OBJECT_STATUS', _n('gunner'), na, 0),
                          ('UNIT_CHANGE_OBJECT_STATUS', _n('gunner b'), na, 0),
                          ('NAMED_FORCE_ATTACK_WAYPOINT', _n('gunner'), m.mark('gunner at')),
                          ('ATTACK_MOVE_TEAM_TO_NAMED_OBJECT', m.teams['Mover'], _n('post'))])
    s8.at(t, 'three', 3.0, [('MOVE_NAMED_UNIT_TO', _n('post'), m.mark('post to'))])
    s8.at(t, 'kill', KILL, [('NAMED_KILL', _n('G1 frog 0')), ('UNIT_KILL_ALL_IN_AREA', p1, 'Test Act2 K'),
                            ('MAP_REVEAL_PERMANENTLY_IN_TRIGGER', 'Test Act2 Rev', p1, 'CNV Act Rev')])
    s8.at(t, 'stop', STOP, [('NAMED_STOP', _n('gunner'))])
    s8.at(t, 'undo', UNDO, [('MAP_UNDO_REVEAL_PERMANENTLY_IN_TRIGGER', 'CNV Act Rev')])
    inside = lambda crew, w: [(w, ('UNIT_HAS_OBJECT_STATUS', u, status('ENCLOSED'))) for u in men(crew)]   # noqa: E731
    s8.total(t, 'CNV_Act2_In', '驻', inside('G1', 1) + inside('G2', 10)
             + [(100, ('NAMED_NOT_DESTROYED', u)) for u in men('G1')])
    t.counters.append(('CNV_Act2_HP', '诱血'))
    t.scripts.append(Script('Test - CNV_Act2_HP', [], [('SET_UNIT_HEALTH_PERCENTAGE_TO_COUNTER', _n('lure'),
                                                        'CNV_Act2_HP')], once=False))
    s8.total(t, 'CNV_Act2_Flags', '旗', [
        (1, ('NAMED_ATTACKED_BY_OBJECTTYPE', _n('lure b'), MAN)),
        (2, ('NAMED_ATTACKED_BY_OBJECTTYPE', _n('lure'), MAN)),
        (4, ('NAMED_NOT_DESTROYED', _n('kin'))), (8, ('NAMED_NOT_DESTROYED', _n('kfoe'))),
        (16, ('NAMED_NOT_DESTROYED', _n('kplant'))), (32, ('NAMED_NOT_DESTROYED', _n('kout'))),
        (64, ('NAMED_INSIDE_AREA', _n('mover'), 'Test Act2 Post A')),
        (128, ('NAMED_INSIDE_AREA', _n('mover'), 'Test Act2 Post B')),
        (256, ('TEAM_DISCOVERED', p1, m.teams['Hide']))])
    s8.watch(t, RUN['more'])
    return t


MISSION = {'engine_acts_seq': mission_seq, 'engine_acts_more': mission_more}
CHECKS = {'engine_acts_seq': {'seq': seq}, 'engine_acts_more': {'more': more}}
