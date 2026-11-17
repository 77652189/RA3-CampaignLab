"""Engine line D's damage line in the simulator (simsweep.Sweeps: ActivateLinearDamageNugget + LinearDamageUpdate) held
to the bench: checks/engine_sweep.py engine_sweepoff (plain retail, no ra3ext), bench 2026-11-10 (work/re/handoff-d.md
rounds 12 / 16 / 17). Counters: frames from the order to the first hit of the row Hammers 150 / 250 / 350 north of the
shooter (近 / 中 / 远), and of the aimed one (瞄) or, in c, the base shooters alive (射手). Its own file so these hunks
share no file with another line's uncommitted ones."""
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
# loaded by file: simbench.py puts the cnv folders on the path itself (no new sys.path edit here: guard G4's ceiling)
_spec = importlib.util.spec_from_file_location('simbench_sweep', ROOT / 'experimental' / 'cnv' / 'simbench.py')
simbench = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(simbench)


def _series(check, until):
    import build
    import sim
    m, t, _ = build.resolve('engine_sweepoff', check)
    engine = sim.Sim(m, t)
    engine.shot_clock = True                    # the line starts on a shot: the discrete hit clock
    return engine.run(until).series


def test_linear_damage_reads_the_shooters_update_speed_a_frame_and_the_sweep_weapon():
    import build
    import sim
    import simsweep
    m, t, _ = build.resolve('engine_sweepoff', 'a')
    d = simsweep.linear_damage('CNV_Sweep', sim.Sim(m, t).own)
    assert (d['start'], d['radius'], d['length'], d['speed']) == (50.0, 10.0, 450.0, 12.0)    # Speed 60 / 5
    assert d['hits'] == [(500.0, 'EXPLOSIVE', 10.0)] and d['affects'] == {'ENEMIES'}


def test_sweep_the_line_walks_out_and_a_stop_does_not_cut_it_at_the_bench_frames():
    for check in ('a', 'b'):                    # b: NAMED_STOP 0.9 s after the order, the line already out walks on
        assert _series(check, 22.0)[-1][1] == [9, 18, 26, 2], check     # bench 12:16 / 12:21: 9 18 26 2 both


def test_sweep_a_killed_shooters_line_stops_with_it_and_the_second_ones_rows_are_hit():
    rows = {s: r for s, r in _series('c', 26.0)}
    near, mid, far, alive = rows[26]
    assert near == 9 and far - mid == 9, rows[26]          # bench 12:48: 9 / 158 / 167 -- mid / far by shooter 2
    # the killed one's line stopped: mid / far were still counting past its ~18 / 26 frames, up to shooter 2's
    assert rows[9][1] > 9 and 150 < mid <= 158, rows
    # GAP: shooter 2 (made at 'sweep spare', facing its default) is 2 frames later on the bench (158 / 167 vs 156 /
    # 165): INFERRED its turn to the target, not modelled
    assert [rows[s][3] for s in (8, 9, 10, 20, 21)] == [1, 0, 1, 1, 0]     # killed at 8.9, made at 10, deleted at 21
