"""R3 step X, a move's goal spot (simpath.free_spot -> spot) against the bench: `engine_drop lanes` and
`engine_dropring tens` 2026-11-17 (experimental/cnv/checks/engine_drop.py; CNVProbe stops read by
work/re/scripts/x_drop.py): units of one kind sent one at a time to one point, on the probe map's open ground."""
import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
# loaded by file: simbench.py puts the cnv folders on the path itself (no new sys.path edit here: guard G4's ceiling)
_spec = importlib.util.spec_from_file_location('simbench', ROOT / 'experimental' / 'cnv' / 'simbench.py')
simbench = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(simbench)
import build  # noqa: E402
import sim  # noqa: E402
import engine.objects.path as simpath  # noqa: E402
from benches.movement.pathing.checks import drop_key, engine_drop  # noqa: E402

# the bench's stops, in the order sent (runs CampDropLanes_mcp_1117_170137, CampRingTens_mcp_1117_170616)
BENCH = {
    ('engine_drop', 'west'): [(3001, 2001), (3041, 2001), (3001, 2041), (2961, 2001), (3041, 2041.8), (2961, 2041)],
    ('engine_drop', 'north'): [(3021, 3001), (3061, 3001), (3021, 3041), (2981, 3001), (3061, 3041), (2981, 3041)],
    ('engine_drop', 'man'): [(3009.9, 4510), (3030, 4510), (3009.3, 4530), (2989.9, 4510), (3030, 4530),
                             (2989.4, 4530)],
    ('engine_dropring', 'tank'): [(3001, 1601), (3041, 1601.2), (3001, 1641), (2961, 1601), (3041, 1641),
                                  (2961, 1641), (2960.4, 1561), (3001, 1561), (3041, 1560.6), (3081, 1601)],
    ('engine_dropring', 'man'): [(3610, 2809.9), (3630, 2809.2), (3610, 2830), (3590, 2809.9), (3630.2, 2829.8),
                                 (3590, 2830), (3590, 2789.9), (3610, 2789.9), (3630, 2789.4), (3650, 2810)],
}
NEAR = 2.0          # the bench's tanks stand +1 off the grid on both axes (not modelled, simpath's INFERRED)


@pytest.fixture(scope='module', params=['engine_drop', 'engine_dropring'])
def stops(request):
    name = request.param
    m, t, _ = build.resolve(name, next(iter(build.MISSIONS[name][1])))
    s = sim.Sim(m, t)
    s.run(engine_drop()['run'](name))
    return name, s


def test_every_unit_stops_where_the_bench_did(stops):
    """Each unit sent to a held point stops within NEAR of the bench's stop: snapped to the grid by its footprint, then
    the first free spot of the rings (east, north, west, north-east, north-west, south-west, south, south-east)."""
    name, s = stops
    for (build_name, lane), want in BENCH.items():
        if build_name != name:
            continue
        for k, (bx, by) in enumerate(want):
            b = s.bodies[f'UNIT - CNV Drop {drop_key(lane, k)}']
            assert abs(b.x - bx) <= NEAR and abs(b.y - by) <= NEAR, (lane, k + 1, (b.x, b.y), (bx, by))


def _spot(want, radius, held):
    return simpath.spot(want, radius, held, lambda x, y: True, 20.0)


def test_snapped_by_footprint_even_to_a_corner_odd_to_a_cell_centre():
    """Nobody about: a Guardian (r 23.3, 2 cells) to the nearest corner, a Peacekeeper (r 7, 1 cell) to the centre of
    the cell the point is in -- even when the point is a corner (bench: (3000, 4500) -> (3010, 4510))."""
    assert _spot((3013.0, 3007.0), 23.3, []) == (3020.0, 3000.0)
    assert _spot((3000.0, 4500.0), 7.0, []) == (3010.0, 4510.0)
    assert _spot((3013.0, 3007.0), 7.0, []) == (3010.0, 3010.0)


def test_spacing_is_the_footprint_not_the_radii():
    """A second Guardian stands 40 east of the first (its 2-cell footprint), not 46.6 (the two radii)."""
    assert _spot((3000.0, 2000.0), 23.3, [(3000.0, 2000.0, 23.3)]) == (3040.0, 2000.0)


def test_no_free_spot_or_closed_ground_gives_none():
    assert simpath.spot((3000.0, 2000.0), 23.3, [], lambda x, y: False, 20.0) is None
    full = [(3000.0 + 40 * i, 2000.0 + 40 * j, 23.3) for i in range(-20, 21) for j in range(-20, 21)]
    assert _spot((3000.0, 2000.0), 23.3, full) is None
