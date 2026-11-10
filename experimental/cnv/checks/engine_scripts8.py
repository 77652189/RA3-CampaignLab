"""Engine probe, inventory batch 3 (docs/engine/inventory.md, the heaviest script actions the simulator lacked):
TEAM_DELETE / TEAM_KILL, TEAM_IDLE_FOR_SECONDS / TEAM_IDLE_FOR_FRAMECOUNT, TEAM_MERGE_INTO_TEAM,
UNIT_SPAWN_NAMED_OBJECT_ON_TEAM_AT_NAMED_OBJECT_LOCATION. Mission here (build engine_scripts8) on maps/probe_border.py
(level ground 5000 x 5000; every place absolute, the scenes >= 1000 apart where an enemy is). The rest of the batch
(the team status, the base power, the player's superweapon cast and its availability) waits in checks/pending_scripts8.py
for the bench (it crashed at start, 11-09): only measured names may stand in an engine_ file (inventory.bench_sources).
What the simulator (sim.py) predicts is in brackets.

  team    the player's crews Del, Kil, Liv (two Guardians each, row y 1000); at 2 s TEAM_DELETE Del, TEAM_KILL Kil,
          Liv the control (the DELETE_LIVING variant is not in script_catalog.json: not asked). 活着 = 1 / 2 Del's, 4 / 8
          Kil's, 16 / 32 Liv's not destroyed; 甲死帧 / 乙死帧 = frames Kil 1 / Del 1 is NAMED_DYING [63 -> 51 at 2 s
          -> 48 a frame later (Del's gone a frame after Kil's); 甲死帧 1, 乙死帧 0]
  idle    crews Idl, Idf, Ctl (two Guardians each, y 2000 / 2200 / 2400) sent 1300 east (MOVE_TEAM_TO) at 1 s; at 3 s
          TEAM_IDLE_FOR_SECONDS(Idl, 3), TEAM_IDLE_FOR_FRAMECOUNT(Idf, 15). 到 = Idl's at the goal x1 + Idf's x10 +
          Ctl's x100 [200 from s15: the order dropped, as the unit versions (engine_scripts7 idle)]
  merge   crews Src (2) and Dst (1); at 1 s TEAM_MERGE_INTO_TEAM(Src, Dst), at 2 s MOVE_TEAM_TO(Dst, goal M). Crews
          Sr2 (2) and Ds2 (1); at 1 s TEAM_MERGE_INTO_TEAM(Sr2, Ds2), at 2 s MOVE_TEAM_TO(Sr2, goal N). 合 = in goal M:
          Src's x1 + Dst's x10; 源 = in goal N: Sr2's x1 + Ds2's x10 [合 1 from s13, 12 from s15; 源 0: the source empty]
  spawn   at 1 s UNIT_SPAWN_NAMED_OBJECT_ON_TEAM_AT_NAMED_OBJECT_LOCATION('... Spawned', Guardian, the player's team,
          the player's Guardian 'anchor' at (3500, 3500)). 生 = 1 the spawned one not destroyed + 2 within 150 of the
          anchor [3 from s1]

读数 (bench 2026-11-09, run_queue engine_scripts8:*; the bench's seconds run ~1 s ahead of the timers):
  team    活着 48 from s1 to the end (s9), 甲死帧 1, 乙死帧 1: TEAM_DELETE and TEAM_KILL take every member at once;
          both the killed and the deleted one are NAMED_DYING for one frame. The first run asked 活着 63 at s1 (FAIL:
          the bench's clock, not the game). The simulator: Del's gone a frame after Kil's, and a deleted one never
          dying (乙死帧 0) -- a frame's difference, not fixed.
  idle    PASS. 到 100 at s12 (the control's first), 200 from s13: TEAM_IDLE_FOR_SECONDS 3 and TEAM_IDLE_FOR_FRAMECOUNT
          15 drop the move order (not a pause), as the unit versions. The simulator agrees.
  merge   PASS. 合 1 at s11, 12 from s13; 源 0 all run: TEAM_MERGE_INTO_TEAM moves the source's members to the target
          (they took the target's order); an order to the source afterwards moves nobody. The simulator agrees.
  spawn   PASS. 生 3 from s1: UNIT_SPAWN_NAMED_OBJECT_ON_TEAM_AT_NAMED_OBJECT_LOCATION makes the named object at the
          object's place (within 150). The simulator agrees.
"""
from maps import probe_border
from parts import Mission, Script, Test, square

