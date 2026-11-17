"""Engine probe, inventory batch 2 (docs/engine/inventory.md, the heaviest inferred script actions that need units):
UNIT_IDLE_FOR_FRAMECOUNT, CREATE_NAMED_ON_TEAM_AT_WAYPOINT_WITH_ORIENTATION / CREATE_UNNAMED_..._WITH_ORIENTATION,
OBJECTLIST_ADDOBJECTTYPE (read by PLAYER_HAS_OBJECT_COMPARISON and the nearest-reference actions),
UNIT_AFFECT_OBJECT_PANEL_FLAGS / TEAM_AFFECT_OBJECT_PANEL_FLAGS (Indestructible), ATTACK_MOVE_NAMED_UNIT_TO,
SET_REF_TO_NEREST_TEAM_OF_TYPE_OWNED_BY_PLAYER. Mission here (build engine_scripts7) on maps/probe_border.py (the
simulator's level ground, 5000 x 5000); the scenes stand >= 1000 apart where an enemy is, so nobody fires across. What
the simulator (sim.py) predicts is in brackets.

  idle    the player's Guardians idle 1-3 at (2900, 4200 / 4350 / 4500), each sent 1200 east at 1 s; at IDLE_AT
          UNIT_IDLE_FOR_FRAMECOUNT(idle 1, 15), (idle 3, 1); idle 2 the control. 一到 / 二到 / 三到 = 1 while idle k is
          at its goal [二到 only: like the seconds version (engine_scripts1 idle) the order is dropped]
  face    at 1 s CREATE_NAMED_..._WITH_ORIENTATION a Guardian at (3700, 4700) angle 0 and (3900, 4700) angle pi/2,
          CREATE_UNNAMED_..._WITH_ORIENTATION at (4100, 4700) pi and (4300, 4700) -3pi/4 (retail's value); 造出 = the
          player's Guardians in that row [4]; the facing is the picture (bench_look at 4 s) [angle in radians, 0 east,
          pi/2 north: the map's own convention, as placed objects]
  panel   the player's Guardians pan 1-4 at (2900 .. 3500, 4700): Indestructible on pan 1 (UNIT_...) and on crew Pan
          = pan 3, pan 4 (TEAM_...) at the start; NAMED_DAMAGE 300 to all four at 2 s, NAMED_KILL pan 1, pan 2, pan 3
          at 4 s; flags off (UNIT pan 1, TEAM Pan) at 6 s; NAMED_DAMAGE 300 to pan 4 and NAMED_KILL pan 1, pan 3 at 8 s.
          血一 / 血二 / 血四 = pan 1 / 2 / 4 health %; 活着 = 1 pan 1 + 2 pan 2 + 4 pan 3 + 8 pan 4 not destroyed
          [damage none on an indestructible one; NAMED_KILL kills it anyway: 15 -> 15 at 2 s -> 8 at 4 s -> 0 at 8 s?
          (Generals' Object::kill goes through attemptDamage, which an indestructible body refuses)]
  amove   lane A: am 1 (400, 4050) ATTACK_MOVE_NAMED_UNIT_TO (2400, 4050) at 1 s; lane B: am 2 (400, 4850)
          MOVE_NAMED_UNIT_TO (2400, 4850); an enemy (s1, NO_ATTACK so it does not shoot back) Guardian 60 off each
          lane halfway (1400). 到一 / 到二 = 1 while am k is at its goal; 敌一 / 敌二 = the enemy's health %
          [am 1 stops, kills e1 and goes on; am 2 drives by, e2 stays 100]
  list    s1's Guardian 'near' (named, 3900, 3000), Peacekeeper 'mid' (unnamed, 4100, 3000), Guardian 'far'
          (unnamed, 4300, 3000); the player's crew Ref, one Guardian at (2900, 3000). At the start
          OBJECTLIST_ADDOBJECTTYPE(Guardian, L), (Peacekeeper, P) twice; at LIST_AT (Peacekeeper, L).
          列表 = s1's objects of L (PLAYER_HAS_OBJECT_COMPARISON) [4 (with the two amove enemies), then 5 from LIST_AT]; 单类 = of P [1];
          at REF_AT SET_REF_TO_NEREST_TEAM_OF_TYPE_OWNED_BY_PLAYER(L, s1, Ref, R1) and the UNNAMED one (L, ..., R2):
          参考 / 无名参考 = 1 / 2 / 4 as the reference stands at near / mid / far [R1 near (named ones count),
          R2 mid (named ones skipped)]

读数 (bench 2026-11-09, run_queue engine_scripts7:*; sim pairs tests/test_simbench.py test_scripts7_*):
  idle    PASS. 二到 1 from s14; 一到, 三到 0 all 25 s: UNIT_IDLE_FOR_FRAMECOUNT drops the order, 15 frames or 1 (as
          the seconds version). The simulator agrees.
  face    PASS. 造出 4 from s1: CREATE_NAMED_ON_TEAM_AT_WAYPOINT_WITH_ORIENTATION and CREATE_UNNAMED_ON_TEAM_AT_WAYPOINT_
          WITH_ORIENTATION make their object at the waypoint. The facing (bench 2026-11-10, CampScr7Face_mcp_1110_
          232041 frame 11, s30; the hull by its two rear aerials, the turret turns on its own): east, north, west,
          south-west for 0, pi/2, pi, -3pi/4 -- radians, 0 east, pi/2 north, as the simulator. The check's own look
          (frame 5) again showed open ground: its bench_camera did not move the camera (the minimap box elsewhere);
          a second bench_camera by hand did.
  panel   PASS (third run; the first two gave NAMED_DAMAGE 300.0 / 200.0, a float, which does nothing --
          engine_garrison). 甲血 乙血 丁血 58 58 58 from s1, 活着 15 -> 11 at s3, 甲血 丁血 16 from s7: NAMED_DAMAGE 200
          took 42 % off pan 1 (UNIT_AFFECT_OBJECT_PANEL_FLAGS Indestructible) and pan 4 (TEAM_..._FLAGS) as off the
          control; NAMED_KILL killed pan 3 (TEAM flag; the first run: pan 1 too). So the flag stops no scripted damage
          nor a kill [the Generals reading was wrong for RA3]; whether it stops a weapon's damage is not measured.
          The simulator now lets NAMED_DAMAGE through (it refused it); weapons still refused (推断).
  list    (third run; the first two stopped in the contract: a ref set by SET_REF_TO_NEREST_TEAM_OF_TYPE_OWNED_BY_
          PLAYER and an object list's name as a type were not published -- contract.py knows both now). 列表 4 all
          run (s1-s11): OBJECTLIST_ADDOBJECTTYPE's list counts in PLAYER_HAS_OBJECT_COMPARISON (s1's 4 Guardians, a
          type given lower case); the Peacekeeper added to it at LIST_AT (4 s) NOT counted (still 4 at s11) [the
          simulator: 5 -- not found why: a list fixed once read? added only in the first frame? strict xfail];
          单类 1 (a type added twice counts once). 参考 1, 无名参考 2 from s5: SET_REF_TO_NEREST_TEAM_OF_TYPE_OWNED_BY_
          PLAYER took the named Guardian nearest the team, the UNNAMED one skipped it for the Peacekeeper -- both with
          an object list for the type. The simulator agrees on the refs.
  amove   PASS (second run; the first run's labels 到一 / 敌一 read '?': a label ending in 一 before the number does
          not parse -- the labels now start with 甲 / 乙). 乙到 1 from s23, 甲到 from s38; 乙敌 100 -> 87 -> 74 -> 60
          (s10-s15) then 60: MOVE_NAMED_UNIT_TO's tank fires as it drives by (3 hits); 甲敌 100 -> 12 by s22 (8 hits,
          ~12.5 % each) then 12 to the end: ATTACK_MOVE_NAMED_UNIT_TO's tank stopped to fight, left the enemy at 12 %
          and went on (arrived 15 s after the mover). The simulator: the attack-mover kills it (0 at 28 s) and has not
          arrived by 60 s; its hits ~6 % each (the weapon's damage: engine line C). strict xfail in test_simbench.
"""
from maps import probe_border
from parts import Mission, Script, Test, counted, square, status

