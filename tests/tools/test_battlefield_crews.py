"""Battlefield's placing of crews (experimental/cnv/engine/state/battlefield.py place_things; step S 11d step 6, work/re/sim_split/
bf_pack/plan.md): a run cut with three of the player's men in a civilian house and two riding the player's Bullfrog,
its file placed onto an empty run of the same map: every thing reads back whole (the passengers in order, at their
holder's spot, carrying the bits it gives; the house the first passenger's), and after the same exits and the same kill
the host reads as the source does -- a passenger's bits go when it comes out, a transport keeps its owner, a killed
Bullfrog kills its riders; the last man out, the house goes back to the civilians on both (its `home`). Six into a
five-place house (the script's instant garrison) read back six; a holder with no hold is refused, and a home on a
transport, on a house with no passengers or of no player; a file's null home on a held house is named; a passenger
the host's filter keeps out is named."""
import copy

import pytest

from test_plans import small  # noqa: F401,I001  (puts experimental/cnv on the path)
import engine.state.battlefield as simbattlefield  # noqa: E402
import engine.testing.small as simsmall  # noqa: E402
from engine.ports.observe import Observe  # noqa: E402
from maps import probe_range  # noqa: E402

P1, CIV = 'Player_1', 'PlyrCivilian'
HOUSE, FROG, MAN, TANK = 'AM_Apartments_01', 'SovietAntiAirShip', 'SovietAntiInfantryInfantry', 'SovietAntiVehicleVehicleTech1'


def _source(men=3):
    w = simsmall.small_world([('house', HOUSE, CIV, 2000.0, 2000.0), ('frog', FROG, P1, 2600.0, 2000.0)]
                             + [(f'man {k}', MAN, P1, 1900.0 + 30 * k, 1800.0) for k in range(men)]
                             + [(f'rider {k}', MAN, P1, 2500.0 + 30 * k, 1800.0) for k in range(2)],
                             model=False, map=probe_range)
    for k in range(men):
        w.act('NAMED_GARRISON_SPECIFIC_BUILDING_INSTANTLY', [f'man {k}', 'house'], 'T')
    for k in range(2):
        w.act('NAMED_GARRISON_SPECIFIC_BUILDING_INSTANTLY', [f'rider {k}', 'frog'], 'T')
    w.run(1.0)
    return w, simbattlefield.export(Observe(w))


def _host(doc):
    host = simsmall.small_world(model=False, map=probe_range)
    return host, simbattlefield.place(host, doc)


def _things(w):
    return {t['id']: t for t in simbattlefield.export(Observe(w))['things']}


def test_the_cut_holds_a_garrison_and_a_transport():
    _, doc = _source()
    got = {t['id']: t for t in doc['things']}
    assert (got['house']['contains'], got['frog']['contains']) == (['man 0', 'man 1', 'man 2'], ['rider 0', 'rider 1'])
    assert (got['house']['owner'], got['frog']['owner']) == (P1, P1)
    assert (got['house']['home'], got['frog']['home'], got['man 0']['home']) == (CIV, None, None)
    assert 'ENCLOSED' in got['man 0']['status'] and 'ENCLOSED' in got['rider 0']['status']
    assert simbattlefield.check(doc) == []


def test_every_thing_reads_back_whole_the_crews_in_order():
    src, doc = _source()
    host, gaps = _host(doc)
    assert gaps == []
    back = simbattlefield.rebase(simbattlefield.export(Observe(host)), doc['t'], doc['frame'])    # its clocks' frames
    assert {t['id']: t for t in back['things']} == {t['id']: t for t in doc['things']}
    for b in host.living():                 # inside as the source's: the holder known by the thing
        g = src.garrison.where.get(src.bodies[b.name].serial)
        assert getattr(host.garrison.where.get(b.serial), 'name', None) == getattr(g, 'name', None)
    assert all(not (host.bodies[f'man {k}'].script_status - host.garrison.boxes[host.bodies['house'].serial]
                    .given[host.bodies[f'man {k}'].serial]) for k in range(3))     # none held as a script's


def test_after_the_same_exits_the_host_reads_as_the_source():
    src, doc = _source()
    host, _ = _host(doc)
    for w in (src, host):
        for u in ('man 0', 'man 1', 'rider 0'):
            w.act('NAMED_EXIT_BUILDING', [u], 'T')
        w.run(w.t + 1.0)
    a, b = _things(src), _things(host)
    keys = ('owner', 'status', 'contains', 'home', 'x', 'y')
    assert {k: {f: a[k][f] for f in keys} for k in a} == {k: {f: b[k][f] for f in keys} for k in b}
    assert 'ENCLOSED' not in b['man 0']['status'] and b['frog']['owner'] == P1 and b['house']['owner'] == P1
    for w in (src, host):                   # the last one out: both houses go back to the civilians
        w.act('NAMED_EXIT_BUILDING', ['man 2'], 'T')
    assert (src.bodies['house'].owner, host.bodies['house'].owner) == (CIV, CIV)
    assert _things(src)['house']['home'] is None and _things(host)['house']['home'] is None


