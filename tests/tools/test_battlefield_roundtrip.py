"""Battlefield's round trip (experimental/cnv/engine/state/battlefield.py round_trip; step S 11d step 8, work/re/sim_split/bf_pack/
plan.md): export -> place onto an empty run of the map -> export, read on the file's clock (rebase), equals the file in
every field it carries, and each field that does not has the placing's gap naming it by its path. Sources: the three
cuts of the hand-made files (tests/fixtures/battlefield; ai_open needs the engine model), a house and a transport with
their crews, a barracks part way through a scout and one full at its door. The checker itself: a field changed on the
host after the placing, a thing taken out or added, the things' order and a timer moved are each found, and with no
gap they are not covered."""
import pytest

from test_plans import small  # noqa: F401,I001  (puts experimental/cnv on the path)
import engine.state.battlefield as simbattlefield  # noqa: E402
import engine.testing.small as simsmall  # noqa: E402
from engine.ports.observe import Observe  # noqa: E402
from maps import probe_range  # noqa: E402
from test_battlefield_crews import _source as _crews  # noqa: E402
from test_battlefield_export import CUTS, _run  # noqa: E402
from test_battlefield_jobs import _source as _jobs  # noqa: E402


def _cut(name):
    m, w, _, doc, _ = _run(name)
    return m.map, doc


SOURCES = {
    **{name: (lambda name=name: _cut(name)) for name in sorted(CUTS)},
    'crews': lambda: (probe_range, _crews()[1]),
    'scout_half': lambda: (probe_range, simbattlefield.export(Observe(_jobs(0.5)))),
    'scout_full': lambda: (probe_range, simbattlefield.export(Observe(_jobs(1.5)))),
}


@pytest.fixture(scope='module', params=sorted(SOURCES))
def source(request):
    return SOURCES[request.param]()


def test_every_difference_has_its_gap(source):
    m, doc = source
    host = simsmall.small_world(model=False, map=m)
    diffs = simbattlefield.round_trip(host, doc)
    assert [path for path, why in diffs if why is None] == []


def test_the_crews_and_jobs_come_back_whole():
    """The made scenes carry nothing the host cannot give: no difference at all."""
    for name in ('crews', 'scout_half', 'scout_full'):
        m, doc = SOURCES[name]()
        assert simbattlefield.round_trip(simsmall.small_world(model=False, map=m), doc) == [], name


def test_a_file_the_host_cannot_take_whole_has_each_difference_named():
    """A height the host does not place and a job its barracks does not build: each comes back different, and the
    placing's gap names it (the job by its own path, a part of the queue)."""
    doc = simbattlefield.export(Observe(_jobs(0.5)))
    i = next(k for k, t in enumerate(doc['things']) if t['id'] == 'barracks')
    j = next(k for k, t in enumerate(doc['things']) if t['id'] == 'plant')
    doc['things'][i]['queue'].append({'template': 'AlliedPowerPlant', 'progress': 0.0, 'paid': 0, 'full': None})
    doc['things'][j]['z'] = 50.0
    assert simbattlefield.check(doc) == []
    diffs = dict(simbattlefield.round_trip(simsmall.small_world(model=False, map=probe_range), doc))
    assert sorted(diffs) == sorted([f'things[{i}].queue', f'things[{j}].z'])
    assert diffs[f'things[{i}].queue'].startswith(f'things[{i}].queue[1]: ')
    assert diffs[f'things[{j}].z'].startswith(f'things[{j}].z: ')


def _back(doc, m=probe_range):
    host = simsmall.small_world(model=False, map=m)
    simbattlefield.place(host, doc)
    return host, simbattlefield.rebase(simbattlefield.export(Observe(host)), doc['t'], doc['frame'])