TANK, PK = 'AlliedAntiVehicleVehicleTech1', 'AlliedAntiInfantryInfantry'
O = (1300.0, 4300.0)                            # probe_border's 'stop row': every place below is absolute
IDLE_AT, LIST_AT, REF_AT = 3.0, 4.0, 6.0
RUN = {'idle': 25.0, 'face': 8.0, 'panel': 12.0, 'amove': 60.0, 'list': 10.0}
EQ = 2
L, P = 'cnv s7 list', 'cnv s7 pk'
FACE = [(3700.0, 0.0, True), (3900.0, 1.5707963, True), (4100.0, 3.1415927, False), (4300.0, -2.3561945, False)]
FACE_Y = 4700.0
LIST_SPOTS = {'near': (3900.0, TANK, True), 'mid': (4100.0, PK, False), 'far': (4300.0, TANK, False)}
LIST_Y = 3000.0


def _n(part):
    return f'UNIT - CNV S7 {part}'


def _put(m, template, x, y, **kw):
    m.put(template, 'stop row', x - O[0], y - O[1], **kw)


def _wp(m, part, x, y):
    m.waypoint(part, f'CNV S7 {part.title()}', 'stop row', x - O[0], y - O[1])


def mission():
    m = Mission(name='CampScr7', map=probe_border, units=[], facts={})
    m.spawns |= {TANK, PK}
    pan, ref = m.crew('Pan'), m.crew('Ref')
    for k, y in enumerate((4200.0, 4350.0, 4500.0), 1):
        _put(m, TANK, 2900.0, y, angle=0.0, name=_n(f'Idle {k}'), role=f'idle {k}')
        _wp(m, f'goal {k}', 4100.0, y)
    for k in range(1, 5):
        _put(m, TANK, 2700.0 + 200.0 * k, 4700.0, angle=0.0, name=_n(f'Pan {k}'), role=f'pan {k}',
             **({'props': {'originalOwner': pan}} if k > 2 else {}))
    for k, (x, _, _) in enumerate(FACE, 1):
        _wp(m, f'face {k}', x, FACE_Y)
    for k, y, e in ((1, 4050.0, 4110.0), (2, 4850.0, 4790.0)):
        _put(m, TANK, 400.0, y, angle=0.0, name=_n(f'Am {k}'), role=f'am {k}')
        _put(m, TANK, 1400.0, e, side='s1', angle=3.1416, name=_n(f'Enemy {k}'), role=f'enemy {k}')
        _wp(m, f'lane {k}', 2400.0, y)
    for part, (x, template, named) in LIST_SPOTS.items():
        _put(m, template, x, LIST_Y, side='s1', angle=3.1416, name=_n(part.title()) if named else '',
             role=part if named else '')
    _put(m, TANK, 2900.0, LIST_Y, angle=0.0, name=_n('Ref'), role='ref', props={'originalOwner': ref})
    return m


