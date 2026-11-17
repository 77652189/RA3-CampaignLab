"""Engine unit test: does the game walk by the map's impassable bits (BlendTileData field 0) alone, or does it work out
cliffs from the heights itself? (docs/engine/terrain.md 3; engine line round 8.)

On the probe map (maps/probe_ground.py) four pens differ only in their ring: steep and unmarked, flat and marked,
steep and marked (the control: as our writers do it), flat and unmarked (the control). In each pen a guardian tank and
an Imperial warrior are ordered to the point 260 north, outside the ring. Each pen's counter adds 1 for the tank and
10 for the warrior standing there: 11 both got out, 1 only the tank, 10 only the warrior, 0 neither.

walk expects the game to go by the bits only (steep unmarked 11, flat marked 0); the controls must read 0 and 11 or
the probe says nothing.
"""
from maps import probe_ground
from parts import Mission, Script, Test, square

TANK = 'AlliedAntiVehicleVehicleTech1'
WARRIOR = 'JapanAntiInfantryInfantry'
WHO = (('tank', TANK, -30.0, 1), ('warrior', WARRIOR, 30.0, 10))
LABEL = {'steep unmarked': '陡坡没标', 'flat marked': '平地标了', 'steep marked': '陡坡标了', 'flat unmarked': '平地没标'}
RUN = 20.0                         # all out by ~s7 (run CampGroundWalk_mcp_1104_153225)


def _key(pen):
    return pen.title().replace(' ', '')


def mission():
    m = Mission(name='CampGround', map=probe_ground, facts={})
    for pen in probe_ground.PENS:
        for part, template, dx, _ in WHO:
            m.put(template, pen, dx, 0, name=f'UNIT - CNV Ground {_key(pen)} {part}', role=f'{pen} {part}')
    return m


def walk(m):
    t = Test()
    order = [('MAP_REVEAL_ALL_PERM', m.player('p1'))]
    for pen in probe_ground.PENS:
        out = f'Test Ground {_key(pen)} Out'
        t.waypoints[out] = m.site(f'{pen} out')
        t.areas[out] = square(*m.site(f'{pen} out'), 70)
        counter = f'CNV_Ground_{_key(pen)}'
        t.counters.append((counter, LABEL[pen]))
        t.scripts.append(Script(f'Test - {counter} zero', [], [('SET_COUNTER', counter, 0)], once=False))
        for part, _, _, worth in WHO:
            name = m.role(f'{pen} {part}').name
            order.append(('MOVE_NAMED_UNIT_TO', name, out))
            t.scripts.append(Script(f'Test - {counter} {part}', [('NAMED_INSIDE_AREA', name, out)],
                                    [('INCREMENT_COUNTER', worth, counter)], once=False))
    t.scripts.insert(0, Script('Test - go', [], order))
    t.expect += [(LABEL['steep unmarked'], RUN - 2, '==', 11), (LABEL['flat marked'], RUN - 2, '==', 0),
                 (LABEL['steep marked'], RUN - 2, '==', 0), (LABEL['flat unmarked'], RUN - 2, '==', 11)]
    t.bench = [('bench_watch', dict(seconds=RUN, every=3, sheet=False, lines=4))]
    return t


# the builds this module makes and their checks (cnv/registry.py)
MISSION = {'engine_terrain': mission}
CHECKS = {'engine_terrain': {'walk': walk}}