def test_the_checker_finds_each_kind_of_difference():
    _, doc = SOURCES['crews']()
    host, back = _back(doc)
    assert simbattlefield._parts(doc, back) == []
    i = next(k for k, t in enumerate(doc['things']) if t['id'] == 'frog')
    changed = dict(back, things=[dict(t, hp=t['hp'] - 1) if t['id'] == 'frog' else t for t in back['things']])
    assert simbattlefield._parts(doc, changed) == [f'things[{i}].hp']
    gone = dict(back, things=[t for t in back['things'] if t['id'] != 'frog'])
    assert simbattlefield._parts(doc, gone) == [f'things[{i}]']
    extra = dict(back, things=back['things'] + [dict(back['things'][0], id='stray')])
    assert simbattlefield._parts(doc, extra) == ["things: 'stray'"]
    turned = dict(back, things=back['things'][::-1])
    assert simbattlefield._parts(doc, turned) == ['things']
    p = sorted(doc['players'])[0]
    poorer = dict(back, players=dict(back['players'], **{p: dict(back['players'][p], money=back['players'][p]['money'] + 1)}))
    assert simbattlefield._parts(doc, poorer) == [f'players.{p}.money']
    power = dict(back['players'][p]['power'], used=back['players'][p]['power']['used'] + 1)
    hungrier = dict(back, players=dict(back['players'], **{p: dict(back['players'][p], power=power)}))
    assert simbattlefield._parts(doc, hungrier) == [f'players.{p}.power.used']
    late = dict(doc, script=dict(doc['script'], timers={'T': 9.0}))
    assert simbattlefield._parts(late, dict(back, script=dict(back['script'], timers={'T': 9.5}))) == ['script.timers.T']
    assert simbattlefield._parts(doc, dict(back, gaps=back['gaps'][1:])) == ['gaps']


def test_a_host_change_after_the_placing_is_not_covered():
    _, doc = SOURCES['crews']()
    host = simsmall.small_world(model=False, map=probe_range)
    gaps = simbattlefield.place(host, doc)
    assert gaps == []
    host.bodies['frog'].set_hp(host.bodies['frog'].hp - 1, tell=False)
    back = simbattlefield.rebase(simbattlefield.export(Observe(host)), doc['t'], doc['frame'])
    i = next(k for k, t in enumerate(doc['things']) if t['id'] == 'frog')
    assert simbattlefield._parts(doc, back) == [f'things[{i}].hp']
    assert not any(simbattlefield._covers(g, f'things[{i}].hp') for g in gaps)


def test_a_gap_covers_its_field_one_it_is_in_and_its_parts_only():
    covers = simbattlefield._covers
    assert covers('things[3].hp: 1 in the file', 'things[3].hp')
    assert covers('things[3]: the host made it', 'things[3].owner')
    assert covers('things[3].queue[0]: not placed', 'things[3].queue')
    assert not covers('things[3].hp: x', 'things[30].hp')
    assert not covers('things[3].hp: x', 'things[3].home')
    assert not covers("things: 'a' living on the host", 'things[0].hp')
    assert covers("things: 'a' (a P T) living on the host", "things: 'a'")
    assert not covers("things: 'ab' (a P T) living", "things: 'a'")
    assert covers('players.P.power.made: 1', 'players.P.power.made')
    assert not covers('players.P.power.made: 1', 'players.P.power.used')


def test_rebase_moves_timers_and_full_jobs_with_the_cut():
    doc = simbattlefield.export(Observe(_jobs(1.5)))
    doc['script']['timers'] = {'T': doc['t'] + 2.0}
    moved = simbattlefield.rebase(doc, doc['t'] + 10.0, doc['frame'] + 150)
    assert (moved['t'], moved['frame']) == (doc['t'] + 10.0, doc['frame'] + 150)
    assert moved['script']['timers']['T'] == pytest.approx(doc['t'] + 12.0)
    job = next(t for t in moved['things'] if t['id'] == 'barracks')['queue'][0]
    assert job['full'] == next(t for t in doc['things'] if t['id'] == 'barracks')['queue'][0]['full'] + 150
    assert simbattlefield.rebase(moved, doc['t'], doc['frame'])['things'] == doc['things']
    assert doc['script']['timers'] == {'T': doc['t'] + 2.0}         # a copy: the file is not touched
