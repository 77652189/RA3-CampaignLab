"""experimental/testbench/cpupool.py (T5): the machine's CPU tokens. Every test here uses a pool in a temporary folder
(never the real <shared>\\locks\\cpu) and an explicit environment, so it neither waits on nor disturbs the lines'
real jobs; the pytest test runs a child pytest with RA3_SHARED pointed at a temporary folder."""
import importlib.util
import json
import os
import subprocess
import sys
import re
import threading
import time
from queue import Queue
from types import SimpleNamespace

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_spec = importlib.util.spec_from_file_location('_cpupool_under_test',
                                               os.path.join(ROOT, 'experimental', 'testbench', 'cpupool.py'))
cp = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(cp)

WAIT_LIMIT = 60  # deadlock guard for synchronization


def pool(tmp_path, tokens=3):
    return cp.Pool(str(tmp_path / 'cpu'), tokens, poll=0.05)


def wait_until(condition, description):
    deadline = time.monotonic() + WAIT_LIMIT
    while not condition():
        assert time.monotonic() < deadline, description
        time.sleep(0.01)


def unexpected_queue(*args, **kwargs):
    pytest.fail('this request must not enter the queue')


def on_wait(monkeypatch, check):
    """Run the check at the pool's retry boundary, after one attempt to acquire."""
    def sleep(_):
        check()

    monkeypatch.setattr(cp, 'time', SimpleNamespace(monotonic=time.monotonic, time_ns=time.time_ns, sleep=sleep))


def test_size_leaves_the_reserve():
    assert cp.size({'RA3_CPU_TOKENS': '5'}) == 5
    assert cp.reserve(8) == 2 and cp.reserve(4) == 1
    cpus = os.cpu_count() or 1
    assert cp.size({}, busy=True) == max(1, cpus - cp.reserve(cpus))
    # user 11-18 (T5c): while the bench lock is free and no game runs, one core is left out, not two
    assert cp.size({}, busy=False, cpus=8) == 7 and cp.size({}, busy=True, cpus=8) == 6
    assert cp.size({}, busy=False, cpus=4) == 3 and cp.size({}, busy=False, cpus=1) == 1


class FakeSlots:
    SLOTS = 2
    GAME = re.compile(r'^ra3_1\.\d+\.game$', re.I)
    USER_GAME = re.compile(r'^gamemd\.exe$', re.I)

    def __init__(self, tasks, held=()):
        self.tasks, self.held = tasks, set(held)

    def _tasks(self):
        return dict(self.tasks)

    def holder(self, i, tasks=None):
        return {'owner': 'bench'} if i in self.held else None


def test_bench_busy_reads_the_bench_lock_and_the_games(monkeypatch):
    def busy(tasks, held=()):
        monkeypatch.setattr(cp, '_slots', FakeSlots(tasks, held))
        return cp.bench_busy()
    assert busy({1: 'python.exe'}) is False
    assert busy({1: 'python.exe'}, held=[2]) is True            # someone holds a bench slot (run_queue's lock)
    assert busy({1: 'ra3_1.12.game'}) is True                    # a game runs (the user's, or a bench one)
    assert busy({1: 'gamemd.exe'}) is True                       # the user's Red Alert 2

    class Broken(FakeSlots):
        def _tasks(self):
            raise OSError('no process list')
    monkeypatch.setattr(cp, '_slots', Broken({}))
    assert cp.bench_busy() is True                               # cannot tell: the smaller pool


def test_the_pool_follows_the_bench_and_takes_back_nothing(tmp_path):
    """7 tokens while the bench is idle, 6 while it works; the change interrupts no holder: the pool only counts as
    full until enough come back."""
    state = {'busy': False}
    p = cp.Pool(str(tmp_path / 'cpu'), poll=0.05, busy=lambda: state['busy'], cpus=8)
    assert p.tokens == 7
    first = [p.try_take(2, f'job{i}') for i in range(3)] + [p.try_take(2, 'job3')]
    assert [len(g) for g in first] == [2, 2, 2, 1] and p.free() == 0
    state['busy'] = True                                         # the bench starts
    assert p.tokens == 6 and len(p.holders()) == 7 and p.spare() == -1 and p.free() == 0
    assert p.try_take(1, 'late') == []                           # nothing for a new job ...
    p.release(first[3])
    assert len(p.holders()) == 6 and p.free() == 0               # ... until one more than the overshoot is back
    p.release(first[2][:1])
    assert p.free() == 1 and len(p.try_take(2, 'late')) == 1
    state['busy'] = False                                        # the bench is done: one more
    assert p.tokens == 7 and p.free() == 1


