"""experimental/testbench/run_queue.py: the batch queue -- input forms, result files, resume, how a fail, a dropout and a
crash are written down. The runner is faked: no game, no build."""
import json
import os
import sys

import pytest

import importlib.util  # noqa: E402

# loaded by its path, so this file needs no sys.path edit (tests/test_architecture.py G4 ratchet)
_SPEC = importlib.util.spec_from_file_location('run_queue', os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'experimental', 'testbench', 'run_queue.py'))
rq = importlib.util.module_from_spec(_SPEC)
sys.modules['run_queue'] = rq
_SPEC.loader.exec_module(rq)

PASS = ('counters (坦克在家): s0-s14: 4 | s15-s55: 0\nPASS 坦克在家 == 0 from s40 until s41: s40-s41: 0\n'
        'RESULT PASS')
FAIL = ('counters (坦克在家): s0-s55: 4\nFAIL 坦克在家 == 0 from s40 until s41: s40-s41: 4\nRESULT FAIL')
DROPOUT = FAIL + '\nBENCH DROPOUT: the capture stopped before the check was over'
NOEXPECT = 'counters (船坞): s0: 1\nRESULT NO EXPECTATIONS'


class Fake:
    """runner(mission, check, build): answers from a table of lists (one answer a call), keeps the calls."""
    def __init__(self, table):
        self.table, self.calls = table, []

    def __call__(self, mission, check, build):
        self.calls.append((mission, check, build))
        answers = self.table[(mission, check)]
        return answers.pop(0) if len(answers) > 1 else answers[0]


def go(queue, runner, tmp_path, **kw):
    lines = []
    kw = dict(jobs=1, git_head='abc1234', out=lines.append) | kw
    return rq.run_queue(queue, runner, str(tmp_path), **kw), lines


# ------------------------------------------------------------ input

def test_items_from_the_command_line():
    assert rq.collect(['aitfany:a', 'aitfmax:a']) == [('aitfany', 'a'), ('aitfmax', 'a')]


@pytest.mark.parametrize('bad', ['', ':a', 'a b:c', 'a:b:c', 'a/b:c', 'a:b-c'])
def test_a_bad_item_is_refused(bad):
    with pytest.raises(ValueError):
        rq.parse_item(bad)


def test_an_item_without_a_check_means_the_empty_check():
    assert rq.parse_item('pairbuild') == ('pairbuild', '') == rq.parse_item('pairbuild:')


def test_a_file_one_check_a_line_with_comments_and_blanks(tmp_path):
    f = tmp_path / 'q.txt'
    f.write_text('# engine\naitfany:a\n\n  aitfmax:a   # the max one\n', encoding='utf-8')
    assert rq.read_list(str(f)) == [('aitfany', 'a'), ('aitfmax', 'a')]


def test_the_three_forms_join_and_a_check_is_queued_once(tmp_path):
    f = tmp_path / 'q.txt'
    f.write_text('b:2\nc:3\n', encoding='utf-8')
    got = rq.collect(['a:1', 'b:2'], str(f), 'engine_', lister=lambda p: [('c', '3'), ('d', '4')] if p == 'engine_' else [])
    assert got == [('a', '1'), ('b', '2'), ('c', '3'), ('d', '4')]


def test_a_prefix_that_matches_nothing_is_an_error():
    with pytest.raises(ValueError, match='no check file'):
        rq.collect([], prefix='nope_', lister=lambda p: [])


def test_the_prefix_lists_the_checks_of_the_matching_check_files():
    got = rq.listing('engine_aiteamfilter')
    # the module grows (B round 81 added aitfland ...): the first six as declared, every one check 'a', no repeats
    assert got[:6] == [(b, 'a') for b in ('aitfany', 'aitfnone', 'aitfall', 'aitfki', 'aitfke', 'aitfmax')]
    assert all(c == 'a' for _, c in got) and len(set(got)) == len(got)
    assert rq.listing('no_such_prefix_') == []


# ------------------------------------------------------------ verdicts

@pytest.mark.parametrize('code, output, verdict', [
    (0, PASS, 'PASS'),
    (0, FAIL, 'FAIL'),
    (0, DROPOUT, 'DROPOUT'),
    (0, NOEXPECT, 'NOEXPECT'),
    (0, 'BUILD FAILED:\nlint: x', 'ERROR'),
    (0, 'bench_start: BENCH: the game is running', 'ERROR'),      # stopped before the judge: no RESULT line
    (1, 'Traceback (most recent call last): ...', 'ERROR'),
    (None, 'TIMEOUT after 5s', 'ERROR'),
])
def test_what_each_output_is(code, output, verdict):
    assert rq.judge(code, output)[0] == verdict


