"""Battlefield's contract (experimental/cnv/engine/state/battlefield.py; step S 11d step 1, work/re/sim_split/bf_pack/plan.md):
the three hand-made files (tests/fixtures/battlefield, cut from levelvision_a, mine_cap and ai_open) hold; each way
of breaking one is refused before anything is placed, the field's path named; the host an empty run of the map."""
import copy
import json
import math
from pathlib import Path

import pytest

from test_plans import small  # noqa: F401,I001  (puts experimental/cnv on the path)
import engine.state.battlefield as simbattlefield  # noqa: E402
import engine.testing.small as simsmall  # noqa: E402
from maps import niagara, probe_range  # noqa: E402

DATA = Path(__file__).resolve().parent.parent / 'fixtures' / 'battlefield'
FILES = {'levelvision_a': probe_range, 'mine_cap': probe_range, 'ai_open': niagara}


def _load(name):
    return json.loads((DATA / f'{name}.json').read_text(encoding='utf-8'))


@pytest.fixture(scope='module')
def hosts():
    return {m: simsmall.small_world(model=False, map=m) for m in {probe_range, niagara}}


@pytest.mark.parametrize('name', sorted(FILES))
def test_the_three_files_hold(name, hosts):
    doc = _load(name)
    assert simbattlefield.check(doc) == []
    assert simbattlefield.preflight(hosts[FILES[name]], doc) == []
    simbattlefield.refuse(hosts[FILES[name]], doc)          # nothing raised, nothing placed
    assert not hosts[FILES[name]].bodies


def _broken(edit):
    doc = _load('levelvision_a')
    edit(doc)
    return simbattlefield.check(doc)


def _set(path, value):
    def edit(doc):
        at = doc
        for k in path[:-1]:
            at = at[k]
        at[path[-1]] = value
    return edit


SHAPE = [
    ('another format', _set(['format'], 'battlefield/2'), "format: 'battlefield/2'"),
    ('a part missing', lambda d: d.pop('script'), 'the file: missing script'),
    ('an unknown part', _set(['extra'], 1), 'the file: unknown extra'),
    ('t not finite', _set(['t'], math.inf), 't: not a finite number'),
    ('t negative', _set(['t'], -1), 't: -1 outside'),
    ('frame not whole', _set(['frame'], 195.5), 'frame: not a whole number'),
    ('frame a bool', _set(['frame'], True), 'frame: not a whole number'),
    ('money NaN', _set(['players', 'Player_1', 'money'], math.nan), 'players.Player_1.money: not a finite number'),
    ('a science twice', _set(['players', 'Player_1', 'sciences'], ['a', 'a']), "players.Player_1.sciences: 'a' twice"),
    ('points negative', _set(['players', 'Player_1', 'science_points'], -1), 'players.Player_1.science_points'),
    ('power missing a side', _set(['players', 'Player_1', 'power'], {'made': 0}), 'players.Player_1.power: missing used'),
    ('a relation of no kind', _set(['players', 'Player_1', 'relations'], {'Soviet_1': 'Ally'}),
     "players.Player_1.relations.Soviet_1: 'Ally' not one of"),
    ('a relation to an unlisted player', _set(['players', 'Player_1', 'relations'], {'Soviet_2': 'Enemy'}),
     'players.Player_1.relations.Soviet_2: not a listed player'),
    ('a relation to itself', _set(['players', 'Player_1', 'relations'], {'Player_1': 'Friend'}),
     'players.Player_1.relations.Player_1: a player toward itself'),
    ('an id twice', _set(['things', 2, 'id'], 'Level base'), "things[2].id: 'Level base' also things[1]"),
    ('an empty template', _set(['things', 0, 'template'], ''), 'things[0].template: not a name'),
    ('x not finite', _set(['things', 1, 'x'], math.nan), 'things[1].x: not a finite number'),
    ('z a string', _set(['things', 1, 'z'], 'ground'), 'things[1].z: not a finite number'),
    ('hp over max', _set(['things', 1, 'hp'], 600), 'things[1].hp: 600 over max_hp 500'),
    ('max_hp zero', _set(['things', 1, 'max_hp'], 0), 'things[1].max_hp: 0 not > 0'),
    ('level zero', _set(['things', 2, 'level'], 0), 'things[2].level: not a whole number >= 1'),
    ('progress over 1', _set(['things', 1, 'queue'], [{'template': 'AlliedScoutInfantry', 'progress': 1.5}]),
     'things[1].queue[0].progress: 1.5 outside [0, 1]'),
    ('a job missing a part', _set(['things', 1, 'queue'], [{'template': 'AlliedScoutInfantry'}]),
     'things[1].queue[0]: missing progress, paid, full'),
    ('paid negative', _set(['things', 1, 'queue'], [{'template': 'AlliedScoutInfantry', 'progress': 0.5,
                                                      'paid': -1, 'full': None}]),
     'things[1].queue[0].paid: not a whole number >= 0'),
    ('full but not at 1', _set(['things', 1, 'queue'], [{'template': 'AlliedScoutInfantry', 'progress': 0.5,
                                                          'paid': 0, 'full': 3}]),
     'things[1].queue[0].full: 3 with progress 0.5'),
    ('at 1 but no frame', _set(['things', 1, 'queue'], [{'template': 'AlliedScoutInfantry', 'progress': 1,
                                                          'paid': 0, 'full': None}]),
     'things[1].queue[0].full: None with progress 1'),
    ('full after the cut', _set(['things', 1, 'queue'], [{'template': 'AlliedScoutInfantry', 'progress': 1,
                                                           'paid': 0, 'full': 10 ** 6}]),
     "things[1].queue[0].full: 1000000 after the file's frame"),
    ('a thing with an unknown field', _set(['things', 1, 'veterancy'], 2), 'things[1]: unknown veterancy'),
    ('a flag not a bool', _set(['script', 'flags'], {'F': 1}), 'script.flags.F: not true / false'),
    ('a timer not finite', _set(['script', 'timers', 'Level eye remove'], math.inf),
     'script.timers.Level eye remove: not a finite number'),
    ('a timer and a counter alike', _set(['script', 'timers', 'Level eye base'], 1.0),
     'script.timers.Level eye base: also a counter'),
    ('an objective of no state', _set(['script', 'objectives'], {'O': 4}), 'script.objectives.O: 4 not one of'),
    ('gaps not names', _set(['gaps'], [1]), 'gaps[0]: not a name'),
]