def _at(t, key, secs, actions):
    timer = f'Test S7 {key} Timer'
    t.scripts += [Script(f'Test - S7 {key} timer', [], [('SET_MILLISECOND_TIMER', timer, secs)]),
                  Script(f'Test - S7 {key}', [('TIMER_EXPIRED', timer)], actions)]


def _sum(t, counter, label, parts):
    """counter = the sum of the weights whose condition holds, recounted every frame. parts: [(weight, condition)]."""
    t.counters.append((counter, label))
    t.scripts.append(Script(f'Test - {counter} zero', [], [('SET_COUNTER', counter, 0)], once=False))
    t.scripts += [Script(f'Test - {counter} {k}', [c], [('INCREMENT_COUNTER', w, counter)], once=False)
                  for k, (w, c) in enumerate(parts)]


def _exact(t, counter, label, player, kind, most=6):
    """counter = how many objects of `kind` (a type or an object list) `player` has (PLAYER_HAS_OBJECT_COMPARISON ==)."""
    t.counters.append((counter, label))
    t.scripts += [Script(f'Test - {counter} {n}', [('PLAYER_HAS_OBJECT_COMPARISON', player, EQ, n, kind)],
                         [('SET_COUNTER', counter, n)], once=False) for n in range(most)]


def _watch(t, run, every=1.0, look=None):
    w = dict(seconds=run, every=every, sheet=False, lines=len(t.counters))
    if look is None:
        t.bench = [('bench_watch', w)]
        return
    at, x, y, note = look
    t.bench = [('bench_watch', dict(w, seconds=at)), ('bench_camera', dict(x=x, y=y, look=False)),
               ('bench_look', dict(note=note)), ('bench_watch', dict(w, seconds=run - at))]


