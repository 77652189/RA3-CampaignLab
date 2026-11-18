r"""The machine's CPU tokens (coordinator 11-18, T5): every heavy job on this machine -- a pytest run's workers, a
simrecord recording, golden, simbench_peak -- takes tokens from one pool before it works, so the lines running side by
side never ask for more cores than there are (11-18 01:48: three lines' tests and recordings at once, CPU at 100%,
every run slow and every timing noisy). The same idea as the bench slots (slots.py, run_queue): a job that finds the
tokens taken waits its turn, it does not fail.

    python -X utf8 experimental/testbench/cpupool.py                     # who holds what, who waits, how many are free
    python -X utf8 experimental/testbench/cpupool.py run -n 2 -- <command ...>
    python -X utf8 experimental/testbench/cpupool.py run --exclusive -- <command ...>    # a clean timing

The pool: os.cpu_count() less the reserve for the game and the bench, which take none -- 2 cores on 8 and more (1
below) while a bench slot is held (run_queue's lock, slots.py) or a game runs, 1 while neither (user 11-18: 7 tokens
on this machine then, 6 while the bench works; a change of state takes back no token already held, the pool only
counts as full until enough are given back). RA3_CPU_TOKENS sets the size. A token is a file
<shared>\locks\cpu\<k>.json written with O_EXCL (owner, pid, the process's start time); a token whose process is gone
(or whose pid now names another process) is free, so a killed job frees its tokens.

First come, first served (T5c, 11-18: a profile run took the whole pool scene after scene -- each release followed at
once by the next exclusive take -- and R's pytest, wanting one token, waited 40 minutes without ever getting it). A job
that waits writes a ticket <shared>\locks\cpu\q-<time>-<pid>-<n>.json; only the first live ticket may take, so a job
never passes one that came before it -- an exclusive one neither passes nor is passed. The first ticket also writes
exclusive.json, the old pending mark: a copy of this file from before T5c (another worktree) takes nothing while that
mark is someone else's, and an old exclusive job's mark holds the queue here the same way.

hold(n, owner, at_least) is the one door:
  * at the top of a process tree it queues, waits until it is first and `at_least` tokens are free (default n), and
    takes min(n, free) of them all at once (all or none, so two jobs never each sit on half of what they need);
  * one request takes at most CAP (2; RA3_CPU_CAP) tokens: asking for more takes CAP and says so -- the whole pool only
    by asking for it (exclusive), so no line's `-n 6` sits on the machine by accident;
  * a process whose ancestor holds tokens (RA3_CPU_HELD in its environment, set while tokens are held) queues for
    nothing: it uses the inherited share and adds what is free now, up to CAP all told, and only while nobody waits
    (so a pytest worker's golden test may widen, but never ahead of the queue and never behind its own parent);
  * exclusive=True (timing: simbench_peak, simrecord time, a --save-durations run) queues like any job and, once first,
    takes every token as it comes free: the reading is the machine's alone.
A waiting job says so on stderr -- its place in the queue and who is ahead, again when its place changes and every
REMIND seconds -- says when it got its tokens, and says so when it is interrupted (T5b: pytest drops a Ctrl+C during
configure without a word, so a run interrupted in the wait looked like one that gave no result). It yields how many
tokens the job may use -- a recorder's -j, a pytest run's workers. RA3_CPU_POOL=0 turns the pool off (every hold
yields n at once). Every take adds a line to <main checkout>\work\logs\cpupool_waits.jsonl ({"t", "owner", "n",
"waited"}; the daily report's flow section reads it).

pytest: tests/conftest.py holds the run's workers (-n; more than CAP runs CAP workers) for the whole session and
gives each worker a share of one; a single-process run (no -n, -n 0) does not queue: it takes the free token when
nobody waits, else runs without one (wait=False: one core at most, which the reserve absorbs -- 11-18 a 0.4 s run
waited two minutes for a full pool); RA3_CPU_EXCLUSIVE=1 makes the run exclusive (the coordinator's timed full run).
affected_tests --cmd prints -n from the tokens free now, at most CAP.
"""
import argparse
import contextlib
import datetime
import importlib.util
import itertools
import json
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
HELD_ENV = 'RA3_CPU_HELD'
POLL = 3.0
REMIND = 300.0      # a waiting job says so again every 5 minutes, so a log shows it still waits
CAP = 2             # tokens one request may take (T5c); the whole pool only by asking for it (exclusive)
MARK = 'exclusive.json'
_SEQ = itertools.count(1)
_slots = None


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _slots_mod():
    global _slots
    if _slots is None:
        _slots = _load('_slots_for_cpupool', os.path.join(HERE, 'slots.py'))
    return _slots


