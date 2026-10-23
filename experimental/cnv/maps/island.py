"""The generated island (CampNew18's terrain: an island in open sea, morning light, the player's start on its west
end). The bench calibration (experimental/testbench/calib.py) is for this map's start camera.

Published: SITES (where a mission may place things, by name), PLAYERS and TEAMS (the map's own player list).
"""
import make_campnew18 as c18
import newmap
from parts import Site

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
    for side, player in SPARE.items():
        out[side] = (dict(props, originalOwner=(props['originalOwner'][0], f'{player}/team{player}')), flags)
    return out
