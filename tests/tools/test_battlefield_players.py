"""Battlefield's placing of players (experimental/cnv/simbattlefield.py place_players / place; step S 11d step 4,
work/re/sim_split/bf_pack/plan.md): the three hand-made files and the three runs they were cut from, placed whole onto
an empty run of their map, read back player for player -- money, protocols and points, player upgrades, relations and
the power the host recomputes from the placed things. Protocols a file holds are held, not bought again (the points
are the file's, placing twice changes nothing), the rank is what the rank protocols say and goes on from there; a
relation off the map's own is set as the file has it; a power, an upgrade or a relation the host cannot give as the
file has it is named by field path; a file whose players the host cannot take places nothing."""
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
import simtech  # noqa: E402
from engine.ports.observe import Observe  # noqa: E402
from maps import niagara, probe_range  # noqa: E402

DATA = Path(__file__).resolve().parent.parent / 'fixtures' / 'battlefield'
FILES = {'levelvision_a': probe_range, 'mine_cap': probe_range, 'ai_open': niagara}
CUTS = {'levelvision_a': 12.5, 'mine_cap': 15, 'ai_open': 41}     # as test_battlefield_export
LEFT = {}     # every file's things, its factory's job too, read back whole (step 7)


def _load(name):
    return json.loads((DATA / f'{name}.json').read_text(encoding='utf-8'))


def _host(m=probe_range):
    return simsmall.small_world(model=False, map=m)


def _players(host):
    return simbattlefield.export(Observe(host))['players']


@pytest.mark.parametrize('name', sorted(FILES))
def test_each_file_reads_back_player_for_player(name):
    doc = _load(name)
    host = _host(FILES[name])
    assert simbattlefield.place(host, doc) == LEFT.get(name, [])
    got = _players(host)
    assert {p: got[p] for p in doc['players']} == doc['players']


@pytest.mark.parametrize('name', sorted(CUTS))
def test_a_runs_whole_export_places_its_players_whole(name):
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
    doc = simbattlefield.export(Observe(w))
    host = _host(m.map)
    gaps = simbattlefield.place(host, doc)
    assert [g for g in gaps if g.startswith('players')] == []
    assert _players(host) == doc['players']          # both sides' books: money, protocols, points, power the same


def test_held_protocols_are_not_paid_again():
    doc = _load('levelvision_a')
    bought = 'playertech_soviet_magneticsatellite_rank_1'
    assert simtech.protocols()[bought][1] > 0       # it costs points to buy
    doc['players']['Soviet_1']['science_points'] = 2
    host = _host()
    assert simbattlefield.place(host, doc) == []
    book = host.books['Soviet_1']
    assert (book.points, bought in book.owned) == (2, True)
    assert simbattlefield.place_players(host, doc) == []       # placed again: nothing paid, nothing given
    assert (book.points, sorted(book.owned)) == (2, doc['players']['Soviet_1']['sciences'])


def test_the_rank_is_what_the_rank_protocols_say_and_goes_on():
    doc = _load('mine_cap')
    me = doc['players']['Player_1']
    me['sciences'] = sorted(me['sciences'] + ['playertech_generic_rank_2', 'playertech_generic_rank_3'])
    host = _host()
    assert simbattlefield.place(host, doc) == []
    book = host.books['Player_1']
    assert (book.rank, book.points, book.earned) == (2, 1, 3)     # rank 3; points 1 as the file says
    for f in range(1, 360 * 15 + 1):                   # 360 s more: rank 4, its one point, its protocol
        book.frame(f)
    assert (book.rank, book.points) == (3, 2)
    assert 'playertech_generic_rank_4' in book.owned and 'playertech_generic_rank_5' not in book.owned


def test_a_relation_off_the_maps_own_is_set_as_the_file_has_it():
    doc = _load('levelvision_a')
    doc['players']['Player_1']['relations'] = {'Soviet_1': 'Friend'}
    doc['players']['Soviet_1']['relations'] = {'Player_1': 'Neutral'}
    host = _host()
    assert simbattlefield.place(host, doc) == []
    assert (host.relations[('Player_1', 'Soviet_1')], host.relations[('Soviet_1', 'Player_1')]) == \
        ('Friend', 'Neutral')
    assert not host.enemy('Player_1', 'Soviet_1') and not host.enemy('Soviet_1', 'Player_1')
    got = _players(host)
    assert (got['Player_1']['relations'], got['Soviet_1']['relations']) == \
        ({'Soviet_1': 'Friend'}, {'Player_1': 'Neutral'})


def test_money_and_a_player_upgrade_are_placed_before_the_things():
    doc = _load('mine_cap')
    doc['players']['Player_1'].update(money=1234.5, upgrades=['Upgrade_AlliedTech2'])
    host = _host()
    seen = []
    real = host.add

    def add(*a, **k):
        seen.append(sorted(host.player_ups.get('Player_1', ())))
        return real(*a, **k)
    host.add = add
    assert simbattlefield.place(host, doc) == []
    assert seen and all(s == ['Upgrade_AlliedTech2'] for s in seen)
    assert host.money['Player_1'] == 1234.5


def test_what_the_host_cannot_give_is_named():
    doc = _load('mine_cap')
    doc['players']['Player_1']['power'] = {'made': 999, 'used': 50}
    host = _host()
    host.act('GIVE_PLAYER_UPGRADE', ['Player_1', 'Upgrade_Before'], 'test')
    gaps = simbattlefield.place(host, doc)
    assert gaps == [
        "players.Player_1.upgrades: [] in the file, the host reads ['Upgrade_Before'] -- "
        + simbattlefield.WHY_PLAYER['upgrades'],
        'players.Player_1.power.made: 999 in the file, the host reads 0 -- ' + simbattlefield.WHY_PLAYER['power']]


def test_place_players_alone_names_the_power_of_things_not_placed():
    doc = _load('mine_cap')
    gaps = simbattlefield.place_players(_host(), doc)
    assert gaps == ['players.Player_1.power.used: 50 in the file, the host reads 0 -- '
                    + simbattlefield.WHY_PLAYER['power']]


def test_a_file_whose_players_the_host_cannot_take_places_nothing():
    doc = _load('mine_cap')
    doc['players']['Player_1']['sciences'].append('playertech_nothing')
    doc['players']['Player_1']['money'] = 5000
    host = _host()
    with pytest.raises(ValueError, match=r"players\.Player_1\.sciences\[2\]: 'playertech_nothing' not a protocol"):
        simbattlefield.place_players(host, doc)
    with pytest.raises(ValueError, match='not a protocol'):
        simbattlefield.place(host, doc)
    assert (host.money.get('Player_1', 0), list(host.bodies)) == (0, [])
    assert sorted(host.books['Player_1'].owned) == ['playertech_allied', 'playertech_generic_rank_1']


def test_a_relation_the_map_has_already_is_refused(monkeypatch):
    doc = _load('levelvision_a')
    doc['players']['Player_1']['relations'] = {'Soviet_1': 'Enemy'}
    host = _host()
    monkeypatch.setattr(host.m, 'relations', {('Player_1', 'Soviet_1'): 'Enemy'}, raising=False)
    assert simbattlefield.preflight(host, doc, things=False) == \
        ["players.Player_1.relations.Soviet_1: 'Enemy' the map's own (a file lists what differs)"]
