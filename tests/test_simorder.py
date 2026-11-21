"""Unit orders as rules (simorder, L5, ADR 0029 step ⑧ "测试分两层"): on the minimal world, only the order functions
run. The whole-mission versions against the bench: test_simbench.py (engine_acts_y hunt, engine_runoffmap, waypaths)."""
from test_plans import small  # noqa: F401,I001  (puts experimental/cnv on the path)
import engine.orders.hunt as simhunt  # noqa: E402
import engine.orders.order as simorder  # noqa: E402
import engine.orders.seq as simseq  # noqa: E402
import engine.testing.small as simsmall  # noqa: E402

APOC = 'SovietAntiVehicleVehicleTech3'


def test_a_hunt_waits_its_repick_after_its_target_dies_then_attack_moves_on_the_nearest_hostile():
    s = simsmall.small_world([('c1', APOC, 'Player_1', 0.0, 0.0), ('c2', APOC, 'Player_1', 60.0, 0.0),
                              ('near', APOC, 'Soviet_1', 600.0, 0.0), ('far', APOC, 'Soviet_1', 1200.0, 0.0)])
    crew = [s.bodies['c1'], s.bodies['c2']]
    hunt = [crew, s.bodies['near'], 0]
    s.hunts.append(hunt)
    peers = simorder.Peers(s)
    s.destroy(s.bodies['near'], 'test')
    simhunt.hunt_due(s, peers, 10)                       # its target just died: the re-pick waits
    assert hunt[1] is None and hunt[2] == 10 + simhunt.HUNT_REPICK
    simhunt.hunt_due(s, peers, 10 + simhunt.HUNT_REPICK - 1)
    assert hunt[1] is None and all(b.mode != 'attack' for b in crew)
    simhunt.hunt_due(s, peers, 10 + simhunt.HUNT_REPICK)
    assert hunt[1] is s.bodies['far'] and all(b.mode == 'attack' for b in crew)


def test_a_new_hunt_takes_its_members_out_of_their_old_crews_and_picks_at_once():
    s = simsmall.small_world([('c1', APOC, 'Player_1', 0.0, 0.0), ('c2', APOC, 'Player_1', 60.0, 0.0),
                              ('foe', APOC, 'Soviet_1', 900.0, 0.0)])
    c1, c2 = s.bodies['c1'], s.bodies['c2']
    s.hunts.append([[c1, c2], None, 10 ** 6])            # an old crew, its pick far off
    simhunt.hunt_due(s, simorder.Peers(s), 5, [c1])
    assert s.hunts == [[[c1], s.bodies['foe'], 5]] and c1.mode == 'attack' and c2.mode != 'attack'


def test_stop_and_stand_drop_the_order_and_a_short_move_is_held_up():
    s = simsmall.small_world([('a', APOC, 'Player_1', 0.0, 0.0)])
    b = s.bodies['a']
    b.mode, b.goal, b.path, b.move_to, b.dest = 'move', None, [], (500.0, 0.0), (500.0, 0.0)
    assert simorder.held_up(b)                           # its way ended 500 short of where it was sent
    b.dest = (b.x + simorder.ARRIVE / 2, 0.0)
    b.move_to = b.dest
    assert not simorder.held_up(b)                       # within ARRIVE: it got there
    simorder.stand(b)
    assert b.mode == 'idle' and b.move_to is None and simseq.idle(simorder.Peers(s), b)
