"""experimental/testbench/cpupool.py (T5): the machine's CPU tokens. Every test here uses a pool in a temporary folder
(never the real <shared>\\locks\\cpu) and an explicit environment, so it neither waits on nor disturbs the lines'
real jobs; the pytest test runs a child pytest with RA3_SHARED pointed at a temporary folder."""
import importlib.util
import json
import os
import subprocess
import sys
import threading
import time

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_spec = importlib.util.spec_from_file_location('_cpupool_under_test',
                                               os.path.join(ROOT, 'experimental', 'testbench', 'cpupool.py'))
cp = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(cp)


def pool(tmp_path, tokens=3):
    return cp.Pool(str(tmp_path / 'cpu'), tokens, poll=0.05)


def hold_in_thread(p, n, release, held, **kw):
    """A holder in a thread (same pid: tokens are files, the pid only says whether the holder lives)."""
    def body():
        with cp.hold(n, 'other', pool=p, env={}, say=lambda m: None, **kw) as got:
            held.append(got)
            release.wait(10)
    t = threading.Thread(target=body)
    t.start()
    return t


def test_size_leaves_the_reserve():
    assert cp.size({'RA3_CPU_TOKENS': '5'}) == 5
    assert cp.reserve(8) == 2 and cp.reserve(4) == 1
    cpus = os.cpu_count() or 1
    assert cp.size({}) == max(1, cpus - cp.reserve(cpus))


def test_take_is_all_or_none_and_frees(tmp_path):
    p = pool(tmp_path)
    a = p.try_take(2, 'a')
    assert len(a) == 2 and p.free() == 1
    got = []
    t = threading.Thread(target=lambda: got.append(p.take(2, 'b')))
    t.start()
    time.sleep(0.3)
    assert not got and p.free() == 1          # one free is not enough for two: it waits, holding none
    p.release(a)
    t.join(5)
    assert len(got[0]) == 2 and p.free() == 1
    p.release(got[0])
    assert p.free() == 3


def test_at_least_takes_what_is_free(tmp_path):
    p = pool(tmp_path)
    a = p.try_take(2, 'a')
    assert len(p.take(3, 'b', at_least=1)) == 1   # a recorder's -j 3 starts with the one free token
    p.release(a)


def test_never_waits_for_more_than_the_pool(tmp_path):
    p = pool(tmp_path, tokens=2)
    assert len(p.take(8, 'big')) == 2


def test_a_dead_holders_token_is_free(tmp_path):
    p = pool(tmp_path)
    os.makedirs(p.folder)
    # this pid, but another start time: the pid was reused by another process, the holder is gone
    with open(p.path(1), 'w', encoding='utf-8') as f:
        json.dump({'owner': 'gone', 'pid': os.getpid(), 'started': 1.0}, f)
    with open(p.path(2), 'w', encoding='utf-8') as f:
        json.dump({'owner': 'gone', 'pid': 2 ** 30}, f)
    assert p.free() == 3 and not os.path.exists(p.path(1))


def test_hold_waits_its_turn_and_says_so(tmp_path):
    p = pool(tmp_path, tokens=2)
    release, held, said = threading.Event(), [], []
    t = hold_in_thread(p, 2, release, held)
    while not held:
        time.sleep(0.01)
    threading.Timer(0.4, release.set).start()
    t0 = time.monotonic()
    env = {}
    with cp.hold(1, 'me', pool=p, env=env, say=said.append) as got:
        waited = time.monotonic() - t0
        assert got == 1 and env[cp.HELD_ENV] == '1'
    t.join(5)
    assert waited >= 0.3 and said and 'waits for 1 of 2' in said[0] and 'other' in said[0]
    assert cp.HELD_ENV not in env and p.free() == 2      # released, the environment as it was


def test_inside_a_holder_it_never_waits(tmp_path):
    p = pool(tmp_path, tokens=3)
    release, held = threading.Event(), []
    t = hold_in_thread(p, 3, release, held)
    while not held:
        time.sleep(0.01)
    env = {cp.HELD_ENV: '1'}
    t0 = time.monotonic()
    with cp.hold(6, 'golden', pool=p, env=env, say=lambda m: None) as got:
        assert got == 1 and time.monotonic() - t0 < 0.2    # pool full: the inherited share, at once
    release.set()
    t.join(5)
    with cp.hold(6, 'golden', pool=p, env=env, say=lambda m: None) as got:
        # its share of one (held by its parent; here nobody, so all three are free) and the three free ones it adds
        assert got == 4 and env[cp.HELD_ENV] == '4' and p.free() == 0
        with cp.hold(3, 'simrecord record', pool=p, env=env, say=lambda m: None) as inner:
            assert inner == 3 and len(p.holders()) == 3     # the child runs inside it, taking nothing
    assert env[cp.HELD_ENV] == '1' and p.free() == 3


