"""The SecondaryDamageTracker module (engine/modules/freeze.py, step M11): its data read from the block (UpdateDuration
seconds, DissipateAmount, MaxDamageClampScaler -- a $ define read as 200 %, nothing as 125 % -- and the EffectInfo
steps lowest first), a hit's cold added as it comes, a tick's melting DissipateAmount / UpdateDuration a second kept
within 0 .. cap x max health, the step the highest Fraction of max health reached (melt says when it moved), and its
state in the frame record where the body's cold / cold_step were. The beam on a Hammer: tests/test_sim.py
(test_a_cryo_beam_slows_by_steps_then_freezes...)."""
from test_plans import small  # noqa: F401,I001  (tests/ is on the path by its conftest; puts experimental/cnv on it)
import simrecord  # noqa: E402
import engine.testing.small as simsmall  # noqa: E402
import engine.data.units as simunits  # noqa: E402
from engine.kernel import interfaces, module, world as kernel_world  # noqa: E402
from engine.modules import freeze  # noqa: E402

HEAD = ' id="ModuleTag_Cold" UpdateDuration="2s" DissipateAmount="50" MaxDamageClampScaler="=$MAX_SECONDARY_DAMAGE_SCALER"'
INNER = '''
      <EffectInfo Fraction="1.0" AttributeModifier="Frozen" OnEnterDisable="true" SetUpgradedArmor="true" />
      <EffectInfo Fraction="0.2" AttributeModifier="Slow20" />
      <EffectInfo Fraction="3.0" Options="DIE_ON_ENTER" />'''
TANK = f'''<GameObject id="CNV_TestColdTank" KindOf="VEHICLE">
  <Behaviors>
    <SecondaryDamageTracker{HEAD}>{INNER}
    </SecondaryDamageTracker>
  </Behaviors>
</GameObject>'''
WARM = '<GameObject id="CNV_TestColdWarm" KindOf="VEHICLE">\n</GameObject>'


def test_the_block_is_read_steps_lowest_first_a_define_cap_200_percent():
    d = freeze.FreezeData.parse(HEAD, INNER)
    assert d.tracker == dict(every=2.0, melt=50.0, cap=2.0, steps=[[0.2, 'Slow20', False, False, False],
                                                                   [1.0, 'Frozen', True, True, False],
                                                                   [3.0, None, False, False, True]])
    d = freeze.FreezeData.parse(' MaxDamageClampScaler="150%"', '')
    assert d.tracker == dict(every=1.0, melt=0.0, cap=1.5, steps=[])
    assert freeze.FreezeData.parse('', '').tracker['cap'] == 1.25


class Tank(module.Thing):
    name, template, alive, max_hp = 'tank', 'CNV_TestColdTank', True, 1000.0


def _tank():
    w = kernel_world.World(lambda t, tag: [(HEAD, INNER)] if tag == 'SecondaryDamageTracker' else [])
    thing = Tank()
    thing.modules = w.build(thing, 1)
    return thing.find(interfaces.Freeze)


def test_cold_melts_dissipate_over_the_update_duration_and_the_step_follows_the_fraction():
    m = _tank()
    assert (m.held(), m.stage()) == (0.0, -1)
    m.add(300.0)
    assert (m.held(), m.stage()) == (300.0, -1)       # added, not yet stepped: the tick's melt steps it
    assert m.melt(1.0) is True and (m.held(), m.stage()) == (275.0, 0)      # 50 / 2 s = 25 a second
    assert m.melt(1.0) is False and (m.held(), m.stage()) == (250.0, 0)
    m.add(800.0)
    assert m.melt(0.5) is True and (m.held(), m.stage()) == (1037.5, 1)     # 1000 = 1.0 x max health: frozen


def test_cold_stays_within_zero_and_the_cap_times_max_health():
    m = _tank()
    m.add(5000.0)
    assert m.melt(0.0) is True and (m.held(), m.stage()) == (2000.0, 1)     # 200 % of 1000; 3.0 never reached
    assert m.melt(1000.0) is True and (m.held(), m.stage()) == (0.0, -1)
    m.add(225.0)
    assert m.melt(1.0) is True and (m.held(), m.stage()) == (200.0, 0)       # 0.2 x 1000 reached exactly: the step


def test_the_record_keeps_cold_and_cold_step_where_the_body_had_them():
    s = simsmall.small_world()
    s.own.update({'CNV_TestColdTank': TANK, 'CNV_TestColdWarm': WARM})
    assert len(simunits.module_blocks('CNV_TestColdTank', 'SecondaryDamageTracker', s.own)) == 1
    s.add('tank', 'CNV_TestColdTank', 'Player_1', 100.0, 100.0)
    s.add('warm', 'CNV_TestColdWarm', 'Player_1', 300.0, 100.0)
    tank, warm = s.bodies['tank'], s.bodies['warm']
    assert warm.find(interfaces.Freeze) is None and s.cold_of(warm)[0] is None
    assert [simrecord.body_state(warm)[k] for k in ('cold', 'cold_step')] == [0.0, -1]
    assert s.cold_of(tank)[0]['melt'] == 50.0
    tank.find(interfaces.Freeze).add(400.0)
    assert [simrecord.body_state(tank)[k] for k in ('cold', 'cold_step')] == [400.0, -1] == [tank.cold, tank.cold_step]
