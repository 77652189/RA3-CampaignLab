"""Frame-by-frame record of a fixed set of simulator runs, for the ADR 0029 refactor: a pure move must leave every
frame's record identical (docs/engine/sim-layers.md "搬迁不改行为").

    python -X utf8 experimental/cnv/simrecord.py record <dir>            # every task, one subprocess each
    python -X utf8 experimental/cnv/simrecord.py time <dir>              # each task's run time again: alone, one
                                                                         # after another, the least of 3 runs
    python -X utf8 experimental/cnv/simrecord.py compare <base> <new>    # first differing line per task, then
                                                                         # each task's run time before and after
    python -X utf8 experimental/cnv/simrecord.py record <dir> --executor public|model|public@model
    python -X utf8 experimental/cnv/simrecord.py cross <public dir> <model dir>
                                                                         # the two script executors frame by frame

The times `record` writes come from runs side by side (-j), a few percent of noise and more on a loaded machine;
`time` replaces them with the least of three lone runs (docs/engine/sim-modules.md 9.3: same machine, one task a
process, the least of three), run it on both sides before explaining a slower step.

A task's record is one text line per engine frame (and one per DT tick): the frame, every body's attributes (sorted,
other bodies by name), and the Sim's observable state (log, flags, counters, timers, objectives, money, power, the
audit set, gaps, ending, series). Runs go in a subprocess with PYTHONHASHSEED=0 so set order is the same each run.
Records are gzip text under the caller's folder (work/logs/simrecord/...), never in the repository.

`--executor` runs every task with that script executor (engine/ports/scripts.py: `public`, the real one,
engine/script/executor.py, is Sim(model=False); `model`, the private model's plug-in, is Sim(model=True);
`public@model`, the public one on the model's world -- its frame clock and the simulator's model-or-not branches --
is Sim(model=True, executor='public'), so of three records one pair differs by the executor, the other by the world) and writes a
cross record instead (CrossRecorder): one line per script step, numbered by the loop's frame, of what the executor
told the world through the port and the script state it leaves. `cross` lines the two up by frame and lists, per
task, each field's first differing frame and how many frames differ: a report, never a pass/fail (the differences
are step Z's work list, judged on the bench by docs/engine/script-semantics.md)."""
import argparse
import gzip
import os
import json
import subprocess
import sys
import time


# name -> (kind, args, seconds). kind: bench = build.resolve(build, check) then Sim.run; old = the same without the
# engine model (Sim(model=False)); retail = a retail map; ai = simai.run (the skirmish AI on the map).
TASKS = {
    'retail_a02': ('retail', ('camp_a02_cannes_smith',), 60.0),
    'retail_s01': ('retail', ('camp_s01_leningradcanals_rao',), 70.0),
    'heal_a': ('bench', ('engine_heal', 'a'), 18.0),
    'passive_a': ('bench', ('engine_passivearea', 'a'), 30.0),
    'wfire_all': ('bench', ('engine_wfire', 'all'), 30.0),
    'levelvision_a': ('bench', ('engine_levelvision', 'a'), 25.0),
    'ai_crush1': ('ai', ('aicrush1', 'a'), 35.0),
    'ai_open': ('ai', ('aiopen', ''), 90.0),
    'old_heal_a': ('old', ('engine_heal', 'a'), 18.0),
    'mine_cap': ('bench', ('mineturn0', 'cap'), 30.0),
    'mine_tower': ('bench', ('aitowerinc5', None), 60.0),
}

SIM_FIELDS = ('log', 'flags', 'counters', 'timers', 'objectives', 'money', 'income', 'ending', 'used', 'unknown',
              'series', 'done', 'disabled', 'events')
SKIP_BODY = frozenset({'heal_seen', 'hurt'})   # K2: AutoHeal's last-frame health became a hurt flag (bookkeeping
                                               # nobody sees; heal_at, what it decides, is still recorded)
EXECUTORS = ('public', 'model', 'public@model')   # --executor (engine/ports/scripts.py): Sim(model=False) /
                                # Sim(model=True) / Sim(model=True, executor='public'): the public one on the model's
                                # world (its clock and model-or-not branches), so a cross against `model` is the
                                # executor alone and one against `public` the world alone
SLOWER = 0.10                  # compare flags a task whose run got more than this much slower (ADR 0029 "搬完" (d))
SHORTEST = 1.0                 # ... and only a run of at least this many seconds (shorter ones are noise)