@pytest.mark.parametrize('why, edit, said', SHAPE, ids=[s[0] for s in SHAPE])
def test_a_broken_file_is_refused_by_its_path(why, edit, said):
    bad = _broken(edit)
    assert any(said in b for b in bad), bad


CREWS = [
    ('a passenger not listed', {1: ['nobody']}, "things[1].contains[0]: 'nobody' not a listed thing"),
    ('a thing inside itself', {1: ['Level base']}, 'things[1].contains[0]: the thing itself'),
    ('a passenger in two places', {1: ['Level eye base target'], 2: ['Level eye base target']},
     "things[2].contains[0]: 'Level eye base target' already inside 'Level base'"),
    ('a ring', {1: ['Level high'], 2: ['Level base']}, 'is inside itself through'),
]


@pytest.mark.parametrize('why, holds, said', CREWS, ids=[c[0] for c in CREWS])
def test_crews_point_at_listed_things_once_without_a_ring(why, holds, said):
    def edit(doc):
        for i, ids in holds.items():
            doc['things'][i]['contains'] = ids
    bad = _broken(edit)
    assert any(said in b for b in bad), bad


def test_a_crew_listed_once_holds():
    assert _broken(_set(['things', 1, 'contains'], ['Level eye base target'])) == []


def _drop_x_break_y(doc):
    del doc['things'][0]['x']
    doc['things'][0]['y'] = []


def _drop_players_break_t(doc):
    del doc['players']
    doc['t'] = 'soon'


# Review z #3 (11-20): a value no float holds, a missing field hiding the next broken one, a key that is no name, a
# file naming no gap.
WHOLE = [
    ('x past a float', _set(['things', 0, 'x'], 10 ** 309), ['things[0].x: not a finite number']),
    ('a missing field hides no other', _drop_x_break_y, ['things[0]: missing x', 'things[0].y: not a finite number']),
    ('a missing part hides no other', _drop_players_break_t, ['the file: missing players', 't: not a finite number']),
    ('a flag of no name', _set(['script', 'flags'], {'': True}), ["script.flags: a key not a name ('')"]),
    ('a counter of no name', _set(['script', 'counters'], {'': 1}), ["script.counters: a key not a name ('')"]),
    ('a relation of no name', _set(['players', 'Player_1', 'relations'], {'': 'Enemy'}),
     ["players.Player_1.relations: a key not a name ('')"]),
    ('no gap named', _set(['gaps'], []), ['gaps: empty (a file names what it leaves out)']),
]


