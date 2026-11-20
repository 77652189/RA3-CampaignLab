"""The ports hand out no container of the world to write (review 1119z P2 #2 + y P3 #5; engine/ports/readonly.py):
a reader of the observation port or a plug-in reading the AI port's Settings / PlayerSystems gets live read-only views,
so `production.jobs(f).clear()` and the like raise instead of changing the run past the command port."""
import inspect

import pytest

from test_plans import small  # noqa: F401,I001  (tests/ is on the path by its conftest; puts experimental/cnv on it)
import engine.testing.small as simsmall  # noqa: E402
from engine.ports import ai as ai_port  # noqa: E402
from engine.ports.observe import Observe  # noqa: E402
from engine.ports.readonly import MapView, SeqView, SetView, view  # noqa: E402

BARRACKS, GI = 'AlliedBarracks', 'AlliedAntiInfantryInfantry'


@pytest.fixture(scope='module')
def world():
    s = simsmall.small_world([('yard', 'AlliedConstructionYard', 'Player_1', 0.0, 0.0),
                              ('barracks', BARRACKS, 'Player_1', 300.0, 0.0)], model=False)
    s.money['Player_1'] = 10000
    s.order_build('Player_1', GI, s.bodies['barracks'])
    s.advance(5)
    s.ai['Player_2'] = 0.0
    s.ai_switches['Player_2'] = {'x': 1}
    s.ai_priorities['Player_2'] = [('Player_1', 3)]
    s.ai_paused.add('Player_2')
    s.firing.append((s.bodies['yard'], 1.0, s.bodies['barracks']))
    return s


# Every reader is called, each argument by its name (review 1120bb P2 #2: `state(thing)` and `ground_map()` were
# outside the guard, which called only those of no argument or a player's). A reader with an argument named
# otherwise fails the guard (KeyError) until it is added here; the doors (members that write) are left out.
_DOORS = ('specimen', 'fresh_sight', 'take_personality', 'add_team_lookup', 'charge', 'multiply_income', 'proto')


def _arg(world, name):
    yard, barracks = world.bodies['yard'], world.bodies['barracks']
    return {'player': 'Player_1', 'side': 'Player_1', 'a': 'Player_1', 'b': 'Player_2', 'thing': barracks,
            'viewer': yard, 'body': yard, 'factory': barracks,
            'target': barracks, 'x': 0.0, 'y': 0.0, 'n': 0, 't': 0.0, 'key': 'x',
            'name': 'barracks', 'template': GI, 'upgrade': 'x', 'behind': 1.0, 'ahead': 1.0, 'v': yard,
            'job': {'cost': 0, 'paid': 0}, 'progress': 0.0}[name]


def _members(port):
    """(name, read) of each public member: a property read, a method called with a sample for each argument it has
    no default for (_arg)."""
    w = port._w
    for name in dir(type(port)):
        if name.startswith('_'):
            continue
        raw = inspect.getattr_static(type(port), name)
        if isinstance(raw, property):
            yield name, lambda name=name: getattr(port, name)
            continue
        f = getattr(port, name)
        if not callable(f) or name.startswith('on_') or name in _DOORS:
            continue
        params = [p.name for p in inspect.signature(f).parameters.values() if p.default is p.empty]
        if name == 'report':
            args = ['log']
        elif name == 'can_hit':
            args = [{'type': 'SMALL_ARMS', 'anti': None}, w.bodies['barracks']]     # a weapon as a thing holds it
        else:
            args = [_arg(w, p) for p in params]
        yield name, lambda f=f, args=args: f(*args)


def _containers(v, out, depth=0):
    """Every list / dict / set (and deque) reachable through v's containers and views (not into other objects), and
    every array a reader could write (a numpy array with its write flag on: the ground's grids)."""
    if depth > 5:
        return
    if isinstance(v, (list, dict, set)) or getattr(getattr(v, 'flags', None), 'writeable', False) is True:
        out.append(v)
    if isinstance(v, (MapView, dict)):
        for k in v:
            _containers(v[k], out, depth + 1)
    elif isinstance(v, (SeqView, SetView, list, tuple, set)):
        for x in v:
            _containers(x, out, depth + 1)


def _leaks(read):
    """Whether a member hands out the world's own: two reads sharing a list / dict / set (a copy is new each time, a
    view is not a container), or an array one could write."""
    a, b = [], []
    _containers(read(), a)
    _containers(read(), b)
    return bool({id(x) for x in a} & {id(x) for x in b}) or any(not isinstance(x, (list, dict, set)) for x in a)