def canon(v, depth=0):
    """A stable text for a value: other bodies by name, sets sorted, floats by repr."""
    import sim
    if isinstance(v, sim.Body):
        return 'B:' + v.name
    if isinstance(v, int) and not isinstance(v, bool) and v > 10 ** 11:
        return 'ID'                              # an id() key (follow offsets): differs run to run
    if v is None or isinstance(v, (bool, int, float, str)):
        return repr(v)
    if depth > 4:
        return '<' + type(v).__name__ + '>'
    if isinstance(v, (list, tuple)):
        return '[' + ','.join(canon(x, depth + 1) for x in v) + ']'
    if isinstance(v, (set, frozenset)):
        return '{' + ','.join(sorted(canon(x, depth + 1) for x in v)) + '}'
    if isinstance(v, dict):
        items = [(canon(k, depth + 1), canon(x, depth + 1)) for k, x in v.items()]
        return '{' + ','.join(f'{k}:{x}' for k, x in sorted(items)) + '}'
    if hasattr(v, '__dict__') and depth < 2:
        return type(v).__name__ + canon({k: x for k, x in vars(v).items() if k != 'sim'}, depth + 1)
    return '<' + type(v).__name__ + '>'


def body_state(b):
    """A body's fields as the record shows them: its own (not `modules`), and beside them the STATE fields its kernel
    modules have set -- a field moved off the body into a module records as it did on the body (step K1 on)."""
    d = {k: v for k, v in vars(b).items() if k != 'modules'}
    for m in b.modules:
        own = vars(m)
        for k in m.STATE:
            if k in own:
                if k in d:
                    raise ValueError(f'{b.name}: {type(m).__name__}.{k} is already a field of the body')
                d[k] = own[k]
    for k in getattr(type(b), 'FORWARDS', ()):     # a moved dataclass field (Body.FORWARDS, step M1): every body had
        d.setdefault(k, getattr(b, k))              # it, None where no module sets it
    return d


class Recorder:
    def __init__(self, s, out):
        self.s, self.out, self.n = s, out, 0
        self.logged = 0
        self.spent = 0.0                # seconds spent writing the record (taken off the run's time)

    def line(self, where):
        t0 = time.perf_counter()
        self._line(where)
        self.spent += time.perf_counter() - t0

    def _line(self, where):
        s = self.s
        parts = [f'{where} t={s.t!r}']
        for b in s.bodies.values():
            d = body_state(b)
            parts.append(b.name + '|' + ';'.join(f'{k}={canon(d[k])}' for k in sorted(d) if k not in SKIP_BODY))
        for f in SIM_FIELDS:
            if f == 'log':
                parts.append('log+' + canon(s.log[self.logged:]))
                self.logged = len(s.log)
            else:
                parts.append(f + '=' + canon(getattr(s, f, None)))
        parts.append('gaps=' + canon({k: v.get('n') for k, v in s.unmodeled.items()}))
        self.out.write(' || '.join(parts) + '\n')
        self.n += 1

    def attach(self):
        s = self
        sim_ = self.s
        if sim_.eng is not None:
            eng = sim_.eng
            inner = eng.step

            def step():
                s.line(f'f{eng.frame}')
                return inner()
            eng.step = step
        tick = sim_.step

        def step_tick():
            r = tick()
            s.line('tick')
            return r
        sim_.step = step_tick


class PortTap:
    """The port's World between an executor and the simulator's (simexec.SimWorld), noting each action the executor
    does (script, name, args as text): every World.action of the public executor, every World.core of the model's
    plug-in (it tells core() each action it runs, its own core ones and those it then hands to action()). Conditions
    are not noted: the plug-in answers flags, counters and timers itself, so the two ask the world different
    questions."""

    def __init__(self, inner, model):
        self.inner, self.model, self.did = inner, model, []

    def note(self, name, args, script):
        self.did.append((getattr(script, 'name', ''), name, [str(a) for a in args]))

    def condition(self, eng, name, args):
        return self.inner.condition(eng, name, args)

    def action(self, eng, name, args):
        if not self.model:
            self.note(name, args, eng.script)
        return self.inner.action(eng, name, args)

    def core(self, eng, name, args, script):
        if self.model:
            self.note(name, args, script)
        return self.inner.core(eng, name, args, script)

    def begin(self, eng):
        return self.inner.begin(eng)

    def update(self, eng):
        return self.inner.update(eng)

    def difficulty(self, side):
        return self.inner.difficulty(side)

    def assumed(self, what):
        return self.inner.assumed(what)


CROSS_FIELDS = ('did', 'flags', 'counters', 'timers', 'objectives', 'ending', 'log', 'alive')


