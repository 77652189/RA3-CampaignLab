"""A run's snapshot in a file (step S 11c, docs/engine/sim-modules.md 9.2): simsnap's or simaisnap's snapshot written
to a gzip JSON file and read back in another process, so a run taken in one process goes on in another.

    {"format": "snapfile/2", "shape": shape(), "meta": {...}, "snapshot": {...}}

`meta` is the taker's (the task, where it was taken, the commit, the counts a recorder goes on from); the snapshot is
as simsnap / simaisnap took it (its own version inside: their restore refuses another, whole). A file is written to a
temporary name beside it and renamed, so a reader never meets half a file (two workers taking the same one: the last
rename wins, both whole).

Reused starts (the peak benchmark's) live under work/cache/snaps/ (`cache_dir`): kept across commits while the
snapshot's shape holds (`shape()`: simsnap's and simaisnap's VERSION and the engine model's pin -- its plug-in keeps
the brains' part); a restore that refuses one is the caller's sign to take it again."""
import gzip
import hashlib
import importlib.util
import io
import json
import os
import tempfile
import time

FORMAT = 'snapfile/2'   # 2: the shape it was taken in (review 1119u P2 #1)
HERE = os.path.dirname(os.path.abspath(__file__))


def save(path, snapshot, **meta):
    """Write `snapshot` (simsnap's / simaisnap's, JSON values) and `meta` to `path` (gzip JSON), whole or not at all,
    with the shape it was taken in (`shape()`: load refuses another). Returns the sha256 (its first 12 hex digits) of
    the bytes this call wrote -- what a result names the start it ran from by; never read back from `path`, which
    another writer may have replaced since (review 1119u P2 #2)."""
    folder = os.path.dirname(os.path.abspath(path))
    os.makedirs(folder, exist_ok=True)
    buf = io.BytesIO()
    # no time and no name in the gzip header: the same snapshot and meta make the same file, the same sha (a start
    # taken again unchanged is the same start, 11c-2)
    with gzip.GzipFile(filename='', mode='wb', fileobj=buf, mtime=0) as f:
        f.write(json.dumps({'format': FORMAT, 'shape': shape(), 'meta': meta, 'snapshot': snapshot}).encode('utf-8'))
    data = buf.getvalue()
    # a short temporary name of its own beside it (u P3 #2: '<path>.<pid>.tmp' outgrew a long path), gone if the
    # rename fails (a reader holding the file on Windows: a few tries, then the error)
    fd, tmp = tempfile.mkstemp(prefix='.snap', suffix='.tmp', dir=folder)
    try:
        with os.fdopen(fd, 'wb') as raw:
            raw.write(data)
        for k in range(RETRIES):
            try:
                os.replace(tmp, path)
                break
            except PermissionError:
                if k == RETRIES - 1:
                    raise
                time.sleep(0.2)
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)
    return hashlib.sha256(data).hexdigest()[:12]


RETRIES = 5


def load(path):
    """(meta, snapshot) of a file `save` wrote, in this shape. Another format, a file taken in another shape (another
    simsnap / simaisnap version or engine model pin -- review 1119u P2 #1: resumed under another model): an error
    naming it, before the caller writes anything."""
    with gzip.open(path, 'rt', encoding='utf-8') as f:
        d = json.load(f)
    if not isinstance(d, dict) or d.get('format') != FORMAT or set(d) != {'format', 'shape', 'meta', 'snapshot'}:
        got = d.get('format') if isinstance(d, dict) else type(d).__name__
        raise ValueError(f'snapfile.load: {path} is not a {FORMAT} file ({got!r})')
    if d['shape'] != shape():
        raise ValueError(f'snapfile.load: {path} was taken in shape {d["shape"]}, this is {shape()}')
    return d['meta'], d['snapshot']


def digest(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for block in iter(lambda: f.read(1 << 20), b''):
            h.update(block)
    return h.hexdigest()[:12]


def _labpaths():
    spec = importlib.util.spec_from_file_location(
        '_labpaths', os.path.join(os.path.dirname(HERE), 'campaign', 'labpaths.py'))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def cache_dir():
    """work/cache/snaps (the main checkout's work for a line's worktree without its own: labpaths.WORK)."""
    return os.path.join(_labpaths().WORK, 'cache', 'snaps')


def shape():
    """What a kept start's shape hangs on: '<simsnap VERSION>-<simaisnap VERSION>-<model pin, 7>'. A file named by
    another is not read (taken again)."""
    import simaisnap
    import simsnap
    with open(os.path.join(HERE, 'inventory_model.rev'), encoding='utf-8') as f:
        pin = f.read().strip()[:7]
    return f'{simsnap.VERSION}-{simaisnap.VERSION}-{pin}'


def cached(name):
    """The path of a kept start `name` (a scene and where it is taken, e.g. 'aiskrand_s_600') for this shape."""
    return os.path.join(cache_dir(), f'{name}_v{shape()}.json.gz')
