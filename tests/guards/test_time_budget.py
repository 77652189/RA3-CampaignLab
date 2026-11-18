"""Each test layer stays under its time ceiling (ADR 0035 6): experimental/testbench/time_budget.py holds the lines,
the last full run's time record holds the numbers. Ceilings only go down (the module's docstring says why)."""
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
_spec = importlib.util.spec_from_file_location('time_budget', ROOT / 'experimental' / 'testbench' / 'time_budget.py')
tb = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(tb)


def test_the_layers_stay_under_their_ceilings():
    m = tb.current()
    if all(secs is None for secs, _ in m.values()):
        pytest.skip('no time record (affected_tests.py --save-durations junit.xml after a full run)')
    grew = tb.over(m)
    assert not grew, (f'{grew}: a test layer takes longer than its line (experimental/testbench/time_budget.py) -- '
                      'make the new tests faster or put a whole-game one on tests/replay_tests.txt; never raise a line')


def test_every_item_has_a_label():
    assert set(tb.LABEL) == set(tb.CEILING)


# a synthetic tree: two module files, a guard, a replay, a plain file; one module file and the plain file timed
FILES = ['tests/modules/test_a.py', 'tests/modules/test_b.py', 'tests/guards/test_g.py', 'tests/test_replay.py',
         'tests/test_plain.py', 'tests/conformance/test_readings.py']
REPLAYS = {'tests/test_replay.py': 'game', 'tests/conformance/test_readings.py': 'game'}
TIMES = {'tests/modules/test_a.py': 2.0, 'tests/guards/test_g.py': 9.0, 'tests/test_replay.py': 500.0,
         'tests/test_plain.py': 4.0, 'tests/conformance/test_readings.py': 300.0}
TESTS = {'tests/conformance/test_readings.py::test_r[x]': 120.0, 'tests/conformance/test_readings.py::test_r[y]': 180.0,
         'tests/test_replay.py::test_long': 500.0}


def test_measure_sums_each_layer_and_guesses_the_untimed_at_the_median():
    m = tb.measure(TIMES, TESTS, FILES, REPLAYS)
    assert m['modules'] == (2.0 + 9.0, 1)            # test_b untimed: median of 2, 4, 9, 300, 500 = 9
    assert m['guards'] == (9.0, 0)
    assert m['daily'] == (2.0 + 9.0 + 9.0 + 4.0, 1)  # every file off the replay list
    assert m['conformance_group'] == (180.0, 0)


def test_a_layer_with_nothing_recorded_is_said_not_guessed():
    m = tb.measure({'tests/test_plain.py': 4.0}, {}, FILES, REPLAYS)
    assert m['modules'] == m['guards'] == m['conformance_group'] == (None, 0)
    assert m['daily'] == (16.0, 3)                    # the plain file timed, three guessed at its 4 s
    assert tb.over(m, dict.fromkeys(tb.CEILING, 0.0)) == [('daily', 16.0, 0.0)]


def test_a_layer_past_its_line_is_caught():
    m = tb.measure(TIMES, TESTS, FILES, REPLAYS)
    lines = {'modules': 11.0, 'guards': 9.0, 'conformance_group': 180.0, 'daily': 24.0}
    assert tb.over(m, lines) == []
    lines['conformance_group'] = 179.0
    assert tb.over(m, lines) == [('conformance_group', 180.0, 179.0)]
    assert tb.over(m, dict(lines, conformance_group=None)) == []     # no line yet: shown, not checked


def test_the_report_rows_and_flags(tmp_path):
    (tmp_path / 'durations.json').write_text(json.dumps({'tests/guards/test_architecture.py': 99999.0}))
    rows, flags = tb.rows(str(tmp_path))
    text = '\n'.join(rows)
    assert '守卫层合计' in text and '模块层合计：没有记录' in text
    assert any(f.startswith('测试耗时越线：守卫层合计') and '上限 360' in f for f in flags)   # the rest at that median
    assert tb.rows(str(tmp_path / 'none')) == (
        ['  测试耗时：没有耗时记录（总控全量时 affected_tests.py --save-durations junit.xml）'], [])