def test_a_killed_transport_kills_its_placed_riders():
    _, doc = _source()
    host, _ = _host(doc)
    host.act('NAMED_KILL', ['frog'], 'T')
    assert [host.bodies[f'rider {k}'].alive for k in range(2)] == [False, False]
    assert all(host.bodies[f'man {k}'].alive for k in range(3))


def test_six_into_a_five_place_house_read_back_six():
    _, doc = _source(men=6)
    host, gaps = _host(doc)
    assert gaps == []
    assert [p.name for p in host.garrison.held(host.bodies['house'])] == [f'man {k}' for k in range(6)]


def test_a_holder_with_no_hold_is_refused_before_anything_is_placed():
    _, doc = _source()
    doc = copy.deepcopy(doc)
    rider = next(t for t in doc['things'] if t['id'] == 'rider 0')
    rider['contains'] = ['man 0']           # a man holds a man: no garrison or transport in its data
    next(t for t in doc['things'] if t['id'] == 'house')['contains'] = ['man 1', 'man 2']
    host = simsmall.small_world(model=False, map=probe_range)
    with pytest.raises(ValueError, match=r"things\[\d+\]\.contains: a SovietAntiInfantryInfantry holds nothing"):
        simbattlefield.place(host, doc)
    assert list(host.living()) == []


def test_a_passenger_the_filter_keeps_out_is_named():
    _, doc = _source()
    doc = copy.deepcopy(doc)
    tank = dict(next(t for t in doc['things'] if t['id'] == 'frog'), id='tank', template=TANK, contains=[])
    doc['things'].append(tank)
    house = next(t for t in doc['things'] if t['id'] == 'house')
    house['contains'] = house['contains'] + ['tank']
    host, gaps = _host(doc)
    said = [g for g in gaps if g.startswith('things[0].contains:')]
    assert len(said) == 1 and "keep out" in said[0] and "'tank'" in said[0]
    assert host.bodies['tank'].alive and host.garrison.where.get(host.bodies['tank'].serial) is None


def _row(doc, tid):
    return next(t for t in doc['things'] if t['id'] == tid)


@pytest.mark.parametrize('why, edit, said', [
    ('a transport', lambda d: _row(d, 'frog').update(home=CIV),
     r"things\[\d+\]\.home: a SovietAntiAirShip has no garrison in the host's data"),
    ('no player', lambda d: _row(d, 'house').update(home='Nobody'), r"things\[0\]\.home: 'Nobody' not a player"),
    ('no passengers', lambda d: _row(d, 'man 0').update(home=CIV), r"things\[\d+\]\.home: 'PlyrCivilian' with no "
                                                                    r"passengers"),
])
def test_a_home_no_building_could_have_is_refused(why, edit, said):
    _, doc = _source()
    doc = copy.deepcopy(doc)
    edit(doc)
    host = simsmall.small_world(model=False, map=probe_range)
    with pytest.raises(ValueError, match=said):
        simbattlefield.place(host, doc)
    assert list(host.living()) == []


def test_a_null_home_on_a_held_house_is_named_and_it_keeps_the_files_owner():
    _, doc = _source()
    doc = copy.deepcopy(doc)
    _row(doc, 'house')['home'] = None       # a file from an engine that does not know the owner before
    host, gaps = _host(doc)
    assert gaps == ["things[0].home: None in the file, the host reads 'Player_1' -- " + simbattlefield.WHY['home']]
    for k in range(3):
        host.act('NAMED_EXIT_BUILDING', [f'man {k}'], 'T')
    assert host.bodies['house'].owner == P1


def test_a_home_other_than_the_sources_is_where_the_emptied_house_goes():
    _, doc = _source()
    doc = copy.deepcopy(doc)
    _row(doc, 'house')['home'] = P1         # a house the player owned before it went in (a file may say so)
    host, gaps = _host(doc)
    assert gaps == [] and _things(host)['house']['home'] == P1
    for k in range(3):
        host.act('NAMED_EXIT_BUILDING', [f'man {k}'], 'T')
    assert host.bodies['house'].owner == P1
