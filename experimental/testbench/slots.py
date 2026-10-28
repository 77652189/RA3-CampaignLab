r"""Bench slots: several bench games at once (coordinator 2026-10-27).

RA3 lets one copy run: a starting game that finds the named mutex 41DAF790-... already there exits in a second
(bench 2026-10-27: a second copy exited at once; with that one mutex closed in the first copy, both ran side by
side at ~118 fps). So every bench game closes that mutex in itself once it is up, and the next one can start --
the user's own game too. A game the bench did not start (the user playing) still keeps the bench out: its mutex
stays, and the bench does not touch other processes.

Slot i has its own lock (shared\locks\bench.json for slot 1, the old name every older tool waits on; bench-2.json,
... after it) and its own shot folder (the capture shim's CNV_SHOT_DIR: shots, shots2, ...). A lock records the
holder's pid, the game's pid and the mod, so a build knows whether a running game has its mod open.

RA3_BENCH_SLOTS (default 2) sets how many games may run at once. No heavy imports: the builders use this too, and
build_lock keeps their SDK compiles one at a time (shared\locks\sdk-build.json).
"""
import ctypes
import ctypes.wintypes as wt
import datetime
import json
import os
import re
import subprocess
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
BENCH = os.environ.get('RA3_BENCH_DIR') or os.path.join(ROOT, 'work', 'testbench', 'RA3')    # the game copy
LOCKS = os.path.join(os.environ['RA3_SHARED'], 'locks') if os.environ.get('RA3_SHARED') else \
    os.path.join(os.path.dirname(ROOT), 'shared', 'locks')
SLOTS = int(os.environ.get('RA3_BENCH_SLOTS', '2'))
INSTANCE_MUTEX = '41DAF790-16F5-4881-8754-59FD8CF3B8D2'
GAME = re.compile(r'^(ra3_1\.\d+\.game|ra3\.exe|ra3ep1.*\.exe)$', re.I)


def lock_path(i):
    return os.path.join(LOCKS, 'bench.json' if i == 1 else f'bench-{i}.json')


def shots_dir(i):
    return os.path.join(BENCH, 'shots' if i == 1 else f'shots{i}')


def _tasks():
    """{pid: image name} of every process."""
    out = subprocess.run(['tasklist', '/FO', 'CSV', '/NH'], capture_output=True, text=True, errors='replace').stdout
    procs = {}
    for line in out.splitlines():
        cols = [c.strip('"') for c in line.split('","')]
        if len(cols) > 1 and cols[1].isdigit():
            procs[int(cols[1])] = cols[0]
    return procs


def holder(i, tasks=None):
    """Who holds slot i now (reslock's rule: a lock with `until` lives till then, one without while its pid lives),
    or None."""
    return _held(lock_path(i), tasks)


def _held(path, tasks=None):
    if not os.path.exists(path):
        return None
    try:
        with open(path, encoding='utf-8-sig') as f:
            held = json.load(f)
    except (OSError, ValueError):       # being written this instant: held
        return {'owner': '?', 'pid': None}
    if held.get('until'):
        return held if datetime.datetime.fromisoformat(held['until']) > datetime.datetime.now() else None
    return held if held.get('pid') in (tasks if tasks is not None else _tasks()) else None


def holders():
    tasks = _tasks()
    return {i: h for i in range(1, SLOTS + 1) if (h := holder(i, tasks))}


def games(tasks=None):
    return {pid for pid, name in (tasks if tasks is not None else _tasks()).items() if GAME.match(name)}


def foreign_games():
    """RA3 processes no bench slot started (the user playing, or an older tool's game)."""
    tasks = _tasks()
    ours = {h.get('game') for i in range(1, SLOTS + 1) if (h := holder(i, tasks))}
    return games(tasks) - ours


def take(owner, note=''):
    """The first free slot, its lock written for this process; None when all are held."""
    os.makedirs(LOCKS, exist_ok=True)
    for i in range(1, SLOTS + 1):
        path = lock_path(i)
        if holder(i) is None and os.path.exists(path):
            try:
                os.remove(path)         # a dead holder's lock
            except OSError:
                continue
        try:
            fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            continue
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            json.dump(dict(owner=owner, pid=os.getpid(), since=datetime.datetime.now().isoformat(timespec='seconds'),
                           until=None, note=note, slot=i), f)
        return i
    return None


def note_game(i, game_pid):
    """Record the slot's game pid in its lock (foreign_games tells ours from the user's by it)."""
    path = lock_path(i)
    with open(path, encoding='utf-8') as f:
        held = json.load(f)
    held['game'] = game_pid
    with open(path + '.tmp', 'w', encoding='utf-8') as f:
        json.dump(held, f)
    os.replace(path + '.tmp', path)


def release(i):
    held = holder(i)
    if held and held.get('pid') == os.getpid():
        os.remove(lock_path(i))


def mod_in_use(name):
    """A bench game has this mod open (its lock's note is the mod's skudef path)."""
    want = name.lower()
    return any(os.path.basename(os.path.dirname(h.get('note') or '')).lower() == want for h in holders().values())


