"""The refactor line R's part of the 11-19 same-name sweep (work/logs/same_name_audit_1119.md, "R · Body、死亡、驻军、
生成" and simmine / the attachment status under "其他"): a thing picked once is kept as that thing and never looked up
again by its name -- a script reference of the name, or a thing made under the name since, must not take its place.
Names are read only where the input itself is a name. One small world each; INFERRED all (no bench reading: a name
taken again is rare in the retail scripts)."""
import math
import types

import pytest

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
    p2 = s.add('p', GI, 'Player_1', 300.0, 320.0, shadow=True)  # at the door, under the name
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
    p2 = s.add('p', GI, 'Player_1', 600.0, 300.0, shadow=True)  # (map load's path)
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
    s.add('gun', GI, 'Player_2', 500.0, 300.0, shadow=True)  # the name taken by another player's infantry
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
    mcv2 = s.add('mcv', 'AlliedMCV', 'Player_1', 600.0, 300.0, shadow=True)  # (map load's path)
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
    new = s.add('node', 'OreNode', 'PlyrCivilian', 300.0, 0.0, shadow=True)  # (map load's path)
    _run(s, mining, (end + 1, 6000), paid, lambda: sum(g for _, g in paid) >= taken + 2 * simmine.MINE_LOAD)
    assert mining.nodes[old.serial]['gathered'] == taken                # the old node's ore: no more taken
    assert 0 < mining.nodes[new.serial]['gathered'] <= sum(g for _, g in paid) - taken + simmine.MINE_LOAD
    assert s.bodies['miner'].find(interfaces.OreMiner).node is new


def test_a_miner_docked_before_loading_takes_nothing_from_a_node_that_has_left_the_world():
    """Review 1119p #4: docked at the node, its batch not yet reserved, the node replaced under its name far away:
    nothing more comes off the old node's ore; the miner looks again (as on its way there). A batch already
    reserved (loading) is left to its own rule."""
    s, mining = _mining()
    paid = []
    b = s.bodies['miner']
    old = s.bodies['node']
    end = _run(s, mining, (1, 2000), paid, lambda: b.mine is not None and b.mine['state'] == 'docked')
    assert mining.nodes[old.serial]['gathered'] == 0 and mining.nodes[old.serial]['at'] is b
    new = s.add('node', 'OreNode', 'PlyrCivilian', 900.0, 0.0, shadow=True)  # (map load's path)
    _run(s, mining, (end + 1, 6000), paid, lambda: sum(g for _, g in paid) >= simmine.MINE_LOAD)
    assert mining.nodes[old.serial]['gathered'] == 0 and mining.nodes[old.serial]['at'] is None
    assert mining.nodes[new.serial]['gathered'] >= simmine.MINE_LOAD     # (the next batch may be reserved)
    assert b.find(interfaces.OreMiner).node is new


@pytest.mark.parametrize('end_it', ['destroy', 'delete'])
@pytest.mark.parametrize('stage', ['to node', 'docked'])
def test_a_node_killed_or_deleted_before_its_batch_is_reserved_gives_no_ore(stage, end_it):
    """Review 1119u P2 #4: a node destroyed stays in the world's bodies (dead) -- held() finds it by identity, so the
    miner on its way there or docked at it still reserved MINE_LOAD off it. Its batch not yet reserved, a dead or
    deleted node gives nothing; the miner looks again (no other node here: nothing is ever paid). INFERRED (no
    bench reading); a batch already reserved (loading) is left to its own rule."""
    s, mining = _mining()
    paid = []
    b = s.bodies['miner']
    old = s.bodies['node']
    end = _run(s, mining, (1, 2000), paid, lambda: b.mine is not None and b.mine['state'] == stage)
    assert b.mine['state'] == stage
    getattr(s, end_it)(old, 'test')
    _run(s, mining, (end + 1, 3000), paid)
    assert mining.nodes[old.serial]['gathered'] == 0 and mining.nodes[old.serial]['at'] is not b
    assert paid == [] and b.mine['state'] == 'locate'


def test_a_load_goes_to_the_refinery_picked_not_a_thing_made_under_its_name():
    s, mining = _mining()
    paid = []
    b = s.bodies['miner']
    end = _run(s, mining, (1, 2000), paid, lambda: b.mine is not None and b.mine['state'] == 'to refinery')
    assert b.mine['state'] == 'to refinery' and paid == []
    s.add('ref', TANK, 'Player_2', 0.0, 0.0, shadow=True)  # an enemy tank under the name
    _run(s, mining, (end + 1, end + 600), paid)
    assert [g for o, g in paid if o == 'Player_1'] == [] and b.mine['state'] == 'find refinery'    # none of its
                                                            # own left: it keeps looking


