"""The generated island (CampNew18's terrain: an island in open sea, morning light, the player's start on its west
end). The bench calibration (experimental/testbench/calib.py) is for this map's start camera."""
import make_campnew18 as c18
import newmap

START = c18.START                                # (1250, 2500): the start and the camera
CENTER, RADIUS = c18.CENTER, c18.RADIUS


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
    return out