def test_one_request_takes_at_most_two(tmp_path):
    p = pool(tmp_path, tokens=6)
    said = []
    with cp.hold(4, 'wide', pool=p, env={}, say=said.append) as got:
        assert got == 2 and len(p.holders()) == 2
    assert any('at most 2' in m for m in said)
    with cp.hold(4, 'wide', pool=p, env={'RA3_CPU_CAP': '3'}, say=said.append) as got:
        assert got == 3
    with cp.hold(1, 'timing', exclusive=True, pool=p, env={}, say=said.append) as got:
        assert got == 6                                          # the whole pool only by asking for it


def test_take_is_all_or_none_and_frees(tmp_path, monkeypatch):
    p = pool(tmp_path)
    a = p.try_take(2, 'a')
    assert len(a) == 2 and p.free() == 1
    def waiting():
        assert p.spare() == 1  # one free is not enough for two: it waits, holding none
        assert p.free() == 0   # and a new job would queue behind it
        p.release(a)

    on_wait(monkeypatch, waiting)
    got = p.take(2, 'b')
    assert len(got) == 2 and p.free() == 1
    p.release(got)
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


def test_hold_waits_its_turn_and_says_so(tmp_path, monkeypatch):
    p = pool(tmp_path, tokens=2)
    held = p.try_take(2, 'other')
    said = []

    def waiting():
        assert len(p.holders()) == 2 and p.spare() == 0
        p.release(held)

    on_wait(monkeypatch, waiting)
    env = {}
    with cp.hold(1, 'me', pool=p, env=env, say=said.append) as got:
        assert got == 1 and env[cp.HELD_ENV] == '1'
    assert said and 'waits for 1 of 2' in said[0] and 'other' in said[0]
    assert 'got 1 CPU tokens after' in said[-1]          # a log shows the wait ended (R 11-18 could not tell)
    assert cp.HELD_ENV not in env and p.free() == 2      # released, the environment as it was


def test_an_interrupted_wait_says_so_and_takes_nothing(tmp_path, monkeypatch):
    p = pool(tmp_path, tokens=2)
    p.try_take(2, 'other')
    said = []

    def interrupt(_):
        raise KeyboardInterrupt
    monkeypatch.setattr(cp.time, 'sleep', interrupt)
    with pytest.raises(KeyboardInterrupt):
        with cp.hold(1, 'me', pool=p, env={}, say=said.append):
            pass
    assert 'waits for 1 of 2' in said[0] and 'interrupted' in said[-1] and 'took none' in said[-1]
    assert len(p.holders()) == 2 and all(r['owner'] == 'other' for r in p.holders().values())


def test_a_long_wait_says_again(tmp_path, monkeypatch):
    p = pool(tmp_path, tokens=1)
    p.try_take(1, 'other')
    said, clock = [], [0.0]
    monkeypatch.setattr(cp.time, 'monotonic', lambda: clock[0])

    def tick(_):
        clock[0] += 200.0
        if clock[0] >= 700:
            p.release([1])
    monkeypatch.setattr(cp.time, 'sleep', tick)
    with cp.hold(1, 'me', pool=p, env={}, say=said.append):
        pass
    assert [s.split(' waits')[0] for s in said if 'waits' in s] == ['cpupool: me', 'cpupool: me still (400 s)']
    assert said[-1] == 'cpupool: me got 1 CPU tokens after 800 s'


def test_inside_a_holder_it_never_waits(tmp_path, monkeypatch):
    p = pool(tmp_path, tokens=2)
    held = p.try_take(2, 'other')
    monkeypatch.setattr(p, '_enqueue', unexpected_queue)
    env = {cp.HELD_ENV: '1'}
    with cp.hold(6, 'golden', pool=p, env=env, say=lambda m: None) as got:
        assert got == 1 and len(p.holders()) == 2    # pool full: the inherited share
    p.release(held)
    p = pool(tmp_path, tokens=4)
    monkeypatch.setattr(p, '_enqueue', unexpected_queue)
    with cp.hold(6, 'golden', pool=p, env=env, say=lambda m: None) as got:
        # its share of one (held by its parent; here nobody) and what is free, up to two all told (T5c)
        assert got == 2 and env[cp.HELD_ENV] == '2' and p.free() == 3
        with cp.hold(3, 'simrecord record', pool=p, env=env, say=lambda m: None) as inner:
            assert inner == 2 and len(p.holders()) == 1     # the child runs inside it, taking nothing
    assert env[cp.HELD_ENV] == '1' and p.free() == 4