def test_the_expectation_lines_and_the_readings_are_picked_out():
    verdict, expectations, readings = rq.judge(0, 'build: ok\n' + PASS)
    assert expectations == ['PASS 坦克在家 == 0 from s40 until s41: s40-s41: 0']
    assert readings.startswith('counters (坦克在家)')


# ------------------------------------------------------------ results

def test_a_result_file_and_a_summary_line_for_every_check(tmp_path):
    results, lines = go([('aitfany', 'a'), ('aitfmax', 'a')], Fake({('aitfany', 'a'): [(0, PASS)], ('aitfmax', 'a'): [(0, FAIL)]}),
                        tmp_path)
    assert {k: r['verdict'] for k, r in results.items()} == {('aitfany', 'a'): 'PASS', ('aitfmax', 'a'): 'FAIL'}
    saved = json.loads((tmp_path / 'aitfany__a.json').read_text(encoding='utf-8'))
    assert saved['mission'] == 'aitfany' and saved['check'] == 'a' and saved['head'] == 'abc1234'
    assert saved['verdict'] == 'PASS' and saved['seconds'] >= 0 and saved['start']
    assert saved['expectations'] == ['PASS 坦克在家 == 0 from s40 until s41: s40-s41: 0']
    assert saved['readings'].startswith('counters (坦克在家)')
    rows = (tmp_path / 'summary.tsv').read_text(encoding='utf-8').splitlines()
    assert rows[0].split('\t') == list(rq.SUMMARY_COLUMNS)
    body = sorted(r.split('\t')[2:5] for r in rows[1:])
    assert body == [['aitfany', 'a', 'PASS'], ['aitfmax', 'a', 'FAIL']]
    assert len(lines) == 2 and all(x.split()[0] in ('PASS', 'FAIL') for x in lines)     # one line a check


def test_a_second_run_adds_a_summary_line_and_replaces_the_json(tmp_path):
    runner = Fake({('m', 'c'): [(0, FAIL), (0, PASS)]})
    go([('m', 'c')], runner, tmp_path)
    go([('m', 'c')], runner, tmp_path)
    assert len((tmp_path / 'summary.tsv').read_text(encoding='utf-8').splitlines()) == 3       # header + 2 runs
    assert json.loads((tmp_path / 'm__c.json').read_text(encoding='utf-8'))['verdict'] == 'PASS'


def test_the_output_prints_only_with_verbose(tmp_path):
    _, quiet = go([('m', 'c')], Fake({('m', 'c'): [(0, PASS)]}), tmp_path)
    _, loud = go([('m', 'c')], Fake({('m', 'c'): [(0, PASS)]}), tmp_path, verbose=True)
    assert len(quiet) == 1 and 'RESULT PASS' not in '\n'.join(quiet)
    assert 'RESULT PASS' in '\n'.join(loud)


# ------------------------------------------------------------ failures and dropouts

def test_a_dropout_is_run_again_by_itself_without_building(tmp_path):
    runner = Fake({('m', 'c'): [(0, DROPOUT), (0, PASS)]})
    results, lines = go([('m', 'c')], runner, tmp_path)
    assert runner.calls == [('m', 'c', True), ('m', 'c', False)]
    r = results[('m', 'c')]
    assert r['verdict'] == 'PASS' and r['attempts'] == ['DROPOUT', 'PASS']
    assert 'DROPOUT>PASS' in lines[0]


def test_a_dropout_that_stays_is_recorded_as_one(tmp_path):
    runner = Fake({('m', 'c'): [(0, DROPOUT)]})
    results, _ = go([('m', 'c')], runner, tmp_path, retry=2)
    assert len(runner.calls) == 3 and results[('m', 'c')]['verdict'] == 'DROPOUT'
    assert json.loads((tmp_path / 'm__c.json').read_text(encoding='utf-8'))['attempts'] == ['DROPOUT'] * 3


def test_no_retry_leaves_the_first_dropout(tmp_path):
    runner = Fake({('m', 'c'): [(0, DROPOUT)]})
    results, _ = go([('m', 'c')], runner, tmp_path, retry=0)
    assert len(runner.calls) == 1 and results[('m', 'c')]['verdict'] == 'DROPOUT'


def test_a_fail_is_not_run_again(tmp_path):
    runner = Fake({('m', 'c'): [(0, FAIL), (0, PASS)]})
    assert go([('m', 'c')], runner, tmp_path)[0][('m', 'c')]['verdict'] == 'FAIL'
    assert len(runner.calls) == 1


