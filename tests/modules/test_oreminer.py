"""The OreMinerBehavior module (engine/modules/oreminer.py, step M9): a miner's trip, kept on the module and read
through the body's `mine` forward; which things mine is "has this module". The collector loop's rules (loads, the
unloading, node claims): tests/test_simmine.py, tests/modules/test_queuedock.py; bench replays: tests/test_simbench.py."""
import pytest

from test_plans import small  # noqa: F401,I001  (tests/ is on the path by its conftest; puts experimental/cnv on it)
import engine.objects.mine as simmine  # noqa: E402
import engine.testing.small as simsmall  # noqa: E402
from engine.kernel import interfaces  # noqa: E402

MINERS = ('AlliedMiner', 'AlliedMiner_Naval', 'SovietMiner', 'SovietMiner_Naval', 'JapanMiner', 'JapanMiner_Naval')


def _world():
    return simsmall.small_world([('ref', 'AlliedRefinery', 'Player_1', 0.0, 0.0),
                                 ('node', 'OreNode', 'PlyrCivilian', 300.0, 0.0),
                                 ('miner', 'AlliedMiner', 'Player_1', 150.0, 60.0)])


def test_every_retail_miner_has_one_and_no_trip_before_it_starts():
    s = simsmall.small_world([(f'm{k}', t, 'Player_1', 100.0 * k, 0.0) for k, t in enumerate(MINERS)]
                             + [('ref', 'AlliedRefinery', 'Player_1', 0.0, 500.0),
                                ('node', 'OreNode', 'PlyrCivilian', 300.0, 500.0)])
    for k in range(len(MINERS)):
        b = s.bodies[f'm{k}']
        assert type(b.find(interfaces.OreMiner)).__name__ == 'OreMiner', MINERS[k]
        assert b.mine is None
    assert s.bodies['ref'].find(interfaces.OreMiner) is None
    assert s.bodies['node'].find(interfaces.OreMiner) is None
    with pytest.raises(AttributeError):
        s.bodies['m0'].mine = {}


def test_the_loop_keeps_the_trip_on_the_module_and_pays_the_load():
    s = _world()
    b = s.bodies['miner']
    paid = []
    mining = simmine.Mining()
    mining.mine_due(s, 1, lambda owner, give: paid.append(give))
    assert b.mine['node'] == 'node' and b.mine['state'] == 'to node'     # its first frame: found the node, off to it
    for frame in range(2, 900):
        mining.mine_due(s, frame, lambda owner, give: paid.append(give))
    assert sum(paid[:simmine.MINE_DOCK]) == 250             # one retail load, unloaded
    trip = b.find(interfaces.OreMiner).trip()
    assert trip is b.mine and trip['node'] == 'node' and trip['ref'] == 'ref'


def test_a_move_drops_the_trip_and_neither_a_thing_without_the_module_nor_the_neutral_sides_miner_mines():
    s = simsmall.small_world([('ref', 'AlliedRefinery', 'Player_1', 0.0, 0.0),
                              ('node', 'OreNode', 'PlyrCivilian', 300.0, 0.0),
                              ('miner', 'AlliedMiner', 'Player_1', 150.0, 60.0),
                              ('tank', 'AlliedAntiVehicleVehicleTech1', 'Player_1', 150.0, -60.0),
                              ('civ', 'AlliedMiner', 'PlyrCivilian', 150.0, -120.0)])
    b, tank, civ = s.bodies['miner'], s.bodies['tank'], s.bodies['civ']
    mining = simmine.Mining()
    for frame in range(1, 30):
        mining.mine_due(s, frame, lambda owner, give: None)
    assert b.mine is not None and b.mine['state'] == 'to node'
    assert tank.mine is None and tank.find(interfaces.OreMiner) is None
    assert civ.mine is None and civ.find(interfaces.OreMiner) is not None
    b.path = [(150.0, 200.0)]                               # a script's move
    mining.mine_due(s, 30, lambda owner, give: None)
    assert b.find(interfaces.OreMiner).trip() is None and b.mine is None
