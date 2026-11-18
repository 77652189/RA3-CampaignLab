"""Frame-by-frame record of a fixed set of simulator runs, for the ADR 0029 refactor: a pure move must leave every
frame's record identical (docs/engine/sim-layers.md "搬迁不改行为").

    python -X utf8 experimental/cnv/simrecord.py record <dir>            # every task, one subprocess each
    python -X utf8 experimental/cnv/simrecord.py time <dir>              # each task's run time again: alone, one
                                                                         # after another, the least of 3 runs
    python -X utf8 experimental/cnv/simrecord.py compare <base> <new>    # first differing line per task, then
                                                                         # each task's run time before and after

The times `record` writes come from runs side by side (-j), a few percent of noise and more on a loaded machine;
`time` replaces them with the least of three lone runs (docs/engine/sim-modules.md 9.3: same machine, one task a
process, the least of three), run it on both sides before explaining a slower step.

A task's record is one text line per engine frame (and one per DT tick): the frame, every body's attributes (sorted,
other bodies by name), and the Sim's observable state (log, flags, counters, timers, objectives, money, power, the
audit set, gaps, ending, series). Runs go in a subprocess with PYTHONHASHSEED=0 so set order is the same each run.
Records are gzip text under the caller's folder (work/logs/simrecord/...), never in the repository."""
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
SKIP_BODY = frozenset()
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
            d = vars(b)
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


def run_task(name, out):
    import build
    import sim
    kind, args, until = TASKS[name]
    if kind == 'retail':
        import retail
        s = sim.Sim(retail.RetailMission(args[0]))
        rec = Recorder(s, out)
        rec.attach()
        t0 = time.perf_counter()
        s.run(until)
    elif kind in ('bench', 'old'):
        m, t, _ = build.resolve(*args)
        s = sim.Sim(m, t, model=kind == 'bench')
        rec = Recorder(s, out)
        rec.attach()
        t0 = time.perf_counter()
        s.run(until)
    elif kind == 'ai':
        import simai
        m, t, _ = build.resolve(*args)
        s = sim.Sim(m, t, 'normal')
        rec = Recorder(s, out)
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
    one = sub.add_parser('one')
    one.add_argument('name')
    one.add_argument('path')
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
            s, rec = run_task(a.name, out)
        total = time.perf_counter() - t0
        with open(timing_path(a.path), 'w', encoding='utf-8') as f:
            json.dump({'total': total, 'record': rec.spent, 'run': rec.ran}, f)
        print(a.name, 'used:', ' / '.join(sorted(s.used)))
        return 0
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
                                      os.path.join(a.dir, n + '.gz')], env=env, stdout=log, stderr=subprocess.STDOUT)
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
