"""The bench's ra3ext switch (engine line D, ADR 0027/0028): a mod starts through ra3ext_launch only when its folder
holds ra3ext.allow, which a build writes exactly for a mission with ext=True; every other start is the plain Popen,
as before -- without the game."""
import os
import subprocess
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'experimental', 'testbench'))
sys.path.insert(0, os.path.join(ROOT, 'experimental', 'cnv'))
import harness  # noqa: E402


def game_args(sku):
    return ['RA3_1.13.game', '-config', 'x.SkuDef', '-win'] + (['-modConfig', str(sku)] if sku else [])


@pytest.fixture
def mod(tmp_path):
    sku = tmp_path / 'CampExt_1.0.skudef'
    sku.write_text('mod-game 1.12\r\n')
    return tmp_path, sku


def test_no_allow_file_no_retail_no_ext(mod):
    folder, sku = mod
    assert not harness.ext_wanted(game_args(sku))
    assert not harness.ext_wanted(game_args(None))
    assert not harness.ext_wanted(['RA3_1.13.game', '-modConfig'])      # a dangling flag
    (folder / 'ra3ext.allow').write_text('')
    assert harness.ext_wanted(game_args(sku))


def test_the_launcher_command_wraps_the_game_command():
    args = game_args('m.skudef')
    cmd = harness.ext_command(args, 'r/ra3ext.log')
    assert cmd[0] == harness.EXT_LAUNCH and cmd[cmd.index('--log') + 1] == 'r/ra3ext.log'
    assert cmd[cmd.index('--cwd') + 1] == harness.BENCH
    assert cmd[cmd.index('--') + 1:] == args


def test_the_launcher_line_is_read():
    got = harness.parse_launch('noise\npid=24376 inject=yes reason=our mod dll_loaded=yes\n')
    assert got == dict(pid='24376', inject='yes', reason='our mod', dll_loaded='yes')
    assert harness.parse_launch('CreateProcess failed 2') == {}


class Started(Exception):
    pass


def test_a_plain_mod_starts_with_popen_as_before(monkeypatch, mod):
    folder, sku = mod
    seen = []
    monkeypatch.setattr(harness.subprocess, 'Popen', lambda a, **kw: seen.append(a) or 'popen')
    monkeypatch.setattr(harness.subprocess, 'run', lambda *a, **kw: (_ for _ in ()).throw(Started('launcher')))
    s = harness.Session()
    s.run_dir = str(folder)
    assert s._start(game_args(sku), {}) == 'popen' and seen == [game_args(sku)]


def test_a_mod_asking_for_ext_goes_through_the_launcher(monkeypatch, mod, tmp_path):
    folder, sku = mod
    (folder / 'ra3ext.allow').write_text('')
    exe = tmp_path / 'ra3ext_launch.exe'
    exe.write_text('')
    monkeypatch.setattr(harness, 'EXT_LAUNCH', str(exe))
    monkeypatch.setattr(harness.subprocess, 'Popen', lambda *a, **kw: (_ for _ in ()).throw(Started('popen')))
    ran = []

    def run(cmd, **kw):
        ran.append(cmd)
        return subprocess.CompletedProcess(cmd, 0, 'pid=4242 inject=yes reason=our mod dll_loaded=yes\n', '')
    monkeypatch.setattr(harness.subprocess, 'run', run)
    monkeypatch.setattr(harness, 'GameProcess', lambda pid: ('game', pid))
    s = harness.Session()
    s.run_dir = str(folder)
    assert s._start(game_args(sku), {}) == ('game', 4242)
    assert ran[0][0] == str(exe) and s.ext_log == os.path.join(str(folder), 'ra3ext.log')


def test_a_launch_without_the_dll_is_an_error_and_the_game_goes(monkeypatch, mod, tmp_path):
    folder, sku = mod
    (folder / 'ra3ext.allow').write_text('')
    exe = tmp_path / 'ra3ext_launch.exe'
    exe.write_text('')
    monkeypatch.setattr(harness, 'EXT_LAUNCH', str(exe))
    monkeypatch.setattr(harness.subprocess, 'run', lambda cmd, **kw: subprocess.CompletedProcess(
        cmd, 0, 'pid=4242 inject=yes reason=our mod dll_loaded=no\n', ''))
    killed = []

    class Game:
        def __init__(self, pid):
            self.pid = pid

        def kill(self):
            killed.append(self.pid)
    monkeypatch.setattr(harness, 'GameProcess', Game)
    s = harness.Session()
    s.run_dir = str(folder)
    with pytest.raises(harness.BenchError, match='not in the game'):
        s._start(game_args(sku), {})
    assert killed == [4242]


def test_a_missing_launcher_is_an_error_not_a_plain_start(monkeypatch, mod, tmp_path):
    folder, sku = mod
    (folder / 'ra3ext.allow').write_text('')
    monkeypatch.setattr(harness, 'EXT_LAUNCH', str(tmp_path / 'none.exe'))
    s = harness.Session()
    s.run_dir = str(folder)
    with pytest.raises(harness.BenchError, match='missing'):
        s._start(game_args(sku), {})


def test_game_process_polls_a_real_child():
    p = subprocess.Popen([sys.executable, '-c', 'import sys; sys.exit(7)'])
    g = harness.GameProcess(p.pid)
    assert g.wait(10) == 7 and g.poll() == 7
    p.wait()
    gone = harness.GameProcess(2 ** 31 - 1)
    assert gone.poll() == -1


def test_a_build_marks_ext_exactly_when_asked(tmp_path):
    import package
    package.mark_ext(str(tmp_path), True)
    assert (tmp_path / 'ra3ext.allow').exists()
    package.mark_ext(str(tmp_path), False)
    assert not (tmp_path / 'ra3ext.allow').exists()
    package.mark_ext(str(tmp_path), False)           # nothing to remove: fine
    assert package.ModSpec(name='x').ext is False
