"""Golden lock recovery on temporary files, without real polling delays."""
import importlib.util
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
from types import SimpleNamespace

import psutil
import pytest

ROOT = Path(__file__).resolve().parents[2]
_spec = importlib.util.spec_from_file_location('golden', ROOT / 'experimental' / 'testbench' / 'golden.py')
golden = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(golden)


def _no_poll(delay):
    pytest.fail(f'stale lock waited for {delay}s')


@pytest.mark.parametrize('pid_reused', [False, True], ids=['dead', 'reused'])
def test_stale_holder_is_replaced_without_polling(tmp_path, monkeypatch, capsys, pid_reused):
    path = tmp_path / 'golden.lock'
    pid = os.getpid()
    started = psutil.Process(pid).create_time()
    old_pid = pid if pid_reused else pid + 1
    old_started = started - 0.5 if pid_reused else started
    create_time = psutil.Process.create_time

    def process_start(process):
        if not pid_reused and process.pid == old_pid:
            raise psutil.NoSuchProcess(old_pid)
        return create_time(process)

    monkeypatch.setattr(psutil.Process, 'create_time', process_start)
    monkeypatch.setattr(golden.time, 'sleep', _no_poll)
    host = socket.gethostname().casefold()
    path.write_text(f'{old_pid} {old_started!r} {host} old', encoding='utf-8')
    monkeypatch.setattr(golden.time, 'time', lambda: 1_000_000)
    os.utime(path, (999_970, 999_970))

    with golden.Lock(path):
        current = path.read_text(encoding='utf-8').split()
        assert current[:3] == [str(pid), repr(started), host]
        assert len(current) == 4 and current[3] != 'old'
    assert not path.exists()
    assert capsys.readouterr().err.splitlines() == [f'golden: reclaimed stale lock (pid {old_pid}, age 30s)']


def test_live_holder_blocks_even_after_three_hours(tmp_path, monkeypatch, capsys):
    path = tmp_path / 'golden.lock'
    pid = os.getpid()
    owner = f'{pid} {psutil.Process(pid).create_time()!r} {socket.gethostname().casefold()} live'
    path.write_text(owner, encoding='utf-8')
    monkeypatch.setattr(golden.time, 'time', lambda: 1_000_000)
    old = 1_000_000 - golden.LOCK_STALE - 1
    os.utime(path, (old, old))
    lock = golden.Lock(path)

    class WouldBlock(Exception):
        pass

    def poll(delay):
        assert delay == lock.wait
        raise WouldBlock

    monkeypatch.setattr(golden.time, 'sleep', poll)
    with pytest.raises(WouldBlock), lock:
        pytest.fail('took a live holder\'s lock')
    assert path.read_text(encoding='utf-8') == owner
    assert capsys.readouterr().err == ''


def test_legacy_lock_follows_the_age_rule(tmp_path, monkeypatch, capsys):
    path = tmp_path / 'golden.lock'
    pid = os.getpid()
    path.write_text(str(pid), encoding='ascii')
    os.utime(path, (1_000_000, 1_000_000))
    now = 1_000_000 + golden.LOCK_STALE
    lock = golden.Lock(path)

    def poll(delay):
        nonlocal now
        assert delay == lock.wait
        assert now == 1_000_000 + golden.LOCK_STALE
        assert path.read_text(encoding='ascii') == str(pid)
        now += 1

    monkeypatch.setattr(golden.time, 'time', lambda: now)
    monkeypatch.setattr(golden.time, 'sleep', poll)
    with lock:
        assert len(path.read_text(encoding='utf-8').split()) == 4
    assert capsys.readouterr().err.splitlines() == [
        f'golden: reclaimed stale lock (pid {pid}, age {golden.LOCK_STALE + 1}s)'
    ]


@pytest.mark.parametrize('expired', [False, True], ids=['fresh', 'expired'])
def test_foreign_holder_uses_age_and_cannot_remove_successor(tmp_path, monkeypatch, expired):
    path = tmp_path / 'golden.lock'
    now = 1_000_000 + golden.LOCK_STALE
    monkeypatch.setattr(golden.time, 'time', lambda: now)
    monkeypatch.setattr(socket, 'gethostname', lambda: 'recording-host')
    holder = golden.Lock(path)
    successor = golden.Lock(path)
    process = psutil.Process
    pid = os.getpid()
    started = process(pid).create_time()
    old_pid = pid + 1

    with monkeypatch.context() as remote:
        remote.setattr(golden.os, 'getpid', lambda: old_pid)
        remote.setattr(psutil, 'Process', lambda pid: SimpleNamespace(create_time=lambda: started))
        holder.__enter__()
    try:
        original = path.read_text(encoding='utf-8')
        os.utime(path, (1_000_000, 1_000_000))

        def local_process(pid):
            if pid == old_pid:
                raise psutil.NoSuchProcess(pid)
            return process(pid)

        def poll(delay):
            nonlocal now
            assert not expired
            assert now == 1_000_000 + golden.LOCK_STALE
            assert path.read_text(encoding='utf-8') == original
            now += 1

        monkeypatch.setattr(psutil, 'Process', local_process)
        monkeypatch.setattr(socket, 'gethostname', lambda: 'waiting-host')
        monkeypatch.setattr(golden.time, 'sleep', poll)
        now += expired
        successor.__enter__()
        replacement = path.read_text(encoding='utf-8')
        assert now == 1_000_000 + golden.LOCK_STALE + 1
    finally:
        holder.__exit__()
    try:
        assert path.exists(), 'the old holder removed the successor lock'
        assert replacement != original
        assert path.read_text(encoding='utf-8') == replacement
    finally:
        successor.__exit__()
    assert not path.exists()


