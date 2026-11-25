"""The LifetimeUpdate module (engine/modules/lifetime.py, step M1): its data read from the block as the bench says
(engine_life: a 30 s wall 450 frames, a 5.5 s core 82), the thing killed in the expire cell at its die frame with what
its death leaves, read only from a mission's own template, set late from outside (the skirmish AI), and its die frame
in the frame record where the body's field was. On the bench: benches/body_death/state/checks.py#engine_life."""
from test_plans import small  # noqa: F401,I001  (tests/ is on the path by its conftest; puts experimental/cnv on it)
import engine.objects.body as simbody  # noqa: E402
import simrecord  # noqa: E402
import engine.testing.small as simsmall  # noqa: E402
import engine.data.units as simunits  # noqa: E402
from engine.kernel import interfaces  # noqa: E402
from engine.modules import lifetime  # noqa: E402

CORE = '''<GameObject id="CNV_TestCore" Side="Neutral" KindOf="IMMOBILE">
  <Behaviors>
    <LifetimeUpdate id="ModuleTag_Life" MinLifetime="1s" MaxLifetime="1s" DeathType="FADED" />
    <CreateObjectDie id="ModuleTag_Wall" CreationList="OCL_CNV_TestWall"><DieMuxData DeathTypes="FADED" /></CreateObjectDie>
  </Behaviors>
</GameObject>
<ObjectCreationList id="OCL_CNV_TestWall"><CreateObject><CreateObject>CNV_TestWall</CreateObject></CreateObject></ObjectCreationList>'''
WALL = '<GameObject id="CNV_TestWall" Side="Neutral" KindOf="IMMOBILE"><Behaviors /></GameObject>'
HEIR = '<GameObject id="CNV_TestHeir" inheritFrom="CNV_TestCore" Side="Neutral" KindOf="IMMOBILE"><Behaviors /></GameObject>'


def test_the_block_is_read_as_the_bench_says_seconds_x_15_cut_down_min_and_max_apart_their_middle():
    assert lifetime.LifetimeData.parse(' MinLifetime="30s" MaxLifetime="30s"', '').frames == 450
    assert lifetime.LifetimeData.parse(' MinLifetime="5.5s" MaxLifetime="5.5s"', '').frames == 82
    d = lifetime.LifetimeData.parse(' MinLifetime="2s" MaxLifetime="4s" DeathType="FADED"', '')
    assert d.frames == 45 and d.death == 'FADED'
    assert lifetime.LifetimeData.parse('', '').death == 'NORMAL'


def _world():
    s = simsmall.small_world()
    s.own.update({'CNV_TestCore': CORE, 'CNV_TestWall': WALL, 'CNV_TestHeir': HEIR})
    return s


def test_a_core_dies_15_frames_after_it_was_made_and_leaves_its_wall_that_frame():
    s = _world()
    s.add('core', 'CNV_TestCore', 'Player_1', 100.0, 100.0)
    core = s.bodies['core']
    m = core.find(interfaces.Lifetime)
    assert isinstance(m, lifetime.Lifetime) and m.data.frames == 15
    made = m.life_end - 15
    assert core.life_end == made + 15 and simrecord.body_state(core)['life_end'] == made + 15
    for f in range(made, made + 15):
        s.world.schedule.run('expire', f)
    assert core.alive and 'lifetime' not in s.used
    s.world.schedule.run('expire', made + 15)
    assert not core.alive and 'lifetime' in s.used
    (wall,) = [b for b in s.bodies.values() if b.template == 'CNV_TestWall']
    assert wall.alive and wall.name.startswith('#left ') and wall.life_end is None


def test_only_the_missions_own_block_of_the_template_is_read_not_an_inherited_one():
    s = _world()
    assert simunits.module_blocks('CNV_TestHeir', 'LifetimeUpdate', s.own) == []
    s.add('heir', 'CNV_TestHeir', 'Player_1', 100.0, 100.0)
    assert s.bodies['heir'].find(interfaces.Lifetime) is None and s.bodies['heir'].life_end is None


def test_a_lifetime_set_late_attaches_the_module_and_kills_at_that_frame_a_dead_things_does_nothing():
    s = _world()
    s.add('w', 'CNV_TestWall', 'Player_1', 0.0, 0.0)
    w = s.bodies['w']
    assert w.find(interfaces.Lifetime) is None          # its Body module only (step B2b)
    s.world.frame = 10
    simbody.last_until(s, w, 40)
    assert w.life_end == 40 and isinstance(w.find(interfaces.Lifetime), lifetime.Lifetime)
    s.world.schedule.run('expire', 10)
    s.world.schedule.run('expire', 39)
    assert w.alive
    s.world.schedule.run('expire', 40)
    assert not w.alive
    s.add('core', 'CNV_TestCore', 'Player_1', 100.0, 100.0)
    core = s.bodies['core']
    s.world.kill(core, 'test')
    s.world.schedule.run('expire', core.life_end)
    assert [b for b in s.bodies.values() if b.template == 'CNV_TestWall'] == [w]     # no wall: it died otherwise