def test_exclusive_stops_new_jobs_and_gets_everything(tmp_path):
    p = pool(tmp_path, tokens=3)
    release, held = threading.Event(), []
    t = hold_in_thread(p, 1, release, held)
    while not held:
        time.sleep(0.01)
    got, said = [], []
    x = threading.Thread(target=lambda: got.append(p.take_all('timing', said.append)))
    x.start()
    time.sleep(0.3)
    assert not got and os.path.exists(p.pending_path)
    assert p.free(me=-1) == 0          # another process sees nothing free while the timing waits
    assert len(p.holders()) == 3       # it already holds the two that were free and waits for the third
    release.set()
    t.join(5)
    x.join(5)
    assert len(got[0]) == 3 and not os.path.exists(p.pending_path)
    assert any('whole pool' in m for m in said)
    p.release(got[0])


def test_off_switch(tmp_path):
    p = pool(tmp_path)
    with cp.hold(5, 'x', pool=p, env={'RA3_CPU_POOL': '0'}) as got:
        assert got == 5 and p.free() == 3


def test_run_command_holds_while_it_runs(tmp_path):
    env = dict(os.environ, RA3_SHARED=str(tmp_path), RA3_CPU_TOKENS='4')
    env.pop(cp.HELD_ENV, None)
    probe = ('import os, glob; print(os.environ["RA3_CPU_HELD"], '
             'len(glob.glob(os.path.join(os.environ["RA3_SHARED"], "locks", "cpu", "[0-9]*.json"))))')
    out = subprocess.run([sys.executable, os.path.join(ROOT, 'experimental', 'testbench', 'cpupool.py'), 'run', '-n',
                          '3', '--', sys.executable, '-c', probe], env=env, capture_output=True, text=True, timeout=60)
    assert out.returncode == 0, out.stderr
    assert out.stdout.split() == ['3', '3']
    assert not [f for f in os.listdir(tmp_path / 'locks' / 'cpu') if f[0].isdigit()]


PROBE = 'CPUPOOL_PROBE'


@pytest.mark.skipif(not os.environ.get(PROBE), reason='run by test_a_pytest_run_holds_its_workers in a child pytest')
def test_probe_inside_a_worker():
    folder = os.path.join(os.environ['RA3_SHARED'], 'locks', 'cpu')
    tokens = [f for f in os.listdir(folder) if f[0].isdigit()]
    pids = set()
    for f in tokens:
        with open(os.path.join(folder, f), encoding='utf-8') as fh:
            pids.add(json.load(fh)['pid'])
    with open(os.environ[PROBE], 'w', encoding='utf-8') as f:
        json.dump({'held': os.environ.get(cp.HELD_ENV), 'tokens': len(tokens), 'holders': sorted(pids),
                   'me': os.getpid()}, f)


def test_a_pytest_run_holds_its_workers(tmp_path):
    pytest.importorskip('xdist')
    report = tmp_path / 'probe.json'
    env = dict(os.environ, RA3_SHARED=str(tmp_path), RA3_CPU_TOKENS='3', **{PROBE: str(report)})
    env.pop(cp.HELD_ENV, None)
    env.pop('RA3_CPU_EXCLUSIVE', None)
    out = subprocess.run([sys.executable, '-m', 'pytest', '-n', '2', '-p', 'no:cacheprovider', '-q',
                          os.path.join(ROOT, 'tests', 'tools', 'test_cpupool.py') + '::test_probe_inside_a_worker'],
                         cwd=ROOT, env=env, capture_output=True, text=True, timeout=300)
    assert out.returncode == 0, out.stdout[-2000:] + out.stderr[-2000:]
    got = json.loads(report.read_text(encoding='utf-8'))
    assert got['held'] == '1'                          # the worker runs in a share of one
    assert got['tokens'] == 2 and len(got['holders']) == 1 and got['me'] not in got['holders']   # the run holds two
    assert not [f for f in os.listdir(tmp_path / 'locks' / 'cpu') if f[0].isdigit()]            # freed at the end
