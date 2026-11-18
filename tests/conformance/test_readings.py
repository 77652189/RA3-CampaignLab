"""The conformance runner (ADR 0035 2): every bench's readings (experimental/cnv/checks/<bench>.readings.toml, format in
experimental/cnv/readings.py) against the plan simulator. One test per group of scenes: each scene runs once, every
reading of it is checked in that run; a reading marked mismatch is checked too (it must still not hold). Skipped
where ra3model.ai is not on this computer."""
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

pytestmark = pytest.mark.skipif(not simai.available(), reason='no ra3model.ai (labpaths.ENGINE_MODEL)')


@pytest.fixture(scope='module')
def lib():
    return simai.model()['xmldata'].Library()


def _rows_of(w):
    import build                                   # on the path once simai is loaded
    labels = [lab for _, lab in w.sim.test.counters]
    return ([t for t, _ in w.sim.series], [dict(zip(labels, v)) for _, v in w.sim.series], dict(w.sim.counters),
            build.judge(w.sim.test, w.sim.series))


@pytest.mark.parametrize('keys, group', GROUPS,
                         ids=[f'{g[0]["bench_file"]}:' + '+'.join(b + (f'.{c}' if c else '') for b, c in k)
                              for k, g in GROUPS])
def test_the_bench_readings_hold_on_the_simulator(lib, keys, group):
    problems = readings.run_group(keys, group, lambda b, c: simai.run(b, c, 0, lib=lib),
                                  lambda w, frames: w.advance(frames), _rows_of)
    assert not problems, '\n'.join(problems)
