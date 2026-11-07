"""A4's bench checks judged in the plan simulator (experimental/cnv/simbench.py, docs/story/sim-vs-bench-a4.md): the ones
the simulator can stand in for pass on the current plan and map, and fail when the player does nothing (so they
are judging something); a reading the simulator has no rule for is listed as SKIP, never as PASS."""
import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
# loaded by file: simbench.py puts the cnv folders on the path itself (no new sys.path edit here: guard G4's ceiling)
_spec = importlib.util.spec_from_file_location('simbench', ROOT / 'experimental' / 'cnv' / 'simbench.py')
simbench = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(simbench)


@pytest.mark.parametrize('check', ['detour', 'queue', 'melt', 'smoke', 'smash', 'win'])
def test_the_simulators_version_of_the_check_holds(check):
    status, lines = simbench.run(check)
    assert status == 0, '\n'.join(lines)


@pytest.mark.parametrize('check', ['detour', 'queue', 'melt'])
def test_it_fails_when_the_player_builds_no_wall(check):
    """Mutation: the wall of the ice order is not made -- the check must say so."""
    status, lines = simbench.run(check, script=[])
    assert status == 1 and any(x.startswith('FAIL') for x in lines), '\n'.join(lines)


def _sim_run(build_name, check, until):
    import build
    import sim
    m, t, _ = build.resolve(build_name, check)
    return sim.Sim(m, t).run(until)


def test_r1_lifetime_as_the_bench():
    """R1 (sim.Sim.expire): bench 2026-11-07 `cnv_check engine_life frames` -- a 30 s wall made by a script in frame 1
    is seen by 451 frames' scripts, the area count drops with it (墙A 451451); a 5.5 s core lives 83 frames' and its
    wall 450 (墙B 83450)."""
    a, b, _ = _sim_run('engine_life', 'frames', 50.0).series[-1][1]
    assert (a, b) == (451451, 83450)


def test_a_counter_the_simulator_cannot_read_is_skipped_not_passed():
    status, lines = simbench.run('smash')
    assert any(x.startswith('SKIP 目标墙血量') for x in lines), '\n'.join(lines)
    assert not any(x.startswith('PASS 目标墙血量') for x in lines)
