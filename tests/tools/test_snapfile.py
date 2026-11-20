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
    with pytest.raises(ValueError, match=f'not a {snapfile.FORMAT} file'):
        snapfile.load(path)


def test_a_kept_start_is_named_by_its_shape():
    """A start under work/cache/snaps is read only by the shape it was taken in (simsnap's, simaisnap's versions,
    the model pin): a newer shape takes it again."""
    import engine.state.ai_snapshot as simaisnap
    import engine.state.snapshot as simsnap
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


# ---- review 1119u (R2 part)
def test_a_file_taken_in_another_shape_is_refused_and_a_resume_of_it_writes_nothing(tmp_path, monkeypatch):
    """u P2 #1: the shape (simsnap / simaisnap versions, the engine model's pin) goes with the file; one taken in
    another (another model) is refused by load, so a resume of it is refused before it runs."""
    path = str(tmp_path / 's.json.gz')
    monkeypatch.setattr(snapfile, 'shape', lambda: '8-10-other00')
    snapfile.save(path, {}, task=TASK, snap='0.5')
    monkeypatch.undo()
    with pytest.raises(ValueError, match='taken in shape 8-10-other00'):
        snapfile.load(path)
    out = io.StringIO()
    with pytest.raises(ValueError, match='taken in shape'):
        simrecord.run_task(TASK, out, snap='0.5', resume=path)
    assert out.getvalue() == ''


def test_save_names_the_bytes_it_wrote_not_what_another_writer_left_there(tmp_path, monkeypatch):
    """u P2 #2: two writers of one file -- the sha save returns is of its own bytes, not read back from the path
    another may have replaced since."""
    path = str(tmp_path / 's.json.gz')
    mine = snapfile.save(str(tmp_path / 'alone.json.gz'), {'a': 1}, task='t')
    real = os.replace

    def replace_then_another_writes(src, dst):
        real(src, dst)
        with open(dst, 'wb') as f:      # the other writer's rename, right after ours
            f.write(b'another writer')

    monkeypatch.setattr(snapfile.os, 'replace', replace_then_another_writes)
    assert snapfile.save(path, {'a': 1}, task='t') == mine != snapfile.digest(path)


def test_a_rename_that_fails_leaves_no_temporary_file_and_its_name_is_short(tmp_path, monkeypatch):
    """u P3 #2: a reader holding the file on Windows (PermissionError on rename): tried again, then the error, the
    temporary file gone; its name short whatever the path's length."""
    folder = tmp_path / 'k'
    path = str(folder / ('x' * 120 + '.json.gz'))
    tried = []

    def held(src, dst):
        tried.append(os.path.basename(src))
        raise PermissionError(13, 'in use', dst)

    monkeypatch.setattr(snapfile.os, 'replace', held)
    monkeypatch.setattr(snapfile.time, 'sleep', lambda s: None)
    with pytest.raises(PermissionError):
        snapfile.save(path, {}, task='t')
    assert len(tried) == snapfile.RETRIES and all(len(n) < 30 for n in tried)
    assert os.listdir(folder) == []


def test_a_fresh_process_reads_a_file_of_this_shape(tmp_path):
    """Review 1119z P2 #4: a process that made no Sim (imported no engine.modules) loads a file this one wrote, and
    the shape it computes is this one's."""
    import subprocess
    import sys
    from pathlib import Path

    import engine.state.snapshot as simsnap
    path = str(tmp_path / 's.json.gz')
    snapfile.save(path, {'a': 1}, task='t')
    cnv = Path(__file__).resolve().parents[2] / 'experimental' / 'cnv'
    code = ('import sys, snapfile, engine.state.snapshot as simsnap; assert "engine.modules" not in sys.modules; '
            'print(snapfile.load(sys.argv[1])[0]["task"], simsnap.version())')
    out = subprocess.run([sys.executable, '-B', '-X', 'utf8', '-c', code, path], capture_output=True, text=True,
                         env={**os.environ, 'PYTHONPATH': str(cnv)}, timeout=300)
    assert out.returncode == 0, out.stderr[-2000:]
    assert out.stdout.split() == ['t', simsnap.version()]


def test_the_cli_resume_refuses_before_it_appends(tmp_path):
    """u P3 #1: `one --resume` checks the file and the first half's record before it opens the record to append:
    no record there -- refused, none made; a file of another task -- refused, the record as it was."""
    import argparse
    snap = str(tmp_path / 's.json.gz')
    snapfile.save(snap, {}, task=TASK, snap='0.5')
    record = tmp_path / 'r.jsonl.gz'
    a = argparse.Namespace(cmd='one', name=TASK, path=str(record), executor=None, snap='0.5', save=None, resume=snap)
    with pytest.raises(ValueError, match="no first half's record"):
        simrecord._main(a)
    assert not record.exists()
    with gzip.open(record, 'wt', encoding='utf-8') as f:
        f.write('first half')
    before = record.read_bytes()
    snapfile.save(snap, {}, task='wfire_all', snap='0.5')
    with pytest.raises(ValueError, match='not heal_a at 0.5'):
        simrecord._main(a)
    assert record.read_bytes() == before
