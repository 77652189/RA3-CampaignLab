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


# ---- InvisibilityBroadcastUpdate (sim.Sim.cloaked; simunits.invis_broadcast): bench 2026-11-05 engine_stealth a / b
# (checks/engine_stealth.py, docs/engine/stealth.md 1-2, 4). A mirage tank carrying GENERIC_TOGGLE_STATE (a script gives
# it) hides the friendly infantry / vehicles within 175; its enemy cannot pick them, the attack order stays and fires
# the moment the aura goes off. The series is read in percent at each second (the bench's seconds run ahead of the
# simulator's, so the times are not compared, the values are).
def _stealth_series(check):
    import build
    import sim
    m, t, _ = build.resolve('engine_stealth', check)
    return {c: [row[1][i] for row in sim.Sim(m, t).run(24.0).series] for i, (c, _) in enumerate(t.counters)}


def test_invisibility_broadcast_the_aura_holds_its_guardian_at_full_health_and_the_control_dies():
    a = _stealth_series('a')
    assert a['CNV_Stealth_BaseHp'] == [100] * 25, a['CNV_Stealth_BaseHp']    # bench 光环血 100 throughout
    assert a['CNV_Stealth_HighHp'][-1] <= 10, a['CNV_Stealth_HighHp']        # bench 对照血 4 at the end
    assert a['CNV_Stealth_Bits'] == [0] * 25                                # STEALTHED never reads (stealth.md 5)


def test_invisibility_broadcast_fire_stops_the_moment_it_hides_and_the_order_waits_for_the_aura_to_drop():
    a, b = _stealth_series('a'), _stealth_series('b')
    order, late = a['CNV_Stealth_OrderHp'], b['CNV_Stealth_SwitchHp']
    assert order[:5] == [100] * 5 and 50 <= order[-1] <= 56, order        # aura off 6 s, on again: bench 54 from s15
    assert order[-1] == order[-3] and order[11] > order[-1], order        # stopped dead once the aura came back
    assert late[0] == 100 and 47 <= late[-1] <= 56 and late[-1] == late[-4], late   # bench 后隐血 50 from s10


def test_invisibility_behavior_a_house_given_garrison_can_stealth_by_script_is_shot_like_a_plain_one():
    b = _stealth_series('b')                                              # bench 隐楼血 = 明楼血 (98 at s4 .. 45)
    assert b['CNV_Stealth_HiddenHp'] == b['CNV_Stealth_PlainHp'] and b['CNV_Stealth_HiddenHp'][-1] < 80, b
