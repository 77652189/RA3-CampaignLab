"""simrecord's executor cross (experimental/cnv/simrecord.py `--executor`, `cross`; step P1): the port tap notes
each action an executor does -- the public executor's World.action, the model plug-in's World.core (it tells core()
every action, then hands only the non-core ones to action()) -- so the two lists compare; `cross` lines two cross
records up by frame and reports each field's first differing frame and count, and the frames only one side ran."""
import gzip
import importlib.util
import os
import types

from test_plans import small  # noqa: F401,I001  (tests/ is on the path by its conftest; puts experimental/cnv on it)

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_spec = importlib.util.spec_from_file_location('simrecord', os.path.join(_ROOT, 'experimental', 'cnv', 'simrecord.py'))
simrecord = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(simrecord)


class World:
    def __init__(self):
        self.calls = []

    def action(self, eng, name, args):
        self.calls.append(('action', name))

    def core(self, eng, name, args, script):
        self.calls.append(('core', name))


def test_the_tap_notes_the_public_executors_actions_and_the_plugins_core_calls():
    sc = types.SimpleNamespace(name='s1')
    eng = types.SimpleNamespace(script=sc)
    pub = simrecord.PortTap(World(), model=False)
    pub.action(eng, 'SET_FLAG', ['f', 1])
    assert pub.did == [('s1', 'SET_FLAG', ['f', '1'])]
    assert pub.inner.calls == [('action', 'SET_FLAG')]

    mod = simrecord.PortTap(World(), model=True)
    mod.core(eng, 'SET_FLAG', ('f', 1), sc)          # a core action: the plug-in only tells core()
    mod.core(eng, 'MOVE_TEAM_TO', ('t', 'wp'), sc)   # a world action: core() first, then action()
    mod.action(eng, 'MOVE_TEAM_TO', ('t', 'wp'))
    assert mod.did == [('s1', 'SET_FLAG', ['f', '1']), ('s1', 'MOVE_TEAM_TO', ['t', 'wp'])]
    assert mod.inner.calls == [('core', 'SET_FLAG'), ('core', 'MOVE_TEAM_TO'), ('action', 'MOVE_TEAM_TO')]


def _write(path, frames):
    with gzip.open(path, 'wt', encoding='utf-8') as f:
        for k, vals in frames:
            f.write(f'x{k} || ' + ' || '.join(f'{fld}={vals.get(fld, "")}' for fld in simrecord.CROSS_FIELDS) + '\n')


def test_cross_reports_each_fields_first_difference_and_the_frames_one_side_lacks(tmp_path, capsys):
    a, b = tmp_path / 'a', tmp_path / 'b'
    a.mkdir()
    b.mkdir()
    _write(a / 't.gz', [(0, {'flags': '{}'}), (1, {'flags': "{'f':1}"}), (2, {'flags': "{'f':1}", 'did': '[x]'})])
    _write(b / 't.gz', [(0, {'flags': '{}'}), (1, {'flags': '{}'})])
    _write(a / 'same.gz', [(0, {})])
    _write(b / 'same.gz', [(0, {})])
    assert simrecord.cross(str(a), str(b), show=1) == 0
    out = capsys.readouterr().out
    assert 'same: frames 0..0 vs 0..0 (1 / 1; only in A 0, only in B 0); same' in out
    assert 't: frames 0..2 vs 0..1 (3 / 2; only in A 1, only in B 0); 1 frames differ' in out
    assert 'flags      first x1, 1 frames' in out
    assert 'did' not in out.split('t: frames')[1]      # frame 2 is only in A: not compared


def test_a_timer_is_recorded_as_its_frames_left_and_one_run_out_as_minus_one():
    assert simrecord.frames_left(12.0, 2.0, 15) == 150          # 10 s at 15 frames a second
    assert simrecord.frames_left(4.3, 2.0, 15) == 34.5          # the public executor's untaken ceil shows
    assert simrecord.frames_left(2.0, 2.0, 15) == 0             # runs out this frame
    assert simrecord.frames_left(1.0, 2.0, 15) == -1            # ran out: the game's table stops at -1


def test_the_public_executor_can_run_on_the_models_clock():
    """--executor public@model: the public executor moves the model's frame on before each frame's scripts."""
    from engine.script import executor
    seen = []

    class World:
        def action(self, eng, name, args):
            seen.append((name, clock.frame))

    clock = types.SimpleNamespace(frame=0)
    sc = types.SimpleNamespace(name='s', levels=(True,), when=[], do=[['DO']], once=False)
    ex = executor.PublicExecutor(World(), [sc], 0, set(), set(), '<not>', clock=clock)
    ex.step()
    ex.step()
    assert seen == [('DO', 1), ('DO', 2)]
    assert 'public@model' in simrecord.EXECUTORS