@pytest.mark.parametrize('why, edit, said', WHOLE, ids=[w[0] for w in WHOLE])
def test_every_problem_of_a_file_is_named(why, edit, said):
    bad = _broken(edit)
    for s in said:
        assert any(s in b for b in bad), bad


def _paths(v, at=()):
    """Every path into a JSON value (its own first)."""
    yield at
    if isinstance(v, dict):
        for k, x in v.items():
            yield from _paths(x, at + (k,))
    elif isinstance(v, list):
        for i, x in enumerate(v):
            yield from _paths(x, at + (i,))


BAD_VALUES = (10 ** 309, -10 ** 309, math.nan, None, True, '', [], {}, [None], {'': None})


def test_no_value_anywhere_breaks_the_check(hosts):
    """Any field of a file set to any JSON value: the check and the preflight answer in field paths, never raise."""
    doc = _load('levelvision_a')
    paths = [p for p in _paths(doc) if p]
    assert len(paths) > 150
    for path in paths:
        for value in BAD_VALUES:
            broken = copy.deepcopy(doc)
            _set(list(path), value)(broken)
            for bad in (simbattlefield.check(broken), simbattlefield.preflight(hosts[probe_range], broken)):
                assert isinstance(bad, list) and all(isinstance(b, str) for b in bad), (path, value)


def test_not_an_object_at_all():
    assert simbattlefield.check([]) == ['the file: not an object (list)']
    bad = simbattlefield.check({**_load('mine_cap'), 'things': {}, 'players': []})
    assert 'things: not a list' in bad and 'players: not an object' in bad


def test_the_host_is_asked_too(hosts):
    host = hosts[probe_range]
    doc = _load('levelvision_a')
    doc['map'] = 'niagara'
    doc['players']['Nobody'] = copy.deepcopy(doc['players']['Player_1'])
    doc['things'][1]['owner'] = 'Nobody'
    doc['things'][2]['template'] = 'NoSuchTemplate'
    doc['things'][3]['queue'] = [{'template': 'NoSuchUnit', 'progress': 0.5, 'paid': 0, 'full': None}]
    bad = simbattlefield.preflight(host, doc)
    for said in ("map: 'niagara', the host is 'probe_range'", 'players.Nobody: not a player of the host',
                 "things[1].owner: 'Nobody' not a player of the host",
                 "things[2].template: 'NoSuchTemplate' not defined", "things[3].queue[0].template: 'NoSuchUnit'"):
        assert any(said in b for b in bad), (said, bad)
    with pytest.raises(ValueError, match=r'not placed \(5\)'):
        simbattlefield.refuse(host, doc)


def test_an_id_a_living_thing_holds_is_refused_and_a_dead_ones_is_not():
    host = simsmall.small_world([('Level base', 'AlliedAntiVehicleVehicleTech3', 'Player_1', 0, 0)],
                                model=False, map=probe_range)
    doc = _load('levelvision_a')
    assert simbattlefield.preflight(host, doc) == ["things[1].id: 'Level base' a living thing of the host holds"]
    host.bodies['Level base'].alive = False
    assert simbattlefield.preflight(host, doc) == []


HUGE = (1.3e308, -1.3e308, 10 ** 30)


def test_a_huge_finite_value_anywhere_is_refused_or_placed():
    """Every number of a file at a huge finite value (and a timer added at one): the preflight refuses it, or the
    placing takes it without raising (review 1120bb P2: a deadline x the frame rate went infinite part way)."""
    doc = _load('levelvision_a')
    doc['script']['timers']['Added'] = 0.0
    paths = [p for p in _paths(doc)
             if p and isinstance(_at(doc, p), (int, float)) and not isinstance(_at(doc, p), bool)]
    assert len(paths) > 50
    for path in paths:
        for value in HUGE:
            broken = copy.deepcopy(doc)
            _set(list(path), value)(broken)
            host = simsmall.small_world(model=False, map=probe_range)
            if not simbattlefield.preflight(host, broken):
                simbattlefield.place(host, broken)


def _at(doc, path):
    for k in path:
        doc = doc[k]
    return doc
