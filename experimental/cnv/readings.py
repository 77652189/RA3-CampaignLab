"""Bench readings as data (ADR 0035 2): checks/<bench>.readings.toml beside the bench's check, read by one conformance
runner (tests/conformance/test_readings.py) that runs each scene once and checks every reading of it in that run.

A file is a list of [[reading]] tables:

    [[reading]]
    id = "crush_keeps_all_four_tanks_alive"            # unique in the file; the old test's name when migrated
    scene = {build = "aicrush1", check = "a", until = 35}
    bench = "坦克数 4 at s28-s33 (bench 2026-11-09)"      # what the bench read
    proves = "simai team attack: Crush -- the tanks survive the run-over"   # which module's which rule
    expect = "win(28, 33, '坦克数') == [4] * 6"         # or a list: every one must hold
    mismatch = "sim 4, 4, 3, 2, 2, 1 guards at s28-33; bench 0"   # only when the simulator does not match yet

- scene: one run, its counters once a second; until is the mission seconds the run goes to. Several readings of the
  same (build, check) share one run: it goes to the longest until and each reading sees its rows as a run to its own
  until would have given (the world advances frame by frame, so a run stopped at 35 is a prefix of one to 76).
- scenes = {name = {build, check, until}, ...} for a reading comparing runs: each name is bound to that run's rows.
- each = [{build = "aiowt", plants = 0}, ...]: one reading per entry, id[build]; build (and check / until) replace the
  scene's, the other keys are names the expressions can use. With scenes, an entry key naming a scene takes a table
  that overrides that scene's build / check / until (each = [{got = {build = "aiidle30"}}, ...]), id[the overridden
  scenes' builds]; every entry overrides at least one scene, the other keys are names as above.
- let = {name = "expression", ...}: evaluated in order before expect (lambdas welcome).
- mismatch: the reading is checked in the same run, expected not to hold (expect evaluates false); if it holds the
  runner says so (drop the mark). Write both numbers. A reading that raises (in let or expect: an index past the end,
  a second missing) is a problem, mismatch mark or not: a run that breaks is never "still off".

Expressions see: rows (list of {counter label: value}, row i ~ mission second i + 1), times (each row's mission
second), first(key, pred=None, rows=rows), vals(rows) (each row's values in counter order), win(t0, t1, key)
(the key's values at mission seconds t0..t1, asserting every second is there), counter(name, scene=None) (a script
counter's value at until, by its name in the scripts: shown on the counter display or not), verdicts(scene=None)
(the check's own expectations judged on the rows to until, build.judge: [(ok, text)]), the scene names, the
each-entry keys, and the builtins. With scenes, counter / verdicts name the scene."""
import collections
import os
import tomllib

HERE = os.path.dirname(os.path.abspath(__file__))
CHECKS = os.path.join(HERE, 'checks')
SUFFIX = '.readings.toml'
KEYS = {'id', 'scene', 'scenes', 'each', 'bench', 'proves', 'expect', 'mismatch', 'let'}
NEEDED = {'id', 'bench', 'proves', 'expect'}
SCENE_KEYS = {'build', 'check', 'until'}


class ReadingError(ValueError):
    pass


def files(folder=CHECKS):
    return sorted(os.path.join(folder, f) for f in os.listdir(folder) if f.endswith(SUFFIX))


def bench_of(path):
    """checks/engine_aicrush.readings.toml -> engine_aicrush (the check module it sits beside)."""
    return os.path.basename(path)[:-len(SUFFIX)]


def _scene(d, where):
    if not isinstance(d, dict) or set(d) - SCENE_KEYS or 'build' not in d or 'until' not in d:
        raise ReadingError(f'{where}: a scene is {{build, check, until}}, got {d!r}')
    return (d['build'], d.get('check', ''), float(d['until']))


def load(path):
    """The file's readings, `each` expanded: [{id, bench_file, scenes {name: (build, check, until)}, single, expect
    [..], let {..}, vars {..}, mismatch, bench, proves}]."""
    with open(path, 'rb') as f:
        data = tomllib.load(f)
    if set(data) - {'reading'}:
        raise ReadingError(f'{path}: only [[reading]] tables, got {sorted(set(data) - {"reading"})}')
    out, seen = [], set()
    for i, r in enumerate(data.get('reading', [])):
        where = f'{os.path.basename(path)} reading {i + 1} ({r.get("id")})'
        if set(r) - KEYS or NEEDED - set(r):
            raise ReadingError(f'{where}: unknown {sorted(set(r) - KEYS)} / missing {sorted(NEEDED - set(r))}')
        if ('scene' in r) == ('scenes' in r):
            raise ReadingError(f'{where}: one of scene / scenes')
        expect = r['expect'] if isinstance(r['expect'], list) else [r['expect']]
        for e in expect + list(r.get('let', {}).values()):
            compile(e, where, 'eval')
        for entry in r.get('each', [None]):
            one = {'bench_file': bench_of(path), 'expect': expect, 'let': dict(r.get('let', {})), 'vars': {},
                   'mismatch': r.get('mismatch'), 'bench': r['bench'], 'proves': r['proves'], 'id': r['id']}
            if 'scene' in r:
                sc = dict(r['scene'])
                if entry is not None:
                    sc.update({k: v for k, v in entry.items() if k in SCENE_KEYS})
                    one['vars'] = {k: v for k, v in entry.items() if k not in SCENE_KEYS}
                    one['id'] = f'{r["id"]}[{sc["build"]}]'
                one['scenes'], one['single'] = {'rows': _scene(sc, where)}, True
            else:
                scs = {n: dict(s) if isinstance(s, dict) else s for n, s in r['scenes'].items()}
                if entry is not None:
                    over = [k for k in entry if k in scs]
                    if not over or set(entry) & SCENE_KEYS or any(not isinstance(entry[k], dict) for k in over):
                        raise ReadingError(f'{where}: an each entry of scenes overrides a scene by name with a table '
                                           f'({sorted(scs)}), got {entry!r}')
                    for k in over:
                        scs[k].update(entry[k])
                    one['vars'] = {k: v for k, v in entry.items() if k not in scs}
                    one['id'] = f'{r["id"]}[{",".join(str(scs[k].get("build")) for k in over)}]'
                one['scenes'] = {n: _scene(s, where) for n, s in scs.items()}
                one['single'] = False
            if one['id'] in seen:
                raise ReadingError(f'{where}: id {one["id"]} twice')
            seen.add(one['id'])
            out.append(one)
    return out


