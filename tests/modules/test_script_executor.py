"""The public script executor (engine/script/executor.py, step P1) on the script executor port
(engine/ports/scripts.py): with a minimal World it asks every condition and does every action through the port, once
a frame, in file order; a once script fires once, a disabled or off-level one not at all; the NOT mark negates and is
reported as an assumption. '<This Player>' reads as the executor's side. The rules behind the names are the world's
(simcond / simact), tested by name there; this is the executor's own loop only."""
import types

from test_plans import small  # noqa: F401,I001  (tests/ is on the path by its conftest; puts experimental/cnv on it)
from engine.ports import scripts as port  # noqa: E402
from engine.script import executor  # noqa: E402

NOT = '<not>'


class Log(port.World):
    def __init__(self, truth):
        self.truth, self.calls, self.seen = truth, [], set()

    def condition(self, eng, name, args):
        self.calls.append(('cond', name, tuple(args)))
        return self.truth.get(name, False)

    def action(self, eng, name, args):
        self.calls.append(('act', name, tuple(args), eng.script.name))

    def assumed(self, what):
        self.seen.add(what)


def script(name, when, do, once=False, levels=(True, True, True)):
    return types.SimpleNamespace(name=name, when=when, do=do, once=once, levels=levels)


def test_each_frame_the_holding_scripts_act_in_file_order_through_the_port():
    w = Log({'YES': True})
    scripts = [script('a', [['YES', 1]], [['DO_A', 'x']]),
               script('b', [['NO']], [['DO_B']]),
               script('c', [['NO', NOT]], [['DO_C', 'y', 'z']], once=True),
               script('d', [], [['DO_D']], levels=(True, False, True)),
               script('e', [], [['DO_E']])]
    done, disabled = set(), {'e'}
    ex = executor.PublicExecutor(w, scripts, 1, done, disabled, NOT, 15)
    assert isinstance(ex, port.Executor)
    ex.step()
    assert w.calls == [('cond', 'YES', (1,)), ('act', 'DO_A', ('x',), 'a'), ('cond', 'NO', ()),
                       ('cond', 'NO', ()), ('act', 'DO_C', ('y', 'z'), 'c')]
    assert done == {'c'} and w.seen == {'inverted'}
    w.calls.clear()
    ex.step()
    assert [c[1] for c in w.calls if c[0] == 'act'] == ['DO_A']


class Core(Log):
    def core(self, eng, name, args, script):
        self.calls.append(('core', name, tuple(args), script.name))


def test_timers_are_the_executors_table_counted_down_before_the_scripts():
    """script-semantics.md 3 (bench engine_script frames, engine_timer): set on frame F to 2.3 s = ceil(34.5) = 35
    frames, a timer first reads expired on frame F + 35; the world hears each timer action (World.core), not
    World.action; a stopped timer is not expired and keeps its frames, a restart runs it on; a never-set one is false
    and reported."""
    w = Core({})
    seen = []
    scripts = [script('set', [], [['SET_MILLISECOND_TIMER', 'T', 2.3]], once=True),
               script('out', [['TIMER_EXPIRED', 'T']], [['SEEN']]),
               script('never', [['TIMER_EXPIRED', 'U']], [['NEVER']])]
    ex = executor.PublicExecutor(w, scripts, 0, set(), set(), NOT, 15)
    for f in range(40):
        w.calls.clear()
        ex.step()
        if any(c[1] == 'SEEN' for c in w.calls):
            seen.append(f)
        if f == 0:
            assert w.calls[0] == ('core', 'SET_MILLISECOND_TIMER', ('T', 2.3), 'set') and ex.counters['T'] == [35, True]
    assert seen[0] == 35 and ex.counters['T'] == [-1, True] and w.seen == {'timer unset'}
    ex.action('STOP_TIMER', ['T'])
    assert not ex.timer_expired('T')
    ex.action('SET_TIMER', ['T', 5])
    ex.action('STOP_TIMER', ['T'])
    ex.step()
    assert ex.counters['T'] == [5, False]
    ex.action('RESTART_TIMER', ['T'])
    ex.action('SUB_FROM_MSEC_TIMER', [0.2, 'T'])           # ceil(3) frames off
    ex.step()
    assert ex.counters['T'] == [1, True]


def test_this_player_is_the_executors_side():
    assert port.this_player(types.SimpleNamespace(_side='Player_1'), ['<This Player>', 'x']) == ['Player_1', 'x']
    assert port.this_player(types.SimpleNamespace(), ['<This Player>']) == ['<This Player>']
