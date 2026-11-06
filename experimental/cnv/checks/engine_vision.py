"""Engine unit test: vision over high ground (ShroudClearingHeight) and how long a script's reveal lasts.

Same stonehenge cast as engine_see (arms W and E; no Tanya, no S): an enemy tower (AlliedBaseDefense) on the ring and
a player's Athena cannon (AlliedAntiStructureVehicle) on the low ground 400 away. Cannons hold fire (stance 3) and no
auto-acquire, so nothing moves or shoots. Probe unit CNV_VisionHi = the retail cannon with ShroudClearingHeight="500"
in its VisionInfo (CNV_VisionHi2: also ShroudClearingRange 500). Spare cannons stand in the cast and are deleted at the
start, so one mission serves every check.

  height    W cannon = CNV_VisionHi, E cannon = retail. Counter 看见: W tower discovered 1, E tower discovered 10,
            W cannon ENEMY_SIGHTED 100, E cannon ENEMY_SIGHTED 1000. Prediction 1101 (E tower not discovered).
  height2   as height with CNV_VisionHi2 on W (ShroudClearingRange 500 as well)
  reshroud  both cannons retail. At Go (1 s) MAP_REVEAL_AT_WAYPOINT, radius 150, p1, on tower W. 揭开 = frames from
            Go on that NAMED_DISCOVERED(p1, tower W) is true; 帧数 = frames since Go. How long the reveal holds.
  resh5     as reshroud with MAP_SHROUD_SET_RESHROUD_TIME 5.0 (seconds: retail A04 uses 1.0) at the start.
  resh0 / resh1 / resh10   the same with 0, 1, 10: how the setting maps to frames.

(Check names are short: the mod name, mission + check, may not pass 15 characters.)

Bench 11-06 (counters 看见 / 揭开 + 帧数; ~15 frames per second):
  height   CampVisHeight_mcp_1106_030642: 看见 1101 from the first reading (s1) to s21, as predicted: W tower
    discovered and both cannons ENEMY_SIGHTED with the ShroudClearingHeight 500 probe on W; E (retail cannon) the
    tower not discovered (no 10) yet its cannon is ENEMY_SIGHTED (the 1000). height2 not run (W already 1).
  reshroud CampVisReshroud_mcp_1106_030845: 揭开 follows 帧数 (29 at s1, 134 at s8), stops at 137 frames after Go
    (between s8 and s9, ~9.1 s) and stays 137 to the end (帧数 482): the reveal lapses after 137 frames.
  resh5    CampVisResh5_mcp_1106_031048 (MAP_SHROUD_SET_RESHROUD_TIME 5.0 at the start): 揭开 60 at s3, stops at 62
    frames (~4.1 s) and stays 62 (帧数 483): shorter than the default 137.
  resh1 CampVisResh1_mcp_1106_032237: 揭开 2. resh10 CampVisResh10_mcp_1106_032431: 137 (as the default).
  resh0 CampVisResh0_mcp_1106_032628: 0 (never shown). So a reveal holds 15 x N - 13 frames (docs/engine/vision.md 2).
"""
import os

import labpaths
from maps import stonehenge
from parts import Mission, Script, Test, Unit
from checks.probe_view import open_in_view

TOWER, CANNON = 'AlliedBaseDefense', 'AlliedAntiStructureVehicle'
HI, HI2 = 'CNV_VisionHi', 'CNV_VisionHi2'
GO, RUN = 1.0, {'height': 20.0, 'height2': 20.0, 'reshroud': 30.0, 'resh5': 30.0, 'resh1': 30.0, 'resh10': 30.0,
               'resh0': 30.0}
TOWERS = {'W': (1280.0, 1350.0), 'E': (2420.0, 1250.0)}
# role: (template, x, y); W has three cannons (probe, probe2, control), the unused ones are deleted at the start
CANNONS = {'W': (HI, 880.0, 1350.0), 'W2': (HI2, 880.0, 1450.0), 'W0': (CANNON, 880.0, 1250.0),
           'E': (CANNON, 2820.0, 1250.0)}