def test_a_load_cut_off_mid_unload_brings_only_what_is_left_to_the_next_refinery():
    """Review 1119p #1: the near refinery taken under its name after 10 unload frames (80 paid of 250); the miner goes
    on to its own far one with the 170 left, not a full load again (it paid 10 x 8 + 250 = 330). INFERRED: the
    cargo is what was not yet delivered; the far unload pays the rest over the usual MINE_DOCK frames."""
    s = simsmall.small_world([('ref', 'AlliedRefinery', 'Player_1', 0.0, 0.0),
                              ('ref2', 'AlliedRefinery', 'Player_1', -900.0, 0.0),
                              ('node', 'OreNode', 'PlyrCivilian', 300.0, 0.0),
                              ('miner', 'AlliedMiner', 'Player_1', 150.0, 60.0)])
    mining = simmine.Mining()
    paid = []
    b = s.bodies['miner']
    end = _run(s, mining, (1, 2000), paid, lambda: b.mine is not None and b.mine['state'] == 'unloading'
               and b.mine['n'] == 10)
    got = sum(g for o, g in paid if o == 'Player_1')
    assert 0 < got < simmine.MINE_LOAD and b.mine['load'] == simmine.MINE_LOAD
    s.add('ref', TANK, 'Player_2', 0.0, 0.0, shadow=True)  # an enemy tank under the near one's name
    end = _run(s, mining, (end + 1, end + 2000), paid, lambda: b.mine['state'] == 'locate')
    assert b.find(interfaces.OreMiner).refinery is s.bodies['ref2']
    assert sum(g for o, g in paid if o == 'Player_1') == simmine.MINE_LOAD     # one load's money, not 330


def test_a_nodes_claim_and_dock_are_the_miners_own_not_a_thing_made_under_its_name():
    s, mining = _mining()
    a = s.bodies['miner']
    node = s.bodies['node']
    _run(s, mining, (1, 3), [])
    n = mining.nodes[node.serial]
    assert n['claim'] is a
    n['at'] = a
    a2 = s.add('miner', 'AlliedMiner', 'Player_1', 300.0, 60.0, shadow=True)  # (map load's path)
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
    child2 = s.add('child', GI, 'Player_1', 500.0, 300.0, shadow=True)  # (map load's path)
    parent2 = s.add('parent', TANK, 'Player_1', 500.0, 300.0, shadow=True)  # (map load's path)
    s.attachment_tick()
    assert child2.attachment_status == set() and parent2.attachment_status == set()
    assert child2.serial not in s.attachments


def test_a_name_a_living_thing_holds_is_refused_and_nothing_is_made():
    """Coord ruling 11-19 17:15: Sim.add never puts a second thing under a living one's name -- what keeps the first
    by identity (a walk-in, a queue, a mine) would be left holding one that silently left the world."""
    s = simsmall.small_world()
    p = s.add('p', GI, 'Player_1', 300.0, 300.0)
    names, serials = set(s.bodies), {b.serial for b in s.living()}
    with pytest.raises(ValueError, match="'p' is held by a living"):
        s.add('p', TANK, 'Player_2', 600.0, 300.0)
    assert set(s.bodies) == names and {b.serial for b in s.living()} == serials
    assert s.bodies['p'] is p and p.alive and p in s.living()


def test_a_dead_or_deleted_ones_name_may_be_taken_again():
    s = simsmall.small_world()
    p = s.add('p', GI, 'Player_1', 300.0, 300.0)
    q = s.add('q', GI, 'Player_1', 400.0, 300.0)
    s.destroy(p, 'test')
    s.delete(q, 'test')
    p2 = s.add('p', GI, 'Player_1', 300.0, 300.0)
    q2 = s.add('q', TANK, 'Player_1', 400.0, 300.0)
    assert s.bodies['p'] is p2 and s.bodies['q'] is q2 and p2 in s.living() and q2 in s.living()
    assert p not in s.living() and q not in s.living()


# ---- O31 (same_name_audit_1119b): a build queue is its factory's own, not its name's

def _queued_at_a_dead_factory(what):
    """A factory of Player_1's queues `what` and pays some; it dies and a living one of the same template is made
    under its name, elsewhere and another player's, before the job is due."""
    s = simsmall.small_world()
    s.money['Player_1'] = s.money['Player_2'] = 100000
    if what == GI:
        f = s.add('f', 'AlliedBarracks', 'Player_1', 300.0, 300.0)
    else:
        s.add('ref', 'AlliedRefinery', 'Player_1', 700.0, 700.0)
        f = s.add('f', 'AlliedConstructionYard', 'Player_1', 300.0, 300.0)
    assert s.order_build('Player_1', what, factory=f if what == GI else None)
    s.produce_due(30)
    paid = 100000 - s.money['Player_1']
    assert paid > 0
    s.destroy(f, 'test')
    f2 = s.add('f', f.template, 'Player_2', 1500.0, 1500.0)
    return s, f2, paid


