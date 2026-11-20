"""Battlefield's export (experimental/cnv/simbattlefield.py export; step S 11d step 2, work/re/sim_split/bf_pack/
plan.md): the three cuts the hand-made files were taken at (tests/fixtures/battlefield) read through the observation
port alone give back every field each file lists, for the players and things it lists (ai_open lists four of its
291 things); the whole export passes the contract and the preflight onto an empty run of the map, is plain JSON, comes
out the same read twice, and reading it changes nothing in the world (its exact snapshot before and after equal)."""
import json
from pathlib import Path

import pytest

from test_plans import small  # noqa: F401,I001  (puts experimental/cnv on the path)
import build  # noqa: E402
import sim  # noqa: E402
import simai  # noqa: E402
import simbattlefield  # noqa: E402
import simrecord  # noqa: E402
import simsmall  # noqa: E402
import simsnap  # noqa: E402
from engine.ports.observe import Observe  # noqa: E402

DATA = Path(__file__).resolve().parent.parent / 'fixtures' / 'battlefield'
CUTS = {'levelvision_a': 12.5, 'mine_cap': 15, 'ai_open': 41}     # the files' cuts: the first tick past each


def _run(name):
    kind, where, _ = simrecord.TASKS[name]
    if kind == 'ai' and not simai.available():
        pytest.skip('the engine model (ra3model.ai) is not on this computer')
    m, t, _ = build.resolve(*where)
    w = sim.Sim(m, t, model=False)
    if kind == 'ai':
        ai = simai.SimAI(w)
        while w.t <= CUTS[name] and w.ending is None:
            ai.advance(1)
    else:
        w.run(CUTS[name])
    assert w.t > CUTS[name] and w.ending is None
    before = simsnap.snapshot(w)
    obs = Observe(w)
    doc = simbattlefield.export(obs)
    return m, w, before, doc, simbattlefield.export(obs)


@pytest.fixture(scope='module', params=sorted(CUTS))
def cut(request):
    name = request.param
    return (name, json.loads((DATA / f'{name}.json').read_text(encoding='utf-8')), *_run(name))


def test_the_export_gives_back_what_each_file_lists(cut):
    name, sample, m, w, before, doc, again = cut
    assert {k: doc[k] for k in ('format', 'map', 't', 'frame', 'script')} == \
        {k: sample[k] for k in ('format', 'map', 't', 'frame', 'script')}
    assert {p: doc['players'].get(p) for p in sample['players']} == sample['players']
    got = {t['id']: t for t in doc['things']}
    assert [got.get(t['id']) for t in sample['things']] == sample['things']


def test_the_whole_export_holds_the_contract_onto_an_empty_run_of_the_map(cut):
    name, sample, m, w, before, doc, again = cut
    assert simbattlefield.check(doc) == []
    assert simbattlefield.preflight(simsmall.small_world(model=False, map=m.map), doc) == []
    assert [t['id'] for t in doc['things']] == [b.name for b in w.living()]
    assert doc['gaps'][:len(simbattlefield.NOT_CARRIED)] == list(simbattlefield.NOT_CARRIED)


def test_the_export_is_plain_json_stable_and_changes_nothing(cut):
    name, sample, m, w, before, doc, again = cut
    assert json.loads(json.dumps(doc)) == doc
    assert json.dumps(again) == json.dumps(doc)
    assert simsnap.snapshot(w) == before


def test_a_relation_a_script_set_is_exported_and_the_maps_own_left_out(cut):
    name, sample, m, w, before, doc, again = cut
    if name != 'levelvision_a':
        pytest.skip('one host is enough')
    obs = Observe(w)
    saved = dict(w.relations)
    try:
        w.relations[('Player_1', 'Soviet_1')] = 'Friend'
        w.relations[('Soviet_1', 'PlyrCivilian')] = 'Enemy'      # toward a player not listed: named in gaps
        out = simbattlefield.export(obs)
    finally:
        w.relations.clear()
        w.relations.update(saved)
    assert out['players']['Player_1']['relations'] == {'Soviet_1': 'Friend'}
    assert out['players']['Soviet_1']['relations'] == {}
    assert out['gaps'][-1] == 'relations toward or of a player not listed: Soviet_1 -> PlyrCivilian Enemy'
    assert simbattlefield.check(out) == []
