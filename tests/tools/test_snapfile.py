"""Step S 11c (docs/engine/sim-modules.md 9.2): a run's snapshot in a file (experimental/cnv/snapfile.py), and guard
7 across processes -- `simrecord snap` takes the cut run in one process, writes it to a file and goes on in another."""
import gzip
import io
import json
import os

import pytest

from test_plans import small  # noqa: F401,I001  (puts experimental/cnv on the path)
import simrecord  # noqa: E402
import snapfile  # noqa: E402

TASK = 'heal_a'         # guard 7's shortest fixed mission


def test_saved_and_loaded_the_same_and_whole(tmp_path):
    path = str(tmp_path / 'a' / 's.json.gz')
    snap = {'version': 1, 'kernel': {'things': [[1, ['M'], [{'x': {'$tuple': [1, 2]}}]]]}}
    sha = snapfile.save(path, snap, task='t', at=9.5)
    assert snapfile.load(path) == ({'task': 't', 'at': 9.5}, snap)
    assert sha == snapfile.digest(path) and len(sha) == 12
    assert os.listdir(tmp_path / 'a') == ['s.json.gz']        # written to a temporary name and renamed


def test_another_format_is_refused(tmp_path):
    path = str(tmp_path / 'x.json.gz')
    with gzip.open(path, 'wt', encoding='utf-8') as f:
        json.dump({'version': 8, 'kernel': {}}, f)            # a bare snapshot, not a file save wrote
    with pytest.raises(ValueError, match='not a snapfile/1 file'):
        snapfile.load(path)


def test_a_kept_start_is_named_by_its_shape():
    """A start under work/cache/snaps is read only by the shape it was taken in (simsnap's, simaisnap's versions,
    the model pin): a newer shape takes it again."""
    import simaisnap
    import simsnap
    p = snapfile.cached('aiskrand_s_600')
    assert os.path.dirname(p) == snapfile.cache_dir() and p.endswith('.json.gz')
    assert f'_v{simsnap.VERSION}-{simaisnap.VERSION}-' in os.path.basename(p)


def test_a_resume_of_another_task_is_refused(tmp_path):
    path = str(tmp_path / 's.json.gz')
    snapfile.save(path, {}, task='wfire_all', snap='0.5')
    with pytest.raises(ValueError, match='not heal_a at 0.5'):
        simrecord.run_task(TASK, io.StringIO(), snap='0.5', resume=path)


def test_guard_7_across_processes_goes_on_as_the_whole_one(tmp_path, capsys):
    """The cut run taken at half in one process, its snapshot a file, written onto the task made anew in another
    and run on: its record (two gzip members) line for line the whole one's, the ends the same."""
    assert simrecord.snap_check(str(tmp_path), [TASK], 0.5, 2) == 0, capsys.readouterr().out
    out = capsys.readouterr().out
    assert f'{TASK} same' in out and 'across processes' in out, out
    meta, snap = snapfile.load(str(tmp_path / f'{TASK}.snap.json.gz'))
    assert meta['task'] == TASK and meta['n'] > 0 and snap['version']