def test_a_unit_queued_at_a_factory_that_died_does_not_come_out_of_one_made_under_its_name():
    s, f2, paid = _queued_at_a_dead_factory(GI)
    s.produce_due(30 * 60)
    assert not [b for b in s.living() if b.template == GI]
    assert s.money['Player_1'] == 100000 - paid and s.money['Player_2'] == 100000     # gone with it, not refunded
    assert not s.queues                                     # the dead one's queue went along
    assert s.order_build('Player_2', GI, factory=f2) and list(s.queues) == [f2.serial]


def test_an_object_upgrade_bought_at_a_structure_that_died_does_not_arrive_on_one_made_under_its_name():
    s, f2, _ = _queued_at_a_dead_factory('Upgrade_AlliedTech2')
    s.produce_due(30 * 60)
    assert 'Upgrade_AlliedTech2' not in f2.upgrades and not s.player_ups.get('Player_1')


# ---- review 1119w P2 #1 / #3: a thing made without a name goes under a key no living thing holds

def test_an_unnamed_creation_whose_counted_key_a_living_one_holds_takes_the_next_free_key():
    s = simsmall.small_world()
    s.point = lambda wp: (300.0, 300.0)
    s.add('x', GI, 'Player_1', 900.0, 900.0)
    held = s.add(f'#created 2 {GI}', GI, 'Player_1', 600.0, 600.0)   # a named creation took the counted key
    simact_world.create_unnamed_on_team_at_waypoint(s, 'CREATE_UNNAMED_ON_TEAM_AT_WAYPOINT', (GI, 'Player_1/t', 'wp'),
                                                    types.SimpleNamespace(name='S'))
    assert s.bodies[f'#created 2 {GI}'] is held and held.alive
    made = s.bodies[f'#created 3 {GI}']
    assert (made.x, made.y, made.team) == (300.0, 300.0, 'Player_1/t')


def test_an_unpacked_builders_archive_key_leaves_a_living_one_under_its_counted_key_in_place():
    s = simsmall.small_world()
    mcv = s.add('mcv', 'AlliedMCV', 'Player_1', 300.0, 300.0)
    mcv.replace = True
    mcv.building = ('AlliedConstructionYard', (300.0, 300.0), 50.0)
    assert s.at_site(mcv, 0.0)
    held = s.add('#packed 1 mcv', GI, 'Player_1', 900.0, 900.0)   # the count the key reads (the builder popped)
    s.build_due(s.frame_now() + 10)
    assert s.bodies['#packed 1 mcv'] is held and held.alive
    assert s.bodies['#packed 2 mcv'] is mcv and s.bodies['mcv'].template == 'AlliedConstructionYard'


RUSH = 'Command_TriggerRushAttackSpecialPower'


def test_a_movement_power_running_on_a_dead_one_does_not_block_or_end_one_made_under_its_name():
    """Same-name sweep 11-19b O58: the rush in flight is the pressing thing's own (simspecial.movement_due by serial)."""
    s = simsmall.small_world()
    p = s.add('p', 'JapanAntiVehicleVehicleTech3', 'Player_1', 300.0, 300.0)
    assert s.movement_power_press(p, RUSH, (p.x + 250, p.y))
    s.advance(30)                                                     # apart by more than a tick (advance's step)
    s.destroy(p, 'test')
    p2 = s.add('p', 'JapanAntiVehicleVehicleTech3', 'Player_1', 300.0, 600.0)
    assert s.movement_power_press(p2, RUSH, (p2.x + 250, p2.y))       # not "a repeated press"
    (due2, *_), = [v for v in s.specials.movement_due.values() if v[1] is p2]
    assert set(s.specials.movement_due) == {p.serial, p2.serial}
    old_due = s.specials.movement_due[p.serial][0]
    assert old_due < due2
    s.advance(old_due - s.frame_now() + 1)                            # the old one's rush ends: only its own
    assert set(s.specials.movement_due) == {p2.serial} and p2.dest is not None


def _bare_brain(s, unpack):
    """A bare Brain of Player_1 on the small world (test_command_port._brain's way): no model, the host's unpack
    frames `unpack` for every template."""
    import simai
    host = simai.SimAI(s, lib=object(), data=object())
    host.unpack = lambda template: unpack
    br = object.__new__(simai.Brain)
    br.host, br.world, br.peers, br.player, br.ids, br.hp = host, s, host.peers, 'Player_1', {}, {}
    br.settings, br.observe = host.settings, host.observe
    br.commands, br.systems = host.commands, host.systems   # the command port, the players' systems (R3 13f-2c)
    br.made, br.unit_q, br.trace, br.later = {}, [], [], []
    return br


