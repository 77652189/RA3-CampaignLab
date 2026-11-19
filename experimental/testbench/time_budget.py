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
# One test's limit, seconds, by its layer (T7, 11-18): tests/conftest.py marks every test that has no `timeout` marker
# of its own with it, so a test that hangs is red and named instead of spinning (R3's pull looped on a retail map 11-18:
# two workers spun 56 minutes each, holding their CPU tokens, and nobody saw). A marker wins over `--timeout` on the
# command line. On Windows pytest-timeout ends the process (os._exit) after dumping the stacks ("Stack of
# pytest_timeout <test id>"): under xdist that is the worker -- the run says "worker 'gwN' crashed while running <test
# id>", counts it failed and starts another worker -- with -n 0 the whole run. A dead process's CPU token is free
# (cpupool: no live pid, no token). From the 11-18 full run's single-test times (work/logs/junit_full_1118b.xml): the
# longest module test 12 s, tool 10 s, guard 81 s (test_architecture's g3b), any other non-replay 99 s, a replay
# 456 s (golden retail_a02); about 5-10 times that, for a loaded machine. Raise one only with the test's measured time.
TEST_TIMEOUT = {
    'modules': 120.0,       # tests/modules/
    'tools': 120.0,         # tests/tools/
    'content': 120.0,       # tests/content/
    'guards': 600.0,        # tests/guards/
    'other': 900.0,         # every other file not on tests/replay_tests.txt
    'replay': 2400.0,       # a file on tests/replay_tests.txt (whole games, the conformance runner, golden)
}
TIMEOUT_SCALE_ENV = 'RA3_TEST_TIMEOUT_SCALE'    # multiplies every limit (0: none; the T7 test shrinks them)


def timeout_layer(path, replays):
    """TEST_TIMEOUT's key for a test file ('tests/<layer>/test_x.py', '/' separated); replays: the replay files'
    paths (replay_files())."""
    if path in replays:
        return 'replay'
    parts = path.split('/')
    if len(parts) > 2 and parts[1] in TEST_TIMEOUT and parts[1] not in ('other', 'replay'):
        return parts[1]
    return 'other'


def timeout_for(path, replays, env=None):
    """One test's limit in seconds for a test in that file (0: no limit)."""
    env = os.environ if env is None else env
    scale = float(env.get(TIMEOUT_SCALE_ENV) or 1)
    return TEST_TIMEOUT[timeout_layer(path, replays)] * scale


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
