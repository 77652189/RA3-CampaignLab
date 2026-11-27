"""The routing grid is derived from one world's current obstacles and surface."""
from types import SimpleNamespace

import pytest

from test_plans import small  # noqa: F401,I001  (puts experimental/cnv on the path)
import platmap  # noqa: E402
import sim  # noqa: E402
import engine.objects.path as simpath  # noqa: E402
import engine.testing.small as simsmall  # noqa: E402
import engine.state.snapshot as simsnap  # noqa: E402
from engine.ports.command import Command  # noqa: E402


PLANT = 'SovietPowerPlant'


def map_ground(base=1, objects=()):
    return sim.Ground(SimpleNamespace(DIMS=(32, 32, 0), LAYOUT=platmap.Layout([], base=base), OBJECTS=objects))


def grid(ground, surface='ground'):
    return simpath.route_grid(ground, surface)


def at(ground, x=1240, y=2360):
    return ground.cell(x, y)


def place(world, p, template=PLANT):
    ok, why = world.commands.do(Command('place', by='ai:Player_1', player='Player_1',
                                        template=template, pos=p, args=(('name', 'obstacle'),)))
    assert ok, why
    return world.bodies['obstacle']


def warm_endpoint(ground):
    c = at(ground)
    old = grid(ground)
    assert old.endpoint(c) == c
    return c, old, ground.version


def assert_endpoint_blocked(ground, c, old, version):
    assert ground.version == version + 1
    assert not ground.cache
    current = grid(ground)
    assert current is not old
    assert not current.cells[c] and current.endpoint(c) != c


def test_path_cache_reuses_grid_and_endpoints_including_none(monkeypatch):
    ground = map_ground()
    p, q = (80, 80), (182, 160)
    calls = []
    original = simpath.open_cell

    def count(mask, cell):
        calls.append(cell)
        return original(mask, cell)

    monkeypatch.setattr(simpath, 'open_cell', count)
    walk = grid(ground)
    assert ground.route('ground', p, q) == [q]
    assert ground.route('ground', p, (181, 160)) == [(181, 160)]  # same cell, actual goal preserved
    assert ground.within('ground', p, q, 20)
    assert grid(ground) is walk
    assert ground.route('water', p, q) is None
    assert ground.route('water', p, q) is None
    assert grid(ground, 'water') is not walk
    assert calls == [ground.cell(*p), ground.cell(*q)] * 2


@pytest.mark.parametrize('wall', [False, True], ids=['structure', 'wall'])
def test_path_cache_invalidates_on_placement(wall):
    world = simsmall.small_world(model=False)
    ground = world.ground
    if wall:
        world.walls[PLANT] = {'shape': 'bar', 'length': 160, 'thick': 20}
    c, old, version = warm_endpoint(ground)
    place(world, ground.world(c))
    assert_endpoint_blocked(ground, c, old, version)


@pytest.mark.parametrize('source', ['named', 'unnamed', 'reinforcement', 'legacy'])
def test_path_cache_invalidates_on_script_creation(source):
    world = simsmall.small_world(model=False)
    ground = world.ground
    c, old, version = warm_endpoint(ground)
    world.waypoints['site'] = ground.world(c)
    script = SimpleNamespace(name='test')
    team = 'Player_1/teamPlayer_1'
    if source == 'named':
        world.act('CREATE_NAMED_ON_TEAM_AT_WAYPOINT', ['plant', PLANT, team, 'site'], script)
    elif source == 'unnamed':
        world.act('CREATE_UNNAMED_ON_TEAM_AT_WAYPOINT', [PLANT, team, 'site'], script)
    elif source == 'reinforcement':
        world.templates[team] = {'units': [(PLANT, 1, 1)]}
        world.reinforce(team, 'site', script)
    else:
        world.happen((0.0, '造', PLANT, 'site', 0.0))
    assert_endpoint_blocked(ground, c, old, version)


def test_path_cache_invalidates_when_the_builder_sets_down_the_structure():
    world = simsmall.small_world(model=False)
    ground = world.ground
    c, old, version = warm_endpoint(ground)
    x, y = ground.world(c)
    builder = world.add('builder', 'AlliedAntiInfantryInfantry', 'Player_1', x, y)
    builder.building = (PLANT, (x, y), 0)
    assert world.production.at_site(builder, 0)
    world.production.put_down(world.production.placing[0][0])
    assert_endpoint_blocked(ground, c, old, version)


