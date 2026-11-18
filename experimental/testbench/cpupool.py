r"""The machine's CPU tokens (coordinator 11-18, T5): every heavy job on this machine -- a pytest run's workers, a
simrecord recording, golden, simbench_peak -- takes tokens from one pool before it works, so the lines running side by
side never ask for more cores than there are (11-18 01:48: three lines' tests and recordings at once, CPU at 100%,
every run slow and every timing noisy). The same idea as the bench slots (slots.py, run_queue): a job that finds the
tokens taken waits its turn, it does not fail.

    python -X utf8 experimental/testbench/cpupool.py                     # who holds what, how many are free
    python -X utf8 experimental/testbench/cpupool.py run -n 4 -- <command ...>
    python -X utf8 experimental/testbench/cpupool.py run --exclusive -- <command ...>    # a clean timing

The pool: os.cpu_count() less RESERVE (2 on 8 cores and more, else 1) for the game and the bench, which take none;
RA3_CPU_TOKENS sets it. A token is a file <shared>\locks\cpu\<k>.json written with O_EXCL (owner, pid, the process's
start time); a token whose process is gone (or whose pid now names another process) is free, so a killed job frees
its tokens.

hold(n, owner, at_least) is the one door:
  * at the top of a process tree it waits until `at_least` tokens are free (default n, never more than the pool) and
    takes min(n, free) of them all at once (all or none, so two jobs never each sit on half of what they need);
  * a process whose ancestor holds tokens (RA3_CPU_HELD in its environment, set while tokens are held) waits for
    nothing: it uses the inherited share and adds what is free now, up to n (so a pytest worker's golden test may
    widen, but a child never queues behind its own parent);
  * exclusive=True (timing: simbench_peak, simrecord time, a --save-durations run) marks the pool pending, so no new
    job starts, and takes every token as it comes free: the reading is the machine's alone.
A waiting job says so on stderr (again every REMIND seconds), says when it got its tokens, and says so when it is
interrupted (T5b: pytest drops a Ctrl+C during configure without a word, so a run interrupted in the wait looked like
one that gave no result). It yields how many tokens the job may use -- a recorder's -j, a pytest run's workers. RA3_CPU_POOL=0 turns the pool
off (every hold yields n at once).

pytest: tests/conftest.py holds the run's workers (-n, or 1) for the whole session and gives each worker a share of
one; RA3_CPU_EXCLUSIVE=1 makes the run exclusive (the coordinator's timed full run). affected_tests --cmd prints -n
from the tokens free now.
"""
import argparse
import contextlib
import datetime
import importlib.util
import json
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
HELD_ENV = 'RA3_CPU_HELD'
POLL = 3.0
REMIND = 300.0      # a waiting job says so again every 5 minutes, so a log shows it still waits


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _default_dir():
    slots = _load('_slots_for_cpupool', os.path.join(HERE, 'slots.py'))
    return os.path.join(slots.LOCKS, 'cpu')


def reserve(cpus):
    return 2 if cpus >= 8 else 1


def size(env=None):
    """Tokens in the pool: RA3_CPU_TOKENS, else the cores less the reserve, at least 1."""
    env = os.environ if env is None else env
    if env.get('RA3_CPU_TOKENS'):
        return max(1, int(env['RA3_CPU_TOKENS']))
    cpus = os.cpu_count() or 1
    return max(1, cpus - reserve(cpus))


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


