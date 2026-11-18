"""How long each test layer may take (ADR 0035 6, docs/engine/testing.md "耗时"): a ceiling per item, read from the
full run's time record (`affected_tests.py --save-durations junit.xml` -> work/testmap/durations.json per file,
durations_tests.json per test). The guard (tests/guards/test_time_budget.py) is red past a ceiling; the daily
report's structure section shows every item against its line and flags `!!` past it.

Ceilings only go down. Lower one when a layer gets faster; never raise one to let a slow test in -- make the test
faster (a module test instead of a replay, a scene from a snapshot) or move it to the replay list on purpose.

An item with no record yet (a layer born after the last full run) is said, not guessed; a test file of the layer
with no record counts at the median file time (as affected_tests' estimate does), so a full run that records a
file nobody had timed moves the number by its real time minus that guess, not by all of it.
"""
import importlib.util
import os

_spec = importlib.util.spec_from_file_location('affected_tests', os.path.join(os.path.dirname(__file__),
                                                                               'affected_tests.py'))
at = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(at)

DURATIONS_TESTS = os.path.join(at.MAPDIR, 'durations_tests.json')

# item -> ceiling in seconds of test time (summed over tests: serial, not wall). Set at T4 (11-18):
#   modules: ADR 0035 6 gives the module layer "a few minutes" as its whole budget. It is the layer meant to grow
#     (each rule moved into engine/modules/ brings its tests), so its line is that budget, not the 31.6 s measured
#     clean (8 files, `-n 2` holding the whole CPU pool, 11-18); lower it once the layer is full.
#   guards: every pick runs them. Tightened 11-18 from 360 to 250: 205 s measured clean (all 8 files, `-n 2`
#     holding the whole CPU pool, RA3_CPU_EXCLUSIVE=1; test_architecture 171 s, test_kernel 27 s of it; the 11-15
#     record said 295 with 5 files guessed, and 227 s a loaded run 11-18). The line is ~20 % over the clean
#     reading: a full run takes its workers' tokens, so it no longer shares cores past the pool, but more workers
#     than 2 still slow each test a little.
#   conformance_group: the slowest group of the conformance runner (one test = one scene's readings). No line
#     yet (None: shown in the report, not checked): no record times single tests until a full run writes
#     durations_tests.json; set it then, 25 % over the slowest group. (A `-n 2` run of the layer 11-18 was
#     stopped at 77 of 118 groups; the layer takes ~77 min there, T2's number.)
#   daily: the daily pick's pool, every test file not on tests/replay_tests.txt; 2860 s in the 11-15 record
#     (2409 s recorded + 41 files not yet timed at the 11 s median), line 25 % over (~6 min over 8 workers). Not
#     retaken clean yet (the pool is ~45 min of test time: the whole machine for ~25 min at `-n 2`): tighten it,
#     and set conformance_group, from the coordinator's next full run, taken with RA3_CPU_EXCLUSIVE=1.
CEILING = {
    'modules': 180.0,
    'guards': 250.0,
    'conformance_group': None,
    'daily': 3600.0,
}
LABEL = {
    'modules': '模块层合计',
    'guards': '守卫层合计（每次都挑）',
    'conformance_group': '一致性跑器最慢一组',
    'daily': '日常挑选池（不在回放名单的文件合计）',
}


def records(mapdir=None):
    """({test file: seconds}, {test id: seconds}) from the time record, keyed by where the files are now."""
    mapdir = mapdir or at.MAPDIR
    files = {at.current_path(k): v for k, v in at.load_json(os.path.join(mapdir, 'durations.json')).items()}
    tests = {}
    for k, v in at.load_json(os.path.join(mapdir, 'durations_tests.json')).items():
        f, _, rest = k.partition('::')
        tests[at.current_path(f) + '::' + rest] = v
    return files, tests


def measure(files, tests, all_files, replays):
    """{item: (seconds or None when nothing of it is recorded, files counted at the median)}."""
    known = sorted(files.values())
    med = known[len(known) // 2] if known else 0.0

    def total(fs):
        fs = list(fs)
        if not any(f in files for f in fs):
            return None, 0
        guessed = [f for f in fs if f not in files]
        return round(sum(files.get(f, med) for f in fs), 1), len(guessed)

    out = {
        'modules': total(f for f in all_files if f.startswith('tests/modules/')),
        'guards': total(f for f in all_files if f.startswith(at.GUARD_LAYER + '/')),
        'daily': total(f for f in all_files if f not in replays),
    }
    groups = [v for k, v in tests.items() if k.startswith('tests/conformance/')]
    out['conformance_group'] = (round(max(groups), 1), 0) if groups else (None, 0)
    return out


def over(measured, ceilings=CEILING):
    """[(item, seconds, ceiling)] past their line."""
    assert set(measured) == set(ceilings), sorted(set(measured) ^ set(ceilings))
    return [(k, measured[k][0], ceilings[k]) for k in sorted(measured)
            if measured[k][0] is not None and ceilings[k] is not None and measured[k][0] > ceilings[k]]


def current(mapdir=None, root=None):
    """measure() on this checkout and the time record."""
    files, tests = records(mapdir)
    return measure(files, tests, at.all_test_files(root), at.replay_files())


def rows(mapdir=None, root=None):
    """(rows, flags) for the daily report's structure section."""
    mapdir = mapdir or at.MAPDIR
    path = os.path.join(mapdir, 'durations.json')
    if not os.path.exists(path):
        return ['  测试耗时：没有耗时记录（总控全量时 affected_tests.py --save-durations junit.xml）'], []
    import datetime
    when = datetime.date.fromtimestamp(os.path.getmtime(path)).isoformat()
    m = current(mapdir, root)
    out = ['  测试耗时（%s 的记录，秒，测试时间合计）：' % when]
    for k in CEILING:
        secs, guessed = m[k]
        line = CEILING[k]
        txt = '没有记录' if secs is None else '%.0f' % secs
        txt += '' if line is None else ' / 上限 %.0f' % line
        if guessed:
            txt += '（%d 个文件没记录，按中位数估）' % guessed
        out.append('    %s：%s' % (LABEL[k], txt))
    return out, ['测试耗时越线：%s %.0f 秒 > 上限 %.0f' % (LABEL[k], s, c) for k, s, c in over(m)]