def test_a_runner_that_crashes_is_an_error_and_the_queue_goes_on(tmp_path):
    def runner(mission, check, build):
        if mission == 'bad':
            raise OSError('no python')
        return 0, PASS
    results, _ = go([('bad', 'c'), ('good', 'c')], runner, tmp_path)
    assert results[('bad', 'c')]['verdict'] == 'ERROR' and 'no python' in results[('bad', 'c')]['output']
    assert results[('good', 'c')]['verdict'] == 'PASS'
    assert (tmp_path / 'bad__c.json').exists()


def test_a_build_failure_and_a_timeout_are_errors(tmp_path):
    runner = Fake({('a', 'c'): [(0, 'BUILD FAILED:\nlint')], ('b', 'c'): [(None, 'TIMEOUT after 5s')]})
    results, _ = go([('a', 'c'), ('b', 'c')], runner, tmp_path)
    assert [r['verdict'] for r in results.values()] == ['ERROR', 'ERROR']
    assert len(runner.calls) == 2                                   # an error is not retried


# ------------------------------------------------------------ resume

def test_resume_skips_a_result_at_the_same_head(tmp_path):
    go([('m', 'c')], Fake({('m', 'c'): [(0, FAIL)]}), tmp_path)
    runner = Fake({('m', 'c'): [(0, PASS)], ('n', 'c'): [(0, PASS)]})
    results, lines = go([('m', 'c'), ('n', 'c')], runner, tmp_path, resume=True)
    assert runner.calls == [('n', 'c', True)] and list(results) == [('n', 'c')]
    assert lines[0].startswith('SKIP') and 'FAIL' in lines[0]


def test_resume_runs_again_after_a_new_head(tmp_path):
    go([('m', 'c')], Fake({('m', 'c'): [(0, PASS)]}), tmp_path)
    runner = Fake({('m', 'c'): [(0, PASS)]})
    go([('m', 'c')], runner, tmp_path, resume=True, git_head='def5678')
    assert len(runner.calls) == 1


def test_resume_any_skips_a_result_made_at_another_head(tmp_path):
    go([('m', 'c')], Fake({('m', 'c'): [(0, PASS)]}), tmp_path)
    runner = Fake({('m', 'c'): [(0, PASS)]})
    results, lines = go([('m', 'c')], runner, tmp_path, resume=True, any_head=True, git_head='def5678')
    assert runner.calls == [] and results == {} and 'abc1234' in lines[0]


@pytest.mark.parametrize('output', [DROPOUT, 'BUILD FAILED:\nx'])
def test_resume_runs_again_what_never_got_a_verdict(tmp_path, output):
    go([('m', 'c')], Fake({('m', 'c'): [(0, output)]}), tmp_path, retry=0)
    runner = Fake({('m', 'c'): [(0, PASS)]})
    go([('m', 'c')], runner, tmp_path, resume=True)
    assert len(runner.calls) == 1


def test_without_resume_everything_runs_again(tmp_path):
    go([('m', 'c')], Fake({('m', 'c'): [(0, PASS)]}), tmp_path)
    runner = Fake({('m', 'c'): [(0, PASS)]})
    go([('m', 'c')], runner, tmp_path)
    assert len(runner.calls) == 1


def test_a_damaged_result_file_is_not_a_result(tmp_path):
    (tmp_path / 'm__c.json').write_text('{ not json', encoding='utf-8')
    runner = Fake({('m', 'c'): [(0, PASS)]})
    go([('m', 'c')], runner, tmp_path, resume=True)
    assert len(runner.calls) == 1


# ------------------------------------------------------------ jobs

def test_jobs_run_checks_side_by_side(tmp_path):
    import threading
    both = threading.Barrier(2, timeout=10)             # passes only when two runs are inside the runner at once

    def runner(mission, check, build):
        both.wait()
        return 0, PASS
    results, _ = go([('a', 'c'), ('b', 'c')], runner, tmp_path, jobs=2)
    assert [r['verdict'] for r in results.values()] == ['PASS', 'PASS']
    assert len((tmp_path / 'summary.tsv').read_text(encoding='utf-8').splitlines()) == 3


def test_the_summary_sentence():
    r = lambda v: dict(verdict=v)  # noqa: E731
    assert rq.summary_line({1: r('PASS'), 2: r('PASS'), 3: r('FAIL')}) == '3 run: FAIL 1, PASS 2'
    assert rq.summary_line({}) == '0 run'
