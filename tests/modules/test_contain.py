"""The contain modules (engine/modules/contain.py, step M14): GarrisonContain / ContestableGarrisonContain /
TransportContain read from the block the port merges up the chain, including the PassengerFilter,
a transport's passengers ENCLOSED, a contestable
one's clearing bits; the passengers, the bits given each, the owner before and the listener's upgrades kept on the
module, which the host's garrisons (simgarrison.Garrisons) find by interface. On the bench: engine_garrison in / hp /
del, engine_transport load (docs/engine/garrison.md)."""
from test_plans import small  # noqa: F401,I001  (tests/ is on the path by its conftest; puts experimental/cnv on it)
import pytest  # noqa: E402
import engine.objects.garrison as simgarrison  # noqa: E402
import engine.testing.small as simsmall  # noqa: E402
from engine.orders import order as simorder, ability as simability  # noqa: E402
import engine.data.units as simunits  # noqa: E402
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


def test_player_exit_all_buildings_lets_nobody_out():
    """engine_plexit a / b (bench 11-23): PLAYER_EXIT_ALL_BUILDINGS on the human player or a campaign computer player
    leaves every man in (unlike TEAM_EXIT_ALL_BUILDINGS), and it is a known action, no gap."""
    import engine.script.act as simact
    s = simsmall.small_world()
    house, house2 = (s.add(n, 'AM_Apartments_01', None, 300.0, y) for n, y in (('house', 300.0), ('house2', 600.0)))
    gi = s.add('gi', 'AlliedAntiInfantryInfantry', s.human, 400.0, 300.0)
    foe = s.add('foe', 'AlliedAntiInfantryInfantry', 'Soviet_4', 400.0, 600.0)
    assert s.garrison.put(gi, house, script=True) and s.garrison.put(foe, house2, script=True)
    for who in (s.human, 'Soviet_4'):
        assert simact.act(s, 'PLAYER_EXIT_ALL_BUILDINGS', [who], None)
    assert s.garrison.held(house) == [gi] and s.garrison.held(house2) == [foe]


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
    s.world.kill(house, 'test')
    assert gi.alive and m.passengers() == [] and 'ENCLOSED' not in gi.script_status
    assert told == [('house', False, 1)]            # a death empties it once (review 1119d #5: no second, deleting)
    house2 = s.add('house2', 'AM_Apartments_01', None, 300.0, 600.0)
    gi2 = s.add('gi2', 'AlliedAntiInfantryInfantry', 'Player_1', 400.0, 600.0)
    assert s.garrison.put(gi2, house2, script=True)
    s.world.remove(house2, 'test')
    (m2,) = house2.find(interfaces.Contain)
    assert not gi2.alive and gi2.deleted and m2.passengers() == []
    assert told[1:] == [('house2', True, 1)]


@pytest.mark.parametrize('end', ['kill', 'remove'])
def test_a_thing_under_a_taken_name_has_none_of_the_old_ones_passengers(end):
    """Review 1119d #1 (coordinator 11-19, INFERRED: no bench): the passengers are the host thing's, not its name's --
    a tank made under the house's name and ended leaves the house's passenger in the house, now and after the
    garrison cell; the house's own end lets it out."""
    s = simsmall.small_world()
    house = s.add('house', 'AM_Apartments_01', None, 300.0, 300.0)
    gi = s.add('gi', 'AlliedAntiInfantryInfantry', 'Player_1', 400.0, 300.0)
    assert s.garrison.put(gi, house, script=True)
    tank = s.add('house', 'SovietAntiVehicleVehicleTech3', 'Player_1', 600.0, 300.0, shadow=True)  # (map load's path)
    assert s.garrison.held(tank) == [] and s.garrison.held(house) == [gi]
    s.garrison.due()                                # it rides with its own host, not the tank
    assert (gi.x, gi.y) == (300.0, 300.0)
    getattr(s.world, end)(tank, 'test')
    assert gi.alive and s.garrison.where.get(gi.serial) is house and s.garrison.held(house) == [gi]
    s.garrison.due()
    assert gi.alive and s.garrison.where.get(gi.serial) is house and (gi.x, gi.y) == (300.0, 300.0)
    getattr(s.world, end)(house, 'test')
    assert gi.serial not in s.garrison.where and s.garrison.held(house) == [] and gi.alive == (end == 'kill')


@pytest.mark.parametrize('filled', [False, True])
def test_a_pending_evacuation_stays_with_its_host_when_its_name_is_taken(filled):
    """B5 review g #1 (as the passengers, review 1119d #1): the evacuation queue is the host thing's -- a house made
    under the old one's name the same frame (empty, or with a passenger of its own) neither drops the old house's
    job nor takes it: the old passenger goes out where the old house is, the new one's stays in."""
    s = simsmall.small_world()
    old = s.add('host', 'AM_Apartments_01', None, 300.0, 300.0)
    p = s.add('p', 'AlliedAntiInfantryInfantry', 'Player_1', 400.0, 300.0)
    assert s.garrison.put(p, old, script=True) and s.garrison.evacuate(old)
    new = s.add('host', 'AM_Apartments_01', None, 600.0, 300.0, shadow=True)  # (map load's path)
    q = s.add('q', 'AlliedAntiInfantryInfantry', 'Player_1', 700.0, 300.0)
    if filled:
        assert s.garrison.put(q, new, script=True)
    s.garrison.due()
    assert [(f[1].name, f[2]) for f in s.garrison.flying] == [('p', (300.0, 300.0))]
    assert s.garrison.held(old) == [] and s.garrison.held(new) == ([q] if filled else [])


