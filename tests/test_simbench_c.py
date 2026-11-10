"""Engine line C's simulator-vs-bench tests (object modules, weapon effects): each takes a reading the bench made and holds
the simulator to it, so a module can be registered in inventory.BENCHED_TESTS against it. A separate file from
test_simbench.py so line C's hunks never share a file with another line's uncommitted ones."""
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
# loaded by file: simbench.py puts the cnv folders on the path itself (no new sys.path edit here: guard G4's ceiling)
_spec = importlib.util.spec_from_file_location('simbench_c', ROOT / 'experimental' / 'cnv' / 'simbench.py')
simbench = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(simbench)


def _sim_run(build_name, check, until):
    import build
    import sim
    m, t, _ = build.resolve(build_name, check)
    return sim.Sim(m, t).run(until)


# ---- RunOffMapBehavior (sim.Sim.flee_start / flee_due; simunits.run_off_map): bench 2026-11-06 engine_runoffmap
# (checks/engine_runoffmap.py, docs/engine/runoffmap.md): the peacekeeper runs to the waypoint `RunOffMap` (a, 200 off)
# or 1000 along its facing (b), is gone 3 frames after it arrives and was never dying; a structure does not run (c);
# NAMED_STOP at frame 15 leaves him standing with the status on (d). 逃帧 = frames not removed + 1000 x frames fleeing.
def test_run_off_map_the_peacekeeper_is_gone_64_and_304_frames_after_the_order_never_dying():
    a = _sim_run('engine_runoffmap', 'a', 20.0).series[-1][1]
    b = _sim_run('engine_runoffmap', 'b', 50.0).series[-1][1]
    assert (a[1], a[3]) == (64064, 15) and (b[1], b[3]) == (304304, 15), (a, b)
    assert a[2] == a[0] - 64 and b[2] == b[0] - 304, (a, b)         # 死法 = removed frames (+ 1000 x dying: none)


def test_run_off_map_a_structure_stays_and_a_stop_takes_the_run_over_with_the_status_left_on():
    c = _sim_run('engine_runoffmap', 'c', 20.0).series[-1][1]
    d = _sim_run('engine_runoffmap', 'd', 20.0).series[-1][1]
    assert c[1] == c[0] and c[2] == 0 and c[3] == 64064, c           # the plant: there all along, never fleeing
    assert d[1] == 1000 * d[0] + d[0] and d[2] == 0 and d[3] == 0, d     # stopped at 15: still there, still fleeing