def test_an_ai_factory_made_under_a_dead_unpacking_ones_name_builds_at_once():
    """Same-name sweep 11-19b O63: the AI's ready gate (made + unpack) reads the factory's own birth frame -- a ready
    barracks under the name of one the AI set down and that died unpacking is not held back to the old one's end."""
    s = simsmall.small_world(model=False)
    s.money['Player_1'] = 10000
    br = _bare_brain(s, unpack=300)
    br.later.append((0, 'AlliedBarracks', (300.0, 300.0), ''))
    br.later_due(0)                                     # the AI's own: born now, unpacking 300 frames
    (old,) = [b for b in s.living() if b.template == 'AlliedBarracks']
    br.unit_q = [GI]
    br.unit_due(30)
    assert br.unit_q == [GI] and not s.queues           # the old one still unpacking: nothing yet
    s.destroy(old, 'test')
    new = s.add(old.name, 'AlliedBarracks', 'Player_1', 600.0, 300.0)   # not the AI's: ready
    br.unit_due(31)
    assert br.unit_q == [] and list(s.queues) == [new.serial]


def test_an_ai_unit_goes_to_the_ready_factory_it_picked_not_one_still_unpacking():
    """Same-name sweep 11-19b N03: the AI's build names the free factory it picked (by serial) -- the shortest-queue
    pick no longer hands the job to an earlier barracks of the AI's still unpacking."""
    s = simsmall.small_world(model=False)
    s.money['Player_1'] = 10000
    br = _bare_brain(s, unpack=300)
    br.later.append((0, 'AlliedBarracks', (300.0, 300.0), ''))
    br.later_due(0)                                     # A: the AI's own, unpacking 300 frames
    (a,) = [b for b in s.living() if b.template == 'AlliedBarracks']
    b = s.add('ready barracks', 'AlliedBarracks', 'Player_1', 600.0, 300.0)   # B: ready
    br.unit_q = [GI]
    br.unit_due(30)
    assert br.unit_q == [] and list(s.queues) == [b.serial] and a.serial != b.serial


# ---- review 1119y P2 #3 / #4: every internal key goes through simworld.free_key, which counts a key the schedule
# still holds a module of as taken too

def test_an_unpacked_builders_archive_key_leaves_a_dead_one_the_schedule_still_holds_in_place():
    import simsnap
    s = simsmall.small_world(model=False)                                 # (the private model takes no snapshots)
    mcv = s.add('mcv', 'AlliedMCV', 'Player_1', 300.0, 300.0)
    mcv.replace = True
    mcv.building = ('AlliedConstructionYard', (300.0, 300.0), 50.0)
    assert s.at_site(mcv, 0.0)
    held = s.add('#packed 2 mcv', GI, 'Player_1', 900.0, 900.0)          # living, under the count after the pop
    dead = s.add('#packed 3 mcv', GI, 'Player_1', 1500.0, 900.0)
    s.destroy(dead, 'test')
    assert len(s.bodies) == 3 and any(m in s.world.schedule.seq for m in dead.modules)   # its AutoHeal still runs
    s.build_due(s.frame_now() + 10)
    assert s.bodies['#packed 2 mcv'] is held and s.bodies['#packed 3 mcv'] is dead
    assert s.bodies['#packed 4 mcv'] is mcv and s.bodies['mcv'].template == 'AlliedConstructionYard'
    simsnap.snapshot(s)                                                   # every scheduled module's thing is held


def test_an_unnamed_map_object_does_not_take_the_index_key_a_named_one_placed_before_holds():
    import parts
    import sim
    from maps import island
    k = len(getattr(island, 'OBJECTS', []))
    m = parts.Mission(name='T', map=island, scripts=[],
                      objects=[parts.Obj(GI, 1250, 2360, side='p1', name=f'#{k + 1}'), parts.Obj(GI, 1550, 2360, side='p1')])
    s = sim.Sim(m, model=False)
    named = s.bodies[f'#{k + 1}']
    assert named.alive and named.x == 1250.0
    other = [b for b in s.living() if b.template == GI and b is not named]
    assert [(b.x, b.alive) for b in other] == [(1550.0, True)] and s.bodies[other[0].name] is other[0]


def test_a_script_line_make_does_not_take_the_counted_key_a_living_one_holds():
    s = simsmall.small_world()
    held = s.add('UNIT - SIM Made 1', GI, 'Player_1', 900.0, 900.0)
    s.commands.post_line(f'0 造 {GI} 在 @1500,2400')
    s.advance(1)
    assert s.bodies['UNIT - SIM Made 1'] is held and held.alive
    made = [b for b in s.living() if b is not held and b.template == GI]
    assert len(made) == 1 and (made[0].x, made[0].y) == (1500.0, 2400.0)
