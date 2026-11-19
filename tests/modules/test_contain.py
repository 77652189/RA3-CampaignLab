"""The contain modules (engine/modules/contain.py, step M14): GarrisonContain / ContestableGarrisonContain /
TransportContain read from the block the port merges up the chain, including the PassengerFilter,
a transport's passengers ENCLOSED, a contestable
one's clearing bits; the passengers, the bits given each, the owner before and the listener's upgrades kept on the
module, which the host's garrisons (simgarrison.Garrisons) find by interface. On the bench: engine_garrison in / hp /
del, engine_transport load (docs/engine/garrison.md)."""
from test_plans import small  # noqa: F401,I001  (tests/ is on the path by its conftest; puts experimental/cnv on it)
import pytest  # noqa: E402
import simgarrison  # noqa: E402
import simsmall  # noqa: E402
import simunits  # noqa: E402
from engine.kernel import interfaces  # noqa: E402
from engine.modules import contain  # noqa: E402

BASE = ('<GameObject id="CNVBase"><Behaviors><GarrisonContain id="G" ContainMax="5" AllowEnemiesInside="false" '
        'ObjectStatusOfContained="ENCLOSED"><PassengerFilter Rule="ANY" Include="INFANTRY">'
        '<ExcludeThing>AlliedScoutInfantry</ExcludeThing></PassengerFilter></GarrisonContain></Behaviors></GameObject>')
CHILD = ('<GameObject id="CNVChild" inheritFrom="CNVBase"><Behaviors><GarrisonContain id="G" ContainMax="2"/>'
         '</Behaviors></GameObject>')


def test_the_block_is_read_with_the_schema_defaults():
    r = contain.ContainData.parse(' id="G"', '').rule
    assert r == {'tag': 'GarrisonContain', 'max': 0, 'allow': {'ENEMIES': True, 'NEUTRAL': True, 'ALLIES': True},
                 'own': False, 'kill': False, 'status': frozenset(), 'clearing': frozenset(), 'rule': 'ANY',
                 'kinds': frozenset(), 'unkinds': frozenset(), 'exclude': frozenset()}
    assert contain.TransportData.parse(' id="T" ObjectStatusOfContained="UNSELECTABLE"', '').rule['status'] == \
        {'UNSELECTABLE', 'ENCLOSED'}                                    # a transport's passengers are ENCLOSED
    head = ' id="C" RequiredClearingObjectStatus="IS_FIRING"'
    assert contain.ContestableData.parse(head, '').rule['clearing'] == {'IS_FIRING'}
    assert contain.ContainData.parse(head, '').rule['clearing'] == frozenset()     # only a contestable one's


def test_the_port_merges_the_same_module_and_its_filter():
    own = {'CNVBase': BASE, 'CNVChild': CHILD}
    (block,) = simunits.module_blocks('CNVChild', 'GarrisonContain', own)
    r = contain.ContainData.parse(*block).rule
    assert r['max'] == 2 and r['allow']['ENEMIES'] is False and r['status'] == {'ENCLOSED'}     # own max, base's rest
    assert r['kinds'] == {'INFANTRY'} and r['exclude'] == {'alliedscoutinfantry'}             # the base's filter
    own['CNVOwnFilter'] = ('<GameObject id="CNVOwnFilter" inheritFrom="CNVBase"><Behaviors><GarrisonContain id="G">'
                           '<PassengerFilter Rule="ALL" Include="VEHICLE"/></GarrisonContain></Behaviors></GameObject>')
    (block,) = simunits.module_blocks('CNVOwnFilter', 'GarrisonContain', own)
    r = contain.ContainData.parse(*block).rule
    # Compiled CNVOwnFilter: ContainMax="5", PassengerFilter Rule="ALL" Include="VEHICLE", ExcludeThing AlliedScoutInfantry.
    assert (r['rule'], r['kinds'], r['exclude'], r['max']) == ('ALL', {'VEHICLE'}, {'alliedscoutinfantry'}, 5)
    (block,) = simunits.module_blocks('AM_Apartments_01', 'ContestableGarrisonContain')
    r = contain.ContestableData.parse(*block).rule
    assert r['max'] == 5 and 'ENCLOSED' in r['status'] and r['kinds'] == {'INFANTRY'}
    assert simunits.module_blocks('AM_Apartments_01', 'GarrisonContain') == []


def test_the_module_keeps_the_passengers_the_bits_and_the_owner_before():
    s = simsmall.small_world()
    house = s.add('house', 'AM_Apartments_01', None, 300.0, 300.0)
    (m,) = house.find(interfaces.Contain)
    assert simgarrison.contain(house) is m and simgarrison.contain(house, simgarrison.TRANSPORT) is None
    gi = s.add('gi', 'AlliedAntiInfantryInfantry', 'Player_1', 400.0, 300.0)
    assert m.passengers() == [] and m.home() == ()
    m.keep_home(None)
    m.keep_home('Player_1')                         # the first kept stays (a neutral owner too)
    m.let_in(gi, frozenset({'ENCLOSED'}))
    assert m.passengers() == [gi] and m.home() == (None,)
    assert m.let_out(gi) == {'ENCLOSED'} and m.passengers() == [] and m.let_out(gi) == frozenset()
    assert m.give_home() is None and m.home() == ()
    m.set_granted({'Upgrade_X'})
    assert m.granted() == {'Upgrade_X'}
    assert gi.find(interfaces.Contain) == ()


