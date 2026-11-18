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


def test_take_is_all_or_none_and_frees(tmp_path):
    p = pool(tmp_path)
    a = p.try_take(2, 'a')
    assert len(a) == 2 and p.free() == 1
    got = []
    t = threading.Thread(target=lambda: got.append(p.take(2, 'b')))
    t.start()
    time.sleep(0.3)
    assert not got and p.spare() == 1         # one free is not enough for two: it waits, holding none
    assert p.free() == 0                      # and a new job would queue behind it
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


def test_inside_a_holder_it_never_waits(tmp_path):
    p = pool(tmp_path, tokens=2)
    release, held = threading.Event(), []
    t = hold_in_thread(p, 2, release, held)
    while not held:
        time.sleep(0.01)
    env = {cp.HELD_ENV: '1'}
    t0 = time.monotonic()
    with cp.hold(6, 'golden', pool=p, env=env, say=lambda m: None) as got:
        assert got == 1 and time.monotonic() - t0 < 0.2    # pool full: the inherited share, at once
    release.set()
    t.join(5)
    p = pool(tmp_path, tokens=4)
    with cp.hold(6, 'golden', pool=p, env=env, say=lambda m: None) as got:
        # its share of one (held by its parent; here nobody) and what is free, up to two all told (T5c)
        assert got == 2 and env[cp.HELD_ENV] == '2' and p.free() == 3
        with cp.hold(3, 'simrecord record', pool=p, env=env, say=lambda m: None) as inner:
            assert inner == 2 and len(p.holders()) == 1     # the child runs inside it, taking nothing
    assert env[cp.HELD_ENV] == '1' and p.free() == 4


def test_inside_a_holder_it_never_jumps_the_queue(tmp_path):
    p = pool(tmp_path, tokens=3)
    release, held = threading.Event(), []
    t = hold_in_thread(p, 2, release, held)
    while not held:
        time.sleep(0.01)
    waiter = threading.Thread(target=lambda: p.release(p.take(2, 'queued')))
    waiter.start()
    while not p.queue():
        time.sleep(0.01)
    with cp.hold(2, 'golden', pool=p, env={cp.HELD_ENV: '1'}, say=lambda m: None) as got:
        assert got == 1 and len(p.holders()) == 2         # one is free, but a job waits for it: no widening
    release.set()
    t.join(5)
    waiter.join(5)


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
    assert not got and [r['owner'] for _, r in p.queue()] == ['timing'] and p.pending()['owner'] == 'timing'
    assert p.free() == 0               # a new job sees nothing free while the timing waits
    assert len(p.holders()) == 3       # it already holds the two that were free and waits for the third
    release.set()
    t.join(5)
    x.join(5)
    assert len(got[0]) == 3 and not p.queue() and p.pending() is None
    assert any('whole pool' in m for m in said)
    p.release(got[0])


def test_first_come_first_served_round_an_exclusive_job(tmp_path):
    """T5c 1, 2, 4: an exclusive job queues like any; the one before it gets served first, the one after it waits
    for it although a token is free; a waiter says its place and who is ahead."""
    p = pool(tmp_path, tokens=3)
    order, says = [], {}

    def job(name, n=1, exclusive=False, hold_for=None):
        def body():
            says[name] = []
            with cp.hold(n, name, exclusive=exclusive, pool=p, env={}, say=says[name].append):
                order.append(name)
                hold_for.wait(10)
        th = threading.Thread(target=body)
        th.start()
        return th

    def queued(k):
        deadline = time.monotonic() + 5
        while len(p.queue()) < k:
            assert time.monotonic() < deadline
            time.sleep(0.01)

    keep_a, keep_b, keep_s1, keep_x, keep_s2 = (threading.Event() for _ in range(5))
    ths = [job('A', 2, hold_for=keep_a), job('B', 1, hold_for=keep_b)]
    while len(order) < 2:
        time.sleep(0.01)
    ths.append(job('S1', hold_for=keep_s1))
    queued(1)
    ths.append(job('X', exclusive=True, hold_for=keep_x))
    queued(2)
    ths.append(job('S2', hold_for=keep_s2))
    queued(3)
    time.sleep(0.3)
    place = [m for m in says['S2'] if 'waits' in m][-1]
    assert 'place 3 in the queue' in place and 'S1 (pid' in place and 'X (pid' in place and 'all (exclusive)' in place
    keep_b.set()                       # one token back: S1 came first
    time.sleep(0.3)
    assert order == ['A', 'B', 'S1']
    keep_a.set()                       # two more back: X takes them, still waits for S1's; S2 does not pass it
    time.sleep(0.3)
    assert order == ['A', 'B', 'S1'] and len(p.holders()) == 3 and p.spare() == 0
    keep_s1.set()
    time.sleep(0.3)
    assert order == ['A', 'B', 'S1', 'X']
    keep_x.set()
    time.sleep(0.3)
    assert order == ['A', 'B', 'S1', 'X', 'S2']
    keep_s2.set()
    for th in ths:
        th.join(5)
    assert not p.queue() and not p.holders() and p.pending() is None


HOG = r'''"""Takes the whole pool over and over, each release followed at once by the next exclusive take (the
profile run that starved R's pytest 11-18), until the stop file appears."""
import importlib.util, os, sys, time
spec = importlib.util.spec_from_file_location('cp_hog', sys.argv[1])
cp = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cp)
p = cp.Pool(sys.argv[2], int(sys.argv[3]), poll=0.05)
while not os.path.exists(sys.argv[4]):
    with cp.hold(1, 'hog', exclusive=True, pool=p, env={}, say=lambda m: None):
        with open(sys.argv[5], 'a') as f:
            f.write('x')
        time.sleep(0.2)
'''


