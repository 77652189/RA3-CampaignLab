"""The AutoHealBehavior module (engine/modules/autoheal.py, step K1): its data read from the block, one module a
block on the things whose template has one, the gated blocks asleep, a thing taken out of the world off the schedule,
and its state in the frame record where the body's fields were. The healing itself: tests/test_simheal.py."""
from test_plans import small  # noqa: F401,I001  (tests/ is on the path by its conftest; puts experimental/cnv on it)
import simrecord  # noqa: E402
import simsmall  # noqa: E402
from engine.kernel import interfaces  # noqa: E402
from engine.modules import autoheal  # noqa: E402

APOC = 'SovietAntiVehicleVehicleTech3'        # AutoHealBehavior: 2 points every 7 frames, 15 frames after a hurt
GUARDIAN = 'AlliedAntiVehicleVehicleTech1'    # one AutoHealBehavior, gated (not modelled)
PLANT = 'AlliedPowerPlant'                    # none


def test_the_apocalypse_reads_2_points_every_7_frames_15_after_a_hurt_the_guardians_is_gated_a_plant_has_none():
    s = simsmall.small_world([('a', APOC, 'Player_1', 0.0, 0.0), ('g', GUARDIAN, 'Player_1', 300.0, 0.0),
                              ('p', PLANT, 'Player_1', 600.0, 0.0)])
    a, g, p = s.bodies['a'], s.bodies['g'], s.bodies['p']
    (m,) = a.find(interfaces.Update)
    assert isinstance(m, autoheal.AutoHeal) and m.data.rule == (2, 7, 15) and m.thing is a and m.world is s.world
    assert [x.data.rule for x in g.modules] == [None]
    assert p.modules == () and 'modules' not in vars(p)


def test_a_gated_block_is_not_modelled_and_its_module_sleeps():
    for head in (' InitiallyActive="false" HealingAmount="5"', ' ObjectStatusValidation="x" HealingAmount="5"',
                 ' Radius="50" HealingAmount="5"'):
        assert autoheal.AutoHealData.parse(head, '').rule is None
    assert autoheal.AutoHealData.parse(' HealingAmount="5"', '<ObjectStatusValidation />').rule is None
    assert autoheal.AutoHealData.parse(' HealingAmount="5" HealingDelay="0.5s"', '').rule == (5, 7, 0)
    s = simsmall.small_world([('a', APOC, 'Player_1', 0.0, 0.0)])
    (m,) = s.bodies['a'].modules
    gated = autoheal.AutoHeal(s.bodies['a'], autoheal.AutoHealData.parse(' InitiallyActive="false"', ''), s.world)
    s.bodies['a'].damage(10)                           # the live one, hurt, waits 15 frames (at full it sleeps too)
    assert gated.update(1) is interfaces.SLEEP and m.update(1) == 15


def test_a_thing_taken_out_of_the_world_leaves_the_schedule():
    s = simsmall.small_world([('a', APOC, 'Player_1', 0.0, 0.0)])
    proto = s.proto('p', APOC, 'Player_1')             # the AI's figures body: made, then out of the registry
    assert 'p' not in s.bodies and proto.modules
    assert set(s.world.schedule.cells['autoheal']) == set(s.bodies['a'].modules)
    s.add('a', APOC, 'Player_1', 10.0, 0.0)            # a new body under the name: the old one leaves
    assert set(s.world.schedule.cells['autoheal']) == set(s.bodies['a'].modules)


def test_the_record_shows_the_modules_state_among_the_bodys_fields():
    s = simsmall.small_world([('a', APOC, 'Player_1', 0.0, 0.0)])
    b = s.bodies['a']
    assert 'heal_at' not in simrecord.body_state(b) and 'modules' not in simrecord.body_state(b)
    s.world.schedule.run('autoheal', 0)
    b.damage(10)
    s.world.schedule.run('autoheal', 1)
    d = simrecord.body_state(b)
    assert d['heal_at'] == 16 and d['hurt'] is False and d['hp'] == b.hp