def test_path_cache_invalidates_when_an_expiring_object_leaves_a_wall():
    world = simsmall.small_world(model=False)
    ground = world.ground
    c, old, version = warm_endpoint(ground)
    world.own['CNV_PathCacheCore'] = f'''
<GameObject id="CNV_PathCacheCore" Side="Neutral" KindOf="IMMOBILE"><Behaviors>
  <LifetimeUpdate id="Life" MinLifetime="1s" MaxLifetime="1s" DeathType="FADED" />
  <CreateObjectDie id="Leave" CreationList="OCL_PathCacheWall" />
</Behaviors></GameObject>
<ObjectCreationList id="OCL_PathCacheWall">
  <CreateObject><CreateObject>{PLANT}</CreateObject></CreateObject>
</ObjectCreationList>
'''
    world.walls[PLANT] = {'shape': 'bar', 'length': 160, 'thick': 20}
    core = world.add('core', 'CNV_PathCacheCore', 'Player_1', *ground.world(c))
    world.world.schedule.run('expire', core.life_end)
    assert not core.alive
    assert_endpoint_blocked(ground, c, old, version)


@pytest.mark.parametrize('action', ['destroy', 'sell', 'garrison'])
def test_path_cache_invalidates_when_a_structure_goes(action):
    world = simsmall.small_world(model=False)
    ground = world.ground
    c = at(ground)
    template = 'SovietBunker' if action == 'garrison' else PLANT
    obstacle = place(world, ground.world(c), template)
    old, version = grid(ground), ground.version
    assert old.endpoint(c) != c
    if action == 'sell':
        world.clock.frame = max(world.frame_now(), obstacle.unpack_end or 0)
        world._life().sell(world, obstacle, world.garrison, world.world.modify, world.wallet.credit)
        assert obstacle.alive and obstacle.sell_end is not None
        assert ground.version == version and grid(ground) is old
        world.world.schedule.run('expire', obstacle.sell_end)
    else:
        if action == 'garrison':
            gi = world.add('gi', 'AlliedAntiInfantryInfantry', 'Player_1', *ground.world(at(ground, 1460)))
            assert world.garrison.put(gi, obstacle, script=True)
            assert ground.version == version and grid(ground) is old
            assert world.garrison.out(gi)
            assert ground.version == version and grid(ground) is old
            assert world.garrison.put(gi, obstacle, script=True)
        world.world.kill(obstacle, 'test')
    assert ground.version == version + 1
    assert not ground.cache
    assert grid(ground) is not old and grid(ground).endpoint(c) == c


def test_path_cache_invalidates_when_fence_moves_only_on_fine_grid():
    ground = map_ground()
    p, q = (40, 160), (280, 160)
    assert ground.set_blocks([], foot=[(151, 151, 40)])
    coarse = ground.foot.copy()
    assert ground.route('foot', p, q) is not None
    old, version = ground.sight('foot'), ground.version

    assert ground.set_blocks([], foot=[(152, 151, 40)])
    assert (ground.foot == coarse).all()
    assert ground.version == version + 1 and not ground.cache
    moved = ground.sight('foot')
    assert sum(a != b for a, b in zip(old.flat, moved.flat)) == 3
    assert not ground.set_blocks([], foot=[(152, 151, 40)])
    assert ground.sight('foot') is moved


def test_path_cache_bridge_is_map_terrain_and_deck_ignores_obstacles():
    p, q = (80, 160), (220, 160)
    bridge = tuple(SimpleNamespace(x=x, y=y, angle=0, template='HB_Bridge_02', flags=flag)
                   for (x, y), flag in zip((p, q), (platmap.BRIDGE_START, platmap.BRIDGE_END)))
    sea, deck = map_ground(0), map_ground(0, bridge)
    assert sea.route('ground', p, q) is None
    assert not deck.cache
    assert deck.route('ground', p, q) == [q]
    old = grid(deck)
    assert not deck.set_blocks([(160, 160, 10)])  # entirely on the deck
    assert deck.version == 0 and grid(deck) is old
    assert deck.route('ground', p, q) == [q]


def test_path_cache_terrain_and_new_sim_have_their_own_empty_cache():
    sea, land = map_ground(0), map_ground()
    p, q = (80, 80), (180, 160)
    assert sea.route('ground', p, q) is None
    assert not land.cache and land.version == sea.version
    assert land.route('ground', p, q) == [q]

    first = simsmall.small_world(model=False).ground
    assert grid(first).endpoint(at(first)) == at(first)
    second = simsmall.small_world(model=False).ground
    assert not second.cache and second.version == first.version
    assert grid(second) is not grid(first)


def test_path_cache_restore_discards_warm_grid_even_at_same_version():
    source = simsmall.small_world(model=False)
    target = simsmall.small_world(model=False)
    ground = target.ground
    c = at(ground)
    assert source.ground.set_blocks([(*ground.world(c), 20)])
    assert ground.set_blocks([(*ground.world(at(ground, 1460)), 20)])
    assert source.ground.version == ground.version == 1
    assert grid(source.ground).endpoint(c) != c
    assert grid(ground).endpoint(c) == c

    simsnap.restore(target, simsnap.snapshot(source))
    assert not ground.cache
    assert ground.version == 1 and grid(ground).endpoint(c) != c
