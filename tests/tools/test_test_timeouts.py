"""Exercise the layer timeout and token recovery after an abrupt pytest exit."""
import importlib.util
import os
from pathlib import Path
import subprocess
import sys
import time

import pytest

ROOT = Path(__file__).resolve().parents[2]
PROBE_ENV = 'RA3_TEST_TIMEOUT_PROBE'
PROBE_ID = 'tests/tools/test_test_timeouts.py::test_timeout_probe_sleeps'

_spec = importlib.util.spec_from_file_location('_cpupool_for_timeout_probe',
                                               ROOT / 'experimental' / 'testbench' / 'cpupool.py')
cpupool = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(cpupool)


@pytest.mark.skipif(os.environ.get(PROBE_ENV) != '1', reason='only run in the timeout subprocess')
def test_timeout_probe_sleeps():
    time.sleep(10)


def test_layer_timeout_names_hang_and_reclaims_cpu_token(tmp_path):
    env = dict(os.environ, RA3_SHARED=str(tmp_path), RA3_CPU_POOL='1', RA3_CPU_TOKENS='1',
               RA3_CPU_EXCLUSIVE='0', PYTEST_ADDOPTS='', RA3_TEST_TIMEOUT_SCALE='0.02', **{PROBE_ENV: '1'})
    env.pop(cpupool.HELD_ENV, None)  # the child must acquire its own token in the isolated pool
    # The tools limit scales from 120 s to 2.4 s. Without the collected mark, the sleep finishes under --timeout.
    result = subprocess.run(
        [sys.executable, '-X', 'utf8', '-m', 'pytest', '-n', '0', '-p', 'no:cacheprovider', '-v',
         '--timeout=3000', '--timeout-method=thread', PROBE_ID],
        cwd=ROOT, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, encoding='utf-8', timeout=30,
    )
    output = result.stdout
    assert result.returncode == 1, output
    assert PROBE_ID in output and '++++ Timeout ++++' in output, output

    pool = cpupool.Pool(str(tmp_path / 'locks' / 'cpu'), tokens=1)
    # The abrupt exit leaves the child's token record behind. The pool must recognize that its owner is gone.
    assert Path(pool.path(1)).is_file(), output
    assert pool.free() == 1