class Pool:
    """The tokens under `folder` (default <shared>\\locks\\cpu); `tokens` (default size()) of them."""

    def __init__(self, folder=None, tokens=None, poll=POLL):
        self.folder = folder or _default_dir()
        self.tokens = tokens or size()
        self.poll = poll

    def path(self, k):
        return os.path.join(self.folder, f'{k}.json')

    @property
    def pending_path(self):
        return os.path.join(self.folder, 'exclusive.json')

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

    def holders(self):
        """{k: record} of every held token."""
        return {k: rec for k in range(1, self.tokens + 1) if (rec := self._live(self.path(k)))}

    def pending(self):
        """The exclusive job waiting for the whole pool (its record), or None."""
        return self._live(self.pending_path)

    def free(self, me=None):
        """Tokens a new job could take now: 0 while another process waits for the pool exclusively."""
        p = self.pending()
        if p and p.get('pid') != (me or os.getpid()):
            return 0
        return self.tokens - len(self.holders())

    def _record(self, owner):
        pid = os.getpid()
        return dict(owner=owner, pid=pid, started=_started(pid),
                    since=datetime.datetime.now().isoformat(timespec='seconds'))

    def _write(self, path, owner):
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
            json.dump(self._record(owner), f)
        return True

    def _drop(self, path):
        rec = self._read(path)
        if rec and rec.get('pid') == os.getpid():
            with contextlib.suppress(OSError):
                os.remove(path)

    def try_take(self, n, owner):
        """Up to n free tokens now, without waiting; the list of token numbers taken."""
        got = []
        for k in range(1, self.tokens + 1):
            if len(got) >= n:
                break
            if self._write(self.path(k), owner):
                got.append(k)
        return got

    def release(self, got):
        for k in got:
            self._drop(self.path(k))

    def take(self, n, owner, at_least=None, say=None):
        """Wait until at_least (default n) tokens are free and no exclusive job is pending, then take min(n, free)
        all at once; the token numbers. Never waits for more than the pool holds."""
        n = max(1, min(n, self.tokens))
        at_least = max(1, min(n if at_least is None else at_least, n))
        t0 = time.monotonic()
        told = None             # when the job last said it waits (None: not yet)
        try:
            while True:
                if self.free() >= at_least:
                    got = self.try_take(n, owner)
                    if len(got) >= at_least:
                        if told is not None and say:
                            say(f'cpupool: {owner} got {len(got)} CPU tokens after {time.monotonic() - t0:.0f} s')
                        return got
                    self.release(got)       # someone took one between the count and the take: all or none
                if say and (told is None or time.monotonic() - told >= REMIND):
                    again = '' if told is None else f'still ({time.monotonic() - t0:.0f} s) '
                    say(f'cpupool: {owner} {again}waits for {at_least} of {self.tokens} CPU tokens '
                        f'({self.describe()})')
                    told = time.monotonic()
                time.sleep(self.poll)
        except KeyboardInterrupt:
            if say:
                say(f'cpupool: {owner} was interrupted (Ctrl+C) after waiting {time.monotonic() - t0:.0f} s for '
                    f'{at_least} CPU tokens; it took none and stops ({self.describe()})')
            raise

    def take_all(self, owner, say=None):
        """Mark the pool pending for this process, then take every token as it comes free; the token numbers."""
        told = False
        while not self._write(self.pending_path, owner):
            if not told and say:
                say(f'cpupool: {owner} waits for another exclusive job ({self.describe()})')
                told = True
            time.sleep(self.poll)
        got = []
        try:
            while len(got) < self.tokens:
                got += self.try_take(self.tokens - len(got), owner)
                if len(got) < self.tokens:
                    if not told and say:
                        say(f'cpupool: {owner} waits for the whole pool, {self.tokens - len(got)} of {self.tokens} '
                            f'tokens still held ({self.describe()})')
                        told = True
                    time.sleep(self.poll)
        except BaseException:
            self.release(got)
            raise
        finally:
            self._drop(self.pending_path)
        return got

    def describe(self):
        hs = self.holders()
        by = {}
        for rec in hs.values():
            key = (rec.get('owner'), rec.get('pid'))
            by[key] = by.get(key, 0) + 1
        parts = [f'{o} (pid {p}) {c}' for (o, p), c in sorted(by.items(), key=lambda kv: str(kv[0]))]
        p = self.pending()
        if p:
            parts.append(f'exclusive pending: {p.get("owner")} (pid {p.get("pid")})')
        return f'{self.tokens - len(hs)} free; ' + ('; '.join(parts) if parts else 'nobody holds any')


def _say(msg):
    print(msg, file=sys.stderr, flush=True)


@contextlib.contextmanager
def hold(n, owner, at_least=None, exclusive=False, pool=None, env=None, say=_say):
    """Hold CPU tokens for the with-block (see the module text); yields how many this job may use. Sets
    RA3_CPU_HELD to that in `env` (default os.environ) for the block, so child processes run inside it."""
    env = os.environ if env is None else env
    n = max(1, int(n))
    if not enabled(env):
        yield n
        return
    pool = pool or Pool()
    inherited = env.get(HELD_ENV)
    got = []
    try:
        if inherited:
            share = max(1, int(inherited))
            if exclusive:
                say(f'cpupool: {owner} wants the whole pool but runs inside a job holding {share}: '
                    'its timing shares the machine')
            if n > share:
                got = pool.try_take(n - share, owner) if pool.free() > 0 else []
            use = min(n, share + len(got)) if not exclusive else share + len(got)
        elif exclusive:
            got = pool.take_all(owner, say)
            use = len(got)
        else:
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
    """Tokens a new job could take now (the pool's size when the pool is off)."""
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
