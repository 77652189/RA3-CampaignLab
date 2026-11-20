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
    python -X utf8 experimental/cnv/simrecord.py snap <dir> [--at 0.5]   # step S's guard 7: each task without the
                                                                         # AI whole, and taken at half, written back
                                                                         # onto the task made anew, run on: the same
                                                                         # record, snapshot at the end and report;
                                                                         # the cut goes through a file to another
                                                                         # process (11c, snapfile)

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
are step Z's work list, judged on the bench by docs/engine/script-semantics.md).

`snap` (step S's guard 7, docs/engine/sim-modules.md 9.2) runs both sides with the public executor (on the model's world where the
task has it): the model's plug-in keeps its state to itself and cannot be taken yet, so its frame lines (on_frame) are
not there and the record is a line per DT tick.

The recorders read the world only through the observation port (engine/ports/observe.py, R3 12b): a field moved
into a kernel module changes the port, never this file. Only run_task, the harness, imports the simulator (to make
the run); tests/guards/test_ports.py holds both. The golden layer copies this file and the port onto its base
together (testbench/golden.py RECORDER_RELS); the port is imported where it is used, so loading this file by its
path (golden, family_close) needs no simulator on sys.path."""
import argparse
import gzip
import os
import json
import subprocess
import sys
import time


# name -> (kind, args, seconds). kind: bench = build.resolve(build, check) then Sim.run; old = the same without the
# engine model (Sim(model=False)); retail = a retail map; ai = simai_run.run (the skirmish AI on the map).
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
SNAP_TASKS = list(TASKS)    # `snap`: every task, the AI's through simaisnap (11b-4d)

SIM_FIELDS = ('log', 'flags', 'counters', 'timers', 'objectives', 'money', 'income', 'ending', 'used', 'unknown',
              'series', 'done', 'disabled', 'events')
SKIP_BODY = frozenset({'heal_seen', 'hurt'})   # K2: AutoHeal's last-frame health became a hurt flag (bookkeeping
                                               # nobody sees; heal_at, what it decides, is still recorded)
SKIP_BODY |= {'leaves'}         # B5b: what a death of age makes is the CreateObjectDie modules' read of the
                                # template (no state); the body's list of it is gone
EXECUTORS = ('public', 'model', 'public@model')   # --executor (engine/ports/scripts.py): Sim(model=False) /
                                # Sim(model=True) / Sim(model=True, executor='public'): the public one on the model's
                                # world (its clock and model-or-not branches), so a cross against `model` is the
                                # executor alone and one against `public` the world alone
SLOWER = 0.10                  # compare flags a task whose run got more than this much slower (ADR 0029 "搬完" (d))
SHORTEST = 1.0                 # ... and only a run of at least this many seconds (shorter ones are noise)


def canon(v, depth=0):
    """A stable text for a value: other bodies by name, sets sorted, floats by repr."""
    from engine.ports.observe import Observe
    if Observe.is_thing(v):
        return 'B:' + v.name
    if isinstance(v, int) and not isinstance(v, bool) and v > 10 ** 11:
        return 'ID'                              # an id() differs run to run; no recorded table keys by one since
                                                 # snapshot step 11b-2 (test_kernel's id guard): kept so a stray
                                                 # one reads as one word, not a difference every run
    if v is None or isinstance(v, (bool, int, float, str)):
        return repr(v)
    if depth > 4:
        return '<' + type(v).__name__ + '>'
    from engine.ports.readonly import MapView, SeqView, SetView   # the port's read-only views read as what they show
    if isinstance(v, (list, tuple, SeqView)):
        return '[' + ','.join(canon(x, depth + 1) for x in v) + ']'
    if isinstance(v, (set, frozenset, SetView)):
        return '{' + ','.join(sorted(canon(x, depth + 1) for x in v)) + '}'
    if isinstance(v, (dict, MapView)):
        items = [(canon(k, depth + 1), canon(x, depth + 1)) for k, x in v.items()]
        return '{' + ','.join(f'{k}:{x}' for k, x in sorted(items)) + '}'
    if hasattr(v, '__dict__') and depth < 2:
        return type(v).__name__ + canon({k: x for k, x in vars(v).items() if k != 'sim'}, depth + 1)
    return '<' + type(v).__name__ + '>'


def body_state(b):
    """A body's fields as the record shows them: the port's state() (its own, its modules' STATE, Body.FORWARDS)."""
    from engine.ports.observe import Observe
    return Observe.state(b)


class Recorder:
    def __init__(self, o, out):
        self.o, self.out, self.n = o, out, 0     # o: the run's observation port (engine/ports/observe.Observe)
        self.logged = 0
        self.spent = 0.0                # seconds spent writing the record (taken off the run's time)

    def line(self, where):
        t0 = time.perf_counter()
        self._line(where)
        self.spent += time.perf_counter() - t0

    def _line(self, where):
        o = self.o
        parts = [f'{where} t={o.t!r}']
        for b in o.things():
            d = o.state(b)
            parts.append(b.name + '|' + ';'.join(f'{k}={canon(d[k])}' for k in sorted(d) if k not in SKIP_BODY))
        for f in SIM_FIELDS:
            if f == 'log':
                new, self.logged = o.log_since(self.logged)
                parts.append('log+' + canon(new))
            else:
                parts.append(f + '=' + canon(o.report(f)))
        parts.append('gaps=' + canon(o.gaps()))
        self.out.write(' || '.join(parts) + '\n')
        self.n += 1

    def attach(self):
        self.o.on_frame(lambda frame: self.line(f'f{frame}'))
        self.o.on_tick(lambda: self.line('tick'))


class PortTap:
    """The port's World between an executor and the simulator's (simexec.SimWorld), noting each action the executor
    does (script, name, args as text): every World.core (the model's plug-in tells core() each action it runs, its own
    core ones and those it then hands to action(); the public executor its timer actions) and the public executor's
    World.action (the plug-in's would be the second time). Conditions
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

    def __init__(self, o, out):
        self.o, self.out, self.n = o, out, 0     # o: the run's observation port
        self.logged = 0
        self.spent = 0.0

    def attach(self):
        o = self.o
        ex, model = o.scripts()
        self.tap = PortTap(ex.world, model)
        ex.world = self.tap
        inner = ex.step

        def step():
            f = ex.frame if model else o.frame()
            r = inner()
            self.line(f'x{f}')
            return r
        ex.step = step

    def line(self, where):
        t0 = time.perf_counter()
        o = self.o
        did, self.tap.did = self.tap.did, []
        new, logged = o.log_since(self.logged)
        vals = {
            'did': canon(did),
            'flags': canon({k: int(v) for k, v in o.flags().items()}),
            'counters': canon(dict(o.counters())),
            'timers': canon({k: frames_left(v, o.t, o.fps) for k, v in o.timers().items()}),
            'objectives': canon(o.objectives()),
            'ending': canon(o.ending()),
            'log': canon(new),
            'alive': canon(sorted(b.name for b in o.living())),
        }
        self.logged = logged
        self.out.write(where + ' || ' + ' || '.join(f'{k}={vals[k]}' for k in CROSS_FIELDS) + chr(10))
        self.n += 1
        self.spent += time.perf_counter() - t0


class _Later:
    """A gzip text file opened on its first write (the CLI's record: a resume refused writes nothing, u P3 #1)."""

    def __init__(self, path, mode):
        self.path, self.mode, self.f = path, mode, None

    def write(self, text):
        if self.f is None:
            self.f = gzip.open(self.path, self.mode, encoding='utf-8')
        return self.f.write(text)

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        if self.f is not None:
            self.f.close()


def _resumable(snapfile, resume, name, snap, record=None):
    """(meta, snapshot) of the file a cut run `name` at `snap` goes on from (snapfile.load: its format and shape),
    or an error naming why not -- another task or cut, and (`record`, the CLI's) no first half's record there to
    go on: asked before anything is written (review 1119u P3 #1)."""
    meta, taken = snapfile.load(resume)
    if (meta.get('task'), meta.get('snap')) != (name, snap):
        raise ValueError(f'simrecord: {resume} is {meta.get("task")} cut at {meta.get("snap")}, '
                         f'not {name} at {snap}')
    if record is not None and not (os.path.isfile(record) and os.path.getsize(record) > 0):
        raise ValueError(f'simrecord: no first half\'s record at {record} to go on from')
    return meta, taken


def run_task(name, out, executor=None, snap=None, save=None, resume=None, record=None):
    """One task's run, its record written to `out`. executor: None the task's own (TASKS: old runs the public one,
    the rest the model's plug-in where it is on this computer) and the full record; 'public' / 'model' /
    'public@model' that executor for every kind and the cross record (CrossRecorder).
    snap (step S's guard 7, `snap` below): the full record on a world a snapshot can be taken of -- the task's own
    with the public executor (the model's plug-in keeps its state to itself), an AI task's the public world --,
    'whole' run through, a fraction
    `at` stopped at the first tick past at x the task's seconds, taken (simsnap; an AI task's SimAI with its brains
    through simaisnap, 11b-4d), through JSON, written onto the same task made anew (an AI task's SimAI made anew on
    it) and run on to the end, the record going on where it stopped (Recorder, the log's count).
    Across processes (11c, `snap`): `save` a path -- the cut run stops once taken, the snapshot and where the record
    stopped written there (snapfile); `resume` that path -- another process makes the task anew, writes the file's
    snapshot onto it and runs on, its record the rest of the cut one's (`out` appended to)."""
    import build
    import sim
    import snapfile
    from engine.ports.observe import Observe
    kind, args, until = TASKS[name]
    if (save or resume) and snap in (None, 'whole'):
        raise ValueError('simrecord: save / resume is a cut run\'s (--snap <fraction>)')
    if resume:
        meta, taken = _resumable(snapfile, resume, name, snap, record)
    model = kind != 'old' if executor is None else executor in ('model', 'public@model')
    if snap is not None and kind == 'ai':   # the model's world keeps the model's script engine as its clock, which
        model = False                       # a snapshot cannot take (simaisnap: the AI's runs on Sim(model=False))
    which = {'executor': 'public'} if executor == 'public@model' or (snap is not None and model) else {}
    make = Recorder if executor is None else CrossRecorder
    if snap is not None and executor is not None:
        raise ValueError(f'simrecord: no snapshot of {name} ({kind}) with executor {executor}: the model\'s plug-in '
                         'cannot be taken')
    if snap is not None:    # the AI's run through simaisnap (the Sim's part and the brains'), the rest simsnap
        if kind == 'ai':
            import simaisnap as snaps
        else:
            import simsnap as snaps

    cut = None if snap in (None, 'whole') else float(snap) * until
    if resume:      # the cut run's first half was another process's: its recorder's counts and times from the file
        rec = Recorder(None, out)
        rec.n, rec.logged, rec.spent, rec.at = meta['n'], meta['logged'], meta['spent'], meta['at']
        t1 = time.perf_counter()
        t0 = t1 - meta['elapsed']
    for half in (1,) if resume else range(1 if cut is None else 2):  # a cut run: the task made again, written back
        if kind == 'retail':
            import retail
            s = sim.Sim(retail.RetailMission(args[0]), model=model, **which)
        else:
            m, t, _ = build.resolve(*args)
            s = sim.Sim(m, t, 'normal', model=model, **which)
        w = None
        if kind == 'ai':
            import simai
            w = simai.SimAI(s, 'normal', 1, None, None, simai.BLOCKS, False)
        if half:
            snaps.restore(s if w is None else w, taken if resume else json.loads(taken))
            o = Observe(s)
            if o.log_since(0)[1] != rec.logged:
                raise RuntimeError(f'simrecord: the restored log has {o.log_since(0)[1]} lines, the run had '
                                   f'{rec.logged}')
            was, rec = rec, Recorder(o, out)    # the record goes on from the line and the log count it stopped at
            rec.n, rec.logged = was.n, was.logged
            rec.spent = was.spent + time.perf_counter() - t1     # taking and writing back: not the run's time
            rec.snap = {'at': was.at, 'bytes': meta['bytes'] if resume else len(taken),
                        'seconds': time.perf_counter() - t1, **({'across': True} if resume else {})}
            rec.attach()
            frame = s.world.frame
            if w is None:
                s.run(until)
            else:               # the AI's run a frame at a time (SimAI.advance), to the frame the whole one ends at
                w.advance(int(until * simai.FPS) - w.frame)
            if s.world.frame == frame:
                raise RuntimeError(f'simrecord: {name} restored at {s.t} ran no frame on to {until}: the cut proves '
                                   'nothing')
            break
        rec = make(Observe(s), out)
        rec.attach()
        t0 = time.perf_counter()
        if cut is None:
            if w is None:
                s.run(until)
            else:
                w.advance(int(until * simai.FPS))
            break
        if w is None:
            s.run(cut)
            last = s.t > until      # Sim.run steps while t <= until: written back there, it would run no frame on
        else:   # a frame at a time to the first tick past the cut, where Sim.run stops (t > cut; a tick is DT)
            while s.t <= cut and s.ending is None:
                w.advance(1)
            last = w.frame >= int(until * simai.FPS)
        if s.ending is not None or s.t <= cut:
            raise RuntimeError(f'simrecord: {name} ended (or went quiet) at {s.t}, before {cut}: nothing to take')
        if last:
            raise ValueError(f'simrecord: {name} cut at {snap} stops at {s.t}, past its end {until}: no frame left '
                             'to run after the snapshot (take it earlier)')
        t1 = time.perf_counter()
        taken, rec.at = json.dumps(snaps.snapshot(s if w is None else w)), s.t
        if save:        # the rest is another process's (resume): where the record stopped goes with the snapshot
            snapfile.save(save, json.loads(taken), task=name, snap=snap, at=rec.at, frame=s.world.frame, n=rec.n,
                          logged=rec.logged, spent=rec.spent, elapsed=t1 - t0, bytes=len(taken))
            rec.saved = save
            return s, rec
    rec.ran = time.perf_counter() - t0 - rec.spent     # the run alone: no imports, map build or record writing
    rec.line('end')
    if snap is not None:    # its end (end_path): the snapshot after the run (the AI's with its brains) and the
        rec.end = {'snapshot': snaps.snapshot(s if w is None else w)}   # report -- it notes what it used (Sim.used)
        rec.end['report'] = s.report()
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
    one.add_argument('--snap', default=None, help="'whole' or a fraction of the run: run_task")
    one.add_argument('--save', default=None, help='a cut run: stop once taken, the snapshot to this file (run_task)')
    one.add_argument('--resume', default=None, help='a cut run: go on from this file, the record appended to')
    sn = sub.add_parser('snap', help="step S's guard 7: each task whole and taken at --at, written back, run on; "
                                     'the two records the same line for line, their ends the same')
    sn.add_argument('dir')
    sn.add_argument('--at', type=float, default=0.5, help='where to take it, a fraction of the task')
    sn.add_argument('--only', nargs='*', default=None)
    sn.add_argument('-j', type=int, default=4)
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
    if a.cmd in ('cross', 'compare'):
        return _main(a)
    # the machine's CPU tokens (cpupool, T5): a recording takes a token a subprocess (-j of them, as many as are free,
    # waiting for one); `time` takes the whole pool so its readings are the machine's alone
    pool = _cpupool()
    if a.cmd == 'time':
        with pool.hold(1, 'simrecord time', exclusive=True):
            return _main(a)
    want = 1
    if a.cmd in ('record', 'snap'):
        want = max(1, min(a.j, len(a.only or TASKS) * (2 if a.cmd == 'snap' else 1)))
    with pool.hold(want, f'simrecord {a.cmd}', at_least=1) as j:
        if a.cmd in ('record', 'snap'):
            a.j = j
        return _main(a)


def _cpupool():
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        '_cpupool', os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'testbench', 'cpupool.py'))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _main(a):
    if a.cmd == 'one':
        t0 = time.perf_counter()
        # a resumed run's record is the rest of the cut one's: a second gzip member, read on as one text; opened on
        # its first line, so a resume run_task refuses (its file, the first half's record) appends nothing (u P3 #1)
        with _Later(a.path, 'at' if a.resume else 'wt') as out:
            _, rec = run_task(a.name, out, a.executor, a.snap, a.save, a.resume, a.path if a.resume else None)
        total = time.perf_counter() - t0
        if a.save:                  # the first half: its end, time and report are the resumed run's
            print(a.name, 'taken at', rec.at, 's ->', a.save)
            return 0
        if a.snap is not None:      # the run's end beside its record: snap_check compares what the record does not show
            with gzip.open(end_path(a.path), 'wt', encoding='utf-8') as f:
                json.dump(rec.end, f)
        with open(timing_path(a.path), 'w', encoding='utf-8') as f:
            json.dump({'total': total, 'record': rec.spent, 'run': rec.ran, **({'snap': rec.snap}
                                                                               if hasattr(rec, 'snap') else {})}, f)
        print(a.name, 'used:', ' / '.join(sorted(rec.o.report('used'))))
        return 0
    if a.cmd == 'cross':
        return cross(a.a, a.b, a.show)
    if a.cmd == 'time':
        return time_tasks(a.dir, a.only or list(TASKS), a.n)
    if a.cmd == 'record':
        extra = ['--executor', a.executor] if a.executor else []
        return 1 if _record(a.dir, [(n, n, extra) for n in a.only or TASKS], a.j) else 0
    if a.cmd == 'snap':
        return snap_check(a.dir, a.only or SNAP_TASKS, a.at, a.j)
    bad = 0
    for f in sorted(os.listdir(a.base)):
        if not f.endswith('.gz'):
            continue
        other = os.path.join(a.new, f)
        if not os.path.exists(other):
            print(f[:-3], 'MISSING in', a.new)
            bad += 1
            continue
        lines, differs = first_difference(os.path.join(a.base, f), other)
        if differs:
            bad += 1
            print(f[:-3], differs)
        else:
            print(f[:-3], 'same', lines, 'lines')
    timing(a.base, a.new)
    return 1 if bad else 0


