"""The ToppleUpdate module (engine/modules/topple.py, step M2): its data read from the block with the SDK defaults, the
fall worked as the reference source has it, a knock or a kill makes it gone its fall plus its SlowDeath delay later --
deleted in the expire cell, never dying -- and its fields in the frame record where the body's were. On the bench:
benches/body_death/state/checks.py#engine_topple, engine_propbody (tests/test_simbench_c.py)."""
from test_plans import small  # noqa: F401,I001  (tests/ is on the path by its conftest; puts experimental/cnv on it)
import simrecord  # noqa: E402
import engine.testing.small as simsmall  # noqa: E402
from engine.kernel import interfaces  # noqa: E402
from engine.modules import topple  # noqa: E402

LAMP = '''<GameObject id="CNV_TestLamp" Side="Neutral" KindOf="IMMOBILE">
  <Behaviors>
    <ToppleUpdate id="ModuleTag_Topple" KillWhenToppled="true" />
    <SlowDeath id="ModuleTag_Burnt" DeathTypes="BURNED" DestructionDelay="5s" />
    <SlowDeath id="ModuleTag_Death" DestructionDelay="2s" />
  </Behaviors>
</GameObject>'''
STUMP = '<GameObject id="CNV_TestStump" Side="Neutral" KindOf="IMMOBILE"><Behaviors /></GameObject>'


def test_the_block_is_read_with_the_sdk_defaults():
    d = topple.ToppleData.parse('', '')
    assert (d.start, d.finish, d.velocity, d.accel, d.bounce, d.minimum) == (False, False, 0.2, 0.01, 0.2, 0.5)
    d = topple.ToppleData.parse(' KillWhenStartToppled="true" InitialVelocityPercent="50%" MinimumToppleSpeed="2"', '')
    assert d.start and not d.finish and d.velocity == 0.5 and d.minimum == 2.0


def test_the_fall_starts_at_once_when_it_kills_on_start_and_never_comes_without_a_force():
    assert topple.fall_frames(1.0, topple.ToppleData(start=True)) == 0
    assert topple.fall_frames(0.0, topple.ToppleData(velocity=0.0, accel=0.0, minimum=0.0)) is None
    slow, fast = topple.fall_frames(0.5, topple.ToppleData()), topple.fall_frames(5.0, topple.ToppleData())
    assert slow is not None and fast is not None and fast < slow


def _world():
    s = simsmall.small_world()
    s.own.update({'CNV_TestLamp': LAMP, 'CNV_TestStump': STUMP})
    return s


def test_a_knocked_lamp_is_deleted_its_fall_plus_its_delay_later_in_the_expire_cell():
    s = _world()
    s.add('lamp', 'CNV_TestLamp', 'Player_1', 100.0, 100.0)
    lamp = s.bodies['lamp']
    m = lamp.find(interfaces.Topple)
    assert isinstance(m, topple.Topple) and lamp.topple['delay'] == 30 and m.delay == 30 and lamp.lies == 2.0
    assert lamp in s.topples and lamp.vision == 0.0 and not lamp.toppled and lamp.topple_end is None
    fall = topple.fall_frames(2.0, m.data)
    s.world.schedule.run('expire', 5)               # standing: it sleeps until a knock wakes it
    assert s.world.schedule.awake('expire') == {}
    m.knock(10, 2.0)
    assert lamp.toppled and lamp.topple_end == 10 + fall + 30
    assert simrecord.body_state(lamp)['topple_end'] == lamp.topple_end
    for f in range(10, lamp.topple_end):
        s.world.schedule.run('expire', f)
    assert lamp.alive
    s.world.schedule.run('expire', lamp.topple_end)
    assert not lamp.alive and lamp.deleted


def test_a_killed_lamp_falls_where_it_stands_once_and_a_body_without_the_module_reads_the_old_defaults():
    s = _world()
    s.add('lamp', 'CNV_TestLamp', 'Player_1', 100.0, 100.0)
    s.add('stump', 'CNV_TestStump', 'Player_1', 200.0, 100.0)
    lamp, stump = s.bodies['lamp'], s.bodies['stump']
    m = lamp.find(interfaces.Topple)
    m.fall_where_it_stands(20)
    m.fall_where_it_stands(25)
    assert lamp.toppled and lamp.topple_end == 50
    state = simrecord.body_state(stump)
    assert (state['topple'], state['toppled'], state['topple_end']) == (None, False, None)
    assert stump.find(interfaces.Topple) is None and stump not in s.topples
