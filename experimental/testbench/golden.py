r"""tests/golden (docs/engine/testing.md, ADR 0035): did a change alter what the simulator does? The fixed tasks of
experimental/cnv/simrecord.py (TASKS) are recorded frame by frame on a base commit and on this checkout, and
compared line by line (simrecord.first_difference).

    python -X utf8 experimental/testbench/golden.py            # what tests/golden would compare, and the result
    python -X utf8 experimental/testbench/golden.py --base <rev> --only heal_a ai_open

Base, recorded per commit rather than kept in the repository (a kept record is 130 MB of gzip text, carries the
retail maps' and the private engine model's behaviour into a public repository, and would be re-recorded every time
a commit means to change behaviour):
  * GOLDEN_BASE (or --base) names it;
  * else, with uncommitted changes under experimental/ the base is HEAD (the commit you are about to make against
    what it will sit on); with none, HEAD~1 (the commit against its parent).
The base is checked out in its own worktree beside this one, <LAB>\RA3-CampaignLab-golden (a sibling, so labpaths
gives it the main checkout's work\ without a junction), with this checkout's simrecord.py copied over its own: both
sides are recorded by the same recorder. Records are cached under work\logs\golden\ by commit and engine model HEAD
(and, for uncommitted work, by the hash of the diff), so a second run is a compare only; the oldest beyond KEEP are removed.

A commit that means to change behaviour says so in its message, one line per commit:
    Golden-Changed: old_heal_a ai_open        (or "Golden-Changed: all")
Every commit after the base up to HEAD is read; GOLDEN_CHANGED in the environment adds names (uncommitted work).
A declared task that differs is a skip carrying the difference, one that does not is a pass.

A task that cannot be recorded on the base (it did not exist there) is a skip; one that cannot be recorded on this
checkout is a failure. The base pinning another engine model (experimental/cnv/inventory_model.rev) than this
checkout skips everything: the two sides would run different models.
"""
import argparse
import contextlib
import hashlib
import importlib.util
import math
import os
import shutil
import socket
import subprocess
import sys
import time
import uuid

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
LAB = os.path.dirname(ROOT)
TREE = os.path.join(LAB, 'RA3-CampaignLab-golden')
SIMRECORD_REL = os.path.join('experimental', 'cnv', 'simrecord.py')
# the recorder: simrecord and the observation port it reads the world through (R3 12b), copied over the base together;
# a base without them cannot be recorded (missing_recorder)
RECORDER_RELS = (SIMRECORD_REL, os.path.join('experimental', 'cnv', 'engine', 'ports', 'observe.py'))
# what the recorder needs beside them and no world logic lives in: copied over too, whether the base has it or not
# (review 1120bb P2 #3: observe.py came to import readonly.py, and a base before it could not be recorded)
RECORDER_HELPERS = (os.path.join('experimental', 'cnv', 'engine', 'ports', 'readonly.py'),)
# the modules of experimental/cnv the recorder imports and reads off the base as it is: the base's own simulator
# (tests/tools/test_golden.py: each one the recorder files import is here or goes over with them)
RECORDER_READS = ('build', 'engine.kernel.interfaces', 'engine.kernel.module', 'retail', 'sim', 'engine.ai.core', 'engine.state.ai_snapshot', 'engine.state.snapshot', 'snapfile')
PIN_REL = 'experimental/cnv/inventory_model.rev'
TRAILER = 'golden-changed:'
KEEP = 4                       # cached record sets kept under work\logs\golden (about 130 MB each)
LOCK_STALE = 3 * 3600          # age limit when the holder cannot be verified

# The recorder must not touch .part before its identity is in the lock. A holder that dies before
# opening the gate closes the pipe, so the recorder exits without running the script.
_RECORDER_GATE = '''\
import os, runpy, sys
if sys.stdin.buffer.read(1) != b'1':
    sys.exit(1)
sys.argv = sys.argv[1:]
if not sys.flags.safe_path:
    sys.path[0] = os.path.dirname(os.path.abspath(sys.argv[0]))
runpy.run_path(sys.argv[0], run_name='__main__')
'''


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