def _record(folder, jobs, j):
    """Each job (task, file name, extra arguments of `one`[, its output's name]) in its own subprocess, j at a time,
    its record <folder>/<file>.gz and its output <file>.txt (or <output>.txt). Returns the files that failed."""
    os.makedirs(folder, exist_ok=True)
    env = dict(os.environ, PYTHONHASHSEED='0')
    procs, failed = [], []
    pending = list(jobs)
    while pending or procs:
        while pending and len(procs) < j:
            n, f, extra, *named = pending.pop(0)
            log = open(os.path.join(folder, (named[0] if named else f) + '.txt'), 'w', encoding='utf-8')
            p = subprocess.Popen([sys.executable, '-X', 'utf8', os.path.abspath(__file__), 'one', n,
                                  os.path.join(folder, f + '.gz')] + extra,
                                 env=env, stdout=log, stderr=subprocess.STDOUT)
            procs.append((f, p, log))
        f, p, log = procs[0]
        p.wait()
        log.close()
        procs.pop(0)
        if p.returncode:
            failed.append(f)
        print(f, 'ok' if not p.returncode else f'FAILED (see {f}.txt)', flush=True)
    return failed


def snap_check(folder, names, at=0.5, j=4):
    """Step S's guard 7 (docs/engine/sim-modules.md 9.2): each task recorded whole (<task>.gz) and taken at `at`
    of its run, through JSON, written onto the task made anew and run on (<task>.snap.gz), both on the world a
    snapshot can be taken of (run_task); the first differing line of each pair, else where their ends differ
    (end_difference: the snapshot at the end and the report), the snapshot's size and time. 0 when every pair is
    the same. Across processes (11c): the cut run stops once taken, its snapshot in a file (<task>.snap.json.gz,
    snapfile), and another process (PYTHONHASHSEED the same) makes the task anew, writes it back and runs on."""
    def file(n):
        return os.path.join(folder, n + '.snap.json.gz')
    failed = _record(folder, [(n, n, ['--snap', 'whole']) for n in names] +
                     [(n, n + '.snap', ['--snap', repr(at), '--save', file(n)]) for n in names], j)
    failed += _record(folder, [(n, n + '.snap', ['--snap', repr(at), '--resume', file(n)], n + '.snap.resume')
                               for n in names if n + '.snap' not in failed], j)
    bad = 0
    for n in names:
        whole, cut = os.path.join(folder, n + '.gz'), os.path.join(folder, n + '.snap.gz')
        if n in failed or n + '.snap' in failed:
            print(n, 'FAILED to run')
            bad += 1
            continue
        lines, differs = first_difference(whole, cut)
        differs = differs or end_difference(whole, cut)
        with open(timing_path(cut), encoding='utf-8') as f:
            took = json.load(f).get('snap', {})
        how = f"taken at {took.get('at')} s, {took.get('bytes', 0) / 1e6:.2f} MB, {took.get('seconds', 0):.2f} s" + \
              (', across processes' if took.get('across') else '')
        if differs:
            bad += 1
            print(n, differs, f'({how})')
        else:
            print(n, 'same', lines, f'lines ({how})')
    return 1 if bad else 0


