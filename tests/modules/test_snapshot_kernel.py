"""The kernel's part of a snapshot (engine/kernel/snap.py, World.snapshot / restore; step S, docs/engine/sim-modules.md
9.2) and the public script executor's (engine/ports/scripts.py Executor.snapshot / restore): taken, through JSON and
back equal; written onto a world (an executor) made anew for the same things (scripts), taken again equal; and run on
from there frame for frame as the one never stopped. A value it cannot keep, other things, other script lists: an
error, never a part left out. With a host (the Sim's own fields) and whole missions: tests/tools/test_snapshot.py
(step 11b-3b, 11b-3c)."""
import json
import random
import types

import pytest

from test_plans import small  # noqa: F401,I001  (tests/ is on the path by its conftest; puts experimental/cnv on it)
from engine.kernel import interfaces, module, snap, world as kernel_world  # noqa: E402
from engine.ports import scripts as port  # noqa: E402
from engine.script import executor, lists  # noqa: E402


class Thing(module.Thing):
    def __init__(self, name, template='T'):
        self.name, self.template = name, template


class Tick(module.Module, interfaces.Update, interfaces.Create):
    """Counts its runs, sleeps every third, keeps a thing, a set, a tuple-keyed table and a random state."""
    PHASE, ORDER = 'tick', 0
    STATE = ('n', 'friend', 'seen', 'table', 'late')

    def on_create(self, frame):
        self.n, self.friend, self.seen, self.table = 0, None, set(), {}

    def update(self, frame):
        self.n += 1
        self.seen.add(frame % 4)
        self.table[(frame, self.thing.name)] = (self.n, [frame])
        if self.n == 2:
            self.late = 'set late'
        return interfaces.SLEEP if self.n % 3 == 0 else 1 + self.n % 2


class Other(module.Module):
    STATE = ('mark',)


def blocks(template, tag):
    return [('', '')] if tag == 'Tick' or (tag == 'Other' and template == 'B') else []


def new_world():
    return kernel_world.World(blocks, tags={'Tick': Tick, 'Other': Other})


def made(w):
    things = [Thing('a'), Thing('b', 'B'), Thing('c')]
    for t in things:
        t.modules = w.build(t, 0)
    return things


def run(w, things, frames):
    for f in frames:
        w.frame = f
        w.schedule.run('tick', f)
        if f == 3:
            w.wake(things[0].modules[0])
            w.used.add('woke')
            w.gap('kind', 'name', 'what')


def test_a_world_taken_mid_run_comes_back_and_runs_on_as_the_one_never_stopped():
    w = new_world()
    things = made(w)
    things[0].modules[0].friend = things[2]
    things[1].modules[1].mark = things[0].modules[0]        # a module of another thing
    w.schedule.remove(things[2].modules[0])                 # a hole in the seqs: kept as it was
    w.schedule.add(things[2].modules[0], 2)
    run(w, things, range(0, 6))
    s = w.snapshot(things)
    assert json.loads(json.dumps(s)) == s                   # 4.2: through JSON and back the same

    w2 = new_world()
    things2 = made(w2)                                      # made for the same things, then written over
    w2.build(Thing('spare'), 0)                             # a thing more made in the new world: the count is the snapshot's
    w2.restore(json.loads(json.dumps(s)), {t.serial: t for t in things2})
    assert w2.snapshot(things2) == s                        # 4.2: taken again, the same
    assert things2[0].modules[0].friend is things2[2] and things2[1].modules[1].mark is things2[0].modules[0]
    assert w2.used is not None and w2.used == {'woke'} and w2.gaps == w.gaps

    for f in range(6, 30):                                  # 4.1 on the kernel: frame for frame the same
        run(w, things, [f])
        run(w2, things2, [f])
        assert w2.snapshot(things2) == w.snapshot(things), f
    late = Thing('d')
    late2 = Thing('d')
    late.modules, late2.modules = w.build(late, 30), w2.build(late2, 30)
    assert late.serial == late2.serial == 3 and w.schedule.seq[late.modules[0]] == w2.schedule.seq[late2.modules[0]]


def test_a_field_not_set_at_the_snapshot_is_taken_off_on_restore():
    w = new_world()
    things = made(w)
    s = w.snapshot(things)                                  # 'late' not set yet
    w2 = new_world()
    things2 = made(w2)
    run(w2, things2, range(0, 6))
    assert hasattr(things2[0].modules[0], 'late')
    w2.restore(s, {t.serial: t for t in things2})
    assert not hasattr(things2[0].modules[0], 'late') and w2.snapshot(things2) == s