def test_inside_a_holder_it_never_jumps_the_queue(tmp_path, monkeypatch):
    p = pool(tmp_path, tokens=3)
    held = p.try_take(2, 'other')

    def waiting():
        assert p.spare() == 1
        with monkeypatch.context() as nested:
            nested.setattr(p, '_enqueue', unexpected_queue)
            with cp.hold(2, 'golden', pool=p, env={cp.HELD_ENV: '1'}, say=lambda m: None) as got:
                assert got == 1 and len(p.holders()) == 2  # one is free, but a job waits for it: no widening
        p.release(held)

    on_wait(monkeypatch, waiting)
    p.release(p.take(2, 'queued'))
    assert not p.holders()


def test_exclusive_stops_new_jobs_and_gets_everything(tmp_path, monkeypatch):
    p = pool(tmp_path, tokens=3)
    held = p.try_take(1, 'other')
    said = []

    def waiting():
        assert [r['owner'] for _, r in p.queue()] == ['timing'] and p.pending()['owner'] == 'timing'
        assert p.free() == 0  # a new job sees nothing free while the timing waits
        assert sorted(r['owner'] for r in p.holders().values()) == ['other', 'timing', 'timing']
        p.release(held)

    on_wait(monkeypatch, waiting)
    got = p.take_all('timing', say=said.append)
    assert len(got) == 3 and not p.queue() and p.pending() is None
    assert any('whole pool' in m for m in said)
    p.release(got)


def test_first_come_first_served_round_an_exclusive_job(tmp_path, monkeypatch):
    """T5c 1, 2, 4: an exclusive job queues like any; the one before it gets served first, the one after it waits
    for it although a token is free; a waiter says its place and who is ahead."""
    p = pool(tmp_path, tokens=3)
    order, says = [], {}
    progress = Queue()
    retry = {name: threading.Semaphore(0) for name in ('S1', 'X', 'S2')}
    release = {name: threading.Event() for name in retry}
    stop = threading.Event()
    threads = []

    class StopJob(Exception):
        pass

    def pause_after_poll():
        name = threading.current_thread().name
        progress.put((name, 'waiting'))
        assert retry[name].acquire(timeout=WAIT_LIMIT), name
        if stop.is_set():
            raise StopJob

    on_wait(monkeypatch, pause_after_poll)

    def job(name, exclusive=False):
        def body():
            says[name] = []
            try:
                with cp.hold(1, name, exclusive=exclusive, pool=p, env={}, say=says[name].append):
                    order.append(name)
                    progress.put((name, 'acquired'))
                    assert release[name].wait(WAIT_LIMIT), name
            except StopJob:
                return
            progress.put((name, 'released'))

        th = threading.Thread(target=body, name=name, daemon=True)
        threads.append(th)
        th.start()

    def expect(name, state):
        assert progress.get(timeout=WAIT_LIMIT) == (name, state)

    a = p.try_take(2, 'A')
    b = p.try_take(1, 'B')
    assert len(a) == 2 and len(b) == 1
    try:
        job('S1')
        expect('S1', 'waiting')
        job('X', exclusive=True)
        expect('X', 'waiting')
        job('S2')
        expect('S2', 'waiting')
        place = says['S2'][-1]
        assert 'place 3 in the queue' in place and 'S1 (pid' in place and 'X (pid' in place
        assert 'all (exclusive)' in place

        p.release(b)
        retry['X'].release()           # even with one free, X cannot pass S1
        expect('X', 'waiting')
        assert p.spare() == 1
        retry['S1'].release()
        expect('S1', 'acquired')
        p.release(a)
        retry['S2'].release()          # S2 gets a chance to grab the two free tokens before X retries
        expect('S2', 'waiting')
        assert p.spare() == 2
        retry['X'].release()
        expect('X', 'waiting')
        assert sorted(r['owner'] for r in p.holders().values()) == ['S1', 'X', 'X']
        release['S1'].set()
        expect('S1', 'released')
        retry['X'].release()
        expect('X', 'acquired')
        release['X'].set()
        expect('X', 'released')
        retry['S2'].release()
        expect('S2', 'acquired')
        release['S2'].set()
        expect('S2', 'released')
    finally:
        stop.set()
        for event in release.values():
            event.set()
        for step in retry.values():
            step.release()
        for th in threads:
            th.join(WAIT_LIMIT)
    assert order == ['S1', 'X', 'S2']
    assert not p.queue() and not p.holders() and p.pending() is None