def idle(m):
    t = Test()
    names = [m.role(f'idle {k}').name for k in (1, 2, 3)]
    _at(t, 'go', 1.0, [('MOVE_NAMED_UNIT_TO', n, m.mark(f'goal {k}')) for k, n in enumerate(names, 1)])
    _at(t, 'idle', IDLE_AT, [('UNIT_IDLE_FOR_FRAMECOUNT', names[0], 15), ('UNIT_IDLE_FOR_FRAMECOUNT', names[2], 1)])
    for k, n in enumerate(names, 1):
        area = f'Test S7 Goal {k}'
        t.areas[area] = square(*m.point(f'goal {k}'), 80.0)
        counted(f'CNV_S7_At{k}', '一二三'[k - 1] + '到', t, named=n, area=area)
    t.expect += [('二到', RUN['idle'] - 2, '==', 1)]
    _watch(t, RUN['idle'])
    return t


def face(m):
    t = Test()
    team = f'{m.player()}/team{m.player()}'
    acts = []
    for k, (x, angle, named) in enumerate(FACE, 1):
        wp = m.mark(f'face {k}')
        acts.append(('CREATE_NAMED_ON_TEAM_AT_WAYPOINT_WITH_ORIENTATION', _n(f'Face {k}'), TANK, team, wp, angle)
                    if named else ('CREATE_UNNAMED_ON_TEAM_AT_WAYPOINT_WITH_ORIENTATION', TANK, team, wp, angle))
    _at(t, 'make', 1.0, acts)
    t.areas['Test S7 Face Row'] = square(4000.0, FACE_Y, 400.0)
    counted('CNV_S7_Made', '造出', t, template=TANK, area='Test S7 Face Row')
    t.expect += [('造出', 4, '==', 4)]
    _watch(t, RUN['face'], look=(4.0, 4000.0, FACE_Y, 'four Guardians made at 1 s, left to right: angle 0, pi/2 '
                                 '(named), pi, -3pi/4 (unnamed) -- which way does each face?'))
    return t


def panel(m):
    t = Test()
    pan = [m.role(f'pan {k}').name for k in range(1, 5)]
    crew = m.teams['Pan']
    t.scripts.append(Script('Test - S7 flags on', [], [('UNIT_AFFECT_OBJECT_PANEL_FLAGS', pan[0], 'Indestructible', 1),
                                                      ('TEAM_AFFECT_OBJECT_PANEL_FLAGS', crew, 'Indestructible', 1)]))
    _at(t, 'hurt', 2.0, [('NAMED_DAMAGE', n, 200) for n in (pan[0], pan[1], pan[3])])     # an integer (engine_garrison)
    _at(t, 'kill', 4.0, [('NAMED_KILL', pan[2])])
    _at(t, 'off', 6.0, [('UNIT_AFFECT_OBJECT_PANEL_FLAGS', pan[0], 'Indestructible', 0),
                        ('TEAM_AFFECT_OBJECT_PANEL_FLAGS', crew, 'Indestructible', 0)])
    _at(t, 'again', 8.0, [('NAMED_DAMAGE', pan[0], 200), ('NAMED_DAMAGE', pan[3], 200)])
    for k, label in ((1, '甲血'), (2, '乙血'), (4, '丁血')):
        counted(f'CNV_S7_H{k}', label, t, health=pan[k - 1])
    _sum(t, 'CNV_S7_Alive', '活着', [(2 ** k, ('NAMED_NOT_DESTROYED', n)) for k, n in enumerate(pan)])
    t.expect += [('活着', RUN['panel'] - 2, '==', 11)]
    _watch(t, RUN['panel'], 0.5)
    return t


