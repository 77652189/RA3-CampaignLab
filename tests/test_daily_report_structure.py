"""daily_report's structure section: the numbers come out and the lines flag (11-17 retrospective)."""
import importlib.util
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_lp = importlib.util.spec_from_file_location('labpaths', ROOT / 'experimental' / 'campaign' / 'labpaths.py')
if 'labpaths' not in sys.modules:           # daily_report imports it by name; loaded by file path, not sys.path (G4)
    sys.modules['labpaths'] = importlib.util.module_from_spec(_lp)
    _lp.loader.exec_module(sys.modules['labpaths'])
spec = importlib.util.spec_from_file_location('daily_report', ROOT / 'experimental' / 'campaign' / 'daily_report.py')
dr = importlib.util.module_from_spec(spec)
spec.loader.exec_module(dr)


def _logs(tmp_path, worst, secs):
    (tmp_path / 'perf').mkdir()
    (tmp_path / 'perf' / 'peak_abc.json').write_text(json.dumps({'rev': 'abc', 'multiple': 1.1, 'worst': worst}))
    (tmp_path / 'full_x.log').write_text('...\n==== 3 failed, 10 passed in %.2fs (x) ====\n' % secs)
    return tmp_path


def test_rows_name_every_number(tmp_path):
    text = '\n'.join(dr.structure(_logs(tmp_path, 1.5, 100)))
    for label in ('sim.py', '内核模块', '高峰负载（abc）', '最近全量（full_x.log）'):
        assert label in text
    assert '!! 高峰' not in text and '!! 全量' not in text


def test_lines_crossed_are_flagged(tmp_path):
    text = '\n'.join(dr.structure(_logs(tmp_path, 0.45, 12222)))
    assert '!! 高峰最慢段慢于实时' in text
    assert '!! 全量测试超过 3 小时' in text


def test_missing_sources_are_said(tmp_path):
    text = '\n'.join(dr.structure(tmp_path))
    assert '没有 perf/peak_*.json' in text and '没有跑完的 full_*.log' in text
    assert '没有 perf/peak_ai_*.json' in text


def test_ai_peak_uses_newest_reading_and_flags_slow_slice(tmp_path):
    perf = _logs(tmp_path, 1.5, 100) / 'perf'
    older, latest = perf / 'peak_ai_older.json', perf / 'peak_ai_latest.json'
    older.write_text(json.dumps({'rev': 'older', 'multiple': 2, 'worst': 1, 'ms_frame': 33.33}))
    latest.write_text(json.dumps({'rev': 'latest', 'multiple': 1.25, 'worst': 0.8, 'ms_frame': 53.33}))
    for name, stamp in (('peak_abc.json', 100), (older.name, 200), (latest.name, 300)):
        os.utime(perf / name, (stamp, stamp))

    text = '\n'.join(dr.structure(tmp_path))
    assert '高峰负载（abc）' in text
    assert '\n  高峰负载（latest）' not in text
    assert 'AI 高峰负载（latest）：全程 1.25 倍实时，最慢 10 秒 0.80 倍，平均 53.33 毫秒/帧' in text
    assert 'AI 高峰负载（older）' not in text
    assert '!! AI 高峰最慢段慢于实时' in text
    assert '!! 高峰最慢段慢于实时' not in text


def _flow_sources(tmp_path, new_reds, steps_between, wait, backlog):
    import time
    logs, re_dir = tmp_path / 'logs', tmp_path / 're'
    logs.mkdir()
    re_dir.mkdir()
    t0 = time.time() - 7200
    (logs / 'full_a.log').write_text('FAILED tests/t.py::old - x\n')
    (logs / 'full_b.log').write_text('FAILED tests/t.py::old - x\n' + ''.join(
        'FAILED tests/t.py::new%d - y\n' % i for i in range(new_reds)))
    os.utime(logs / 'full_a.log', (t0, t0))
    os.utime(logs / 'full_b.log', (t0 + 3600, t0 + 3600))
    steps = [(int(t0) + 60 * (i + 1), 'M%d something' % i) for i in range(steps_between)]
    (logs / 'cpupool_waits.jsonl').write_text(json.dumps({'t': time.time(), 'owner': 'p', 'waited': wait}) + '\n')
    (re_dir / 'handoff-r.md').write_text('## 搬完后有意改行为\n' + '- x\n' * backlog + '## 状态\n- y\n', encoding='utf-8')
    return logs, re_dir, steps


def test_flow_rows_name_every_number(tmp_path):
    logs, re_dir, steps = _flow_sources(tmp_path, 1, 4, 30, 3)
    text = '\n'.join(dr.flow(logs, re_dir, steps))
    for label in ('重构步', '4 步', '新 1 条，其间 4 步', '平均 30 秒', '搬完再改的清单：3 条'):
        assert label in text
    assert '!!' not in text


def test_flow_lines_crossed_are_flagged(tmp_path):
    logs, re_dir, steps = _flow_sources(tmp_path, 3, 2, 900, 16)
    text = '\n'.join(dr.flow(logs, re_dir, steps))
    assert '!! 全量新红平均每步超过' in text
    assert '!! 等令牌平均超过' in text
    assert '!! 搬完再改的清单超过' in text


def test_flow_missing_sources_are_said(tmp_path):
    text = '\n'.join(dr.flow(tmp_path, tmp_path, []))
    assert '不到两次全量' in text and '没有 cpupool_waits.jsonl' in text and '没有 handoff-r.md' in text
