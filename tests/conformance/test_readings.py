"""The conformance runner (ADR 0035 2): every bench's readings (experimental/cnv/checks/<bench>.readings.toml, format in
experimental/cnv/readings.py) against the plan simulator. One test per group of scenes: each scene runs once, every
reading of it is checked in that run; a reading marked mismatch is checked too (it must still not hold). Where the
engine model is not on this computer the runner runs on the plan simulator's own path: a group whose scene hands a
player to the skirmish AI is skipped (simai.NoModel), a reading marked mismatch_nomodel is checked as a mismatch."""
import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


def _load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / 'experimental' / 'cnv' / f'{name}.py')
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


readings = _load('readings')
simai = _load('simai')

GROUPS = readings.groups(readings.load_all())

MODEL = simai.available()


@pytest.fixture(scope='module')
def lib():
    return simai.model()['xmldata'].Library() if MODEL else None


def _rows_of(w):
    import build                                   # on the path once simai is loaded
    labels = [lab for _, lab in w.sim.test.counters]
    return ([t for t, _ in w.sim.series], [dict(zip(labels, v)) for _, v in w.sim.series], dict(w.sim.counters),
            build.judge(w.sim.test, w.sim.series))


def _start(lib, build, check, script='', shot_clock=False, blocks=simai.BLOCKS):
    """A scene's run at frame 0 (readings.RUN_OPTS): the player's script given to the Sim, its clock set before a frame,
    the AI brains given the blocks."""
    try:
        w = simai.run(build, check, 0, lib=lib, script=script, blocks=blocks)
    except simai.NoModel as e:
        pytest.skip(f'needs ra3model.ai: {e}')
    w.sim.shot_clock = shot_clock
    return w


def _advance(w, frames):
    try:
        w.advance(frames)
    except simai.NoModel as e:                    # the mission hands a player to the AI later
        pytest.skip(f'needs ra3model.ai: {e}')


def test_the_runner_gives_a_scene_its_run_options(lib):
    """script reaches the Sim (不打: the player's units hold fire, Sim.combat), shot_clock is set before a frame and
    the brains get the blocks."""
    build, check = GROUPS[0][0][0][:2]              # any scene of the data: the options are the runner's, not a bench's
    plain, opted = _start(lib, build, check), _start(lib, build, check, '不打', True, ())
    assert (plain.sim.combat, plain.sim.shot_clock, plain.sim.t, plain.blocks) == (True, False, 0.0, simai.BLOCKS)
    assert (opted.sim.combat, opted.sim.shot_clock, opted.sim.t, opted.blocks) == (False, True, 0.0, ())


@pytest.mark.parametrize('keys, group', GROUPS,
                         ids=[f'{g[0]["bench_file"]}:' + '+'.join(readings.label(k) for k in ks) for ks, g in GROUPS])
def test_the_bench_readings_hold_on_the_simulator(lib, keys, group):
    problems = readings.run_group(keys, group, lambda b, c, **opts: _start(lib, b, c, **opts),
                                  _advance, _rows_of, MODEL)
    assert not problems, '\n'.join(problems)
