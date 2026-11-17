"""Frame-by-frame record of a fixed set of simulator runs, for the ADR 0029 refactor: a pure move must leave every
frame's record identical (docs/engine/sim-layers.md "搬迁不改行为").

    python -X utf8 experimental/cnv/simrecord.py record <dir>            # every task, one subprocess each
    python -X utf8 experimental/cnv/simrecord.py compare <base> <new>    # first differing line per task

A task's record is one text line per engine frame (and one per DT tick): the frame, every body's attributes (sorted,
other bodies by name), and the Sim's observable state (log, flags, counters, timers, objectives, money, power, the
audit set, gaps, ending, series). Runs go in a subprocess with PYTHONHASHSEED=0 so set order is the same each run.
Records are gzip text under the caller's folder (work/logs/simrecord/...), never in the repository."""
import argparse
import gzip
import os
import subprocess
import sys


# name -> (kind, args, seconds). kind: bench = build.resolve(build, check) then Sim.run; old = the same without the
# engine model (Sim.step_old); retail = a retail map; ai = simai.run (the skirmish AI on the map).
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

    def line(self, where):
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
        s.run(until)
    elif kind in ('bench', 'old'):
        m, t, _ = build.resolve(*args)
        s = sim.Sim(m, t, model=kind == 'bench')
        rec = Recorder(s, out)
        rec.attach()
        s.run(until)
    elif kind == 'ai':
        import simai
        m, t, _ = build.resolve(*args)
        s = sim.Sim(m, t, 'normal')
        rec = Recorder(s, out)
        rec.attach()
        w = simai.SimAI(s, 'normal', 1, None, None, simai.BLOCKS, False)
        w.advance(int(until * simai.FPS))
    rec.line('end')
    return s


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
    c = sub.add_parser('compare')
    c.add_argument('base')
    c.add_argument('new')
    a = ap.parse_args()
    if a.cmd == 'one':
        with gzip.open(a.path, 'wt', encoding='utf-8') as out:
            s = run_task(a.name, out)
        print(a.name, 'used:', ' / '.join(sorted(s.used)))
        return 0
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
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