def first_difference(base, new):
    """Two records (gzip text) line by line: (lines, None) where they are the same, else (line number, a report of
    the first differing line: its frame on each side and up to 3 differing parts, each with up to 4 differing fields).
    tests/golden (experimental/testbench/golden.py) reports through it too."""
    with gzip.open(base, 'rt', encoding='utf-8') as x, gzip.open(new, 'rt', encoding='utf-8') as y:
        n = 0
        while True:
            lx, ly = x.readline(), y.readline()
            n += 1
            if lx != ly:
                px, py = lx.rstrip(chr(10)).split(' || '), ly.rstrip(chr(10)).split(' || ')
                diff = [(i, u, v) for i, (u, v) in enumerate(zip(px, py)) if u != v][:3]
                out = [f'DIFFERS at line {n}: {px[0][:40]} vs {py[0][:40]}; parts {len(px)} {len(py)}']
                for i, u, v in diff:
                    iu, iv = u.split(';'), v.split(';')
                    out.append(f'   in {u[:30]} ' + repr([(p, q) for p, q in zip(iu, iv) if p != q][:4] or
                                                        (u[:300], v[:300])))
                return n, chr(10).join(out)
            if not lx:
                return n - 1, None


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


def end_path(gz):
    """A `snap` run's end beside its record: {'snapshot': simsnap.snapshot at the end, 'report': Sim.report()}."""
    return (gz[:-3] if gz.endswith('.gz') else gz) + '.end.json.gz'