HOG = r'''"""Takes the whole pool over and over, each release followed at once by the next exclusive take (the
profile run that starved R's pytest 11-18), until the stop file appears."""
import importlib.util, sys, time
from pathlib import Path

spec = importlib.util.spec_from_file_location('cp_hog', sys.argv[1])
cp = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cp)
state = Path(sys.argv[2])
stop, cycles = state / 'stop', state / 'cycles'
requeued = state / 'hog-requeued'
p = cp.Pool(str(state / 'cpu'), 3, poll=0.05)

def wait_for(signal):
    while not (signal.exists() or stop.exists()):
        time.sleep(0.01)

def say(message):
    if 'waits for' in message and cycles.exists() and not requeued.exists():
        requeued.touch()
        wait_for(state / 'retry-hog')

while not stop.exists():
    with cp.hold(1, 'hog', exclusive=True, pool=p, env={}, say=say):
        first = not cycles.exists()
        with cycles.open('a') as f:
            f.write('x')
        if first:
            wait_for(state / 'release-hog')
'''


def test_a_small_job_is_not_starved_by_one_exclusive_take_after_another(tmp_path, monkeypatch):
    """T5c 3 (the cpupool before it: red -- the small job never gets in while the hog runs)."""
    (tmp_path / 'hog.py').write_text(HOG, encoding='utf-8')
    stop, cycles, requeued = (tmp_path / name for name in ('stop', 'cycles', 'hog-requeued'))
    queued, retry, acquired, release = (threading.Event() for _ in range(4))
    p = pool(tmp_path, tokens=3)

    def pause_small():
        assert not queued.is_set(), 'small still waits after the hog gave up its tokens'
        queued.set()
        assert retry.wait(WAIT_LIMIT), 'small was not told to retry'

    on_wait(monkeypatch, pause_small)

    def take_small():
        with cp.hold(1, 'small', pool=p, env={}, say=lambda m: None):
            acquired.set()
            assert release.wait(WAIT_LIMIT), 'small was not told to release its token'

    small = threading.Thread(target=take_small, daemon=True)
    hog = subprocess.Popen([sys.executable, str(tmp_path / 'hog.py'),
                            os.path.join(ROOT, 'experimental', 'testbench', 'cpupool.py'), str(tmp_path)])
    try:
        wait_until(cycles.exists, 'hog did not take the pool')
        small.start()
        assert queued.wait(WAIT_LIMIT), 'small did not queue behind the running hog'
        (tmp_path / 'release-hog').touch()
        # Let the hog requeue before small retries, so the hog cannot lose merely because it was slower.
        wait_until(lambda: requeued.exists() or cycles.stat().st_size >= 2, 'hog did not try to reacquire')
        assert requeued.exists() and cycles.read_text() == 'x', 'hog jumped ahead of the queued small job'
        retry.set()
        assert acquired.wait(WAIT_LIMIT), 'small was starved by the hog'
        assert hog.poll() is None and cycles.read_text() == 'x'  # small got in before the next exclusive take
        release.set()
        small.join(WAIT_LIMIT)
        assert not small.is_alive()
        (tmp_path / 'retry-hog').touch()
        wait_until(lambda: cycles.stat().st_size >= 2, 'hog did not reacquire after small released its token')
    finally:
        release.set()
        retry.set()
        stop.write_text('')
        try:
            hog.wait(10)
        except subprocess.TimeoutExpired:
            hog.kill()
            hog.wait()
        finally:
            if small.ident is not None:
                small.join(WAIT_LIMIT)
    assert hog.returncode == 0 and not small.is_alive()