def _default_dir():
    return os.path.join(_slots_mod().LOCKS, 'cpu')


def _default_log():
    """<main checkout>\\work\\logs\\cpupool_waits.jsonl (labpaths.WORK: a line's worktree writes the main one's)."""
    try:
        return os.path.join(_slots_mod().labpaths.WORK, 'logs', 'cpupool_waits.jsonl')
    except Exception:       # noqa: BLE001 -- a bare clone: no log
        return None


def reserve(cpus, busy=True):
    """Cores left out of the pool: while the bench or a game runs 2 on 8 cores and more, else 1; 1 while neither."""
    return (2 if cpus >= 8 else 1) if busy else 1


def bench_busy():
    """True while a bench slot is held (run_queue's lock, slots.py) or a game runs (any RA3, the user's other games);
    True too when that cannot be read (the safe side: the smaller pool)."""
    try:
        sl = _slots_mod()
        tasks = sl._tasks()
        if any(sl.holder(i, tasks) for i in range(1, sl.SLOTS + 1)):
            return True
        return any(sl.GAME.match(name) or sl.USER_GAME.match(name) for name in tasks.values())
    except Exception:       # noqa: BLE001 -- no process list, no locks folder: assume the bench works
        return True


def size(env=None, busy=None, cpus=None):
    """Tokens in the pool: RA3_CPU_TOKENS, else the cores less the reserve (busy: bench_busy() now), at least 1."""
    env = os.environ if env is None else env
    if env.get('RA3_CPU_TOKENS'):
        return max(1, int(env['RA3_CPU_TOKENS']))
    cpus = cpus or os.cpu_count() or 1
    busy = bench_busy() if busy is None else busy
    return max(1, cpus - reserve(cpus, busy))


def cap(env=None):
    """Tokens one request may take: RA3_CPU_CAP, else CAP."""
    env = os.environ if env is None else env
    return max(1, int(env.get('RA3_CPU_CAP') or CAP))


def enabled(env=None):
    env = os.environ if env is None else env
    return env.get('RA3_CPU_POOL', '1') not in ('0', 'off', 'no')


def _started(pid):
    """The process's start time (pid reuse check), or None when it is gone or cannot be read."""
    try:
        import psutil
        return psutil.Process(pid).create_time()
    except Exception:       # noqa: BLE001 -- psutil missing, NoSuchProcess, AccessDenied: no start time
        return None


def _alive(rec):
    pid = rec.get('pid')
    if not isinstance(pid, int):
        return False
    started = _started(pid)
    if started is None:
        try:
            import psutil   # noqa: F401
            return False    # psutil is here and says the process is gone
        except ImportError:
            return True     # cannot tell: keep it (a stale token can be removed by hand)
    return rec.get('started') is None or abs(rec['started'] - started) < 1.0


def _wants(rec):
    return 'all (exclusive)' if rec.get('exclusive') else str(rec.get('need', '?'))