def load_all(folder=CHECKS):
    return [r for p in files(folder) for r in load(p)]


def groups(readings):
    """Readings in groups that share runs (a comparison joins its scenes' groups): [(sorted run keys, readings)],
    a run key (build, check). Each group is one conformance test: its runs once, all its readings."""
    parent = {}

    def find(k):
        while parent.setdefault(k, k) != k:
            k = parent[k]
        return k
    for r in readings:
        keys = [s[:2] for s in r['scenes'].values()]
        for k in keys[1:]:
            parent[find(k)] = find(keys[0])
        find(keys[0])
    out = {}
    for r in readings:
        out.setdefault(find(next(iter(r['scenes'].values()))[:2]), []).append(r)
    res = []
    for rs in out.values():
        keys = sorted({s[:2] for r in rs for s in r['scenes'].values()})
        res.append((keys, rs))
    return sorted(res)


def untils(readings):
    """{(build, check): sorted untils the readings ask of it}."""
    out = {}
    for r in readings:
        for b, c, u in r['scenes'].values():
            out.setdefault((b, c), set()).add(u)
    return {k: sorted(v) for k, v in out.items()}


def snapshots(start, advance, rows_of, wanted):
    """Run each (build, check) once: start(build, check) -> world, advance(world, frames), rows_of(world) -> (times,
    rows, counters, verdicts). {(build, check, until): Run} for every until in wanted, the world advanced to each in
    turn: counters {script counter name: value} then, verdicts the check's own [(ok, text)] on the rows so far."""
    out = {}
    for (b, c), us in sorted(wanted.items()):
        w, done = start(b, c), 0
        for u in us:
            frames = int(u * FPS) - done
            advance(w, frames)
            done += frames
            times, rows, counters, verdicts = rows_of(w)
            out[(b, c, u)] = Run(list(times), [dict(r) for r in rows], dict(counters), list(verdicts))
    return out


Run = collections.namedtuple('Run', 'times rows counters verdicts')     # one snapshot (see snapshots)


FPS = 15     # simai.FPS (checked by tests/tools/test_readings_format.py against the simulator's)


def namespace(reading, runs):
    """The names a reading's expressions see, its runs given as {(build, check, until): Run}."""
    ns = dict(reading['vars'])
    for name, key in reading['scenes'].items():
        ns[name] = runs[key].rows

    def run_of(scene):
        if scene is None and not reading['single']:
            raise ReadingError(f'{reading["id"]}: name the scene ({sorted(reading["scenes"])})')
        return runs[reading['scenes']['rows' if scene is None else scene]]
    ns['counter'] = lambda name, scene=None: run_of(scene).counters[name]
    ns['verdicts'] = lambda scene=None: run_of(scene).verdicts
    if reading['single']:
        times, rows = runs[reading['scenes']['rows']][:2]
        ns['times'] = times

        def first(key, pred=None, rows=rows):
            pred = pred or (lambda v: v >= 1)
            return next((i for i, r in enumerate(rows) if pred(r[key])), None)

        def win(t0, t1, key):
            got = [(t, r[key]) for t, r in zip(times, rows) if t0 <= t <= t1]
            assert [t for t, _ in got] == list(range(t0, t1 + 1)), [t for t, _ in got]
            return [v for _, v in got]
        ns.update(first=first, win=win)
    else:
        def first(key, pred=None, rows=None):
            pred = pred or (lambda v: v >= 1)
            return next((i for i, r in enumerate(rows) if pred(r[key])), None)
        ns['first'] = first
    ns['vals'] = lambda rows: [list(r.values()) for r in rows]
    return ns


def check(reading, runs):
    """None when the reading is as its data says (holds, or is marked a mismatch and evaluates false); else what is
    wrong, one line. Raising is always wrong: a mismatch mark covers a run that reads otherwise, not one that breaks."""
    ns = namespace(reading, runs)
    try:
        for name, e in reading['let'].items():
            ns[name] = eval(e, ns)
        failed = next((e for e in reading['expect'] if not eval(e, ns)), None)
    except Exception as x:       # a reading that cannot be evaluated on this run (an index past the end, ...)
        return f'{reading["id"]}: {type(x).__name__}: {x}'
    if reading['mismatch']:
        return None if failed else f'{reading["id"]}: marked mismatch but now holds -- drop the mark'
    if failed is None:
        return None
    return f'{reading["id"]}: does not hold: {failed}'


def run_group(keys, readings, start, advance, rows_of):
    """Every reading of a group checked on one run per scene: [problems]."""
    runs = snapshots(start, advance, rows_of, untils(readings))
    return [p for p in (check(r, runs) for r in readings) if p]
