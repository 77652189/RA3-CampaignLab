"""The world and AI views share ordered membership across repeated calls."""
from test_plans import small  # noqa: F401,I001
import engine.ai.core as simai  # noqa: E402
import engine.testing.small as simsmall  # noqa: E402
import engine.state.snapshot as simsnap  # noqa: E402
from engine.kernel import interfaces  # noqa: E402
from engine.ports.observe import Observe  # noqa: E402


UNIT = 'AlliedAntiInfantryInfantry'
OBJECTS = [('a', UNIT, 'PlyrCivilian', 300, 300), ('b', UNIT, 'PlyrCivilian', 400, 300)]


def _assert_view(actual, *expected):
    assert isinstance(actual, list)
    assert len(actual) == len(expected)
    assert all(a is b for a, b in zip(actual, expected))


def test_living_cache_reuses_scans_and_returns_independent_lists():
    world = simsmall.small_world(OBJECTS, model=False)
    brain = simai.Brain.__new__(simai.Brain)
    brain.world = world
    a, b = world.bodies.values()
    scans = 0

    class CountedBodies(dict):
        def values(self):
            nonlocal scans
            scans += 1
            return super().values()

    world.bodies = CountedBodies(world.bodies)
    for query in (world.living, brain.living):
        query().reverse()
        query().clear()
        _assert_view(query(), a, b)
    assert scans == 1


def test_living_cache_tracks_same_frame_world_and_spawn_changes():
    world = simsmall.small_world(OBJECTS, model=False)
    brain = simai.Brain.__new__(simai.Brain)
    brain.world = world
    old_a, b = world.bodies.values()
    frame = world.frame_now()
    _assert_view(world.living(), old_a, b)
    _assert_view(brain.living(), old_a, b)

    world.world.remove(old_a, 'test')                         # (Sim.add refuses a living one's name)
    a = world.add('a', UNIT, world.human, 350, 300)
    _assert_view(world.living(), a, b)  # a reused name keeps its dict position
    world.proto(UNIT, world.human)
    _assert_view(brain.living(), a, b)
    Observe(world).specimen('specimen', UNIT, world.human)
    _assert_view(world.living(), a, b)

    house = world.add('house', 'AM_Apartments_01', world.foe, 350, 350)
    yard = world.add('factory', 'AlliedWarFactory', world.human, 600, 600)
    drones = yard.spawned_children
    assert len(drones) == 3
    _assert_view(world.living(), a, b, house, yard, *drones)
    _assert_view(brain.living(), a, b, house, yard)
    assert world.garrison.put(a, house, script=True)
    _assert_view(brain.living(), a, b, house, yard)
    assert world.garrison.out(a)
    b.owner = world.human
    _assert_view(world.living(), a, b, house, yard, *drones)
    assert [p for p in brain.living() if p.owner == world.human] == [a, b, yard]

    world.world.kill(yard, 'test')  # the same broadcast deletes its drones
    for pk in [p for p in world.living() if p.name.startswith('#left')]:  # and its Peacekeeper (CreateObjectDie.FIGHT)
        world.world.remove(pk, 'test')
    _assert_view(world.living(), a, b, house)
    world.world.remove(b, 'test')
    _assert_view(brain.living(), a, house)
    _assert_view(world.living(), a, house)
    assert world.frame_now() == frame


def test_living_cache_is_rebuilt_on_same_frame_snapshot_restore():
    source = simsmall.small_world(OBJECTS, model=False)
    target = simsmall.small_world(OBJECTS, model=False)
    a, b = target.bodies.values()
    source.world.remove(source.bodies['a'], 'test')
    saved = simsnap.snapshot(source)
    source.living()
    assert not simsnap.unclassified(source)
    assert simsnap.snapshot(source) == saved
    _assert_view(target.living(), a, b)
    simsnap.restore(target, saved)
    _assert_view(target.living(), b)
    assert simsnap.snapshot(target) == saved


def test_living_cache_invalidates_when_a_registered_body_becomes_a_slave():
    world = simsmall.small_world(OBJECTS, model=False)
    brain = simai.Brain.__new__(simai.Brain)
    brain.world = world
    a, b = world.bodies.values()
    yard = world.add('factory', 'AlliedWarFactory', world.human, 600, 600)
    spawner, = yard.find(interfaces.Spawn)

    _assert_view(brain.living(), a, b, yard)
    world.world.bind_slave(b, yard, spawner)
    _assert_view(brain.living(), a, yard)
    _assert_view(world.living(), a, b, yard, *yard.spawned_children)


def test_living_cache_invalidates_when_slaved_enslave_is_called_directly():
    """Review 1119l P3: the module's own enslave (not World.bind_slave) drops the views too."""
    world = simsmall.small_world(OBJECTS, model=False)
    brain = simai.Brain.__new__(simai.Brain)
    brain.world = world
    a, b = world.bodies.values()
    yard = world.add('factory', 'AlliedWarFactory', world.human, 600, 600)
    spawner, = yard.find(interfaces.Spawn)
    slave = world.world.attach(b, 'SlavedUpdate')
    _assert_view(brain.living(), a, b, yard)
    slave.enslave(yard, spawner)
    _assert_view(brain.living(), a, yard)
