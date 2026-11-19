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
sides are recorded by the same recorder. Records are cached under work\logs\golden\ by commit (and, for uncommitted
work, by the hash of the diff), so a second run is a compare only; the oldest beyond KEEP are removed.

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
import os
import shutil
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
LAB = os.path.dirname(ROOT)
TREE = os.path.join(LAB, 'RA3-CampaignLab-golden')
SIMRECORD_REL = os.path.join('experimental', 'cnv', 'simrecord.py')
# the recorder: simrecord and the observation port it reads the world through (R3 12b), copied over the base together
RECORDER_RELS = (SIMRECORD_REL, os.path.join('experimental', 'cnv', 'engine', 'ports', 'observe.py'))
PIN_REL = 'experimental/cnv/inventory_model.rev'
TRAILER = 'golden-changed:'
KEEP = 4                       # cached record sets kept under work\logs\golden (about 130 MB each)
LOCK_STALE = 3 * 3600          # age limit for legacy locks without a process start time


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


labpaths = _load('labpaths', os.path.join(ROOT, 'experimental', 'campaign', 'labpaths.py'))
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
    texts = []
    for rel in RECORDER_RELS:
        with open(os.path.join(root, rel), 'rb') as f:
            texts.append(f.read())
    return _digest(*texts)


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
    """Serialize changes to the lock file so stale recovery cannot remove a successor's lock."""
    if os.name == 'nt':
        import ctypes
        from ctypes import wintypes

        kernel = ctypes.windll.kernel32
        kernel.CreateMutexW.restype = wintypes.HANDLE
        name = _digest(os.path.normcase(os.path.realpath(path)))
        handle = wintypes.HANDLE(kernel.CreateMutexW(None, False, ctypes.c_wchar_p('Global\\RA3Golden-' + name)))
        if not handle:
            raise ctypes.WinError()
        try:
            result = kernel.WaitForSingleObject(handle, wintypes.DWORD(0xFFFFFFFF))
            if result not in (0, 0x80):  # acquired, including when the previous owner died
                raise ctypes.WinError()
            try:
                yield
            finally:
                kernel.ReleaseMutex(handle)
        finally:
            kernel.CloseHandle(handle)
    else:
        import fcntl

        fd = os.open(os.path.dirname(path), os.O_RDONLY)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX)
            yield
        finally:
            os.close(fd)


def _stale_holder(path):
    import psutil

    with open(path, encoding='ascii', errors='replace') as f:
        fields = f.read().split()
        age = time.time() - os.fstat(f.fileno()).st_mtime

    try:
        pid, started = fields
        pid, started = int(pid), float(started)
    except ValueError:
        if age > LOCK_STALE:
            return (fields[0] if len(fields) == 1 and fields[0].isdigit() else '?'), age
        return None

    try:
        if psutil.Process(pid).create_time() == started:
            return None
    except psutil.AccessDenied:
        return None
    except psutil.NoSuchProcess:
        pass
    return pid, age


class Lock:
    """One golden run at a time on this computer (pytest-xdist workers, other lines): an O_EXCL file."""

    def __init__(self, path, wait=2.0):
        self.path, self.wait = path, wait

    def __enter__(self):
        import psutil

        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        pid = os.getpid()
        started = psutil.Process(pid).create_time()
        owner = f'{pid} {started!r}'
        while True:
            with _lock_update(self.path):
                try:
                    stale = _stale_holder(self.path)
                    if stale is not None:
                        os.remove(self.path)
                except OSError:
                    stale = None
                try:
                    f = open(self.path, 'x', encoding='ascii')
                except FileExistsError:
                    pass
                else:
                    try:
                        with f:
                            f.write(owner)
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
            os.remove(self.path)


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
    for rel in RECORDER_RELS:
        shutil.copyfile(os.path.join(root, rel), os.path.join(tree, rel))


def complete(folder, names):
    return all(os.path.exists(os.path.join(folder, n + '.gz')) or os.path.exists(os.path.join(folder, n + '.failed'))
               for n in names)


def record(code_root, names, folder, jobs):
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
    subprocess.run([sys.executable, '-X', 'utf8', os.path.join(code_root, SIMRECORD_REL), 'record', tmp,
                    '--only', *missing, '-j', str(jobs)], cwd=code_root, capture_output=True, text=True,
                   encoding='utf-8', errors='replace')
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
                return f.read()[-1500:]
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
    with Lock(os.path.join(CACHE, 'golden.lock')):
        base_dir = os.path.join(CACHE, f'c-{base[:12]}-{recorder_hash()}')
        new_dir = os.path.join(CACHE, work_key(root))
        if not complete(base_dir, names):
            prepare_tree(base, root)
            record(TREE, names, base_dir, jobs)
        if not complete(new_dir, names):
            record(root, names, new_dir, jobs)
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
        elif run.failed('base', n):
            print(f'{n:14} skip: not recordable on the base')
        else:
            d = run.difference(n)
            if d and n not in run.changed:
                bad += 1
            print(f'{n:14}', 'same' if not d else ('changed (declared): ' if n in run.changed else '') + d)
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
