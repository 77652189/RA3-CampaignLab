"""T7: every test has its layer's limit (experimental/testbench/time_budget.py TEST_TIMEOUT, given by tests/conftest.py);
one that passes it is red, named, and its run's CPU token comes back. The child runs use a pool in a temporary folder
(RA3_SHARED), as tests/tools/test_cpupool.py does, so they neither wait on nor disturb the lines' real jobs."""
import importlib.util
import json
import os
import subprocess
import sys
import time

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _load(name, rel):
    spec = importlib.util.spec_from_file_location(name, os.path.join(ROOT, *rel.split('/')))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


tb = _load('_time_budget_under_test', 'experimental/testbench/time_budget.py')
cp = _load('_cpupool_for_timeouts', 'experimental/testbench/cpupool.py')

PROBE = 'RA3_TIMEOUT_PROBE'
PROBE_ID = 'tests/tools/test_timeouts.py::test_probe_sleeps_past_its_limit'


def test_each_layer_has_its_limit():
    replays = {'tests/conformance/test_readings.py': 'game', 'tests/test_sim.py': 'game'}
    got = {p: tb.timeout_layer(p, replays) for p in [
        'tests/modules/test_a.py', 'tests/tools/test_a.py', 'tests/content/test_a.py', 'tests/guards/test_a.py',
        'tests/test_maps.py', 'tests/test_sim.py', 'tests/conformance/test_readings.py', 'tests/golden/test_g.py']}
    assert got == {'tests/modules/test_a.py': 'modules', 'tests/tools/test_a.py': 'tools',
                   'tests/content/test_a.py': 'content', 'tests/guards/test_a.py': 'guards',
                   'tests/test_maps.py': 'other', 'tests/test_sim.py': 'replay',
                   'tests/conformance/test_readings.py': 'replay', 'tests/golden/test_g.py': 'other'}
    assert tb.timeout_for('tests/guards/test_a.py', {}, env={}) == tb.TEST_TIMEOUT['guards']
    assert tb.timeout_for('tests/guards/test_a.py', {}, env={tb.TIMEOUT_SCALE_ENV: '0.5'}) == \
        tb.TEST_TIMEOUT['guards'] / 2
    assert tb.timeout_for('tests/guards/test_a.py', {}, env={tb.TIMEOUT_SCALE_ENV: '0'}) == 0


def test_this_test_has_the_tools_limit(request):
    scale = float(os.environ.get(tb.TIMEOUT_SCALE_ENV) or 1)
    assert request.node.get_closest_marker('timeout').args == (tb.TEST_TIMEOUT['tools'] * scale,)


@pytest.mark.skipif(not os.environ.get(PROBE), reason='run by the tests below in a child pytest')
def test_probe_sleeps_past_its_limit():
    folder = os.path.join(os.environ['RA3_SHARED'], 'locks', 'cpu')
    holders = []
    for f in os.listdir(folder):
        if f[0].isdigit():
            with open(os.path.join(folder, f), encoding='utf-8') as fh:
                holders.append(json.load(fh)['pid'])
    with open(os.environ[PROBE], 'w', encoding='utf-8') as fh:
        json.dump({'holders': holders}, fh)
    time.sleep(60)


def _run_probe(tmp_path, workers):
    report = tmp_path / 'probe.json'
    env = dict(os.environ, RA3_SHARED=str(tmp_path), RA3_CPU_TOKENS='3', PYTEST_ADDOPTS='',
               **{PROBE: str(report), tb.TIMEOUT_SCALE_ENV: '0.02'})     # tools: 120 s -> 2.4 s
    env.pop(cp.HELD_ENV, None)
    env.pop('RA3_CPU_EXCLUSIVE', None)
    t0 = time.time()
    out = subprocess.run([sys.executable, '-X', 'utf8', '-m', 'pytest', '-n', str(workers), '-p', 'no:cacheprovider',
                          '-q', PROBE_ID], cwd=ROOT, env=env, capture_output=True, text=True, timeout=300)
    took = time.time() - t0
    text = out.stdout + out.stderr
    assert report.exists(), text[-3000:]                 # the probe ran, holding the run's token(s)
    held = json.loads(report.read_text(encoding='utf-8'))['holders']
    assert held, text[-3000:]
    assert out.returncode != 0, text[-3000:]             # red: the 60 s sleep did not finish
    assert took < 50, (took, text[-3000:])
    assert not cp.Pool(str(tmp_path / 'locks' / 'cpu'), 3).holders()      # its token is free again
    return text


def test_a_test_past_its_limit_ends_a_single_run_named(tmp_path):
    text = _run_probe(tmp_path, 0)
    assert 'Timeout' in text and 'test_probe_sleeps_past_its_limit' in text, text[-3000:]


def test_a_test_past_its_limit_ends_its_worker_named(tmp_path):
    pytest.importorskip('xdist')
    text = _run_probe(tmp_path, 1)
    assert 'crashed while running' in text and 'test_probe_sleeps_past_its_limit' in text, text[-3000:]