def busy(name):
    """Why the mod `name` must not be rewritten now, or '': a game the bench did not start is up (it may have any
    mod open), or a bench game has this one open. Other bench games read other mods: the build goes ahead."""
    if foreign_games():
        return 'RA3 is running (not a bench game)'
    if mod_in_use(name):
        return f'a bench game has {name} open'
    return ''


def build_lock(note='', poll=3.0):
    """Wait for the one SDK build at a time and hold it; returns the release function (call it once the compile is
    done; process exit frees it too, by the pid rule). Builds share the SDK (its CNVUnits folder, BinaryAssetBuilder):
    bench 2026-10-27, two at once and one failed with an empty build log."""
    path = os.path.join(LOCKS, 'sdk-build.json')
    os.makedirs(LOCKS, exist_ok=True)
    while True:
        try:
            fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            if _held(path) is None:
                try:
                    os.remove(path)     # a dead builder's lock
                except OSError:
                    pass
            else:
                time.sleep(poll)
            continue
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            json.dump(dict(owner='sdk build', pid=os.getpid(), since=datetime.datetime.now().isoformat(timespec='seconds'),
                           until=None, note=note), f)
        break

    def release():
        held = _held(path)
        if held and held.get('pid') == os.getpid():
            os.remove(path)
    return release


# -- the one-copy mutex ------------------------------------------------------------------------------------------
_k32, _nt = ctypes.WinDLL('kernel32', use_last_error=True), ctypes.WinDLL('ntdll')
_k32.OpenProcess.restype = wt.HANDLE
_k32.GetCurrentProcess.restype = wt.HANDLE
_k32.DuplicateHandle.argtypes = [wt.HANDLE, wt.HANDLE, wt.HANDLE, ctypes.POINTER(wt.HANDLE), wt.DWORD, wt.BOOL,
                                 wt.DWORD]
_k32.CloseHandle.argtypes = [wt.HANDLE]
_nt.NtQuerySystemInformation.argtypes = [ctypes.c_ulong, ctypes.c_void_p, ctypes.c_ulong,
                                         ctypes.POINTER(ctypes.c_ulong)]
_nt.NtQueryObject.argtypes = [wt.HANDLE, ctypes.c_ulong, ctypes.c_void_p, ctypes.c_ulong,
                              ctypes.POINTER(ctypes.c_ulong)]


class _Entry(ctypes.Structure):     # SYSTEM_HANDLE_TABLE_ENTRY_INFO_EX
    _fields_ = [('Object', ctypes.c_void_p), ('Pid', ctypes.c_size_t), ('Handle', ctypes.c_size_t),
                ('Access', ctypes.c_ulong), ('Trace', ctypes.c_ushort), ('Type', ctypes.c_ushort),
                ('Attr', ctypes.c_ulong), ('Res', ctypes.c_ulong)]


class _UStr(ctypes.Structure):
    _fields_ = [('Length', ctypes.c_ushort), ('MaxLength', ctypes.c_ushort), ('Buffer', ctypes.c_void_p)]


def _handles(pid):
    size = 1 << 22
    while True:
        buf = ctypes.create_string_buffer(size)
        st = _nt.NtQuerySystemInformation(64, buf, size, ctypes.byref(ctypes.c_ulong())) & 0xFFFFFFFF
        if st != 0xC0000004:        # STATUS_INFO_LENGTH_MISMATCH: a bigger buffer
            break
        size *= 2
    if st:
        return []
    n = ctypes.c_size_t.from_buffer(buf).value
    return [e.Handle for e in (_Entry * n).from_buffer(buf, 16) if e.Pid == pid]


def _query(h, cls):
    buf = ctypes.create_string_buffer(0x1000)
    if _nt.NtQueryObject(h, cls, buf, 0x1000, ctypes.byref(ctypes.c_ulong())) != 0:
        return None
    u = _UStr.from_buffer(buf)
    return ctypes.wstring_at(u.Buffer, u.Length // 2) if u.Buffer else ''


def free_instance(pid):
    """Close the one-copy mutex inside game `pid`, so another copy can start; True once it was found and closed."""
    hp = _k32.OpenProcess(0x40, False, pid)        # PROCESS_DUP_HANDLE
    if not hp:
        return False
    me, done = _k32.GetCurrentProcess(), False
    try:
        for hv in _handles(pid):
            d = wt.HANDLE()
            if not _k32.DuplicateHandle(hp, hv, me, ctypes.byref(d), 0, False, 2):     # DUPLICATE_SAME_ACCESS
                continue
            try:
                # the type first: asking a pipe its name can hang
                hit = _query(d, 2) == 'Mutant' and (_query(d, 1) or '').endswith(INSTANCE_MUTEX)
            finally:
                _k32.CloseHandle(d)
            if hit and _k32.DuplicateHandle(hp, hv, None, None, 0, False, 1):          # DUPLICATE_CLOSE_SOURCE
                done = True
    finally:
        _k32.CloseHandle(hp)
    return done
