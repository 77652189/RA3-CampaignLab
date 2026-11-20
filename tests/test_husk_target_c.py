"""Husk rejects ordinary neutral objects; see work/re/c_husk_report.md."""
import importlib.util
import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('simai_run', ROOT / 'experimental/cnv/simai_run.py')
simai_run = importlib.util.module_from_spec(spec)
spec.loader.exec_module(simai_run)
simai = simai_run.simai    # one copy of simai, the run's (R3 13f-2d)
BUILDS = ('aihusknone', 'aihusknamed')


def native_picks(build):
    import teamlog
    return teamlog.target_picks(str(ROOT / f'tests/fixtures/{build}_target_picks.txt'))


@pytest.mark.parametrize('build', BUILDS)
def test_husk_native_selection_distinguishes_ordinary_neutral_oil(build):
    import teamlog
    rows = native_picks(build)
    assert rows
    for row in rows:
        assert row['state_id'] == teamlog.state_hash('CNVStateTP')
        assert row['index'] == row['slot'] == 0
        assert row['found'] == (build == 'aihusknamed')
        if row['found']:
            assert row['target'] > 0 and row['point'] == (2900.0, 3300.0)
        else:
            assert row['target'] is None and row['count'] == 0


@pytest.mark.parametrize('build', BUILDS)
def test_husk_named_selection_replays_native(build):
    if not simai.available():
        pytest.skip('no private AI model')
    rows = native_picks(build)
    assert rows
    w = simai_run.run(build, 'a', until=3)
    picks = [text for _, kind, text in w.brains['Soviet_1'].ai.log
             if kind == 'target' and text.startswith('CNVStateTP: ')]
    assert bool(picks) == rows[0]['found']
    if rows[0]['found']:
        # Native and model object IDs differ; verify the selected model object
        # is the published exact-name control, not an unrelated neutral object.
        chosen = {int(re.search(r'-> \[(\d+)\]', text)[1]) for text in picks}
        assert len(chosen) == 1
        oil = next(t for t in w.brains['Soviet_1'].view.things if t.id in chosen)
        assert oil.name == w.sim.m.role('husk oil control').name
        assert (oil.x, oil.y) == rows[0]['point']


@pytest.mark.parametrize('build', BUILDS)
def test_husk_original_readings_and_public_record(build):
    path = Path(simai.labpaths.WORK) / 're/c_husk_measured.json'
    if not path.exists():
        pytest.skip('private original archive unavailable')
    original = json.loads(path.read_text(encoding='utf-8'))[build]
    assert original['verdict'] == 'PASS'
    rows = [r for r in original['rows'] if 20 <= r[0] <= 21]
    assert rows and all(r[1] is not None and r[2] == [4] for r in rows)
    for row in original['picks']:
        for key in ('brain', 'state', 'heuristic'):
            row[key] = 'redacted'
    assert json.loads(json.dumps(native_picks(build))) == original['picks']
