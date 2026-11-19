"""Observe the effects of ending a thing through Sim.destroy and Sim.delete."""
import pytest
from test_plans import small  # noqa: F401,I001  (puts experimental/cnv on the path)

import simsmall  # noqa: E402
from engine.kernel import interfaces, module  # noqa: E402


class EndCalls(module.Module, interfaces.Die, interfaces.Destroy):
    def __init__(self, thing, data, world):
        super().__init__(thing, data, world)
        self.deaths = 0
        self.destroys = 0

    def on_die(self, info):
        self.deaths += 1

    def on_destroy(self):
        self.destroys += 1


def test_drone_death_queues_one_refill_and_spawner_deletion_clears_it():
    s = simsmall.small_world([('factory', 'AlliedWarFactory', 'Player_1', 300, 300)], model=False)
    factory = s.bodies['factory']
    killed, removed, survivor = factory.spawned_children  # InitialBurst="3"
    assert all(drone.alive for drone in (killed, removed, survivor))
    gap = ('SpawnBehavior', factory.template)
    initial_gaps = s.unmodeled.get(gap, {}).get('n', 0)
    assert factory.spawn_refills == []

    # SpawnReplaceDelayData="10s" at 15 logic frames per second.
    due = s.frame_now() + 10 * 15
    refill = (due, 'ModuleTag_SpawnRepairDrones', 'AlliedWarFactoryRepairDrone')
    s.destroy(killed, 'drone killed')
    assert not killed.alive and not killed.deleted
    assert factory.spawn_refills == [refill]
    assert s.unmodeled.get(gap, {}).get('n', 0) == initial_gaps

    s.delete(removed, 'drone deleted')
    assert not removed.alive and removed.deleted
    assert factory.spawn_refills == [refill]
    assert s.unmodeled[gap]['n'] == initial_gaps + 1
    assert survivor.alive

    s.delete(factory, 'spawner deleted')
    assert factory.spawn_refills == []
    assert not survivor.alive and survivor.deleted  # SpawnedRequireSpawner="true"
    assert s.unmodeled[gap]['n'] == initial_gaps + 1


@pytest.mark.parametrize('template, kill_passengers', [
    pytest.param('AM_Apartments_01', False, id='garrison'),
    pytest.param('AlliedAntiInfantryVehicle', True, id='transport'),
])
@pytest.mark.parametrize('end, deaths', [('destroy', 1), ('delete', 0)])
def test_host_end_resolves_passengers_and_tells_modules_once(template, kill_passengers, end, deaths):
    s = simsmall.small_world(model=False)
    host = s.add('host', template, None, 300, 300)
    passenger = s.add('passenger', 'AlliedAntiInfantryInfantry', 'Player_1', 400, 300)
    assert s.garrison.put(passenger, host, script=True)
    assert s.garrison.held(host) == [passenger] and 'ENCLOSED' in passenger.script_status

    s.world.tags = {**s.world.tags, 'TestEndCalls': EndCalls}
    calls = s.world.attach(host, 'TestEndCalls')
    finish = getattr(s, end)
    finish(host, 'host ended')
    finish(host, 'host already ended')

    assert (calls.deaths, calls.destroys) == (deaths, 1)
    assert s.garrison.held(host) == []
    assert 'ENCLOSED' not in passenger.script_status
    assert passenger.alive == (end == 'destroy' and not kill_passengers)
    assert passenger.deleted == (end == 'delete')
