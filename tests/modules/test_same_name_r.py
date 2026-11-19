"""The refactor line R's part of the 11-19 same-name sweep (work/logs/same_name_audit_1119.md, "R · Body、死亡、驻军、
生成" and simmine / the attachment status under "其他"): a thing picked once is kept as that thing and never looked up
again by its name -- a script reference of the name, or a thing made under the name since, must not take its place.
Names are read only where the input itself is a name. One small world each; INFERRED all (no bench reading: a name
taken again is rare in the retail scripts)."""
import math
import types

from test_plans import small  # noqa: F401,I001  (tests/ is on the path by its conftest; puts experimental/cnv on it)
import simact_object  # noqa: E402
import simact_world  # noqa: E402
import simcond_object  # noqa: E402
import simcond_world  # noqa: E402
import simmine  # noqa: E402
import simsmall  # noqa: E402
from engine.kernel import interfaces  # noqa: E402

GI = 'AlliedAntiInfantryInfantry'
TANK = 'AlliedAntiVehicleVehicleTech1'


def test_one_sent_into_a_building_is_the_one_that_goes_in_not_a_thing_made_under_its_name():
    s = simsmall.small_world()
    house = s.add('house', 'AM_Apartments_01', 'PlyrCivilian', 300.0, 300.0)
    p = s.add('p', GI, 'Player_1', 900.0, 300.0)
    s.garrison.send(p, house)
    p2 = s.add('p', GI, 'Player_1', 300.0, 320.0)      # at the door, under the name
    s.garrison.due()
    assert s.garrison.held(house) == [] and not s.garrison.busy(p2)
    assert s.garrison.put(p2, house)                    # it may go in: the walk was simply not its own


def test_one_on_its_way_into_a_building_is_not_idle():
    """A sequential script's next step waits for it (simorder.idle reads the walk-ins by the thing)."""
    s = simsmall.small_world()
    house = s.add('house', 'AM_Apartments_01', 'PlyrCivilian', 300.0, 300.0)
    p = s.add('p', GI, 'Player_1', 900.0, 300.0)
    s.garrison.send(p, house)
    p.path = []                                         # only the walk-in keeps it busy
    assert p.serial in s.garrison.going and not s.idle(p)


def test_one_inside_is_that_thing_a_thing_made_under_its_name_is_not_inside_nor_let_out():
    s = simsmall.small_world()
    house = s.add('house', 'AM_Apartments_01', None, 300.0, 300.0)
    p = s.add('p', GI, 'Player_1', 300.0, 320.0)
    assert s.garrison.put(p, house, script=True)
    p2 = s.add('p', GI, 'Player_1', 600.0, 300.0)
    assert not s.garrison.busy(p2) and not s.garrison.out(p2)
    assert s.garrison.held(house) == [p] and s.garrison.where[p.serial] is house and (p2.x, p2.y) == (600.0, 300.0)
    (box,) = house.find(interfaces.Contain)
    assert set(box.given) == {p.serial}
    assert s.garrison.out(p) and s.garrison.held(house) == []


def test_the_attacked_by_conditions_read_the_object_that_hit_not_a_thing_made_under_its_name():
    s = simsmall.small_world()
    victim = s.add('victim', 'AlliedPowerPlant', 'Player_1', 300.0, 300.0)
    gun = s.add('gun', TANK, 'Player_2', 500.0, 300.0)
    victim.set_last_damage('Player_2', gun)
    assert simcond_object.named_attacked_by_player(s, 'NAMED_ATTACKED_BY_PLAYER', ['victim', 'Player_2'])
    gun.owner = 'Player_3'                              # changed hands: counts for its new owner (the game's id)
    assert simcond_object.named_attacked_by_player(s, 'NAMED_ATTACKED_BY_PLAYER', ['victim', 'Player_3'])
    s.add('gun', GI, 'Player_2', 500.0, 300.0)          # the name taken by another player's infantry
    assert victim.last_by == 'gun' and victim.find(interfaces.Body).last_attacker() is gun
    assert not simcond_object.named_attacked_by_player(s, 'NAMED_ATTACKED_BY_PLAYER', ['victim', 'Player_2'])
    assert not simcond_object.named_attacked_by_objecttype(s, 'NAMED_ATTACKED_BY_OBJECTTYPE', ['victim', GI])
    assert simcond_world.attacker(s, victim) is None


def test_reinforcements_at_a_unit_come_where_the_unit_checked_stands():
    s = simsmall.small_world()
    s.templates['Player_1/T'] = {'units': [(GI, 1, 1)], 'instances': 0}
    s.add('lead', TANK, 'Player_1', 300.0, 300.0)
    other = s.add('other', TANK, 'Player_2', 700.0, 600.0)
    s.refs['lead'] = other                              # the script's reference of that name
    was = set(s.bodies)
    simact_world.create_reinforcement_team_at_unit_position(s, 'CREATE_REINFORCEMENT_TEAM_AT_UNIT_POSITION',
                                                            ['T', 'lead'], types.SimpleNamespace(name='test'))
    (new,) = [s.bodies[k] for k in set(s.bodies) - was]
    assert math.hypot(new.x - other.x, new.y - other.y) < 1.0