labpaths = _load('labpaths', os.path.join(ROOT, 'experimental', 'campaign', 'labpaths.py'))
modelpin = _load('modelpin', os.path.join(ROOT, 'experimental', 'cnv', 'modelpin.py'))
simrecord = _load('simrecord', os.path.join(ROOT, SIMRECORD_REL))
CACHE = os.path.join(labpaths.WORK, 'logs', 'golden')


class Skip(Exception):
    """Nothing to compare (no engine model, the model pin moved): tests/golden skips with this reason."""


def git(root, *args, check=True):
    r = subprocess.run(['git', '-C', root, *args], capture_output=True, text=True, encoding='utf-8', timeout=600)
    if check and r.returncode:
        raise RuntimeError(f'git {" ".join(args)} in {root}: {r.stderr.strip()}')
    return r.stdout


def dirty(root):
    """Uncommitted changes (and untracked files) under experimental/: what the simulator runs is not HEAD."""
    return bool(git(root, 'status', '--porcelain', '--', 'experimental').strip())


def base_rev(root, env):
    """The commit the base side is recorded on (the module's docstring), as a full id."""
    want = env.get('GOLDEN_BASE') or ('HEAD' if dirty(root) else 'HEAD~1')
    return git(root, 'rev-parse', '--verify', want + '^{commit}').strip()


def declared(root, base, env, tasks):
    """Task names declared changed: Golden-Changed lines of the commits base..HEAD, and GOLDEN_CHANGED. 'all' is
    every task; a name that is not a task is an error (a typo would quietly declare nothing)."""
    text = git(root, 'log', '--format=%B', f'{base}..HEAD')
    names = []
    for line in text.splitlines():
        if line.strip().lower().startswith(TRAILER):
            names += line.strip()[len(TRAILER):].replace(',', ' ').split()
    names += env.get('GOLDEN_CHANGED', '').replace(',', ' ').split()
    if 'all' in names:
        return set(tasks)
    unknown = sorted(set(names) - set(tasks))
    if unknown:
        raise ValueError(f'Golden-Changed names no task: {unknown} (tasks: {sorted(tasks)})')
    return set(names)


def _digest(*parts):
    h = hashlib.sha1()
    for p in parts:
        h.update(p if isinstance(p, bytes) else p.encode('utf-8'))
        h.update(b'\0')
    return h.hexdigest()[:10]


def recorder_hash(root=ROOT):
    """The cache suffix covers the engine model HEAD, the recorder (RECORDER_RELS), its helpers and this file
    (prepare_tree: what a base gets copied in). A change to base preparation records it anew -- a `.failed` left by
    the old way is not taken as done (review 1120dd P2: the readonly.py copy fixed, the old base failure still read
    and skipped)."""
    texts = []
    for path in [os.path.join(root, rel) for rel in RECORDER_RELS + RECORDER_HELPERS] + [os.path.abspath(__file__)]:
        with open(path, 'rb') as f:
            texts.append(f.read())
    return _digest(*texts, modelpin.head(labpaths.ENGINE_MODEL) or '')


def work_key(root):
    """The cache name of this checkout's side: c-<commit> when clean, w-<commit>-<hash of the diff and the
    untracked files under experimental/> when not; with the recorder's own hash (a new recorder records anew)."""
    head = git(root, 'rev-parse', 'HEAD').strip()
    rec = recorder_hash()
    if not dirty(root):
        return f'c-{head[:12]}-{rec}'
    parts = [git(root, 'diff', 'HEAD', '--binary', '--', 'experimental')]
    for rel in sorted(git(root, 'ls-files', '--others', '--exclude-standard', '--', 'experimental').split()):
        with open(os.path.join(root, rel), 'rb') as f:
            parts += [rel, f.read()]
    return f'w-{head[:12]}-{_digest(*parts)}-{rec}'


def pin_at(root, rev):
    """The engine model commit `rev` pins, or None where it pins none."""
    r = subprocess.run(['git', '-C', root, 'show', f'{rev}:{PIN_REL}'], capture_output=True, text=True)
    return r.stdout.split()[0] if r.returncode == 0 and r.stdout.split() else None


def pin_here(root):
    try:
        with open(os.path.join(root, PIN_REL), encoding='utf-8') as f:
            return f.read().split()[0]
    except (OSError, IndexError):
        return None


