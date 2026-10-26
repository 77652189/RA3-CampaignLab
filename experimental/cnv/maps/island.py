"""The generated island (CampNew18's terrain: an island in open sea, morning light, the player's start on its west
end). The bench calibration (experimental/testbench/calib.py) is for this map's start camera.

The terrain stays as it is: A8 and the unit benches (most on the west field, A8 across to the east sites) are
measured on it. The scenery (retail trees, bushes, small rocks: platprops) dresses only its coasts north and south
and its east tip -- off the west field and its benches, off the way east, off every site -- and has nothing that
counts as a STRUCTURE or a VEHICLE (no buildings, fences, lamps or big rocks: CampKinds counts those kinds over the
whole island, every player's).

Published: SITES (where a mission may place things, by name), PLAYERS and TEAMS (the map's own player list),
SCENERY (computed on first use).
"""
import numpy as np

import make_campnew18 as c18
import mapterrain
import newmap
import platprops
from platprops import area, clumps, scatter, shore
from parts import Obj, Site

START = c18.START                                # (1250, 2500): the start and the camera
CENTER, RADIUS = c18.CENTER, c18.RADIUS

SITES = {
    'island': Site(*CENTER, RADIUS, 'the whole island (2500, 2500), radius 1800'),
    'start': Site(*START, 0.0, "the player's start; the start camera looks here"),
    'base factory': Site(START[0] + 300, START[1] + 60, 0.0, "a war factory's pad 300 east of the start"),
    'base power': Site(START[0] + 300, START[1] - 140, 0.0, "a power plant's pad by the factory's"),
    'west field': Site(1180.0, 2375.0, 450.0, 'open grass in the start camera\'s view: bench scenes'),
    'west shore': Site(1300.0, 2300.0, 200.0, 'a staging ground south-east of the start'),
    'base edge': Site(1450.0, 2450.0, 150.0, "open ground at the east edge of the player's base, ~250 from an army "
                                             'on the west field (first try (1550, 2600) was on the war factory)'),
    'east field': Site(3000.0, 2600.0, 250.0, 'open ground in the middle of the east end, between east 1 and 2'),
    'east 1': Site(3400.0, 2200.0, 300.0, 'the east end, south (+y is north): room for a base or a platform'),
    'east 2': Site(3500.0, 2900.0, 300.0, 'the east end, middle'),
    'east 3': Site(3200.0, 3500.0, 300.0, 'the east end, north'),
}
PLAYERS = {'p1': 'Player_1', 's1': 'Soviet_1'}
# Heidelberg's player list also has Soviet_2 .. Soviet_6, enemies of the player, idle: a side each for whoever
# needs one of its own (the clones' mind control: units/clone.py)
SPARE = {f's{k}': f'Soviet_{k}' for k in range(2, 7)}
PLAYERS.update(SPARE)
TEAMS = {'p1': 'Player_1/teamPlayer_1'}           # the player's default team: everything placed for them, built too


def terrain(m):
    """Heights, ground textures, water, lighting (CampNew18's generate; its demo units go again in assemble)."""
    c18.generate(m)


def like(m, objs, tmpl):
    """Property templates for placing: a plain player unit, a plain Soviet unit, a waypoint."""
    out = {}
    for k in objs.kids:
        t = tmpl(k)
        key = {'*Waypoints/Waypoint': 'wp', 'AlliedAntiVehicleVehicleTech1': 'p1',
               'SovietAntiVehicleVehicleTech1': 's1'}.get(t)
        if key:
            out.setdefault(key, newmap.typed_props_of(m, k))
    assert set(out) == {'wp', 'p1', 's1'}, out.keys()
    props, flags = out['s1']
    assert props['originalOwner'][1] == 'Soviet_1/teamSoviet_1', props['originalOwner']
    for side, player in {**SPARE, **NEUTRAL}.items():
        out[side] = (dict(props, originalOwner=(props['originalOwner'][0], f'{player}/team{player}')), flags)
    return out


# the container's own neutral players: ore nodes, tech buildings, bridges (retail: PlyrNeutral), city buildings
NEUTRAL = {'neutral': 'PlyrNeutral', 'civ': 'PlyrCivilian'}

WOODS = {'HB_Tree03': 3, 'HB_Tree04': 2, 'HB_Tree05': 2, 'CC_Tree03': 2, 'OK_Tree01': 1}
UNDER = {'CC_Bush01': 3, 'CC_BUSH02': 3, 'HB_GRASS02': 3, 'YU_BUSH05': 2, 'YU_SMALLROCKS01': 1, 'YU_SMALLROCKS02': 1}
# kept open: the west field and everything the benches put round it (offsets to ~600), and the way from there to
# the east sites (A8's assault)
AVOID = [(1180.0, 2375.0, 1150.0), ((1100.0, 2600.0), (3700.0, 2700.0), 1400.0)]


def ground():
    """The island's heights as platprops asks them: CampNew18's noise (generate), computed without the map."""
    w, h, b = platprops.platmap.CONTAINER
    dims = type('Dims', (), {'width': w, 'height': h, 'border': b})
    e = np.zeros((h, w), np.float32)
    for (i, j), v in newmap.island_heights(dims, center=CENTER, radius=RADIUS).items():
        e[j, i] = v
    assert mapterrain.CELL == platprops.CELL
    return platprops.Ground(e=e)


def _scenery():
    g = ground()
    picks = []

    def put(cands):
        picks.extend(platprops.place(cands, None, SITES, keep=picks, avoid=AVOID, ground=g))
    whole = area('rect', (0, 0, 5000, 5000))
    put(scatter(whole, WOODS, 55, 71, density=0.85, patches=0.5))
    put(shore(g, {**WOODS, 'CC_BUSH02': 3}, 60, 72))
    put(clumps(whole, 25, 50, 3, {'YP_LOG01': 1, 'YP_LOG02': 1}, 73))
    put(scatter(whole, UNDER, 95, 74, density=0.45, patches=0.35))
    return [Obj(t, round(x, 1), round(y, 1), side='civ', angle=round(a, 3), site='map') for t, x, y, a in picks]


def __getattr__(name):
    """SCENERY on first use: a second or two of noise, not paid by every import of the map."""
    if name == 'SCENERY':
        globals()['SCENERY'] = _scenery()
        return globals()['SCENERY']
    raise AttributeError(name)