def test_a_named_walk_to_a_container_goes_where_the_one_checked_stands():
    s = simsmall.small_world()
    b = s.add('b', GI, 'Player_1', 300.0, 300.0)
    s.add('car', TANK, 'Player_1', 400.0, 300.0)
    other = s.add('other', TANK, 'Player_1', 300.0, 600.0)
    s.refs['car'] = other
    simact_object.named_garrison_specific_building(s, 'NAMED_GARRISON_SPECIFIC_BUILDING', ['b', 'car'], None)
    end = b.path[-1] if b.path else b.dest
    assert end is not None and math.hypot(end[0] - other.x, end[1] - other.y) < 60.0


def test_an_unpack_due_is_the_builders_own_a_thing_made_under_its_name_is_not_replaced():
    s = simsmall.small_world()
    mcv = s.add('mcv', 'AlliedMCV', 'Player_1', 300.0, 300.0)
    mcv.replace = True
    mcv.building = ('AlliedConstructionYard', (300.0, 300.0), 50.0)
    assert s.at_site(mcv, 0.0)
    mcv2 = s.add('mcv', 'AlliedMCV', 'Player_1', 600.0, 300.0)
    mcv2.replace = True
    was = set(s.bodies)
    s.build_due(s.frame_now() + 10)
    assert mcv2.alive and not mcv2.deleted and s.bodies['mcv'] is mcv2 and set(s.bodies) == was
    assert s.due == []


def _mining():
    s = simsmall.small_world([('ref', 'AlliedRefinery', 'Player_1', 0.0, 0.0),
                              ('node', 'OreNode', 'PlyrCivilian', 300.0, 0.0),
                              ('miner', 'AlliedMiner', 'Player_1', 150.0, 60.0)])
    return s, simmine.Mining()


def _run(s, mining, frames, paid, until=None):
    for frame in range(frames[0], frames[1]):
        mining.mine_due(s, frame, lambda owner, give: paid.append((owner, give)))
        if until and until():
            return frame
    return frames[1]


def test_a_node_made_under_the_old_ones_name_has_none_of_its_ore_taken():
    s, mining = _mining()
    paid = []
    old = s.bodies['node']
    end = _run(s, mining, (1, 2000), paid, lambda: sum(g for _, g in paid) >= simmine.MINE_LOAD)
    taken = mining.nodes[old.serial]['gathered']
    assert taken >= simmine.MINE_LOAD
    new = s.add('node', 'OreNode', 'PlyrCivilian', 300.0, 0.0)
    _run(s, mining, (end + 1, 6000), paid, lambda: sum(g for _, g in paid) >= taken + 2 * simmine.MINE_LOAD)
    assert mining.nodes[old.serial]['gathered'] == taken                # the old node's ore: no more taken
    assert 0 < mining.nodes[new.serial]['gathered'] <= sum(g for _, g in paid) - taken + simmine.MINE_LOAD
    assert s.bodies['miner'].find(interfaces.OreMiner).node is new


def test_a_load_goes_to_the_refinery_picked_not_a_thing_made_under_its_name():
    s, mining = _mining()
    paid = []
    b = s.bodies['miner']
    end = _run(s, mining, (1, 2000), paid, lambda: b.mine is not None and b.mine['state'] == 'to refinery')
    assert b.mine['state'] == 'to refinery' and paid == []
    s.add('ref', TANK, 'Player_2', 0.0, 0.0)                # an enemy tank under the name
    _run(s, mining, (end + 1, end + 600), paid)
    assert [g for o, g in paid if o == 'Player_1'] == [] and b.mine['state'] == 'find refinery'    # none of its
                                                            # own left: it keeps looking


def test_a_nodes_claim_and_dock_are_the_miners_own_not_a_thing_made_under_its_name():
    s, mining = _mining()
    a = s.bodies['miner']
    node = s.bodies['node']
    _run(s, mining, (1, 3), [])
    n = mining.nodes[node.serial]
    assert n['claim'] is a
    n['at'] = a
    a2 = s.add('miner', 'AlliedMiner', 'Player_1', 300.0, 60.0)
    om = a2.find(interfaces.OreMiner)
    om.set_trip({'state': 'docked', 'node': None, 'ref': None, 'due': 10 ** 9, 'load': 0, 'n': 0, 'leg': None})
    om.head_for(node=node)
    b = s.add('b', 'AlliedMiner', 'Player_1', 150.0, -60.0)
    assert not mining._claimed(s, n, b, node) and not mining._docked(s, n['at'], node)
    n['claim'] = n['at'] = a2                           # the new one's own claim and dock hold
    assert mining._claimed(s, n, b, node) and mining._docked(s, n['at'], node)


def test_the_attachment_status_goes_on_the_linked_things_not_on_ones_made_under_their_names():
    s = simsmall.small_world()
    child = s.add('child', GI, 'Player_1', 300.0, 300.0)
    parent = s.add('parent', TANK, 'Player_1', 300.0, 300.0)
    s.attachments[child.serial] = (child, parent, {'child': {'ATTACHED'}, 'parent': {'VEHICLE_ATTACHED'}})
    s.attachment_tick()
    assert child.attachment_status == {'ATTACHED'} and parent.attachment_status == {'VEHICLE_ATTACHED'}
    child2 = s.add('child', GI, 'Player_1', 500.0, 300.0)
    parent2 = s.add('parent', TANK, 'Player_1', 500.0, 300.0)
    s.attachment_tick()
    assert child2.attachment_status == set() and parent2.attachment_status == set()
    assert child2.serial not in s.attachments
