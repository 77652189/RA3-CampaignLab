"""R3 step X, an infantry group's ends (simpath.formation_spots -> block) against the bench: `engine_column lanes`,
`engine_crowd big`, `engine_colgate two` 2026-11-17 (experimental/cnv/benches/movement/pathing/checks.py#engine_column; CNVProbe stops read by
work/re/scripts/x_column.py): Peacekeepers sent to one point by one MOVE_TEAM_TO, on the probe map's open ground."""
import importlib.util
import math
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
from benches.movement.pathing.checks import COLUMN_RUN, column_key  # noqa: E402

# the bench's stops, in the order of engine_column.starts (runs CampColsLanes_mcp_1117_214108,
# CampCrowdBig_mcp_1117_214334, rounded to 0.1)
BENCH = {
    ('engine_column', 'w6'): [(3009.4, 2010), (3010, 2050), (3009.8, 1970), (2970, 2050), (2969.8, 1970),
                              (2970, 2010)],
    ('engine_column', 'n6'): [(3010, 3010.5), (3050, 3010.8), (2970, 3010), (3050, 3050.8), (2970, 3050),
                              (3010, 3050.6)],
    ('engine_column', 'w3'): [(3009.9, 4490), (3009.2, 4530), (2969.9, 4510)],
    ('engine_column', 'near'): [(3009.5, 1609.9), (3009.4, 1649.7), (3010, 1570), (2970, 1650), (2970, 1570),
                                (2969.9, 1610)],
    ('engine_column', 'd6'): [(4310, 2010), (4269.5, 2029.4), (4329.4, 1969.5), (4250, 2010), (4310, 1950),
                              (4270, 1970)],
    ('engine_crowd', 'w16'): [(3010, 2350), (3010, 2390), (3009.8, 2430), (3009.5, 2470),
                              (2970, 2350), (2970, 2390), (2969.8, 2430), (2969.4, 2470),
                              (2930, 2350), (2930, 2390), (2929.8, 2430), (2929.4, 2470),
                              (2890, 2350), (2890, 2390), (2889.8, 2430), (2889.4, 2470)],
    ('engine_crowd', 'n10'): [(3590, 3010), (3630, 3010.2), (3550, 3010), (3670, 3010), (3590, 3050),
                              (3630, 3050.2), (3550, 3050), (3670, 3050), (3590, 3090), (3630, 3090.2)],
    # run CampColGateTwo_mcp_1117_214947: two men (one behind the other / side by side), six sent 20 short, six anyhow
    ('engine_colgate', 'w2'): [(3009.9, 1990), (3009.2, 2030)],
    ('engine_colgate', 'w2s'): [(3010, 2390), (3009.8, 2430)],
    ('engine_colgate', 'close'): [(3010, 1610), (3010, 1650), (3010, 1570), (2969.8, 1649.7), (2970, 1570),
                                  (2969.8, 1610)],
    ('engine_colgate', 'scat'): [(3009.7, 4510), (3010, 4530), (2989.4, 4470), (2970, 4510), (2950, 4470),
                                 (2970, 4550)],
}
# lanes whose start blocks have no two men level along the way in and abreast: each man's own stop is the bench's;
# in the others the bench's blocks tie (which of two goes first is INFERRED, simpath.block), so only the set of stops
EACH = {('engine_crowd', 'w16'), ('engine_colgate', 'scat')}
NEAR = 1.5          # the bench's men stop up to 0.6 short of a cell centre (the walk's last frame)


@pytest.fixture(scope='module', params=sorted({b for b, _ in BENCH}))
def run(request):
    name = request.param
    m, t, _ = build.resolve(name, next(iter(build.MISSIONS[name][1])))
    s = sim.Sim(m, t)
    s.run(COLUMN_RUN)
    return name, s


def _stops(s, lane, count):
    return [(s.bodies[f'UNIT - CNV Col {column_key(lane, k)}'].x,
             s.bodies[f'UNIT - CNV Col {column_key(lane, k)}'].y) for k in range(count)]


def test_the_group_stands_in_the_benchs_block(run):
    """Every lane's men stand on the bench's spots (each spot taken once): ceil(sqrt(n)) files and the rows 40 apart,
    the front row on the point, turned with the way in, each spot snapped to its cell's centre."""
    name, s = run
    for (b, lane), want in BENCH.items():
        if b != name:
            continue
        got = _stops(s, lane, len(want))
        left = list(want)
        for k, (x, y) in enumerate(got):
            hit = [w for w in left if abs(w[0] - x) <= NEAR and abs(w[1] - y) <= NEAR]
            assert hit, (lane, k, (x, y), 'not one of the bench stops still free', left)
            left.remove(hit[0])
        if (b, lane) in EACH:
            for k, ((x, y), (bx, by)) in enumerate(zip(got, want)):
                assert abs(x - bx) <= NEAR and abs(y - by) <= NEAR, (lane, k, (x, y), (bx, by))


def test_block_files_rows_and_turn():
    """simpath.block alone: 3, 6, 10, 16 men -> 2, 3, 4, 4 files; rows BLOCK back from the point, each row centred;
    a way in from the south-west turns the block 45 degrees."""
    for n, files in ((3, 2), (6, 3), (10, 4), (16, 4)):
        starts = [(2500.0 - 30 * k, 2000.0) for k in range(n)]           # in file: the way in due east
        spots = simpath.block(starts, (3000.0, 2000.0))
        front = [q for q in spots if abs(q[0] - 3000.0) < 1e-6]
        assert len(front) == files, (n, spots)
        rows = sorted({round(q[0], 6) for q in spots}, reverse=True)
        assert rows == [3000.0 - simpath.BLOCK * r for r in range(len(rows))], (n, rows)
        for r in rows:
            ys = sorted(q[1] for q in spots if round(q[0], 6) == r)
            assert abs(sum(ys) / len(ys) - 2000.0) < 1e-6, (n, ys)
            assert all(abs(b - a - simpath.BLOCK) < 1e-6 for a, b in zip(ys, ys[1:])), (n, ys)
    starts = [(2600.0 - 30 * (k // 2) + (10 if k % 2 else -10), 2600.0 - 30 * (k // 2) - (10 if k % 2 else -10))
              for k in range(6)]
    spots = simpath.block(starts, (3000.0, 3000.0))
    u, l = (math.sqrt(0.5), math.sqrt(0.5)), (-math.sqrt(0.5), math.sqrt(0.5))
    frame = sorted((round((x - 3000.0) * u[0] + (y - 3000.0) * u[1], 6), round((x - 3000.0) * l[0] + (y - 3000.0) * l[1], 6))
                   for x, y in spots)
    assert frame == [(-40.0, -40.0), (-40.0, 0.0), (-40.0, 40.0), (0.0, -40.0), (0.0, 0.0), (0.0, 40.0)], frame