def test_an_older_cpupools_pending_mark_holds_the_queue_and_the_first_waiter_sets_one(tmp_path, monkeypatch):
    """Worktrees run older copies of this file: their exclusive.json (no ticket) holds the queue here, and the first
    waiter here writes one, which those copies read as 'someone waits for the pool: take nothing'."""
    p = pool(tmp_path, tokens=2)
    os.makedirs(p.folder)
    parent = os.getppid()
    with open(p.pending_path, 'w', encoding='utf-8') as f:
        json.dump({'owner': 'old timing', 'pid': parent, 'started': cp._started(parent)}, f)

    def behind_older():
        assert p.spare() == 2 and p.free() == 0 and 'older cpupool' in p.describe()
        os.remove(p.pending_path)  # the old job got its pool and dropped the mark

    on_wait(monkeypatch, behind_older)
    got = p.take(1, 'new')
    assert len(got) == 1 and p.pending() is None
    p.release(got)

    held = p.try_take(2, 'other')

    def first_waiter():
        mark = p.pending()
        assert mark['owner'] == 'new' and mark['pid'] == os.getpid() and mark['ticket'] == p.queue()[0][0]
        p.release(held)

    on_wait(monkeypatch, first_waiter)
    got = p.take(1, 'new')
    assert p.pending() is None
    p.release(got)


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
    assert out.stdout.split() == ['2', '2'] and 'at most 2' in out.stderr      # one request: two at most (T5c)
    assert not [f for f in os.listdir(tmp_path / 'locks' / 'cpu') if f[0].isdigit()]


INTERRUPT_PLUGIN = '''"""Loaded with -p before tests/conftest.py: the first sleep (the CPU-token wait) is a Ctrl+C."""
import time


def _interrupt(_):
    raise KeyboardInterrupt


time.sleep = _interrupt
'''


def test_a_pytest_run_interrupted_while_it_waits_says_why(tmp_path):
    """A pytest run waited for tokens, then ended with no output at all -- pytest drops an
    interrupt during configure without a word (exit 2, empty stdout, only the wait line on stderr). The run must say
    it was interrupted waiting for tokens."""
    (tmp_path / 'interrupt_wait.py').write_text(INTERRUPT_PLUGIN, encoding='utf-8')
    p = cp.Pool(str(tmp_path / 'locks' / 'cpu'), 2, poll=0.05)
    taken = p.try_take(2, 'holder')       # this process holds the whole pool: the child must wait
    try:
        env = dict(os.environ, RA3_SHARED=str(tmp_path), RA3_CPU_TOKENS='2',
                   PYTHONPATH=os.pathsep.join([str(tmp_path), os.environ.get('PYTHONPATH', '')]))
        env.pop(cp.HELD_ENV, None)
        env.pop('RA3_CPU_EXCLUSIVE', None)
        # -n 1: a run with workers queues (a single-process one does not wait at all, 11-18)
        out = subprocess.run([sys.executable, '-X', 'utf8', '-m', 'pytest', '-n', '1', '-p', 'interrupt_wait', '-p',
                              'no:cacheprovider', '-q', os.path.join(ROOT, 'tests', 'tools', 'test_cpupool.py') +
                              '::test_size_leaves_the_reserve'],
                             cwd=ROOT, env=env, capture_output=True, text=True, encoding='utf-8', timeout=120)
    finally:
        p.release(taken)
    assert len(taken) == 2
    assert out.returncode == 2, out.stdout[-2000:] + out.stderr[-2000:]
    assert 'waits for 1 of 2 CPU tokens' in out.stderr
    assert 'interrupted while waiting for 1 CPU tokens' in out.stderr, out.stderr[-2000:]


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
                   'me': os.getpid(), 'workers': os.environ.get('PYTEST_XDIST_WORKER_COUNT')}, f)


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


