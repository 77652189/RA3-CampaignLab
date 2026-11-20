"""Battlefield's placing of things (experimental/cnv/simbattlefield.py place_things; step S 11d step 3, work/re/sim_split/
bf_pack/plan.md): the three hand-made files (tests/fixtures/battlefield) placed onto an empty run of their map read back
through the export thing for thing -- the refinery's one collector the host made, moved to the file's spot; the two
rank 4 Mirages at 625 HP -- with nothing else living; ai_open's factory job at half, paid 100. A file the
preflight refuses places nothing; what the host cannot give (an explicit height, a rank without its creation upgrade,
another max health, a status bit it derives) and what a later step places are named by field path."""
import json
from pathlib import Path

import pytest

from test_plans import small  # noqa: F401,I001  (puts experimental/cnv on the path)
import simbattlefield  # noqa: E402
import simsmall  # noqa: E402
from engine.ports.observe import Observe  # noqa: E402
from maps import niagara, probe_range  # noqa: E402

DATA = Path(__file__).resolve().parent.parent / 'fixtures' / 'battlefield'
FILES = {'levelvision_a': probe_range, 'mine_cap': probe_range, 'ai_open': niagara}
LEFT = {}     # every file's things, its factory's job too, read back whole (step 7)


AI_YARD = 'UNIT - CNV AI Yard'      # ai_open's: its queue is the skirmish AI's (step 9, test_battlefield_ai)


def _load(name):
    """A sample file without the AI yard's structures (placed onto a host with no AI, each would be named: that and
    the placing with one are test_battlefield_ai's)."""
    doc = json.loads((DATA / f'{name}.json').read_text(encoding='utf-8'))
    return dict(doc, things=[dict(t, queue=[]) if t['id'] == AI_YARD else t for t in doc['things']])


def _place(doc, m=probe_range, objects=()):
    host = simsmall.small_world(objects, model=False, map=m)
    return host, simbattlefield.place_things(host, doc)


@pytest.mark.parametrize('name', sorted(FILES))
def test_each_file_reads_back_thing_for_thing(name):
    doc = _load(name)
    host, gaps = _place(doc, FILES[name])
    assert gaps == LEFT.get(name, [])
    out = simbattlefield.export(Observe(host))
    assert simbattlefield.check(out) == []
    got = {t['id']: t for t in out['things']}
    want = doc['things']
    assert [got[t['id']] for t in want] == want
    assert sorted(b.name for b in host.living()) == sorted(t['id'] for t in doc['things'])


def test_the_refinery_makes_one_collector_the_files_on_the_files_spot():
    doc = _load('mine_cap')
    host, _ = _place(doc)
    miners = [b for b in host.living() if b.template == 'AlliedMiner']
    refinery = host.bodies['UNIT - CNV Mine Refinery']
    assert [(b.name, b.x, b.y, b.unpack_parent) for b in miners] == \
        [('#unpack UNIT - CNV Mine Refinery', 3102.5472222222224, 4302.547222222222, refinery)]


def test_the_two_rank_4_mirages_are_625_hp():
    host, _ = _place(_load('levelvision_a'))
    ranked = sorted((b.name, b.level_rank, b.hp, b.max_hp) for b in host.living() if b.level_rank > 1)
    assert ranked == [('Level high', 4, 625, 625), ('Level removed', 4, 625, 625)]


def test_a_refused_file_places_nothing():
    host = simsmall.small_world([('Level base', 'AlliedAntiVehicleVehicleTech3', 'Player_1', 0, 0)],
                                model=False, map=probe_range)
    with pytest.raises(ValueError, match=r"things\[1\]\.id: 'Level base' a living thing of the host holds"):
        simbattlefield.place_things(host, _load('levelvision_a'))
    assert list(host.bodies) == ['Level base']


def test_a_collector_the_file_does_not_list_is_taken_out():
    doc = _load('mine_cap')
    doc['things'] = doc['things'][:2]
    host, gaps = _place(doc)
    assert gaps == []
    assert sorted(b.name for b in host.living()) == ['#0', 'UNIT - CNV Mine Refinery']


