"""engine_aibasedef aibdi1 / aibdi0 / aibdi2 (D round 132): a StaticDefense team of four Peacekeepers beside the
AI's yard, no enemy, its micro state 8 (idle) from the team's construction; four of the AI's AlliedBaseDefense 80-90
west of them (missions/aibasedef_bench.idle_mission).

Bench 11-13 (counters 进炮塔 炮塔数 步兵数; the teams host's order log, work/re/d132_whenidle.md):
  aibdi1  EnterBaseDefenses + WhenIdle on:  0 4 4 @ s1 | 1 @ s2-s5 | 2 @ s6-s55. The enter orders come from the
          base-defense routine (d131 section 2) only: 4 at frame 50 (all to turret 1), 3 at frame 98 (turret 2).
  aibdi0  WhenIdle off:                     0 @ s1-s3 | 1 @ s4-s55
  aibdi2  EnterBaseDefenses off:            0 @ s1-s3 | 1 @ s4-s55
          In both controls the base-defense routine sends NO order; the one man inside comes from 4 enter orders
          at frame 80 from another routine (near the micro manager's construction, not read), the same in both:
          a path neither switch gates. So the WhenIdle branch is told apart by the order's source, not the counter.
"""
import pytest

from test_simai_bench_b import lib, _probe_run, pytestmark  # noqa: F401


def test_both_switches_on_the_idle_team_goes_into_the_turrets(lib):
    """aibdi1: inside to the end (bench from s2), into the AI's turrets."""
    w, rows = _probe_run('aibdi1', lib, 56.0)
    got = {t: r['进炮塔'] for (t, _), r in zip(w.sim.series, rows)}
    assert all(got[t] >= 1 for t in range(15, 56)), got
    entries = [e for e in w.garrison.log if not e[3]]
    assert entries and all(e[2].startswith('UNIT - CNV AI Turret ') for e in entries)


@pytest.mark.xfail(strict=True, raises=AssertionError,
                   reason='bench: orders at frame 50 (the team built in state 8 at the start: s1 is handed to the AI '
                          'at the start) and 2 inside from s6; model: one man at s12.5 (after the wake) and 1 inside. '
                          'work/re/d132_whenidle.md')
def test_both_switches_on_timing_and_count(lib):
    w, rows = _probe_run('aibdi1', lib, 56.0)
    got = {t: r['进炮塔'] for (t, _), r in zip(w.sim.series, rows)}
    assert [got[t] for t in range(1, 56)] == [0] + [1] * 4 + [2] * 50, got


@pytest.mark.parametrize('build', ['aibdi0', 'aibdi2'])
@pytest.mark.xfail(strict=True, raises=AssertionError,
                   reason='bench: one man inside from s4 via an enter order no switch gates (frame 80, another '
                          'routine, not read); the model has only the switch-gated routines, so none goes in. '
                          'work/re/d132_whenidle.md')
def test_either_switch_off_one_man_still_goes_in(lib, build):
    """aibdi0 / aibdi2: 1 inside from s4 to s55 (bench), by the ungated path."""
    w, rows = _probe_run(build, lib, 56.0)
    got = {t: r['进炮塔'] for (t, _), r in zip(w.sim.series, rows)}
    assert all(got[t] == 1 for t in range(4, 56)), got


@pytest.mark.parametrize('build', ['aibdi0', 'aibdi2'])
def test_either_switch_off_the_base_defense_routine_sends_nobody(lib, build):
    """The model's switch-gated routine: with either switch off no garrison entry in state 8 (bench: no order from the
    base-defense routine in either control)."""
    w, _ = _probe_run(build, lib, 56.0)
    assert [e for e in w.garrison.log if not e[3]] == []
