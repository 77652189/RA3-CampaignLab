"""The ports hand out no container of the world to write (review 1119z P2 #2 + y P3 #5; engine/ports/readonly.py):
a reader of the observation port or a plug-in reading the AI port's Settings / PlayerSystems gets live read-only views,
so `systems.queues.clear()` and the like raise instead of changing the run past the command port."""
import inspect

import pytest

from test_plans import small  # noqa: F401,I001  (tests/ is on the path by its conftest; puts experimental/cnv on it)
import simsmall  # noqa: E402
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


def _members(port):
    """(name, value) of each public member readable with no argument or with a player only."""
    for name in dir(type(port)):
        if name.startswith('_'):
            continue
        raw = inspect.getattr_static(type(port), name)
        if isinstance(raw, property):
            yield name, lambda: getattr(port, name)
            continue
        f = getattr(port, name)
        if not callable(f) or name.startswith('on_') or name in ('specimen', 'fresh_sight', 'take_personality',
                                                                 'add_team_lookup', 'charge', 'multiply_income'):
            continue
        params = [p for p in inspect.signature(f).parameters.values() if p.default is p.empty]
        if not params:
            yield name, f
        elif [p.name for p in params] == ['player']:
            yield name, lambda f=f: f('Player_1')


def _containers(v, out, depth=0):
    """Every list / dict / set (and deque) reachable through v's containers and views (not into other objects)."""
    if depth > 5:
        return
    if isinstance(v, (list, dict, set)):
        out.append(v)
    if isinstance(v, (MapView, dict)):
        for k in v:
            _containers(v[k], out, depth + 1)
    elif isinstance(v, (SeqView, SetView, list, tuple, set)):
        for x in v:
            _containers(x, out, depth + 1)


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
        a, b = [], []
        _containers(read(), a)
        _containers(read(), b)
        if {id(x) for x in a} & {id(x) for x in b}:
            shared.append(name)
    assert shared == []


def test_the_guard_finds_a_planted_door(world):
    class Leaky(ai_port.PlayerSystems):
        __slots__ = ()

        def jobs(self):
            return self._w.queues
    names = []
    for name, read in _members(Leaky(world)):
        a, b = [], []
        _containers(read(), a)
        _containers(read(), b)
        if {id(x) for x in a} & {id(x) for x in b}:
            names.append(name)
    assert names == ['jobs']


def test_the_review_repro_raises(world):
    systems, settings, obs = ai_port.PlayerSystems(world), ai_port.Settings(world), Observe(world)
    serial = world.bodies['barracks'].serial
    assert systems.queues[serial][0]['template'] == GI          # read as before
    for write in (lambda: systems.queues.clear(), lambda: systems.queues[serial].append({}),
                  lambda: systems.queues[serial][0].update(progress=100), lambda: settings.ai_paused.add('x'),
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