def test_a_transport_keeps_its_owner_and_its_passengers_are_enclosed():
    s = simsmall.small_world()
    boat = s.add('boat', 'AlliedAntiInfantryVehicle', 'Player_2', 300.0, 300.0)
    gi = s.add('gi', 'AlliedAntiInfantryInfantry', 'Player_1', 400.0, 300.0)
    assert s.garrison.spec(boat) is None and s.garrison.box(boat)['tag'] == 'TransportContain'
    assert s.garrison.put(gi, boat, script=True)
    assert boat.owner == 'Player_2' and 'ENCLOSED' in gi.script_status and s.garrison.held(boat) == [gi]


def test_an_evacuate_button_empties_only_a_host_whose_command_set_holds_it():
    # review 1122yy #1: the Sudden transport's DisguisedEvacuate pressed on a Twinblade emptied it all the same
    s = simsmall.small_world(model=False)
    boat = s.add('boat', 'AlliedAntiInfantryVehicle', 'Player_1', 300.0, 300.0)
    assert s.garrison.put(s.add('gi', 'AlliedAntiInfantryInfantry', 'Player_1', 400.0, 300.0), boat, script=True)
    for button, out in (('Command_DisguisedEvacuate', False), ('Command_AlliedAntiInfantryVehicleEvacuate', True)):
        s.act('NAMED_USE_COMMANDBUTTON_ABILITY_AT_WAYPOINT', ['boat', button, '@900,300'], None)
        assert (boat.serial in s.garrison.ejecting) == out


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


def test_the_multigunner_turret_seats_one_of_its_own_keeps_him_hurt_and_kills_him_with_it():
    """bench engine_turretgar_e g: one seat, no enemy, still in at 10 % (GARRISONABLE_UNTIL_DESTROYED), dead with it."""
    s = simsmall.small_world()
    gun = s.add('gun', 'AlliedBaseDefense', 'Player_1', 300.0, 300.0)
    a, b = (s.add(n, 'AlliedAntiInfantryInfantry', 'Player_1', 400.0, 300.0) for n in 'ab')
    foe = s.add('foe', 'AlliedAntiInfantryInfantry', 'Soviet_1', 400.0, 300.0)
    assert [s.garrison.put(u, gun) for u in (foe, a, b)] == [False, True, False]
    gun.set_hp(gun.max_hp * .1, tell=False)
    s.garrison.hurt(gun)
    assert s.garrison.held(gun) == [a]
    s.world.kill(gun, 'test')
    assert not a.alive and b.alive


def test_the_bomber_drop_flies_its_load_to_the_spot_before_it_ejects():
    """engine_acts_drop air (round 276): the drop OCL's two bombers carry their InitialPayload; StartAbilityRange 0
    with the spot away: the load stays aboard until the bomber is there (garrison.ARRIVE), then goes out."""
    bomber = 'CAMP_AlliedBomberAircraft_Infantry_1'
    assert simgarrison.ocl_transports('OCL_CAMPAlliedBomberDrop2') == [
        (bomber, -70.0, 0.0, 'SpecialPower_EjectPassengers'), (bomber, 70.0, 0.0, 'SpecialPower_EjectPassengers')]
    assert simgarrison.initial_payload(bomber) == [('AlliedAntiInfantryInfantry', 3), ('AlliedAntiVehicleInfantry', 2)]
    s = simsmall.small_world()
    g = s.add('bomber', bomber, 'Player_1', 300.0, 300.0)
    gi = s.add('gi', 'AlliedAntiInfantryInfantry', 'Player_1', 300.0, 300.0)
    assert s.garrison.put(gi, g, script=True)
    assert s.garrison.eject(g, None, (300.0, 700.0), power='SpecialPower_EjectPassengers')
    s.garrison.due()
    assert s.garrison.held(g) == [gi]
    g.y = 695.0
    s.garrison.due()
    assert s.garrison.held(g) == [] and not getattr(g, 'flee', None)
    s.garrison.due()                             # emptied: RunOffMapWhenDone sends it off (review 1121mm #2)
    assert s.garrison.leaving == [g]
    simability.flee_due(s, simorder.Peers(s), 0)
    assert g.flee and 'FLEE_OFF_MAP' in g.script_status
    import engine.script.cond_object as cond     # the type area counts leave out one without SELECTABLE (mm #3)
    s.areas['a'] = [(0, 0), (1000, 0), (1000, 1000), (0, 1000)]
    for name, fn in (('', cond.player_has_comparison_unit_type_in_trigger_area),
                     ('_COMPLETELY_BUILT', cond.player_has_comparison_unit_type_in_trigger_area_completely_built)):
        assert [fn(s, name, ['Player_1', 3, 1, t, 'a']) for t in (bomber, 'AlliedAntiInfantryInfantry')] == [False, True]
