"""Golden lock recovery on temporary files, without real polling delays."""
import importlib.util
import os
from pathlib import Path

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
    path.write_text(f'{old_pid} {old_started!r}', encoding='ascii')
    monkeypatch.setattr(golden.time, 'time', lambda: 1_000_000)
    os.utime(path, (999_970, 999_970))

    with golden.Lock(path):
        assert path.read_text(encoding='ascii').split() == [str(pid), repr(started)]
    assert not path.exists()
    assert capsys.readouterr().err.splitlines() == [f'golden: reclaimed stale lock (pid {old_pid}, age 30s)']


def test_live_holder_blocks_even_after_three_hours(tmp_path, monkeypatch, capsys):
    path = tmp_path / 'golden.lock'
    pid = os.getpid()
    owner = f'{pid} {psutil.Process(pid).create_time()!r}'
    path.write_text(owner, encoding='ascii')
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
    assert path.read_text(encoding='ascii') == owner
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
        assert len(path.read_text(encoding='ascii').split()) == 2
    assert capsys.readouterr().err.splitlines() == [
        f'golden: reclaimed stale lock (pid {pid}, age {golden.LOCK_STALE + 1}s)'
    ]
