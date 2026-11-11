"""HB_Bridge_02 generation only, Niagara 270 / 700, no damage or engineers.

XML: end caps 75 each, alternating centers A/B 150 each, two gatehouses.
Prediction (rounding INFERRED): ceil((length-150)/150) centers, A first:
270 -> End/End2/A/B/Gate = 1/1/1/0/2; 700 -> 1/1/2/2/2.
Each decimal digit is count+1 (0 means no matching count, NOT zero objects).
Ends row = (Gate+1)*100 + (End2+1)*10 + End+1; center = (B+1)*10+A+1.
Only exact equality 0..7 is encoded; overflow or unavailable conditions cannot
masquerade as a valid zero. All five precise retail templates are queried.
BENCH 2026-11-11: s1-s23 322/12/322/33; all stable-window expectations PASS.
Only the two observed lengths are modeled; arbitrary-length rounding stays open.
"""
from types import SimpleNamespace

import platmap
from maps import island, niagara
from parts import Mission, Script, Test, square

FIELDS = ('End', 'End2', 'Center', 'Center2', 'GateHouse')


def mission():
    probe_map = SimpleNamespace(**vars(niagara))
    probe_map.PLAYERS = {**niagara.PLAYERS, **island.NEUTRAL}
    probe_map.OBJECTS = niagara.OBJECTS[6:]  # remove all three original bridge pairs
    m = Mission(name='CampBridge', map=probe_map, units=[])
    m.spawns.update('HB_Bridge_02_' + field for field in FIELDS)
    origin = m.site('front')
    for role, (p, q) in zip(('short', 'long'), (niagara.BRIDGES[0], niagara.BRIDGES[2])):
        for k, (x, y, angle, flags) in enumerate(platmap.bridge(p, q)):
            m.put('HB_Bridge_02', 'front', x-origin[0], y-origin[1], side='neutral',
                  angle=angle, flags=flags, role=f'{role} {k}', name=f'Bridge {role} {k}')
        # Include gatehouses outside the endpoints; no other bridge in this region.
        m.areas['Bridge ' + role] = square((p[0]+q[0])/2, p[1], 550)
    return m


def check(m):
    t = Test()
    t.scripts = [Script('Bridge reveal', [], [('MAP_REVEAL_ALL_PERM', m.player('p1'))])]
    for role, labels, values in (('short', ('短端量', '短中量'), (322, 12)),
                                  ('long', ('长端量', '长中量'), (322, 33))):
        rows = [f'Bridge {role} ends', f'Bridge {role} centers']
        t.counters += list(zip(rows, labels))
        t.scripts.append(Script('Bridge reset ' + role, [],
                                [('SET_COUNTER', row, 0) for row in rows], once=False))
        for field, row, weight in zip(FIELDS, (rows[0], rows[0], rows[1], rows[1], rows[0]),
                                      (1, 10, 1, 10, 100)):
            for n in range(8):
                t.scripts.append(Script(f'Bridge {role} {field} {n}', [
                    ('PLAYER_HAS_COMPARISON_UNIT_TYPE_IN_TRIGGER_AREA', m.player('neutral'),
                     2, n, 'HB_Bridge_02_' + field, 'Bridge ' + role)], [
                    ('INCREMENT_COUNTER', (n+1)*weight, row)], once=False))
        t.expect += [(label, 4, '==', value, 18) for label, value in zip(labels, values)]
    t.bench = [('bench_watch', dict(seconds=20, every=1, sheet=False, lines=4))]
    return t


MISSION = {'engine_bridgebuilder': mission}
CHECKS = {'engine_bridgebuilder': {'a': check}}
