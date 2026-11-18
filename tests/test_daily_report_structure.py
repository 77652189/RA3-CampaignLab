"""daily_report's structure section: the numbers come out and the lines flag (11-17 retrospective)."""
import importlib.util
import json
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