def test_the_host_puts_one_in_through_the_module():
    s = simsmall.small_world()
    house = s.add('house', 'AM_Apartments_01', None, 300.0, 300.0)
    gi = s.add('gi', 'AlliedAntiInfantryInfantry', 'Player_1', 400.0, 300.0)
    assert s.garrison.put(gi, house, script=True)
    (m,) = house.find(interfaces.Contain)
    assert m.passengers() == [gi] and s.garrison.held(house) == [gi] and house.owner == 'Player_1'
    assert 'ENCLOSED' in gi.script_status and m.home() == (None,)
    assert s.garrison.out(gi) and house.owner is None and 'ENCLOSED' not in gi.script_status and m.home() == ()


def test_a_buildings_end_empties_it_through_its_module():
    """Step B4c: a house's death tells its Contain module (Die) -- the passenger out alive, no
    KillPassengersOnDeath -- and a deletion (Destroy only) takes the passenger with it."""
    s = simsmall.small_world()
    told = []
    vacate = s.world._vacate
    s.world._vacate = lambda thing, delete: told.append((thing.name, delete, len(s.garrison.held(thing)))) or \
        vacate(thing, delete)
    house = s.add('house', 'AM_Apartments_01', None, 300.0, 300.0)
    gi = s.add('gi', 'AlliedAntiInfantryInfantry', 'Player_1', 400.0, 300.0)
    (m,) = house.find(interfaces.Contain)
    assert isinstance(m, interfaces.Die) and isinstance(m, interfaces.Destroy)
    assert s.garrison.put(gi, house, script=True)
    s.destroy(house, 'test')
    assert gi.alive and m.passengers() == [] and 'ENCLOSED' not in gi.script_status
    assert told == [('house', False, 1)]            # a death empties it once (review 1119d #5: no second, deleting)
    house2 = s.add('house2', 'AM_Apartments_01', None, 300.0, 600.0)
    gi2 = s.add('gi2', 'AlliedAntiInfantryInfantry', 'Player_1', 400.0, 600.0)
    assert s.garrison.put(gi2, house2, script=True)
    s.delete(house2, 'test')
    (m2,) = house2.find(interfaces.Contain)
    assert not gi2.alive and gi2.deleted and m2.passengers() == []
    assert told[1:] == [('house2', True, 1)]


@pytest.mark.parametrize('end', ['destroy', 'delete'])
def test_a_thing_under_a_taken_name_has_none_of_the_old_ones_passengers(end):
    """Review 1119d #1 (coordinator 11-19, INFERRED: no bench): the passengers are the host thing's, not its name's --
    a tank made under the house's name and ended leaves the house's passenger in the house, now and after the
    garrison cell; the house's own end lets it out."""
    s = simsmall.small_world()
    house = s.add('house', 'AM_Apartments_01', None, 300.0, 300.0)
    gi = s.add('gi', 'AlliedAntiInfantryInfantry', 'Player_1', 400.0, 300.0)
    assert s.garrison.put(gi, house, script=True)
    tank = s.add('house', 'SovietAntiVehicleVehicleTech3', 'Player_1', 600.0, 300.0)
    assert s.garrison.held(tank) == [] and s.garrison.held(house) == [gi]
    s.garrison.due()                                # it rides with its own host, not the tank
    assert (gi.x, gi.y) == (300.0, 300.0)
    getattr(s, end)(tank, 'test')
    assert gi.alive and s.garrison.where.get('gi') is house and s.garrison.held(house) == [gi]
    s.garrison.due()
    assert gi.alive and s.garrison.where.get('gi') is house and (gi.x, gi.y) == (300.0, 300.0)
    getattr(s, end)(house, 'test')
    assert 'gi' not in s.garrison.where and s.garrison.held(house) == [] and gi.alive == (end == 'destroy')


def test_a_transport_keeps_its_owner_and_its_passengers_are_enclosed():
    s = simsmall.small_world()
    boat = s.add('boat', 'AlliedAntiInfantryVehicle', 'Player_2', 300.0, 300.0)
    gi = s.add('gi', 'AlliedAntiInfantryInfantry', 'Player_1', 400.0, 300.0)
    assert s.garrison.spec(boat) is None and s.garrison.box(boat)['tag'] == 'TransportContain'
    assert s.garrison.put(gi, boat, script=True)
    assert boat.owner == 'Player_2' and 'ENCLOSED' in gi.script_status and s.garrison.held(boat) == [gi]


def test_at_the_reallydamaged_line_everyone_comes_out():
    s = simsmall.small_world()
    house = s.add('house', 'AM_Apartments_01', None, 300.0, 300.0)
    gi = s.add('gi', 'AlliedAntiInfantryInfantry', 'Player_1', 400.0, 300.0)
    assert simgarrison.really('AM_Apartments_01') == simgarrison.REALLY_DAMAGED
    s.garrison.put(gi, house, script=True)
    house.set_hp(house.max_hp * .34, tell=False)
    s.garrison.hurt(house)
    assert s.garrison.held(house) == [gi]
    house.set_hp(house.max_hp * .33, tell=False)
    s.garrison.hurt(house)
    assert s.garrison.held(house) == [] and house.owner is None