def test_a_pytest_run_asking_for_more_runs_two_workers(tmp_path):
    """T5c: -n 3 is not an exclusive run: it holds two tokens and runs two workers, so nothing runs on a core it
    did not take."""
    pytest.importorskip('xdist')
    report = tmp_path / 'probe.json'
    env = dict(os.environ, RA3_SHARED=str(tmp_path), RA3_CPU_TOKENS='4', **{PROBE: str(report)})
    for k in (cp.HELD_ENV, 'RA3_CPU_EXCLUSIVE', 'RA3_CPU_CAP'):
        env.pop(k, None)
    out = subprocess.run([sys.executable, '-m', 'pytest', '-n', '3', '-p', 'no:cacheprovider', '-q',
                          os.path.join(ROOT, 'tests', 'tools', 'test_cpupool.py') + '::test_probe_inside_a_worker'],
                         cwd=ROOT, env=env, capture_output=True, text=True, timeout=300)
    assert out.returncode == 0, out.stdout[-2000:] + out.stderr[-2000:]
    got = json.loads(report.read_text(encoding='utf-8'))
    assert got['tokens'] == 2 and got['workers'] == '2', got
    assert 'the run uses 2 workers' in out.stderr


def test_every_take_is_logged_for_the_daily_report(tmp_path, monkeypatch):
    """work/logs/cpupool_waits.jsonl: one line a take, the format daily_report.flow() reads."""
    log = tmp_path / 'waits.jsonl'
    p = cp.Pool(str(tmp_path / 'cpu'), 2, poll=0.05, log=str(log))
    now = 1_700_000_000.0
    monkeypatch.setattr(cp.time, 'time', lambda: now)
    with cp.hold(2, 'me', pool=p, env={}, say=lambda m: None):
        pass
    with cp.hold(1, 'timing', exclusive=True, pool=p, env={}, say=lambda m: None):
        pass
    rows = [json.loads(line) for line in log.read_text(encoding='utf-8').splitlines()]
    assert [(r['owner'], r['n']) for r in rows] == [('me', 2), ('timing', 2)]
    assert all(set(r) == {'t', 'owner', 'n', 'waited'} and r['t'] == now and r['waited'] >= 0 for r in rows)
    quiet = cp.Pool(str(tmp_path / 'cpu2'), 2, poll=0.05)
    assert quiet.log is None            # a pool in a test's folder never writes the machine's log


def test_a_single_process_does_not_queue(tmp_path, monkeypatch):
    p = pool(tmp_path, tokens=2)
    said = []
    with monkeypatch.context() as no_queue:
        no_queue.setattr(p, '_enqueue', unexpected_queue)
        with cp.hold(1, 'pytest', pool=p, env={}, say=said.append, wait=False) as got:
            assert got == 1 and len(p.holders()) == 1  # a free token, nobody waiting: it takes it
        held = p.try_take(2, 'other')
        with cp.hold(1, 'pytest', pool=p, env={}, say=said.append, wait=False) as got:
            assert got == 1 and len(p.holders()) == 2  # full: runs without one
    assert 'runs without a CPU token' in said[-1]
    p.release(held[:1])

    def waiting():
        with monkeypatch.context() as no_queue:
            no_queue.setattr(p, '_enqueue', unexpected_queue)
            with cp.hold(1, 'pytest', pool=p, env={}, say=said.append, wait=False):
                assert p.spare() == 1  # one is free, but a job waits for it
        p.release(held[1:])

    on_wait(monkeypatch, waiting)
    p.release(p.take(2, 'queued'))
    assert not p.holders()


def test_a_single_process_pytest_runs_at_once_on_a_full_pool(tmp_path):
    """Coordinator 11-18: a 0.4 s single-process run waited two minutes for a full pool."""
    p = cp.Pool(str(tmp_path / 'locks' / 'cpu'), 2, poll=0.05)
    taken = p.try_take(2, 'holder')
    try:
        env = dict(os.environ, RA3_SHARED=str(tmp_path), RA3_CPU_TOKENS='2')
        for k in (cp.HELD_ENV, 'RA3_CPU_EXCLUSIVE'):
            env.pop(k, None)
        out = subprocess.run([sys.executable, '-X', 'utf8', '-m', 'pytest', '-p', 'no:cacheprovider', '-q',
                              os.path.join(ROOT, 'tests', 'tools', 'test_cpupool.py') + '::test_size_leaves_the_reserve'],
                             cwd=ROOT, env=env, capture_output=True, text=True, encoding='utf-8', timeout=120)
    finally:
        p.release(taken)
    assert out.returncode == 0, out.stdout[-2000:] + out.stderr[-2000:]
    assert 'runs without a CPU token' in out.stderr and 'waits' not in out.stderr