def differences(a, b, at='', most=8):
    """Where two snapshots (through JSON) differ: up to `most` paths, a row of the host's or the bodies' lists named
    by its first item (the field's path, the body's key). [] when they are the same. `snap` reads the two runs'
    ends through it (end_difference): a field the record does not show (the cells ever seen) still has to come back."""
    out = []

    def walk(x, y, at):
        if len(out) >= most:
            return
        if type(x) is not type(y):
            out.append(at or '.')
        elif isinstance(x, dict):
            for k in sorted(set(x) | set(y), key=str):
                if k in x and k in y:
                    walk(x[k], y[k], f'{at}.{k}')
                else:
                    out.append(f'{at}.{k} (one side only)')
        elif isinstance(x, list):
            if len(x) != len(y):
                out.append(f'{at} ({len(x)} items, {len(y)})')
                return
            for i, (u, v) in enumerate(zip(x, y)):
                name = u[0] if isinstance(u, list) and u and isinstance(u[0], str) else i
                walk(u, v, f'{at}[{name}]')
        elif x != y:
            out.append(at or '.')
    walk(a, b, at)
    return out[:most]


def end_difference(whole, cut):
    """Two `snap` runs' ends (end_path): None when the same, else what differs -- the snapshot's paths (a field the
    record does not show, as the cells ever seen) and the report's lines (what a field sorted as not to be taken
    feeds: snapshot.md 4.4, the cells ever seen sorted a cache read the same at both ends and lost the report's
    known area)."""
    import difflib
    ends = []
    for gz in (whole, cut):
        with gzip.open(end_path(gz), 'rt', encoding='utf-8') as f:
            ends.append(json.load(f))
    (x, y), out = ends, []
    where = differences(x['snapshot'], y['snapshot'])
    if where:
        out.append('ENDS DIFFER in the snapshot at ' + ', '.join(where))
    lines = [d for d in difflib.unified_diff(x['report'], y['report'], lineterm='', n=0)
             if d[:1] in '+-' and d[:3] not in ('---', '+++')]
    if lines:
        out.append(f'ENDS DIFFER in the report, {len(lines)} lines: ' +
                   ' | '.join(d[:160] for d in lines[:4]))
    return chr(10).join(out) or None


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