def test_a_name_the_host_gave_a_made_thing_holds_the_files_thing():
    doc = _load('mine_cap')
    doc['things'][2]['template'], doc['things'][2]['hp'], doc['things'][2]['max_hp'] = 'SovietEngineer', 50, 50
    host, gaps = _place(doc)
    assert gaps == ["things[2]: the host made '#unpack UNIT - CNV Mine Refinery' alongside its maker, a Player_1 "
                    "AlliedMiner; taken out, the file's placed instead"]
    b = host.bodies['#unpack UNIT - CNV Mine Refinery']
    assert (b.alive, b.template, b.x, b.y) == (True, 'SovietEngineer', 3102.5472222222224, 4302.547222222222)
    assert [o.template for o in host.living()].count('AlliedMiner') == 0


def test_what_the_host_cannot_give_is_named_by_field():
    doc = _load('levelvision_a')
    base, high, order, removed = doc['things'][1:5]
    base['z'] = 30.0
    order['level'] = 3                                           # no creation upgrade gives it
    high['status'].remove('WEAPON_UPGRADED_01')                  # the heroic rank's upgrade gives it
    high['status'].append('UNSELECTABLE')                        # a bit no source derives: held as a script's
    high['status'].sort()
    removed['hp'], removed['max_hp'] = 250, 1000                 # another max health: its share kept
    host, gaps = _place(doc)
    said = ['things[1].z: 30.0 in the file, the host reads None',
            'things[2].status:', 'things[3].level: 3 in the file, the host reads 1',
            'things[4].hp: 250 in the file, the host reads 156.25', 'things[4].max_hp: 1000 in the file, the host reads 625']
    assert len(gaps) == len(said) and all(any(g.startswith(s) for g in gaps) for s in said), gaps
    assert 'UNSELECTABLE' in host.bodies['Level high'].status
    assert 'WEAPON_UPGRADED_01' in host.bodies['Level high'].status


def _no_collector():
    doc = _load('mine_cap')
    doc['things'] = [t for t in doc['things'] if t['template'] != 'AlliedMiner']    # the source's was gone
    return doc


def test_a_collector_the_file_has_not_leaves_the_host_whole():
    """Review 1120aa P2: the refinery's collector the host made alongside, taken out -- no corpse, no module of it
    left in the schedule (its cells and its order table)."""
    host, gaps = _place(_no_collector())
    assert gaps == []
    assert sorted(b.name for b in host.living()) == ['#0', 'UNIT - CNV Mine Refinery']
    sched = host.world.schedule
    held = [m for cell in sched.cells.values() for m in cell] + list(sched.seq)
    assert [m.thing.name for m in held if m.thing.template == 'AlliedMiner'] == []
    assert not any(b.template == 'AlliedMiner' for b in host.bodies.values())


def test_a_script_reference_of_its_name_does_not_spare_the_collector():
    """Review 1120aa P2: a reference named as the collector points at another (deleted) thing: the collector the
    host made goes all the same (by the thing, not its name), the reference to the other kept."""
    import parts
    host = simsmall.small_world(model=False, map=probe_range)
    script = parts.Script('Review', [], [])
    ref = '#unpack UNIT - CNV Mine Refinery'
    host.act('CREATE_NAMED_ON_TEAM_AT_WAYPOINT', ['marker', 'AlliedMiner', 'Player_1/t', '@3300,4300'], script)
    host.act('SET_REF_TO_NEREST_TEAM_OF_TYPE_OWNED_BY_PLAYER', ['AlliedMiner', 'Player_1', 'Player_1/t', ref], script)
    host.act('NAMED_DELETE', ['marker'], script)
    assert host.refs[ref].name == 'marker' and list(host.living()) == []
    gaps = simbattlefield.place(host, _no_collector())
    assert [t['id'] for t in simbattlefield.export(Observe(host))['things']] == ['#0', 'UNIT - CNV Mine Refinery']
    assert host.refs[ref].name == 'marker'
    assert not [g for g in gaps if g.startswith('things:')], gaps


def test_a_living_thing_not_in_the_file_is_named():
    doc = _load('levelvision_a')
    host = simsmall.small_world([('stray', 'SovietAntiInfantryInfantry', 'Player_1', 900.0, 900.0)], model=False,
                                map=probe_range)
    gaps = simbattlefield.place_things(host, doc)
    assert gaps == ["things: 'stray' (a Player_1 SovietAntiInfantryInfantry) living on the host, not in the file"]
