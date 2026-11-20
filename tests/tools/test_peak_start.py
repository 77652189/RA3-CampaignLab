"""The peak benchmark from a snapshot (step S 11c-2; experimental/cnv/simbench_peak.py ai_start / run_ai(start=)):
the scene's start taken once and kept, read back the next time (the same file, its sha in the result), taken again
with a line when none is kept or restore refuses it, and the run timed from it a world that goes on. Guard 7's
ai_crush1 here (a short AI task; the benchmark's own scene is too long to take in a test)."""
import gzip
import json

import pytest

from test_plans import small  # noqa: F401,I001  (puts experimental/cnv on the path)
import simai  # noqa: E402
import simaisnap  # noqa: E402
import simbench_peak  # noqa: E402
import simrecord  # noqa: E402
import snapfile  # noqa: E402

SCENE = simrecord.TASKS['ai_crush1'][1]
AT = 4.0


@pytest.fixture(autouse=True)
def _model():
    if not simai.available():
        pytest.skip('the engine model (ra3model.ai) is not on this computer')


def test_a_start_is_taken_once_then_read_back(tmp_path, capsys):
    path = str(tmp_path / 'start.json.gz')
    w, info = simbench_peak.ai_start(AT, SCENE, path)
    assert info['taken'] and 'taking the start again (none kept)' in capsys.readouterr().out
    assert AT < w.sim.t <= AT + 0.5 and w.brains
    taken = simaisnap.snapshot(w)
    again, info2 = simbench_peak.ai_start(AT, SCENE, path)
    assert not info2['taken'] and info2['sha'] == info['sha'] == snapfile.digest(path)
    assert 'taking' not in capsys.readouterr().out
    assert simaisnap.snapshot(again) == taken


def test_a_start_restore_refuses_is_taken_again(tmp_path, capsys):
    path = str(tmp_path / 'start.json.gz')
    _, info = simbench_peak.ai_start(AT, SCENE, path)
    meta, s = snapfile.load(path)
    s['version'] = simaisnap.VERSION - 1                # an older shape: refused whole
    snapfile.save(path, s, **meta)
    capsys.readouterr()
    _, info2 = simbench_peak.ai_start(AT, SCENE, path)
    assert info2['taken'] and info2['sha'] == info['sha']
    assert 'taking the start again (refused: simaisnap.restore: not a snapshot of this shape' in capsys.readouterr().out
    with gzip.open(path, 'wb') as f:                    # a broken file
        f.write(b'{')
    _, info3 = simbench_peak.ai_start(AT, SCENE, path)
    assert info3['taken'] and info3['sha'] == info['sha']


def test_a_start_of_another_scene_or_time_is_not_read(tmp_path, capsys):
    path = str(tmp_path / 'start.json.gz')
    simbench_peak.ai_start(AT, SCENE, path)
    meta, s = snapfile.load(path)
    snapfile.save(path, s, **{**meta, 'at': AT + 1})
    capsys.readouterr()
    _, info = simbench_peak.ai_start(AT, SCENE, path)
    assert info['taken'] and 'not ' in capsys.readouterr().out


def test_the_run_is_timed_from_the_start_and_names_it(tmp_path):
    path = str(tmp_path / 'start.json.gz')
    r = simbench_peak.run_ai(2.0, AT, SCENE, path)
    assert r['start']['sha'] == snapfile.digest(path) and r['start']['at'] == AT and r['model'] is False
    assert r['secs'] == 2.0 and r['slices'] and r['ms_frame'] > 0
    assert json.loads(json.dumps(r)) == r