@contextlib.contextmanager
def _lock_update(path):
    """Serialize read/modify/write across hosts on a file whose identity survives lock replacement."""
    with open(os.fspath(path) + '.guard', 'a+b') as guard:
        if os.name == 'nt':
            import msvcrt

            guard.seek(0)
            msvcrt.locking(guard.fileno(), msvcrt.LK_LOCK, 1)
            try:
                yield
            finally:
                msvcrt.locking(guard.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl

            fcntl.flock(guard.fileno(), fcntl.LOCK_EX)
            yield


def _process_matches(fields):
    """True for the same live process, False for a dead/reused PID, None if unverifiable."""
    import psutil

    try:
        pid, started = int(fields[0]), float(fields[1])
        if pid <= 0 or not math.isfinite(started) or started <= 0:
            return None
        return psutil.Process(pid).create_time() == started
    except (psutil.AccessDenied, ValueError, OverflowError):
        return None
    except psutil.NoSuchProcess:
        return False


def _stale_holder(path, host):
    with open(path, encoding='utf-8', errors='replace') as f:
        fields = f.read().split()
        age = time.time() - os.fstat(f.fileno()).st_mtime

    old_pid = fields[0] if fields and fields[0].isdigit() else '?'
    if len(fields) in (4, 6) and fields[2] == host:
        holder = _process_matches(fields[:2])
        recorder = _process_matches(fields[4:]) if len(fields) == 6 else False
        if holder is True or recorder is True:
            return None
        if holder is False and recorder is False:
            return old_pid, age
    return (old_pid, age) if age > LOCK_STALE else None


class Lock:
    """One golden run at a time per cache, including while its orphaned recorder runs."""

    def __init__(self, path, wait=2.0):
        self.path, self.wait = path, wait

    def __enter__(self):
        import psutil

        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        pid = os.getpid()
        started = psutil.Process(pid).create_time()
        host = socket.gethostname().casefold()
        self.owner = self.contents = f'{pid} {started!r} {host} {uuid.uuid4().hex}'
        self.recorder = None
        while True:
            with _lock_update(self.path):
                try:
                    stale = _stale_holder(self.path, host)
                    if stale is not None:
                        os.remove(self.path)
                except OSError:
                    stale = None
                try:
                    f = open(self.path, 'x', encoding='utf-8')
                except FileExistsError:
                    pass
                else:
                    try:
                        with f:
                            f.write(self.contents)
                    except BaseException:
                        with contextlib.suppress(OSError):
                            os.remove(self.path)
                        raise
                    if stale is not None:
                        old_pid, age = stale
                        print(f'golden: reclaimed stale lock (pid {old_pid}, age {age:.0f}s)', file=sys.stderr)
                    return self
            time.sleep(self.wait)

    def __exit__(self, *exc):
        with _lock_update(self.path), contextlib.suppress(OSError):
            with open(self.path, encoding='utf-8', errors='replace') as f:
                contents = f.read()
            if contents == self.contents and (self.recorder is None or self.recorder.poll() is not None):
                os.remove(self.path)

    def run_recorder(self, script, args, cwd):
        import psutil

        # Let the recorder finish its workers if the holder is interrupted or terminated.
        flags = subprocess.CREATE_NEW_PROCESS_GROUP if os.name == 'nt' else 0
        with subprocess.Popen([sys.executable, '-X', 'utf8', '-c', _RECORDER_GATE, script, *args], cwd=cwd,
                              stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                              creationflags=flags, start_new_session=os.name != 'nt') as recorder:
            self.recorder = recorder
            with _lock_update(self.path):
                with open(self.path, 'r+', encoding='utf-8') as f:
                    if f.read() != self.contents:
                        raise RuntimeError('golden: lost the lock before starting the recorder')
                    started = psutil.Process(recorder.pid).create_time()
                    self.contents = f'{self.owner} {recorder.pid} {started!r}'
                    stat = os.fstat(f.fileno())
                    f.seek(0)
                    f.write(self.contents)
                    f.truncate()
                os.utime(self.path, ns=(stat.st_atime_ns, stat.st_mtime_ns))
                recorder.stdin.write(b'1')
                recorder.stdin.close()
            recorder.wait()


def _plain_dir(path):
    """A directory that is no link or junction, holding none: safe to remove as a whole (AGENTS.md red line)."""
    if not os.path.isdir(path) or labpaths._linked(path):
        return False
    for top, dirs, _ in os.walk(path):
        if any(labpaths._linked(os.path.join(top, d)) for d in dirs):
            return False
    return True


def missing_recorder(root, rev):
    """The recorder files (RECORDER_RELS, `/`-separated) that `rev` does not have. A base before the observation port
    (R3 12b, 6755aa55) has no engine/ports/observe.py: today's simrecord reads the world only through it, and a port
    copied onto a world that predates it is not the base's own simulator -- such a base cannot be recorded."""
    out = []
    for rel in RECORDER_RELS:
        rel = rel.replace(os.sep, '/')
        if subprocess.run(['git', '-C', root, 'cat-file', '-e', f'{rev}:{rel}'], capture_output=True).returncode:
            out.append(rel)
    return out


def prepare_tree(rev, root=ROOT, tree=TREE):
    """The base worktree at `rev` with this checkout's recorder copied in. Refuses a tree holding a work\\ of its own
    (a junction there is how work\\ was emptied, 11-10): the golden tree never has one; and a base without the
    recorder's files (missing_recorder: before the observation port), before touching the tree."""
    missing = missing_recorder(root, rev)
    if missing:
        raise RuntimeError(f'the base {rev[:10]} predates the observation port (it has no {", ".join(missing)}): '
                           'the recorder reads the world through it and cannot record that base; '
                           'set GOLDEN_BASE to a commit at or after 6755aa55')
    own = labpaths.local_work_path(tree)
    if os.path.exists(own) and not labpaths.only_logs(own):
        raise RuntimeError(f'{tree} has a work\\ of its own: the golden tree must not (remove it by hand, AGENTS.md)')
    if not os.path.exists(os.path.join(tree, '.git')):
        git(root, 'worktree', 'prune')
        git(root, 'worktree', 'add', '--detach', tree, rev)
    else:
        git(tree, 'checkout', '--force', '--detach', rev)
    for rel in RECORDER_RELS + RECORDER_HELPERS:
        os.makedirs(os.path.dirname(os.path.join(tree, rel)), exist_ok=True)
        shutil.copyfile(os.path.join(root, rel), os.path.join(tree, rel))


def complete(folder, names):
    return all(os.path.exists(os.path.join(folder, n + '.gz')) or os.path.exists(os.path.join(folder, n + '.failed'))
               for n in names)


def record(code_root, names, folder, jobs, lock):
    """simrecord record of the tasks not yet in `folder`, run from `code_root`'s own simrecord.py (its code). A task
    that fails leaves <task>.failed beside its log <task>.txt."""
    missing = [n for n in names if not (os.path.exists(os.path.join(folder, n + '.gz')) or
                                        os.path.exists(os.path.join(folder, n + '.failed')))]
    if not missing:
        return
    os.makedirs(folder, exist_ok=True)
    tmp = folder + '.part'
    if os.path.isdir(tmp) and _plain_dir(tmp):
        shutil.rmtree(tmp)
    lock.run_recorder(os.path.join(code_root, SIMRECORD_REL), ['record', tmp, '--only', *missing, '-j', str(jobs)],
                      cwd=code_root)
    for n in missing:
        for ext in ('.txt', '.time.json'):
            if os.path.exists(os.path.join(tmp, n + ext)):
                os.replace(os.path.join(tmp, n + ext), os.path.join(folder, n + ext))
        gz = os.path.join(tmp, n + '.gz')
        ok = os.path.exists(gz) and os.path.exists(os.path.join(folder, n + '.time.json'))
        if ok:
            os.replace(gz, os.path.join(folder, n + '.gz'))
        else:
            open(os.path.join(folder, n + '.failed'), 'w').close()
    if _plain_dir(tmp):
        shutil.rmtree(tmp)


def prune(cache=CACHE, keep=KEEP, spare=()):
    """Remove the oldest cached record sets beyond `keep` (only c-/w- directories of this tool, never `spare`)."""
    try:
        sets = [os.path.join(cache, d) for d in os.listdir(cache) if d[:2] in ('c-', 'w-')]
    except OSError:
        return []
    sets = [d for d in sets if os.path.isdir(d) and d not in spare]
    sets.sort(key=os.path.getmtime, reverse=True)
    gone = []
    for d in sets[max(0, keep - len(spare)):]:
        if _plain_dir(d):
            shutil.rmtree(d, ignore_errors=True)
            gone.append(d)
    return gone


class Run:
    """Both sides recorded: `base` / `new` folders, `changed` (declared), and per task its difference."""

    def __init__(self, base_rev, base, new, changed, names):
        self.base_rev, self.base, self.new, self.changed, self.names = base_rev, base, new, changed, names

    def failed(self, side, name):
        folder = self.base if side == 'base' else self.new
        if not os.path.exists(os.path.join(folder, name + '.failed')):
            return None
        try:
            with open(os.path.join(folder, name + '.txt'), encoding='utf-8', errors='replace') as f:
                return f.read()[-1500:] or '(empty log)'     # '' would read as not failed (review ff P3)
        except OSError:
            return '(no log)'

    def difference(self, name):
        """None where the two records are the same, else simrecord's report of the first differing line."""
        _, differs = simrecord.first_difference(os.path.join(self.base, name + '.gz'),
                                                os.path.join(self.new, name + '.gz'))
        return differs


def records(names=None, env=None, root=ROOT, jobs=None):
    """Record what is missing on both sides (under the lock) and return the Run. Raises Skip where there is nothing
    to compare."""
    env = os.environ if env is None else env
    names = list(names or simrecord.TASKS)
    if not os.path.isdir(labpaths.ENGINE_MODEL):
        raise Skip(f'no engine model at {labpaths.ENGINE_MODEL}: the tasks need it')
    jobs = jobs or int(env.get('GOLDEN_J', '6'))
    base = base_rev(root, env)
    if pin_at(root, base) != pin_here(root):
        raise Skip(f'the engine model pin moved between the base {base[:10]} and this checkout '
                   f'({pin_at(root, base)} -> {pin_here(root)}): set GOLDEN_BASE to a commit with the same pin')
    changed = declared(root, base, env, simrecord.TASKS)
    with Lock(os.path.join(CACHE, 'golden.lock')) as lock:
        base_dir = os.path.join(CACHE, f'c-{base[:12]}-{recorder_hash()}')
        new_dir = os.path.join(CACHE, work_key(root))
        if not complete(base_dir, names):
            prepare_tree(base, root)
            record(TREE, names, base_dir, jobs, lock)
        if not complete(new_dir, names):
            record(root, names, new_dir, jobs, lock)
        prune(spare=(base_dir, new_dir))
    return Run(base, base_dir, new_dir, changed, names)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    ap.add_argument('--base', help='the base commit (GOLDEN_BASE)')
    ap.add_argument('--only', nargs='*', default=None)
    ap.add_argument('-j', type=int, default=None)
    a = ap.parse_args()
    env = dict(os.environ)
    if a.base:
        env['GOLDEN_BASE'] = a.base
    try:
        run = records(a.only, env, jobs=a.j)
    except Skip as e:
        print('skip:', e)
        return 0
    print(f'base {run.base_rev[:10]} ({run.base}) vs this checkout ({run.new}); declared changed: '
          f'{sorted(run.changed) or "none"}')
    bad = 0
    for n in run.names:
        if run.failed('new', n):
            bad += 1
            print(f'{n:14} FAILED to record here:', run.failed('new', n)[-300:])
        elif run.failed('base', n):         # nothing compared: a failure unless the change declares the task (new)
            if n not in run.changed:
                bad += 1
            print(f'{n:14} not recordable on the base' + (' (declared changed)' if n in run.changed else
                                                          ' -- nothing compared:'), run.failed('base', n)[-300:])
        else:
            d = run.difference(n)
            if d and n not in run.changed:
                bad += 1
            print(f'{n:14}', 'same' if not d else ('changed (declared): ' if n in run.changed else '') + d)
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
