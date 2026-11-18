"""The public script executor (engine/script/executor.py, step P1, Z) on the script executor port
(engine/ports/scripts.py): with a minimal World it asks every condition and does every action through the port, once
a frame, in the game's order (script-semantics.md 1: side lists, loose scripts then groups, subroutines only when
called); a once script fires once, an inactive or off-level one not at all; the NOT mark negates and is reported as
an assumption. '<This Player>' reads as the executor's side. The rules behind the names are the world's
(simcond / simact), tested by name there; this is the executor's own loop only."""
import types

from test_plans import small  # noqa: F401,I001  (tests/ is on the path by its conftest; puts experimental/cnv on it)
from engine.ports import scripts as port  # noqa: E402
from engine.script import executor  # noqa: E402
from engine.script import lists  # noqa: E402

NOT = '<not>'


class Log(port.World):
    def __init__(self, truth):
        self.truth, self.calls, self.seen = truth, [], set()

    def condition(self, eng, name, args):
        self.calls.append(('cond', name, tuple(args)))
        return self.truth.get(name, False)

    def action(self, eng, name, args):
        self.calls.append(('act', name, tuple(port.this_player(eng, args)), eng.script.name))

    def assumed(self, what):
        self.seen.add(what)


def script(name, when, do, once=False, levels=(True, True, True), active=True, sub=False):
    return types.SimpleNamespace(name=name, when=when, do=do, once=once, levels=levels, active=active, sub=sub)


def run(w, scripts, level=0):
    """Our compiled scripts as the executor's one list (engine/script/lists.from_cnv)."""
    return executor.PublicExecutor(w, lists.from_cnv(scripts, NOT), level, 15, assume_inverted=True)


def test_each_frame_the_holding_scripts_act_in_file_order_through_the_port():
    w = Log({'YES': True})
    scripts = [script('a', [['YES', 1]], [['DO_A', 'x']]),
               script('b', [['NO']], [['DO_B']]),
               script('c', [['NO', NOT]], [['DO_C', 'y', 'z']], once=True),
               script('d', [], [['DO_D']], levels=(True, False, True)),
               script('e', [], [['DO_E']], active=False)]
    ex = run(w, scripts, 1)
    assert isinstance(ex, port.Executor)
    ex.step()
    assert w.calls == [('cond', 'YES', (1,)), ('act', 'DO_A', ('x',), 'a'), ('cond', 'NO', ()),
                       ('cond', 'NO', ()), ('act', 'DO_C', ('y', 'z'), 'c')]
    assert not ex.script_named('c').active and w.seen == {'inverted'}
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
    ex = run(w, scripts)
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


def sc(name, *acts, **kw):
    """A script that holds every frame, doing `acts` (name, *args each)."""
    C = lists.Content
    return lists.Script(name, [[C('CONDITION_TRUE')]], [C(a[0], tuple(a[1:])) for a in acts],
                        once=kw.pop('once', False), **kw)


def test_side_lists_loose_scripts_then_groups_and_subroutines_only_when_called():
    """script-semantics.md 1: the lists in side order, each its loose scripts first (file order), then its active
    groups that are not subroutines; a subroutine (group or script) runs only when CALL_SUBROUTINE calls it;
    ENABLE_SCRIPT / DISABLE_SCRIPT switch a group and a script of the name and arm a once script that fired again
    (8 item 10); the switches and the call are the executor's, the world told (World.core)."""
    G = lists.Group
    p1 = lists.ScriptList('P1', [G('g', [sc('in g', ('G',))]),
                                 sc('loose', ('L', '<This Player>')),
                                 G('off', [sc('in off', ('OFF',))], active=False),
                                 G('sub', [sc('in sub', ('SUB',))], subroutine=True),
                                 sc('subscript', ('SS',), subroutine=True)])
    p2 = lists.ScriptList('P2', [sc('caller', ('CALL_SUBROUTINE', 'sub'), ('CALL_SUBROUTINE', 'subscript'),
                                    ('ENABLE_SCRIPT', 'off'), ('BEFORE',), once=True),
                                 G('outer', [G('inner', [sc('nested', ('N',))])])])
    w = Core({})
    ex = executor.PublicExecutor(w, [p1, p2], 0, 15)
    ex.step()
    assert [c[1:] for c in w.calls] == [
        ('L', ('P1',), 'loose'), ('G', (), 'in g'),
        ('CALL_SUBROUTINE', ('sub',), 'caller'), ('SUB', (), 'in sub'),
        ('CALL_SUBROUTINE', ('subscript',), 'caller'), ('SS', (), 'subscript'),
        ('ENABLE_SCRIPT', ('off',), 'caller'), ('BEFORE', (), 'caller'), ('N', (), 'nested')]
    assert not ex.script_named('caller').active
    w.calls.clear()
    ex.step()
    assert [c[1] for c in w.calls] == ['L', 'G', 'OFF', 'N']
    ex.action('DISABLE_SCRIPT', ['g'])
    ex.action('ENABLE_SCRIPT', ['caller'])
    w.calls.clear()
    ex.step()
    assert [c[1] for c in w.calls if c[0] == 'act'] == ['L', 'OFF', 'SUB', 'SS', 'BEFORE', 'N']


def test_an_or_of_ands_its_else_actions_and_a_delayed_script():
    """script-semantics.md 1-2: OR groups of ANDed conditions, an empty OR group skipped (a script with none never
    holds); else actions when none holds, a once script then off too; a disabled condition holds (INFERRED); an
    interval script first 0..2 s in at random, then every interval seconds."""
    S, C = lists.Script, lists.Content
    w = Log({'YES': True})
    scripts = [S('or', [[C('NO')], [], [C('YES'), C('NO', enabled=False)]], [C('OR')], once=False),
               S('none', [], [C('NONE')], once=False),
               S('else', [[C('NO')]], [C('THEN')], [C('ELSE')], once=True),
               S('every 2', [[C('CONDITION_TRUE')]], [C('TICK')], once=False, interval=2)]
    ex = executor.PublicExecutor(w, [lists.ScriptList('', scripts)], 0, 15, seed=0)
    ticks = []
    for f in range(1, 100):
        w.calls.clear()
        ex.step()
        acts = [c[1] for c in w.calls if c[0] == 'act']
        assert acts[0] == 'OR' and ('ELSE' in acts) == (f == 1) and 'NONE' not in acts and 'THEN' not in acts
        if 'TICK' in acts:
            ticks.append(f)
    assert 0 <= ticks[0] <= 30 and len(ticks) >= 3 and all(b - a == 30 for a, b in zip(ticks, ticks[1:]))