@pytest.mark.parametrize('invalid', [False, True], ids=['denied', 'invalid'])
def test_unverifiable_holder_uses_age(tmp_path, monkeypatch, invalid):
    path = tmp_path / 'golden.lock'
    with golden.Lock(path):
        owner = path.read_text(encoding='utf-8')
    pid = -1 if invalid else os.getpid() + 1
    path.write_text(owner.replace(str(os.getpid()), str(pid), 1), encoding='utf-8')
    original = path.read_text(encoding='utf-8')
    os.utime(path, (1_000_000, 1_000_000))
    now = 1_000_000 + golden.LOCK_STALE
    process = psutil.Process

    def query(other_pid):
        if other_pid == pid and not invalid:
            raise psutil.AccessDenied(pid)
        return process(other_pid)

    def poll(delay):
        nonlocal now
        assert now == 1_000_000 + golden.LOCK_STALE
        assert path.read_text(encoding='utf-8') == original
        now += 1

    monkeypatch.setattr(psutil, 'Process', query)
    monkeypatch.setattr(golden.time, 'time', lambda: now)
    monkeypatch.setattr(golden.time, 'sleep', poll)
    with golden.Lock(path):
        assert now == 1_000_000 + golden.LOCK_STALE + 1
        assert path.read_text(encoding='utf-8') != original
    assert not path.exists()


@pytest.mark.skipif(os.name != 'nt', reason='Windows holder termination regression')
def test_killed_holder_keeps_recording_protected(tmp_path, monkeypatch):
    runner = tmp_path / 'holder.py'
    recorder = tmp_path / 'recorder.py'
    release = tmp_path / 'release'
    ready = tmp_path / 'ready'
    output = tmp_path / 'cache' / 'w-test'
    partial = output.with_suffix('.part') / 'task.gz'
    recorder.write_text('''\
from pathlib import Path
import os
import sys
import time

folder = Path(sys.argv[2])
folder.mkdir()
(folder / 'task.gz').write_text('record', encoding='ascii')
(folder / 'task.time.json').write_text('{}', encoding='ascii')
if not Path('release').exists():
    Path('ready.tmp').write_text(str(os.getpid()), encoding='ascii')
    Path('ready.tmp').rename('ready')
    deadline = time.monotonic() + 30
    while not Path('release').exists() and time.monotonic() < deadline:
        time.sleep(0.02)
''', encoding='utf-8')
    runner.write_text(f'''\
from pathlib import Path
import runpy

namespace = runpy.run_path({golden.__file__!r})
records = namespace['records']
namespace['labpaths'].ENGINE_MODEL = str(Path.cwd())
records.__globals__.update(
    CACHE=str(Path.cwd() / 'cache'), SIMRECORD_REL='recorder.py',
    base_rev=lambda *args: '1' * 40, pin_at=lambda *args: None, pin_here=lambda *args: None,
    declared=lambda *args: set(), recorder_hash=lambda: 'test', work_key=lambda root: 'w-test',
)
records(['task'], root=str(Path.cwd()), jobs=1)
''', encoding='utf-8')
    base = tmp_path / 'cache' / 'c-111111111111-test'
    base.mkdir(parents=True)
    (base / 'task.gz').touch()
    holder = subprocess.Popen([sys.executable, '-X', 'utf8', str(runner)], cwd=tmp_path)
    recording = None
    try:
        deadline = time.monotonic() + 15
        while not ready.exists():
            assert holder.poll() is None and time.monotonic() < deadline, 'recorder did not start'
            time.sleep(0.02)
        recording = psutil.Process(int(ready.read_text(encoding='ascii')))
        holder.kill()
        holder.wait(timeout=10)

        def poll(delay):
            assert partial.read_text(encoding='ascii') == 'record'
            assert recording.is_running()
            release.touch()
            recording.wait(timeout=10)

        monkeypatch.setattr(golden.time, 'sleep', poll)
        monkeypatch.setattr(golden, 'SIMRECORD_REL', 'recorder.py')
        with golden.Lock(tmp_path / 'cache' / 'golden.lock') as successor:
            assert release.exists(), 'successor took the lock while the old recorder was still live'
            assert not recording.is_running()
            golden.record(str(tmp_path), ['task'], str(output), 1, successor)
        assert (output / 'task.gz').read_text(encoding='ascii') == 'record'
        assert not partial.exists()
    finally:
        release.touch()
        if holder.poll() is None:
            holder.kill()
        holder.wait(timeout=10)
        if recording is not None:
            recording.wait(timeout=10)