def _ports(s):
    return [Observe(s), ai_port.Settings(s), ai_port.PlayerSystems(s)]


@pytest.mark.parametrize('which', [0, 1, 2], ids=['Observe', 'Settings', 'PlayerSystems'])
def test_no_member_hands_out_a_live_container(world, which):
    """A member read twice whose two results share a list / dict / set is handing out the world's own (a copy is new
    each time, a view is not a container)."""
    port = _ports(world)[which]
    shared = []
    for name, read in _members(port):
        if name in ('mission', 'model', 'scripts'):     # the mission's data and the executor: objects, not tables
            continue
        if _leaks(read):
            shared.append(name)
    assert shared == []


def test_the_guard_finds_a_planted_door(world):
    class Leaky(ai_port.PlayerSystems):
        __slots__ = ()

        def jobs(self):
            return self._w.queues
    names = []
    for name, read in _members(Leaky(world)):
        if _leaks(read):
            names.append(name)
    assert names == ['jobs']


def test_the_review_repro_raises(world):
    systems, settings, obs = ai_port.PlayerSystems(world), ai_port.Settings(world), Observe(world)
    serial = world.bodies['barracks'].serial
    jobs = world.production.jobs(serial)                        # what Observe.queue / jobs read (S7b)
    assert jobs[0]['template'] == GI and systems.busy(world.bodies['barracks'])
    for write in (lambda: jobs.append({}), lambda: jobs[0].update(progress=100), lambda: settings.ai_paused.add('x'),
                  lambda: settings.ai_switches['Player_2'].pop('x'), lambda: obs.firing().clear(),
                  lambda: obs.flags().__setitem__('f', 1), lambda: obs.counters().__delitem__('c')):
        with pytest.raises((AttributeError, TypeError)):
            write()
    assert world.queues[serial] and world.ai_paused == {'Player_2'} and world.ai_switches['Player_2'] == {'x': 1}


def test_a_view_is_live_and_reads_as_its_container(world):
    obs = Observe(world)
    flags = obs.flags()
    world.flags['seen'] = 1
    assert flags['seen'] == 1 and flags == dict(world.flags) and dict(flags) == world.flags
    f = obs.firing()
    assert f == world.firing and list(f) == world.firing and len(f + obs.volleys()) == len(world.firing)
    assert obs.firing()[0] is world.firing[0]                # a tuple of things comes back itself
    assert view([(1, [2])])[0] == (1, [2]) and isinstance(view([(1, [2])])[0][1], SeqView)
    assert ai_port.Settings(world).ai_paused == {'Player_2'} and 'Player_2' in ai_port.Settings(world).ai_paused
    del world.flags['seen']


def test_a_things_state_and_the_ground_map_are_read_only():
    """Review 1120bb P2 #2: `Observe.state(u)['path'].clear()` emptied a moving unit's path, and `ground_map()[0]`
    was the routing grid itself (writeable). The state's values are views now, the grids arrays one cannot write; both
    still read as before (the frame record and SimUI's picture)."""
    from maps import probe_range
    from engine.ports.command import Command
    w = simsmall.small_world([('u', 'AlliedAntiVehicleVehicleTech1', 'Player_1', 1060, 1230)], model=False,
                             map=probe_range)
    o = Observe(w)
    u = o.thing('u')
    assert w.commands.do(Command('move', units=('u',), place='@1360,1450'))[0]
    row = o.state(u)
    assert len(u.path) == 1 and row['path'] == u.path and list(row['path']) == list(u.path)
    for write in (lambda: row['path'].clear(), lambda: row['path'].append((0, 0)), lambda: row['status'].add('x'),
                  lambda: row['armor'].__setitem__('x', 1)):
        with pytest.raises((AttributeError, TypeError)):
            write()
    assert len(u.path) == 1 and 'x' not in u.status
    walk, water, z, origin, step = o.ground_map()
    for grid in (walk, water, z):
        with pytest.raises(ValueError):
            grid[0, 0] = grid[0, 0]
    assert (walk == w.ground.grids['ground']).all()
    # review 1120dd P2: a view with the flag off could be made writeable again (its base was the routing grid)
    before = w.ground.grids['ground'].copy()
    walk.setflags(write=True)
    walk[...] = 0
    assert (w.ground.grids['ground'] == before).all() and (o.ground_map()[0] == before).all()