def test_what_it_cannot_keep_or_other_things_is_an_error_not_a_part_left_out():
    w = new_world()
    things = made(w)
    things[0].modules[0].friend = object()
    with pytest.raises(TypeError, match='Tick of .a.\\.friend'):
        w.snapshot(things)
    things[0].modules[0].friend = None
    with pytest.raises(ValueError, match='held by the schedule'):
        w.snapshot(things[:2])                              # c's module held, c not given
    s = w.snapshot(things)
    w2 = new_world()
    others = [Thing('a'), Thing('b'), Thing('c')]           # b of another template: no Other module
    for t in others:
        t.modules = w2.build(t, 0)
    with pytest.raises(ValueError, match='has modules'):
        w2.restore(s, {t.serial: t for t in others})
    with pytest.raises(ValueError, match='one side only'):
        w2.restore(s, {t.serial: t for t in others[:2]})


def test_the_values_marks_come_back_as_they_were():
    t = Thing('x')
    t.serial = 7
    v = {'plain': [1, 2.5, None, True, 'x'], 'tuple': (1, (2,)), 'set': {3, 1}, 'frozen': frozenset({'a'}),
         'keys': {(1, 2): 'k', 3: 'i'}, '$looks': 'like a mark', 'thing': t, 'inf': float('inf')}
    e = snap.encode(v)
    assert json.loads(json.dumps(e)) == e
    back = snap.decode(e, {7: t})
    assert back == v and back['thing'] is t
    assert {k: type(x) for k, x in back.items()} == {k: type(x) for k, x in v.items()}    # a set == its frozenset
    assert snap.encode({1, 'a', (2,)}) == snap.encode({(2,), 'a', 1})      # a set's list does not hang on its order
    with pytest.raises(ValueError, match='mark'):
        snap.decode({'$weapon': ['T', 'k']}, {})
    assert snap.decode({'$weapon': ['T', 'k']}, {}, lambda mark, x: ('w', *x)) == ('w', 'T', 'k')


# ------------------------------------------------------------------------------------------- the script executor
class Log(port.World):
    def __init__(self):
        self.calls = []

    def condition(self, eng, name, args):
        return name == 'YES' or (name == 'HALF' and eng.steps % 2 == 0)

    def action(self, eng, name, args):
        self.calls.append((eng.steps, name, tuple(args), eng.script.name))


def scripts():
    def s(name, when, do, once=False, active=True, sub=False, interval=0):
        x = types.SimpleNamespace(name=name, when=when, do=do, once=once, levels=(True, True, True),
                                  active=active, sub=sub)
        return x, interval
    rows = [s('every', [['YES']], [['DO', 'e'], ['SET_RANDOM_COUNTER', 'r', 1, 9], ['DISPLAY_COUNTER', 'r', 'R']]),
            s('half', [['HALF']], [['DO', 'h'], ['SET_MILLISECOND_TIMER', 't', 0.5]]),
            s('once', [['YES']], [['DO', 'o'], ['DISABLE_SCRIPT', 'half']], once=True),
            s('back', [['TIMER_EXPIRED', 't']], [['ENABLE_SCRIPT', 'half'], ['DO', 'b']]),
            s('slow', [['YES']], [['DO', 's']], interval=1),
            s('slow', [['YES']], [['DO', 's2']], interval=2)]
    return rows


def new_executor(w):
    rows = scripts()
    ls = lists.from_cnv([x for x, _ in rows], '<not>')
    for it, (_, interval) in zip(ls[0].items, rows):
        it.interval = interval
    return executor.PublicExecutor(w, ls, 0, 15, seed=3)


def test_the_public_executor_taken_mid_run_comes_back_and_runs_on_as_the_one_never_stopped():
    w = Log()
    ex = new_executor(w)
    for _ in range(40):
        ex.step()
    s = ex.snapshot()
    assert json.loads(json.dumps(s)) == s
    w2 = Log()
    ex2 = new_executor(w2)
    ex2.restore(json.loads(json.dumps(s)))
    assert ex2.snapshot() == s and ex2.script is ex2.script_named(ex.script.name)
    assert ex2.log == ex.log and ex2.readings() == ex.readings() and ex.readings()
    w.calls.clear()
    for _ in range(80):
        ex.step()
        ex2.step()
        assert ex2.snapshot() == ex.snapshot()
    assert w2.calls == w.calls and {c[1] for c in w.calls} >= {'DO'}
    assert {c[2] for c in w.calls} >= {('e',), ('s',), ('s2',)}


def test_other_script_lists_are_refused_and_an_executor_without_snapshots_says_so():
    ex = new_executor(Log())
    s = ex.snapshot()
    s['active'][0][1] = 'renamed'
    with pytest.raises(ValueError, match='other script lists'):
        new_executor(Log()).restore(s)

    class Bare(port.Executor):
        def step(self):
            pass
    with pytest.raises(NotImplementedError, match='does not take snapshots'):
        Bare().snapshot()
    with pytest.raises(NotImplementedError, match='does not take snapshots'):
        Bare().restore({})


def test_the_random_draws_go_on_from_where_they_were():
    ex = new_executor(Log())
    ex.rng.random()
    s = ex.snapshot()
    ex2 = new_executor(Log())
    ex2.restore(s)
    assert [ex2.rng.random() for _ in range(3)] == [ex.rng.random() for _ in range(3)]
    assert isinstance(ex2.rng, random.Random)