def test_a_small_job_is_not_starved_by_one_exclusive_take_after_another(tmp_path):
    """T5c 3 (the cpupool before it: red -- the small job never gets in while the hog runs)."""
    (tmp_path / 'hog.py').write_text(HOG, encoding='utf-8')
    folder, stop, cycles = tmp_path / 'cpu', tmp_path / 'stop', tmp_path / 'cycles'
    hog = subprocess.Popen([sys.executable, str(tmp_path / 'hog.py'),
                            os.path.join(ROOT, 'experimental', 'testbench', 'cpupool.py'), str(folder), '3', str(stop),
                            str(cycles)])
    got = []
    p = pool(tmp_path, tokens=3)
    try:
        deadline = time.monotonic() + 30
        while not cycles.exists():
            assert time.monotonic() < deadline and hog.poll() is None
            time.sleep(0.05)
        small = threading.Thread(target=lambda: got.append(p.take(1, 'small')), daemon=True)
        small.start()
        small.join(5)                  # some 25 of the hog's turns
        served_while_hogged = bool(got)
    finally:
        stop.write_text('')
        if got:
            p.release(got[0])          # the hog waits for the whole pool: give it back before waiting for its end
        hog.wait(30)
    small.join(10)
    if len(got) == 1 and not served_while_hogged:
        p.release(got[0])
    assert served_while_hogged, 'the small job waited 5 s behind %d exclusive takes' % len(cycles.read_text())


def test_an_older_cpupools_pending_mark_holds_the_queue_and_the_first_waiter_sets_one(tmp_path):
    """Worktrees run older copies of this file: their exclusive.json (no ticket) holds the queue here, and the first
    waiter here writes one, which those copies read as 'someone waits for the pool: take nothing'."""
    p = pool(tmp_path, tokens=2)
    os.makedirs(p.folder)
    parent = os.getppid()
    with open(p.pending_path, 'w', encoding='utf-8') as f:
        json.dump({'owner': 'old timing', 'pid': parent, 'started': cp._started(parent)}, f)
    got = []
    t = threading.Thread(target=lambda: got.append(p.take(1, 'new')))
    t.start()
    time.sleep(0.3)
    assert not got and p.free() == 0 and 'older cpupool' in p.describe()
    os.remove(p.pending_path)          # the old job got its pool and dropped the mark
    t.join(5)
    assert len(got[0]) == 1
    p.release(got[0])
    held = p.try_take(2, 'other')
    t = threading.Thread(target=lambda: got.append(p.take(1, 'new')))
    t.start()
    time.sleep(0.3)
    mark = p.pending()
    assert mark['owner'] == 'new' and mark['pid'] == os.getpid() and mark['ticket'] == p.queue()[0][0]
    p.release(held)
    t.join(5)
    assert p.pending() is None
    p.release(got[-1])


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
    """R 11-18 (T5b): family_close's pytest waited for tokens, then ended with no output at all -- pytest drops an
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


def test_every_take_is_logged_for_the_daily_report(tmp_path):
    """work/logs/cpupool_waits.jsonl: one line a take, the format daily_report.flow() reads."""
    log = tmp_path / 'waits.jsonl'
    p = cp.Pool(str(tmp_path / 'cpu'), 2, poll=0.05, log=str(log))
    t0 = time.time()
    with cp.hold(2, 'me', pool=p, env={}, say=lambda m: None):
        pass
    with cp.hold(1, 'timing', exclusive=True, pool=p, env={}, say=lambda m: None):
        pass
    rows = [json.loads(line) for line in log.read_text(encoding='utf-8').splitlines()]
    assert [(r['owner'], r['n']) for r in rows] == [('me', 2), ('timing', 2)]
    assert all(set(r) == {'t', 'owner', 'n', 'waited'} and r['t'] >= t0 - 1 and r['waited'] >= 0 for r in rows)
    quiet = cp.Pool(str(tmp_path / 'cpu2'), 2, poll=0.05)
    assert quiet.log is None            # a pool in a test's folder never writes the machine's log


def test_a_single_process_does_not_queue(tmp_path):
    p = pool(tmp_path, tokens=2)
    said = []
    with cp.hold(1, 'pytest', pool=p, env={}, say=said.append, wait=False) as got:
        assert got == 1 and len(p.holders()) == 1          # a free token, nobody waiting: it takes it
    held = p.try_take(2, 'other')
    t0 = time.monotonic()
    with cp.hold(1, 'pytest', pool=p, env={}, say=said.append, wait=False) as got:
        assert got == 1 and time.monotonic() - t0 < 0.5 and len(p.holders()) == 2    # full: runs without one
    assert 'runs without a CPU token' in said[-1]
    p.release(held[:1])
    waiter = threading.Thread(target=lambda: p.release(p.take(2, 'queued')))
    waiter.start()
    while not p.queue():
        time.sleep(0.01)
    with cp.hold(1, 'pytest', pool=p, env={}, say=said.append, wait=False):
        assert len(p.holders()) == 1                       # one is free, but a job waits for it: not taken
    p.release(held)
    waiter.join(5)


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
