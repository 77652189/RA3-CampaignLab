"""Missing data is an error, not an empty answer (line A, 11-13): a worktree whose work/ held only an empty logs/
was taken for its own work, the simulator found no SageXML index, built an empty unit table and cached it -- every
fight then read 0 and nothing said why. labpaths now borrows the main checkout's work over a logs-only one, and the
simulator's cached tables refuse to be built, or trusted, empty."""
import json
import os
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'experimental', 'campaign'))
sys.path.insert(0, os.path.join(HERE, '..', 'experimental', 'cnv'))
import labpaths  # noqa: E402
import simunits  # noqa: E402


def _tree(tmp_path, own):
    main = tmp_path / 'RA3-CampaignLab'
    (main / 'work').mkdir(parents=True)
    line = tmp_path / 'RA3-CampaignLab-a'
    line.mkdir()
    if own is not None:
        (line / 'work').mkdir()
        for name in own:
            (line / 'work' / name).mkdir()
    return str(line), str(main)


@pytest.mark.parametrize('own, borrows', [(None, True), ((), True), (('logs',), True), (('logs', 'sim'), False)])
def test_a_worktree_borrows_the_main_work_over_a_logs_only_one(tmp_path, own, borrows):
    line, main = _tree(tmp_path, own)
    got = labpaths._work(root=line, main=main, env={})
    assert got == os.path.join(main if borrows else line, 'work')


def test_cnv_work_still_wins(tmp_path):
    line, main = _tree(tmp_path, ('logs',))
    assert labpaths._work(root=line, main=main, env={'CNV_WORK': 'X'}) == 'X'


def test_the_main_checkout_keeps_its_own_work(tmp_path):
    line, main = _tree(tmp_path, ('logs',))
    assert labpaths._work(root=main, main=main, env={}) == os.path.join(main, 'work')


def test_units_without_the_index_raise(tmp_path, monkeypatch):
    monkeypatch.setattr(simunits, 'INDEX', str(tmp_path / 'none.json'))
    with pytest.raises(simunits.MissingData, match='none.json'):
        list(simunits.units())


def test_an_empty_build_is_never_cached(tmp_path):
    path = tmp_path / 'cache.json'
    with pytest.raises(simunits.MissingData):
        simunits._cached(str(path), dict, lambda t: not t)
    assert not path.exists()


def test_an_empty_cache_is_built_again(tmp_path):
    path = tmp_path / 'cache.json'
    path.write_text('{}', encoding='utf-8')
    assert simunits._cached(str(path), lambda: {'a': 1}, lambda t: not t) == {'a': 1}
    assert json.loads(path.read_text(encoding='utf-8')) == {'a': 1}
    with pytest.raises(simunits.MissingData):                   # still empty: an error, the file left for the next run
        path.write_text('{}', encoding='utf-8')
        simunits._cached(str(path), dict, lambda t: not t)
