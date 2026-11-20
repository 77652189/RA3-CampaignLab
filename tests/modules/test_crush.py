"""The CrusherInfo module (engine/modules/crush.py, step M3): its levels read from the block, each inherited one by one
up the chain (the template data port reads CrusherInfo merged), the body's crusher / crushable forwarded from it with
the old defaults when it has none, and in the frame record where the body's fields were. On the bench:
checks/engine_crush.py (tests/test_simbench.py), engine_dynamics (tests/test_simbench_c.py)."""
from test_plans import small  # noqa: F401,I001  (tests/ is on the path by its conftest; puts experimental/cnv on it)
import simrecord  # noqa: E402
import engine.testing.small as simsmall  # noqa: E402
import engine.data.units as simunits  # noqa: E402
from engine.kernel import interfaces  # noqa: E402
from engine.modules import crush  # noqa: E402

BASE = '''<GameObject id="CNV_TestCrushBase" Side="Neutral" KindOf="VEHICLE">
  <CrusherInfo CrusherLevel="10" CrushableLevel="20" />
  <Behaviors />
</GameObject>'''
TANK = '''<GameObject id="CNV_TestCrushTank" inheritFrom="CNV_TestCrushBase" Side="Neutral" KindOf="VEHICLE">
  <CrusherInfo CrusherLevel="30" />
  <Behaviors />
</GameObject>'''
EMPTY = '''<GameObject id="CNV_TestCrushEmpty" inheritFrom="CNV_TestCrushBase" Side="Neutral" KindOf="VEHICLE">
  <!-- <CrusherInfo CrusherLevel="99" /> -->
  <CrusherInfo />
  <Behaviors />
</GameObject>'''
STUMP = '<GameObject id="CNV_TestCrushStump" Side="Neutral" KindOf="IMMOBILE"><Behaviors /></GameObject>'
OWN = {'CNV_TestCrushBase': BASE, 'CNV_TestCrushTank': TANK, 'CNV_TestCrushEmpty': EMPTY,
       'CNV_TestCrushStump': STUMP}


def test_the_block_is_read_and_a_missing_level_has_its_default():
    d = crush.CrushData.parse(' CrusherLevel="20" CrushableLevel="10"', '')
    assert (d.crusher, d.crushable) == (20, 10)
    d = crush.CrushData.parse('', '')
    assert (d.crusher, d.crushable) == (0, None)


def test_each_level_is_the_nearest_templates_that_writes_it():
    def levels(t):
        blocks = simunits.module_blocks(t, 'CrusherInfo', OWN)
        return None if not blocks else (crush.CrushData.parse(*blocks[0]).crusher,
                                        crush.CrushData.parse(*blocks[0]).crushable)
    assert levels('CNV_TestCrushTank') == (30, 20)          # its own crusher level, its base's crushable one
    assert levels('CNV_TestCrushEmpty') == (10, 20)         # an empty block (a comment is no level): both its base's
    assert levels('CNV_TestCrushStump') is None             # none up the chain: no module


def test_the_body_reads_its_levels_from_the_module_and_the_old_defaults_without_one():
    s = simsmall.small_world()
    s.own.update(OWN)
    s.add('tank', 'CNV_TestCrushTank', 'Player_1', 100.0, 100.0)
    s.add('stump', 'CNV_TestCrushStump', 'Player_1', 200.0, 100.0)
    tank, stump = s.bodies['tank'], s.bodies['stump']
    assert isinstance(tank.find(interfaces.Crush), crush.Crush)
    assert (tank.crusher, tank.crushable) == (30, 20)
    assert stump.find(interfaces.Crush) is None and (stump.crusher, stump.crushable) == (0, None)
    state = simrecord.body_state(tank)
    assert (state['crusher'], state['crushable']) == (30, 20)
    state = simrecord.body_state(stump)
    assert (state['crusher'], state['crushable']) == (0, None)
