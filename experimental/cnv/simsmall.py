"""The minimal world for rule tests (ADR 0029 "测试分两层"): an island with no scripts and only the objects given, so a
rule test builds its world in a second or two and runs only the subsystem it asks about, instead of a whole mission."""
import sim  # noqa: I001  (first: it puts experimental/cnv and campaign on the path)
import parts
from maps import island


def small_world(objects=(), model=True, map=island):
    """A Sim on the island map (or `map`, a maps module) with no scripts and only `objects`: (name, template, owner,
    x, y) each. Players are the map's (on the island Player_1 the human). model=False: without the private engine
    model (the frame loop's scripts cell runs the Python scripts)."""
    s = sim.Sim(parts.Mission(name='T', map=map, scripts=[]), model=model)
    for name in list(s.bodies):
        del s.bodies[name]
    for name, template, owner, x, y in objects:
        s.add(name, template, owner, x, y)
    return s