TANK = 'AlliedAntiVehicleVehicleTech1'
O = (1300.0, 4300.0)                            # probe_border's 'stop row': every place below is absolute
RUN = {'team': 8.0, 'idle': 30.0, 'merge': 30.0, 'spawn': 6.0, 'status': 20.0, 'power': 10.0}
TEAM_ROW = {'Del': 800.0, 'Kil': 1300.0, 'Liv': 1800.0}
IDLE_ROW = {'Idl': 2000.0, 'Idf': 2200.0, 'Ctl': 2400.0}
MERGE_ROW = {'Src': (3200.0, 2), 'Dst': (3400.0, 1), 'Sr2': (3700.0, 2), 'Ds2': (3900.0, 1)}
GOALS = {'idle Idl': (2100.0, 2000.0), 'idle Idf': (2100.0, 2200.0), 'idle Ctl': (2100.0, 2400.0),
         'merge M': (2000.0, 3300.0), 'merge N': (2000.0, 3800.0)}
STATUS = {'hold': ((3500.0, 1000.0), (3500.0, 1150.0), (3620.0, 1075.0)), 'free': ((3500.0, 2300.0), None,
                                                                                    (3620.0, 2300.0))}
ANCHOR = (3500.0, 3500.0)
SPAWNED = 'UNIT - CNV S8 Spawned'


def _n(part):
    return f'UNIT - CNV S8 {part}'


def _put(m, template, x, y, **kw):
    m.put(template, 'stop row', x - O[0], y - O[1], **kw)


def mission(name='CampScr8'):
    m = Mission(name=name, map=probe_border, units=[], facts={})
    m.spawns |= {TANK}
    for crew, x in TEAM_ROW.items():
        c = m.crew(crew)
        for k in (1, 2):
            _put(m, TANK, x + 150.0 * (k - 1), 1000.0, angle=0.0, name=_n(f'{crew} {k}'), role=f'{crew} {k}',
                 props={'originalOwner': c})
    for crew, y in IDLE_ROW.items():
        c = m.crew(crew)
        for k in (1, 2):
            _put(m, TANK, 700.0 + 150.0 * k, y, angle=0.0, name=_n(f'{crew} {k}'), role=f'{crew} {k}',
                 props={'originalOwner': c})
    for crew, (y, n) in MERGE_ROW.items():
        c = m.crew(crew)
        for k in range(1, n + 1):
            _put(m, TANK, 700.0 + 150.0 * k, y, angle=0.0, name=_n(f'{crew} {k}'), role=f'{crew} {k}',
                 props={'originalOwner': c})
    for part, (x, y) in GOALS.items():
        m.waypoint(part, f'CNV S8 {part.title()}', 'stop row', x - O[0], y - O[1])
    hold = m.crew('Hold')
    for part, (a, b, e) in STATUS.items():      # pending_scripts8 status's scene
        kw = {'props': {'originalOwner': hold}} if part == 'hold' else {}
        _put(m, TANK, *a, angle=0.0, name=_n(f'{part.title()} 1'), role=f'{part} 1', **kw)
        if b:
            _put(m, TANK, *b, angle=0.0, name=_n(f'{part.title()} 2'), role=f'{part} 2', **kw)
        _put(m, TANK, *e, side='s1', angle=3.1416, name=_n(f'{part.title()} Foe'), role=f'{part} foe')
    _put(m, TANK, *ANCHOR, angle=1.5708, name=_n('Anchor'), role='anchor')
    return m


def at(t, key, secs, actions):
    timer = f'Test S8 {key} Timer'
    t.scripts += [Script(f'Test - S8 {key} timer', [], [('SET_MILLISECOND_TIMER', timer, secs)]),
                  Script(f'Test - S8 {key}', [('TIMER_EXPIRED', timer)], actions)]


def total(t, counter, label, parts):
    """counter = the sum of the weights whose condition holds, recounted every frame. parts: [(weight, condition)]."""
    t.counters.append((counter, label))
    t.scripts.append(Script(f'Test - {counter} zero', [], [('SET_COUNTER', counter, 0)], once=False))
    t.scripts += [Script(f'Test - {counter} {k}', [c], [('INCREMENT_COUNTER', w, counter)], once=False)
                  for k, (w, c) in enumerate(parts)]