def frames_left(due, now, fps):
    """A running timer's frames left as the game's counter table holds it (script-semantics.md 3): from the mission
    second it runs out at (Sim.timers: either executor's) and the frame's second; one that ran out reads -1, where
    the game's stops. Two places: an untaken ceil (a public timer of 2.3 s) shows as a fraction."""
    v = round((due - now) * fps, 2)
    v = max(-1, v)
    return int(v) if v == int(v) else v


class CrossRecorder:
    """The cross record (`--executor`): after each script step a line `x<frame>` -- the loop's frame the step ran on
    (the plug-in's own number before it moves it on, the public executor's frame_now()), so the n-th step of either
    has the same number -- with the actions it did (PortTap) and the script state after: flags (as 0 / 1), plain
    counters, timers (frames_left: the frames each has left, as the game's table keeps them, so the two executors'
    frame numbers being one apart does not show), objectives, the ending, the timeline's new lines, the living
    bodies' names."""

    def __init__(self, s, out):
        self.s, self.out, self.n = s, out, 0
        self.logged = 0
        self.spent = 0.0

    def attach(self):
        s = self.s
        ex = s.executor
        model = s.eng is not None and ex is s.eng
        self.tap = PortTap(ex.world, model)
        ex.world = self.tap
        inner = ex.step

        def step():
            f = ex.frame if model else s.frame_now()
            r = inner()
            self.line(f'x{f}')
            return r
        ex.step = step

    def line(self, where):
        t0 = time.perf_counter()
        s = self.s
        did, self.tap.did = self.tap.did, []
        vals = {
            'did': canon(did),
            'flags': canon({k: int(v) for k, v in s.flags.items()}),
            'counters': canon(dict(s.counters)),
            'timers': canon({k: frames_left(v, s.t, s.fps) for k, v in s.timers.items()}),
            'objectives': canon(s.objectives),
            'ending': canon(s.ending),
            'log': canon(s.log[self.logged:]),
            'alive': canon(sorted(b.name for b in s.living())),
        }
        self.logged = len(s.log)
        self.out.write(where + ' || ' + ' || '.join(f'{k}={vals[k]}' for k in CROSS_FIELDS) + chr(10))
        self.n += 1
        self.spent += time.perf_counter() - t0