def amove(m):
    t = Test()
    am = [m.role(f'am {k}').name for k in (1, 2)]
    en = [m.role(f'enemy {k}').name for k in (1, 2)]
    t.scripts.append(Script('Test - S7 hold fire', [], [('UNIT_CHANGE_OBJECT_STATUS', n, status('NO_ATTACK'), 1)
                                                       for n in en]))
    _at(t, 'go', 1.0, [('ATTACK_MOVE_NAMED_UNIT_TO', am[0], m.mark('lane 1')),
                       ('MOVE_NAMED_UNIT_TO', am[1], m.mark('lane 2'))])
    for k in (1, 2):
        area = f'Test S7 Lane {k}'
        t.areas[area] = square(*m.point(f'lane {k}'), 80.0)
        counted(f'CNV_S7_Lane{k}', '甲乙'[k - 1] + '到', t, named=am[k - 1], area=area)
    for k in (1, 2):
        counted(f'CNV_S7_E{k}', '甲乙'[k - 1] + '敌', t, health=en[k - 1])
    t.expect += [('甲到', RUN['amove'] - 2, '==', 1), ('乙到', RUN['amove'] - 2, '==', 1)]
    _watch(t, RUN['amove'])
    return t


def list_(m):
    t = Test()
    s1 = m.player('s1')
    t.scripts.append(Script('Test - S7 lists', [], [('OBJECTLIST_ADDOBJECTTYPE', TANK.lower(), L),
                                                    ('OBJECTLIST_ADDOBJECTTYPE', PK.lower(), P),
                                                    ('OBJECTLIST_ADDOBJECTTYPE', PK.lower(), P)]))
    _at(t, 'grow', LIST_AT, [('OBJECTLIST_ADDOBJECTTYPE', PK.lower(), L)])
    ref = m.teams['Ref']
    _at(t, 'refs', REF_AT, [('SET_REF_TO_NEREST_TEAM_OF_TYPE_OWNED_BY_PLAYER', L, s1, ref, 'UNITRef - CNV S7 R1'),
                            ('SET_REF_TO_NEREST_TEAM_OF_UNNAMED_TYPE_OWNED_BY_PLAYER', L, s1, ref, 'UNITRef - CNV S7 R2')])
    _exact(t, 'CNV_S7_L', '列表', s1, L)
    _exact(t, 'CNV_S7_P', '单类', s1, P)
    for part, (x, _, _) in LIST_SPOTS.items():
        t.areas[f'Test S7 At {part}'] = square(x, LIST_Y, 60.0)
    for counter, label, r in (('CNV_S7_R1', '参考', 'UNITRef - CNV S7 R1'), ('CNV_S7_R2', '无名参考', 'UNITRef - CNV S7 R2')):
        _sum(t, counter, label, [(w, ('NAMED_INSIDE_AREA', r, f'Test S7 At {part}'))
                                 for w, part in ((1, 'near'), (2, 'mid'), (4, 'far'))])
    t.expect += [('列表', 2, '==', 4), ('列表', RUN['list'] - 2, '==', 4), ('单类', RUN['list'] - 2, '==', 1)]
    _watch(t, RUN['list'])
    return t


MISSION = {'engine_scripts7': mission}
CHECKS = {'engine_scripts7': {'idle': idle, 'face': face, 'panel': panel, 'amove': amove, 'list': list_}}
