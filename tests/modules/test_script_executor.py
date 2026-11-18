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
    ex = executor.PublicExecutor(w, scripts, 1, done, disabled, NOT)
    assert isinstance(ex, port.Executor)
    ex.step()
    assert w.calls == [('cond', 'YES', (1,)), ('act', 'DO_A', ('x',), 'a'), ('cond', 'NO', ()),
                       ('cond', 'NO', ()), ('act', 'DO_C', ('y', 'z'), 'c')]
    assert done == {'c'} and w.seen == {'inverted'}
    w.calls.clear()
    ex.step()
    assert [c[1] for c in w.calls if c[0] == 'act'] == ['DO_A']


def test_this_player_is_the_executors_side():
    assert port.this_player(types.SimpleNamespace(_side='Player_1'), ['<This Player>', 'x']) == ['Player_1', 'x']
    assert port.this_player(types.SimpleNamespace(), ['<This Player>']) == ['<This Player>']