def run_task(name, out, executor=None):
    """One task's run, its record written to `out`. executor: None the task's own (TASKS: old runs the public one,
    the rest the model's plug-in where it is on this computer) and the full record; 'public' / 'model' /
    'public@model' that executor for every kind and the cross record (CrossRecorder)."""
    import build
    import sim
    kind, args, until = TASKS[name]
    model = kind != 'old' if executor is None else executor in ('model', 'public@model')
    which = {'executor': 'public'} if executor == 'public@model' else {}
    make = Recorder if executor is None else CrossRecorder
    if kind == 'retail':
        import retail
        s = sim.Sim(retail.RetailMission(args[0]), model=model, **which)
        rec = make(s, out)
        rec.attach()
        t0 = time.perf_counter()
        s.run(until)
    elif kind in ('bench', 'old'):
        m, t, _ = build.resolve(*args)
        s = sim.Sim(m, t, model=model, **which)
        rec = make(s, out)
        rec.attach()
        t0 = time.perf_counter()
        s.run(until)
    elif kind == 'ai':
        import simai
        m, t, _ = build.resolve(*args)
        s = sim.Sim(m, t, 'normal', model=model, **which)
        rec = make(s, out)
        rec.attach()
        w = simai.SimAI(s, 'normal', 1, None, None, simai.BLOCKS, False)
        t0 = time.perf_counter()
        w.advance(int(until * simai.FPS))
    rec.ran = time.perf_counter() - t0 - rec.spent     # the run alone: no imports, map build or record writing
    rec.line('end')
    return s, rec


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    sub = ap.add_subparsers(dest='cmd', required=True)
    r = sub.add_parser('record')
    r.add_argument('dir')
    r.add_argument('--only', nargs='*', default=None)
    r.add_argument('-j', type=int, default=4)
    r.add_argument('--executor', choices=EXECUTORS, default=None)
    one = sub.add_parser('one')
    one.add_argument('name')
    one.add_argument('path')
    one.add_argument('--executor', choices=EXECUTORS, default=None)
    x = sub.add_parser('cross')
    x.add_argument('a')
    x.add_argument('b')
    x.add_argument('--show', type=int, default=2, help='differing frames shown in full per field')
    tm = sub.add_parser('time')
    tm.add_argument('dir')
    tm.add_argument('--only', nargs='*', default=None)
    tm.add_argument('-n', type=int, default=3, help='runs a task (the least is kept)')
    c = sub.add_parser('compare')
    c.add_argument('base')
    c.add_argument('new')
    a = ap.parse_args()
    if a.cmd == 'one':
        t0 = time.perf_counter()
        with gzip.open(a.path, 'wt', encoding='utf-8') as out:
            s, rec = run_task(a.name, out, a.executor)
        total = time.perf_counter() - t0
        with open(timing_path(a.path), 'w', encoding='utf-8') as f:
            json.dump({'total': total, 'record': rec.spent, 'run': rec.ran}, f)
        print(a.name, 'used:', ' / '.join(sorted(s.used)))
        return 0
    if a.cmd == 'cross':
        return cross(a.a, a.b, a.show)
    if a.cmd == 'time':
        return time_tasks(a.dir, a.only or list(TASKS), a.n)
    if a.cmd == 'record':
        os.makedirs(a.dir, exist_ok=True)
        names = a.only or list(TASKS)
        env = dict(os.environ, PYTHONHASHSEED='0')
        procs, failed = [], []
        pending = list(names)
        while pending or procs:
            while pending and len(procs) < a.j:
                n = pending.pop(0)
                log = open(os.path.join(a.dir, n + '.txt'), 'w', encoding='utf-8')
                p = subprocess.Popen([sys.executable, '-X', 'utf8', os.path.abspath(__file__), 'one', n,
                                      os.path.join(a.dir, n + '.gz')] +
                                     (['--executor', a.executor] if a.executor else []), env=env, stdout=log, stderr=subprocess.STDOUT)
                procs.append((n, p, log))
            n, p, log = procs[0]
            p.wait()
            log.close()
            procs.pop(0)
            if p.returncode:
                failed.append(n)
            print(n, 'ok' if not p.returncode else f'FAILED (see {n}.txt)', flush=True)
        return 1 if failed else 0
    bad = 0
    for f in sorted(os.listdir(a.base)):
        if not f.endswith('.gz'):
            continue
        other = os.path.join(a.new, f)
        if not os.path.exists(other):
            print(f[:-3], 'MISSING in', a.new)
            bad += 1
            continue
        with gzip.open(os.path.join(a.base, f), 'rt', encoding='utf-8') as x, \
                gzip.open(other, 'rt', encoding='utf-8') as y:
            n = 0
            while True:
                lx, ly = x.readline(), y.readline()
                n += 1
                if lx != ly:
                    bad += 1
                    px, py = lx.split(' || '), ly.split(' || ')
                    diff = [(i, u, v) for i, (u, v) in enumerate(zip(px, py)) if u != v][:3]
                    print(f[:-3], f'DIFFERS at line {n}: {px[0][:40]} vs {py[0][:40]}; parts', len(px), len(py))
                    for i, u, v in diff:
                        iu, iv = u.split(';'), v.split(';')
                        print('   in', u[:30], [(p, q) for p, q in zip(iu, iv) if p != q][:4] or (u[:300], v[:300]))
                    break
                if not lx:
                    print(f[:-3], 'same', n - 1, 'lines')
                    break
    timing(a.base, a.new)
    return 1 if bad else 0


def read_cross(path):
    """A cross record: {frame: {field: text}} and the frames in order."""
    got, order = {}, []
    with gzip.open(path, 'rt', encoding='utf-8') as f:
        for ln in f:
            head, *parts = ln.rstrip(chr(10)).split(' || ')
            if not head.startswith('x'):
                continue
            k = int(head[1:])
            got[k] = dict(p.split('=', 1) for p in parts)
            order.append(k)
    return got, order


def cross(da, db, show=2):
    """Two cross records' folders (`record --executor` each) frame by frame: per task the frames only one side ran,
    and per field its first differing frame, how many frames differ, the first `show` of them in full. Returns 0."""
    for f in sorted(os.listdir(da)):
        if not f.endswith('.gz'):
            continue
        name = f[:-3]
        other = os.path.join(db, f)
        if not os.path.exists(other):
            print(name, 'MISSING in', db)
            continue
        a, oa = read_cross(os.path.join(da, f))
        b, ob = read_cross(other)
        both = [k for k in oa if k in b]
        only_a, only_b = len(oa) - len(both), sum(1 for k in ob if k not in a)
        per = {}
        for k in both:
            for fld in CROSS_FIELDS:
                if a[k].get(fld) != b[k].get(fld):
                    per.setdefault(fld, []).append(k)
        span = lambda o: f'{o[0]}..{o[-1]}' if o else '-'
        print(f'{name}: frames {span(oa)} vs {span(ob)} ({len(oa)} / {len(ob)}; only in A {only_a}, only in B '
              f'{only_b}); ' + ('same' if not per else f'{len(set().union(*per.values()))} frames differ'))
        for fld in CROSS_FIELDS:
            if fld not in per:
                continue
            ks = per[fld]
            print(f'   {fld:10} first x{ks[0]}, {len(ks)} frames')
            for k in ks[:show]:
                print(f'      x{k} A {a[k].get(fld, "")[:400]}')
                print(f'      x{k} B {b[k].get(fld, "")[:400]}')
    return 0