def frames(t, counter, label, cond):
    t.counters.append((counter, label))
    t.scripts.append(Script(f'Test - {counter}', cond, [('INCREMENT_COUNTER', 1, counter)], once=False))


def watch(t, run, every=1.0):
    t.bench = [('bench_watch', dict(seconds=run, every=every, sheet=False, lines=len(t.counters)))]


def _goal(t, m, part):
    area = f'Test S8 {part.title()}'
    t.areas[area] = square(*m.point(part), 150.0)
    return area


def team(m):
    t = Test()
    at(t, 'end', 2.0, [('TEAM_DELETE', m.teams['Del']), ('TEAM_KILL', m.teams['Kil'])])
    names = [m.role(f'{c} {k}').name for c in TEAM_ROW for k in (1, 2)]
    total(t, 'CNV_S8_Alive', '活着', [(2 ** k, ('NAMED_NOT_DESTROYED', n)) for k, n in enumerate(names)])
    frames(t, 'CNV_S8_KDie', '甲死帧', [('NAMED_DYING', m.role('Kil 1').name)])
    frames(t, 'CNV_S8_DDie', '乙死帧', [('NAMED_DYING', m.role('Del 1').name)])
    t.expect += [('活着', RUN['team'] - 2, '==', 48)]        # the bench's seconds run ~1 s ahead: s1 already 48
    watch(t, RUN['team'], 0.5)
    return t


def idle(m):
    t = Test()
    at(t, 'go', 1.0, [('MOVE_TEAM_TO', m.teams[c], m.mark(f'idle {c}')) for c in IDLE_ROW])
    at(t, 'idle', 3.0, [('TEAM_IDLE_FOR_SECONDS', m.teams['Idl'], 3), ('TEAM_IDLE_FOR_FRAMECOUNT', m.teams['Idf'], 15)])
    parts = []
    for w, c in ((1, 'Idl'), (10, 'Idf'), (100, 'Ctl')):
        area = _goal(t, m, f'idle {c}')
        parts += [(w, ('NAMED_INSIDE_AREA', m.role(f'{c} {k}').name, area)) for k in (1, 2)]
    total(t, 'CNV_S8_At', '到', parts)
    t.expect += [('到', RUN['idle'] - 2, '>=', 200)]
    watch(t, RUN['idle'])
    return t


def merge(m):
    t = Test()
    at(t, 'merge', 1.0, [('TEAM_MERGE_INTO_TEAM', m.teams['Src'], m.teams['Dst']),
                         ('TEAM_MERGE_INTO_TEAM', m.teams['Sr2'], m.teams['Ds2'])])
    at(t, 'go', 2.0, [('MOVE_TEAM_TO', m.teams['Dst'], m.mark('merge M')),
                      ('MOVE_TEAM_TO', m.teams['Sr2'], m.mark('merge N'))])
    for counter, label, goal, src, dst in (('CNV_S8_M', '合', 'merge M', 'Src', 'Dst'),
                                           ('CNV_S8_N', '源', 'merge N', 'Sr2', 'Ds2')):
        area = _goal(t, m, goal)
        total(t, counter, label, [(1, ('NAMED_INSIDE_AREA', m.role(f'{src} {k}').name, area)) for k in (1, 2)]
              + [(10, ('NAMED_INSIDE_AREA', m.role(f'{dst} 1').name, area))])
    t.expect += [('合', RUN['merge'] - 2, '==', 12)]
    watch(t, RUN['merge'])
    return t


def spawn(m):
    t = Test()
    at(t, 'spawn', 1.0, [('UNIT_SPAWN_NAMED_OBJECT_ON_TEAM_AT_NAMED_OBJECT_LOCATION', SPAWNED, TANK, m.team(),
                          m.role('anchor').name)])
    t.areas['Test S8 Anchor'] = square(*ANCHOR, 150.0)
    total(t, 'CNV_S8_Spawn', '生', [(1, ('NAMED_NOT_DESTROYED', SPAWNED)),
                                    (2, ('NAMED_INSIDE_AREA', SPAWNED, 'Test S8 Anchor'))])
    t.expect += [('生', RUN['spawn'] - 2, '==', 3)]
    watch(t, RUN['spawn'], 0.5)
    return t


MISSION = {'engine_scripts8': mission}
CHECKS = {'engine_scripts8': {'team': team, 'idle': idle, 'merge': merge, 'spawn': spawn}}
