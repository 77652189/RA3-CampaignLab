"""The StructureUnpackUpdate module (engine/modules/unpack.py, step M10): UnpackTime read through the port (a '=$NAME'
define from the file that supplies the block), the end set only on a structure made in the
run, read through the body's `unpack_end` forward and in the frame record where the body's field was. The power factor's
stretch and what unpacking holds back (power, fire, a sale): tests/test_simbench.py (engine_powerdef), test_sell.py."""
import pytest

from test_plans import small  # noqa: F401,I001  (tests/ is on the path by its conftest; puts experimental/cnv on it)
import simrecord  # noqa: E402
import engine.testing.small as simsmall  # noqa: E402
import engine.data.units as simunits  # noqa: E402
from engine.kernel import interfaces  # noqa: E402
from engine.modules import unpack  # noqa: E402


def test_the_block_is_read_seconds_x_15_rounded_nothing_is_none():
    assert unpack.UnpackData.parse(' UnpackTime="1.5s"', '').frames == round(22.5) == 22     # Python's rounding
    assert unpack.UnpackData.parse(' UnpackTime="10s"', '').frames == 150
    assert unpack.UnpackData.parse(' UnpackTime="0s"', '').frames == 0
    assert unpack.UnpackData.parse('', '').frames == 0


def test_a_define_is_spelled_out_in_the_file_that_supplies_the_block():
    (head, _), = simunits.module_blocks('SovietPowerPlant', 'StructureUnpackUpdate')
    assert '=$' not in head and unpack.UnpackData.parse(head, '').frames == 150      # SovietPowerPlant.xml: 10 s
    (head, _), = simunits.module_blocks('AlliedRefinery_NoHarvester', 'StructureUnpackUpdate')
    # Compiled AlliedRefinery_NoHarvester: ModuleTag_StructureUnpackUpdate UnpackTime="4s".
    assert unpack.UnpackData.parse(head, '').frames == 60

    # Compiled JapanBaseDefense_S07: ModuleTag_StructureUnpack="15s", ModuleTag_StructureUnpack_02="5s".
    template = 'JapanBaseDefense_S07'
    s = simsmall.small_world()
    first, selected = s.world.data_of(template, 'StructureUnpackUpdate')
    assert (first.frames, selected.frames) == (225, 75)
    b = s.add('defense', template, 'Player_1', 0.0, 0.0)
    assert b.find(interfaces.Unpack).data is selected


def test_only_a_structure_made_in_the_run_unpacks_and_the_end_is_in_the_record():
    s = simsmall.small_world([('placed', 'SovietPowerPlant', 'Player_1', 0.0, 0.0)])
    placed = s.bodies['placed']
    m = placed.find(interfaces.Unpack)
    assert isinstance(m, unpack.Unpack) and m.frames() == 150
    assert placed.unpack_end is None and simrecord.body_state(placed)['unpack_end'] is None
    made = s.frame_now()
    s.add('built', 'SovietPowerPlant', 'Player_1', 400.0, 0.0, by='script', at=s.t)
    built = s.bodies['built']
    end = built.find(interfaces.Unpack).end_frame()
    assert end is not None and end >= made + 150 and built.unpack_end == end
    assert simrecord.body_state(built)['unpack_end'] == end
    with pytest.raises(AttributeError):
        built.unpack_end = 0


def test_a_thing_without_the_block_has_no_module_and_never_unpacks():
    s = simsmall.small_world()
    s.add('tank', 'AlliedAntiVehicleVehicleTech1', 'Player_1', 0.0, 0.0, by='script', at=s.t)
    assert s.bodies['tank'].find(interfaces.Unpack) is None and s.bodies['tank'].unpack_end is None


def test_an_untargeted_unpack_button_stops_only_a_unit_whose_command_set_holds_it():
    # review 1121oo #1: a Guardian on its way kept going when a script pressed an egg's button on it
    s = simsmall.small_world([('tank', 'AlliedAntiVehicleVehicleTech1', 'Player_1', 2000.0, 2500.0),
                              ('egg', 'JapanBaseDefenseEgg', 'Player_1', 2000.0, 2800.0)], model=False)
    for n in ('tank', 'egg'):
        s.act('MOVE_NAMED_UNIT_TO', [n, '@3000,2500'], None)
    s.advance(10)
    for n in ('tank', 'egg'):
        s.act('NAMED_USE_COMMANDBUTTON_ABILITY', [n, 'Command_UnPackJapanBaseDefenseEgg'], None)
    s.advance(60)
    assert s.bodies['tank'].path and not s.bodies['egg'].path