def time_tasks(folder, names, runs=3):
    """Each task run `runs` times, one subprocess at a time, its record thrown away; <task>.time.json in `folder`
    gets the least run and total ('runs': how many). Returns 1 if a run failed."""
    import tempfile
    os.makedirs(folder, exist_ok=True)
    env = dict(os.environ, PYTHONHASHSEED='0')
    failed = 0
    with tempfile.TemporaryDirectory() as tmp:
        for n in names:
            got = []
            for k in range(runs):
                gz = os.path.join(tmp, f'{n}.{k}.gz')
                with open(os.path.join(tmp, n + '.txt'), 'w', encoding='utf-8') as log:
                    p = subprocess.run([sys.executable, '-X', 'utf8', os.path.abspath(__file__), 'one', n, gz],
                                       env=env, stdout=log, stderr=subprocess.STDOUT)
                if p.returncode:
                    break
                with open(timing_path(gz), encoding='utf-8') as f:
                    got.append(json.load(f))
            if len(got) < runs:
                failed = 1
                print(n, 'FAILED')
                continue
            best = {'run': min(g['run'] for g in got), 'total': min(g['total'] for g in got),
                    'record': min(g['record'] for g in got), 'runs': runs}
            with open(timing_path(os.path.join(folder, n + '.gz')), 'w', encoding='utf-8') as f:
                json.dump(best, f)
            each = ', '.join('%.2f' % g['run'] for g in got)
            print(f'{n:14} run {best["run"]:7.2f} (of {each})', flush=True)
    return failed


def timing_path(gz):
    return gz[:-3] + '.time.json' if gz.endswith('.gz') else gz + '.time.json'


def timing(base, new, slower=SLOWER, shortest=SHORTEST):
    """Each task's run time before and after (ADR 0029 "搬完" (d): a step more than `slower` slower is to be
    explained); `run` is the simulated run alone (Sim.run / SimAI.advance less the record's own writing), `total` the
    subprocess's whole time (imports, map build, the engine model's load, the record). Tasks run side by side (-j),
    so a few percent is noise, and a run under `shortest` seconds is not flagged at all (measured 11-17: the same
    code's 0.04 s run read +54%); rerun the two with `record --only <task> -j 1` before explaining one. Skips tasks
    where either side has no timing (older records). Returns the task names flagged slower."""
    rows, flagged = [], []
    for f in sorted(os.listdir(base)):
        if not f.endswith('.gz'):
            continue
        try:
            with open(timing_path(os.path.join(base, f)), encoding='utf-8') as x, \
                    open(timing_path(os.path.join(new, f)), encoding='utf-8') as y:
                jb, jn = json.load(x), json.load(y)
            tb, tn, ab, an = jb['run'], jn['run'], jb['total'], jn['total']
        except (OSError, ValueError, KeyError):
            continue
        rows.append((f[:-3], tb, tn, ab, an))
    if not rows:
        print('timing: no timings on both sides (records made before simrecord timed its runs)')
        return flagged
    print('timing, seconds (run: the simulated run alone; total: the whole subprocess):')
    for name, tb, tn, ab, an in rows:
        change = (tn - tb) / tb if tb else 0.0
        mark = '  short' if tb < shortest else '  SLOWER' if change > slower else ''
        if mark == '  SLOWER':
            flagged.append(name)
        print(f'   {name:14} run {tb:7.2f} -> {tn:7.2f} {change:+6.1%}   total {ab:6.1f} -> {an:6.1f}{mark}')
    sb, sn = sum(r[1] for r in rows), sum(r[2] for r in rows)
    ab, an = sum(r[3] for r in rows), sum(r[4] for r in rows)
    print(f'   {"all":14} run {sb:7.2f} -> {sn:7.2f} {(sn - sb) / sb if sb else 0.0:+6.1%}   total {ab:6.1f} -> {an:6.1f}')
    return flagged


if __name__ == '__main__':
    sys.exit(main())