def probe(id, rng=False):
    x = open(os.path.join(labpaths.SDK3, 'SageXML', 'Allied', 'Units', CANNON + '.xml'), encoding='utf-8').read()
    old = 'VisionRange="500"\n\t\t\tShroudClearingRange="=$STANDARD_SHROUD_CLEAR"'
    new = ('VisionRange="500"\n\t\t\tShroudClearingHeight="500"\n\t\t\tShroudClearingRange="'
           + ('500' if rng else '=$STANDARD_SHROUD_CLEAR') + '"')
    for o, n in ((f'id="{CANNON}"', f'id="{id}"'), (f'EditorName="{CANNON}"', f'EditorName="{id}"'), (old, new)):
        assert x.count(o) == 1, (o[:50], x.count(o))
        x = x.replace(o, n, 1)
    return Unit(id, x, names=dict(unit=id), what='引擎探针：原版雅典娜炮，ShroudClearingHeight 500',
                params=dict(height=500, range=rng))


def mission():
    m = Mission(name='CampVis', map=stonehenge, units=[probe(HI), probe(HI2, True)], facts={})
    cx, cy = m.site('start')
    for k, (tx, ty) in TOWERS.items():
        m.put(TOWER, 'start', tx - cx, ty - cy, side='s1', name=f'UNIT - CNV Vis Tower {k}', role=f'tower {k}')
    for k, (tmpl, ax, ay) in CANNONS.items():
        m.put(tmpl, 'start', ax - cx, ay - cy, name=f'UNIT - CNV Vis Cannon {k}', role=f'cannon {k}',
              angle=0.0 if k == 'E' else 3.1416)
    return open_in_view(m, 'Vision')


def _test(m, which):
    t = Test()
    p1, s1 = m.player('p1'), m.player('s1')
    keep = {'height': ('W', 'E'), 'height2': ('W2', 'E')}.get(which, ('W0', 'E'))
    start = []
    for k in CANNONS:
        n = m.role(f'cannon {k}').name
        if k in keep:
            start += [('UNIT_SET_STANCE', n, 3), ('UNIT_ALLOW_AI_AUTOACQUIRE', n, 0)]
        else:
            start.append(('NAMED_DELETE', n))
    tw = lambda k: m.role(f'tower {k}').name
    if which.startswith('height'):
        w, e = (m.role(f'cannon {keep[0]}').name, m.role('cannon E').name)
        c = 'Test Vision'
        t.counters.append((c, '看见'))
        t.scripts.append(Script('Test - start', [], start))
        for k, step in (('W', 1), ('E', 10)):
            t.scripts.append(Script(f'Test - see {k}', [('NAMED_DISCOVERED', p1, tw(k))],
                                    [('INCREMENT_COUNTER', step, c)]))
        for n, step in ((w, 100), (e, 1000)):
            t.scripts.append(Script(f'Test - sighted {step}', [('ENEMY_SIGHTED', n, 'Enemy', s1)],
                                    [('INCREMENT_COUNTER', step, c)]))
        t.expect = [('看见', 0, 'ever>=', 1101)]
        t.bench = [('bench_watch', dict(seconds=RUN[which], every=1, sheet=False, lines=1))]
        return t
    if which != 'reshroud':  # resh<N>: MAP_SHROUD_SET_RESHROUD_TIME N at the start
        start.append(('MAP_SHROUD_SET_RESHROUD_TIME', float(which[4:])))
    start.append(('SET_MILLISECOND_TIMER', 'Test Go', GO))
    t.scripts.append(Script('Test - start', [], start))
    t.waypoints['Test Reveal'] = TOWERS['W']
    t.scripts.append(Script('Test - go', [('TIMER_EXPIRED', 'Test Go')],
                            [('MAP_REVEAL_AT_WAYPOINT', 'Test Reveal', 150.0, p1), ('SET_FLAG', 'Test Going', 1)]))
    going = ('FLAG', 'Test Going', 1)
    t.counters.append(('Test Open', '揭开'))
    t.counters.append(('Test Frames', '帧数'))
    t.scripts.append(Script('Test - frames', [going], [('INCREMENT_COUNTER', 1, 'Test Frames')], once=False))
    t.scripts.append(Script('Test - open', [going, ('NAMED_DISCOVERED', p1, tw('W'))],
                            [('INCREMENT_COUNTER', 1, 'Test Open')], once=False))
    t.expect = [('帧数', 0, 'ever>=', 1, RUN[which])]
    t.bench = [('bench_watch', dict(seconds=RUN[which], every=1, sheet=False, lines=2))]
    return t


MISSION = {'engine_vision': mission}
CHECKS = {'engine_vision': {w: (lambda m, w=w: _test(m, w)) for w in RUN}}