class Pool:
    """The tokens under `folder` (default <shared>\\locks\\cpu). `tokens` fixes the size; else it is size() now,
    or, for tests, cpus less reserve(cpus, busy()) with `busy` a function standing for the bench."""

    def __init__(self, folder=None, tokens=None, poll=POLL, busy=None, cpus=None, log=None):
        # the wait log (one line a take, the daily report's flow section reads it): the machine's pool only -- a
        # pool in a test's folder (or under a test's RA3_SHARED) writes none unless given one
        self.log = log if log is not None else (None if folder or os.environ.get('RA3_SHARED') else _default_log())
        self.folder = folder or _default_dir()
        self.fixed = tokens
        self.poll = poll
        self.busy = busy
        self.cpus = cpus
        self._seen = None       # (when, size): the bench is looked at once a poll, not at every count

    @property
    def tokens(self):
        if self.fixed:
            return self.fixed
        if self.busy is not None:
            cpus = self.cpus or os.cpu_count() or 1
            return max(1, cpus - reserve(cpus, self.busy()))
        now = time.monotonic()
        if self._seen is None or now - self._seen[0] >= self.poll:
            self._seen = (now, size(cpus=self.cpus))
        return self._seen[1]

    def path(self, k):
        return os.path.join(self.folder, f'{k}.json')

    @property
    def pending_path(self):
        return os.path.join(self.folder, MARK)

    def _read(self, path):
        try:
            with open(path, encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            return None
        except (OSError, ValueError):
            return {'owner': '?', 'pid': None, 'busy': True}     # being written this instant: held

    def _live(self, path):
        """The record at path if its holder lives (a dead holder's file is removed), else None."""
        rec = self._read(path)
        if rec is None:
            return None
        if rec.get('busy') or _alive(rec):
            return rec
        with contextlib.suppress(OSError):
            os.remove(path)
        return None

    def _names(self):
        try:
            return os.listdir(self.folder)
        except FileNotFoundError:
            return []

    def holders(self):
        """{k: record} of every held token (any number: a token taken while the pool was larger still counts)."""
        ks = sorted(int(n[:-5]) for n in self._names() if n.endswith('.json') and n[:-5].isdigit())
        return {k: rec for k in ks if (rec := self._live(self.path(k)))}

    def queue(self):
        """[(ticket file name, record)] of the jobs waiting, first come first."""
        names = sorted(n for n in self._names() if n.startswith('q-') and n.endswith('.json'))
        return [(n, rec) for n in names if (rec := self._live(os.path.join(self.folder, n)))]

    def pending(self):
        """The live pending mark (exclusive.json): the first waiter's, or an old exclusive job's; or None."""
        return self._live(self.pending_path)

    def spare(self):
        """Tokens not held now (less than 0 while the pool is smaller than what was taken when it was larger)."""
        return self.tokens - len(self.holders())

    def ahead(self, ticket=None):
        """The records of the jobs before `ticket` (a ticket file name; None: a job not queued yet, so everyone):
        earlier tickets, and an old exclusive job's pending mark."""
        q = self.queue()
        out = [rec for name, rec in q if ticket is None or name < ticket]
        mark = self.pending()
        if mark and mark.get('ticket') != ticket and mark.get('ticket') not in {name for name, _ in q}:
            out.append(dict(mark, exclusive=True))
        return out

    def free(self):
        """Tokens a new job could take now: 0 while anyone waits (it would queue behind them)."""
        return 0 if self.ahead() else max(0, self.spare())

    def _record(self, owner, **extra):
        pid = os.getpid()
        return dict(owner=owner, pid=pid, started=_started(pid),
                    since=datetime.datetime.now().isoformat(timespec='seconds'), **extra)

    def _write(self, path, owner, **extra):
        os.makedirs(self.folder, exist_ok=True)
        try:
            fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            if self._live(path) is not None:
                return False
            try:
                fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            except FileExistsError:
                return False
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            json.dump(self._record(owner, **extra), f)
        return True

    def _drop(self, path):
        rec = self._read(path)
        if rec and rec.get('pid') == os.getpid():
            with contextlib.suppress(OSError):
                os.remove(path)

    def try_take(self, n, owner):
        """Up to n of the tokens not held now, without waiting or queueing; the list of token numbers taken."""
        want = min(n, self.spare())
        got, k = [], 0
        while len(got) < want and k < self.tokens + 64:
            k += 1
            if self._write(self.path(k), owner):
                got.append(k)
        over = len(self.holders()) - self.tokens
        if over > 0:            # another job took between the count and the take: give back what is too many
            back, got = got[len(got) - min(over, len(got)):], got[:len(got) - min(over, len(got))]
            self.release(back)
        return got

    def release(self, got):
        for k in got:
            self._drop(self.path(k))

    def _enqueue(self, owner, need, exclusive):
        name = f'q-{time.time_ns():020d}-{os.getpid()}-{next(_SEQ)}.json'
        while not self._write(os.path.join(self.folder, name), owner, need=need, exclusive=exclusive):
            name = f'q-{time.time_ns():020d}-{os.getpid()}-{next(_SEQ)}.json'
        return name

    def take(self, n, owner, at_least=None, say=None, exclusive=False):
        """Queue; once first, wait until at_least (default n) tokens are free and take min(n, free) all at once --
        exclusive: every token as it comes free; the token numbers. Never waits for more than the pool holds."""
        t0 = time.monotonic()
        want = max(1, n)
        need = max(1, min(want if at_least is None else at_least, want))
        ticket = self._enqueue(owner, need, exclusive)
        marked = False
        got = []
        told = place = None     # when the job last said it waits (None: not yet), and the place it said
        try:
            while True:
                tokens = self.tokens
                ahead = self.ahead(ticket)
                if not ahead and not marked:
                    marked = self._write(self.pending_path, owner, ticket=ticket)
                    if not marked:
                        continue        # an old exclusive job marked it this instant: it is ahead
                if not ahead:
                    if exclusive:
                        got += self.try_take(tokens - len(got), owner)
                        if len(got) >= tokens:
                            break
                    elif self.spare() >= min(need, tokens):
                        got = self.try_take(min(want, tokens), owner)
                        if len(got) >= min(need, tokens):
                            break
                        self.release(got)       # someone took one between the count and the take: all or none
                        got = []
                if say and (told is None or place != len(ahead) + 1 or time.monotonic() - told >= REMIND):
                    again = '' if told is None else f'still ({time.monotonic() - t0:.0f} s) '
                    what = 'the whole pool' if exclusive else f'{min(need, tokens)} of {tokens} CPU tokens'
                    queue = (f'place {len(ahead) + 1} in the queue, ahead: ' +
                             '; '.join(f'{r.get("owner")} (pid {r.get("pid")}) wants {_wants(r)}' for r in ahead)
                             if ahead else 'first in the queue')
                    say(f'cpupool: {owner} {again}waits for {what}, {queue} ({self.describe()})')
                    told, place = time.monotonic(), len(ahead) + 1
                time.sleep(self.poll)
            if told is not None and say:
                say(f'cpupool: {owner} got {len(got)} CPU tokens after {time.monotonic() - t0:.0f} s')
            self.note(owner, len(got), time.monotonic() - t0)
            return got
        except BaseException as e:
            self.release(got)
            if isinstance(e, KeyboardInterrupt) and say:
                say(f'cpupool: {owner} was interrupted (Ctrl+C) after waiting {time.monotonic() - t0:.0f} s for '
                    f'{"the whole pool" if exclusive else f"{need} CPU tokens"}; it took none and stops '
                    f'({self.describe()})')
            raise
        finally:
            self._drop(os.path.join(self.folder, ticket))
            if marked:
                self._drop(self.pending_path)

    def note(self, owner, n, waited):
        """One line in the wait log: {"t": unix seconds when taken, "owner", "n": tokens taken, "waited": seconds}."""
        if not self.log:
            return
        with contextlib.suppress(OSError):
            os.makedirs(os.path.dirname(self.log), exist_ok=True)
            with open(self.log, 'a', encoding='utf-8') as f:
                f.write(json.dumps(dict(t=round(time.time(), 1), owner=owner, n=n, waited=round(waited, 1))) + '\n')

    def take_all(self, owner, say=None):
        """Queue for the whole pool; once first, take every token as it comes free; the token numbers."""
        return self.take(1, owner, say=say, exclusive=True)

    def describe(self):
        hs = self.holders()
        by = {}
        for rec in hs.values():
            key = (rec.get('owner'), rec.get('pid'))
            by[key] = by.get(key, 0) + 1
        parts = [f'{o} (pid {p}) {c}' for (o, p), c in sorted(by.items(), key=lambda kv: str(kv[0]))]
        q = self.queue()
        if q:
            parts.append('queue: ' + ', '.join(f'{i}. {r.get("owner")} (pid {r.get("pid")}) wants {_wants(r)}'
                                               for i, (_, r) in enumerate(q, 1)))
        p = self.pending()
        if p and p.get('ticket') is None:
            parts.append(f'exclusive pending (an older cpupool): {p.get("owner")} (pid {p.get("pid")})')
        tokens = self.tokens
        return f'{max(0, tokens - len(hs))} of {tokens} free; ' + ('; '.join(parts) if parts else 'nobody holds any')


def _say(msg):
    print(msg, file=sys.stderr, flush=True)


@contextlib.contextmanager
def hold(n, owner, at_least=None, exclusive=False, pool=None, env=None, say=_say, wait=True):
    """Hold CPU tokens for the with-block (see the module text); yields how many this job may use. Sets
    RA3_CPU_HELD to that in `env` (default os.environ) for the block, so child processes run inside it.
    wait=False: one process, no queue -- the free token if nobody waits, else it runs without one (yields 1)."""
    env = os.environ if env is None else env
    n = max(1, int(n))
    if not enabled(env):
        yield n
        return
    pool = pool or Pool()
    limit = cap(env)
    inherited = env.get(HELD_ENV)
    got = []
    try:
        if inherited:
            share = max(1, int(inherited))
            if exclusive:
                say(f'cpupool: {owner} wants the whole pool but runs inside a job holding {share}: '
                    'its timing shares the machine')
            want = n if exclusive else min(n, max(share, limit))
            if want > share and pool.free() > 0:    # free() is 0 while anyone waits: a child never jumps the queue
                got = pool.try_take(want - share, owner)
            use = share + len(got) if exclusive else min(n, share + len(got))
        elif exclusive:
            got = pool.take_all(owner, say)
            use = len(got)
        elif not wait:
            # one process that does not queue (a single-process pytest): the free token if nobody waits for it, else
            # none -- it runs on the reserve's core rather than wait minutes for a run of seconds
            got = pool.try_take(1, owner) if pool.free() > 0 else []
            if got:
                pool.note(owner, 1, 0.0)
            else:
                say(f'cpupool: {owner} runs without a CPU token: none free and it does not queue ({pool.describe()})')
            use = 1
        else:
            if n > limit:
                say(f'cpupool: {owner} asks for {n} CPU tokens; one request takes at most {limit} '
                    '(exclusive -- RA3_CPU_EXCLUSIVE=1 for pytest -- for the whole pool)')
                n = limit
            got = pool.take(n, owner, at_least, say)
            use = len(got)
        before = env.get(HELD_ENV)
        env[HELD_ENV] = str(use)
        try:
            yield use
        finally:
            if before is None:
                env.pop(HELD_ENV, None)
            else:
                env[HELD_ENV] = before
    finally:
        pool.release(got)


def free_now(env=None, pool=None):
    """Tokens a new job could take now (0 while anyone waits; the pool's size when the pool is off)."""
    env = os.environ if env is None else env
    if not enabled(env):
        return size(env)
    return (pool or Pool()).free()


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    sub = ap.add_subparsers(dest='cmd')
    r = sub.add_parser('run', help='hold tokens while a command runs')
    r.add_argument('-n', type=int, default=1)
    r.add_argument('--exclusive', action='store_true')
    r.add_argument('--owner', default=None)
    r.add_argument('command', nargs=argparse.REMAINDER)
    a = ap.parse_args(argv)
    if a.cmd == 'run':
        cmd = a.command[1:] if a.command[:1] == ['--'] else a.command
        if not cmd:
            ap.error('run: no command')
        with hold(a.n, a.owner or os.path.basename(cmd[0]), exclusive=a.exclusive):
            return subprocess.run(cmd).returncode
    pool = Pool()
    print(f'{pool.tokens} CPU tokens in {pool.folder}: {pool.describe()}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
