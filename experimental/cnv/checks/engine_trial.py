"""Engine unit test: where a unit stops when the pathfinder's search runs out (engine line round 11, part 2b;
docs/engine/pathing.md). The map is the shell line's trial map drawn on the map page (work/mappage/trial/trial.py,
a draft in work/: ADR 0017 -- this check reads it from there and says so when it is missing).

Read from the program (RA3 1.13, engine line's private notes): a plain move request that cannot reach its goal --
the search used up its cell limit, or ran out of cells -- does not fail; it walks to the cell, among those it
looked at, nearest the goal in a straight line, and stops there. The engine model (RA3-EngineModel, find_path)
says, on this map: from the start, the plateau and the lake shore run out of the limit although the walkable regions
join them; the unit stops at about (1930, 1810), under the plateau's south cliff, and (990, 510), against the west
face of the cliff wall; the ramp foot is reached (the control).

trial: an IFV each from the start to the plateau, the lake shore and the ramp foot. Counters: 10 at the goal,
1 by the model's stop, 100 on the way round (plateau: the ramp foot; lake shore: the wall gap).
"""
import importlib.util
import os

from parts import Mission, Script, Test, square
from checks.probe_view import open_in_view

IFV = 'AlliedAntiAirVehicleTech1'
MAPPAGE = os.path.normpath(os.path.join(os.path.dirname(__file__), '..', '..', '..', 'work', 'mappage'))
DRAFT = os.path.join(MAPPAGE, 'trial', 'trial.py')
# the engine line's copies of the trial map (work/mappage/<v>/<v>.py, never the shell line's original):
# trial2 -- the west cliff wall runs into the south map edge (no slit under its cap);
# trial3 -- the wall ends at y 400 (a 350-wide way round to the south).
VARIANTS = {'engine_trial': 'trial', 'engine_trial2': 'trial2', 'engine_trial3': 'trial3'}
LANES = {   # goal: (model's stop, the way round, label)
    'plateau': ((1930.0, 1810.0), 'ramp foot', '东北高地'),
    'lake shore': ((990.0, 510.0), 'wall gap', '湖南岸'),
    'ramp foot': (None, None, '坡脚'),
}


def _key(s):
    return s.title().replace(' ', '')


def _draft(v='trial'):
    path = os.path.join(MAPPAGE, v, f'{v}.py')
    if not os.path.exists(path):
        raise FileNotFoundError(f'the trial map draft is not there: {path} (the map page, serve.py --new trial; '
                                f'trial2/trial3 are the engine line\'s copies of it)')
    spec = importlib.util.spec_from_file_location(f'engine_{v}_map', path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _mission(v):
    m = Mission(name=f'Camp{v.title()}', map=_draft(v), facts={})
    for k, lane in enumerate(LANES):
        m.put(IFV, 'start', -60.0 + 60.0 * k, 0, role=f'{lane} ifv', name=f'UNIT - CNV Trial {_key(lane)} Ifv')
    return open_in_view(m, 'Trial')    # K5: the start is too near the map's edge


def mission():
    return _mission('trial')


def trial(m):
    t = Test()
    order = [('MAP_REVEAL_ALL_PERM', m.player('p1'))]
    for lane, (stop, way, label) in LANES.items():
        wp = f'Test Trial {_key(lane)} Goal'
        t.waypoints[wp] = m.site(lane)
        order += m.order('move', [m.role(f'{lane} ifv').name], wp, crew=f'Trial{_key(lane)}')
        ifv = m.role(f'{lane} ifv').name
        counter = f'CNV_Trial_{_key(lane)}'
        t.counters.append((counter, label))
        t.scripts.append(Script(f'Test - {counter} zero', [], [('SET_COUNTER', counter, 0)], once=False))
        worth = [(f'Test Trial {_key(lane)} At', square(*m.site(lane), 120.0), 10)]
        if stop is not None:
            worth.append((f'Test Trial {_key(lane)} Stop', square(*stop, 150.0), 1))
            worth.append((f'Test Trial {_key(lane)} Way', square(*m.site(way), 150.0), 100))
        for k, (area, box, n) in enumerate(worth):
            t.areas[area] = box
            t.scripts.append(Script(f'Test - {counter} {k}', [('NAMED_INSIDE_AREA', ifv, area)],
                                    [('INCREMENT_COUNTER', n, counter)], once=False))
    t.scripts.insert(0, Script('Test - go', [], order))
    t.bench = [('bench_watch', dict(seconds=60, every=3, sheet=False, lines=3))]
    t.expect = [('坡脚', 0, 'ever==', 10, 60)]          # the control; plateau / lake shore are read, not judged
    return t


BANDS_X = ((0.0, 500.0), (500.0, 800.0), (800.0, 950.0), (950.0, 1050.0), (1050.0, 3000.0))   # 1 .. 10 000
BANDS_Y = ((0.0, 300.0), (300.0, 600.0), (600.0, 900.0), (900.0, 1300.0), (1300.0, 3000.0))


def where(m):
    """Where the lake shore IFV stops: an x counter and a y counter, the strip it is in worth 1, 10, ... 10 000."""
    t = Test()
    lane = 'lake shore'
    wp = 'Test Trial LakeShore Goal'
    t.waypoints[wp] = m.site(lane)
    order = [('MAP_REVEAL_ALL_PERM', m.player('p1'))]
    order += m.order('move', [m.role(f'{lane} ifv').name], wp, crew='TrialLakeShore')
    ifv = m.role(f'{lane} ifv').name
    for axis, bands in (('X', BANDS_X), ('Y', BANDS_Y)):
        counter = f'CNV_Trial_Lake{axis}'
        t.counters.append((counter, f'湖南岸{axis}'))
        t.scripts.append(Script(f'Test - {counter} zero', [], [('SET_COUNTER', counter, 0)], once=False))
        for k, (a, b) in enumerate(bands):
            area = f'Test Trial Lake {axis}{k}'
            t.areas[area] = [(a, 0.0), (b, 0.0), (b, 3000.0), (a, 3000.0)] if axis == 'X' else \
                [(0.0, a), (3000.0, a), (3000.0, b), (0.0, b)]
            t.scripts.append(Script(f'Test - {counter} {k}', [('NAMED_INSIDE_AREA', ifv, area)],
                                    [('INCREMENT_COUNTER', 10 ** k, counter)], once=False))
    t.scripts.insert(0, Script('Test - go', [], order))
    t.bench = [('bench_watch', dict(seconds=45, every=3, sheet=False, lines=2))]
    return t


# the builds this module makes and their checks (cnv/registry.py)
MISSION = {b: (lambda v=v: _mission(v)) for b, v in VARIANTS.items()}
CHECKS = {b: {'trial': trial, 'where': where} for b in VARIANTS}
