"""The StructureUnpackUpdate module (engine/modules/unpack.py, step M10): UnpackTime read through the port (a '=$NAME'
define from the asked template's own file, as the reader it replaced), the end set only on a structure made in the
run, read through the body's `unpack_end` forward and in the frame record where the body's field was. The power factor's
stretch and what unpacking holds back (power, fire, a sale): tests/test_simbench.py (engine_powerdef), test_sell.py."""
import pytest

from test_plans import small  # noqa: F401,I001  (tests/ is on the path by its conftest; puts experimental/cnv on it)
import simrecord  # noqa: E402
import simsmall  # noqa: E402
import simunits  # noqa: E402
from engine.kernel import interfaces  # noqa: E402
from engine.modules import unpack  # noqa: E402


def test_the_block_is_read_seconds_x_15_rounded_nothing_is_none():
    assert unpack.UnpackData.parse(' UnpackTime="1.5s"', '').frames == round(22.5) == 22     # Python's rounding
    assert unpack.UnpackData.parse(' UnpackTime="10s"', '').frames == 150
    assert unpack.UnpackData.parse(' UnpackTime="0s"', '').frames == 0
    assert unpack.UnpackData.parse('', '').frames == 0


def test_a_define_is_spelled_out_from_the_templates_own_file_an_inherited_one_from_another_file_reads_as_nothing():
    (head, _), = simunits.module_blocks('SovietPowerPlant', 'StructureUnpackUpdate')
    assert '=$' not in head and unpack.UnpackData.parse(head, '').frames == 150      # SovietPowerPlant.xml: 10 s
    (head, _), = simunits.module_blocks('AlliedRefinery_NoHarvester', 'StructureUnpackUpdate')
    assert unpack.UnpackData.parse(head, '').frames == 0     # AlliedRefinery's define, not in its file (kept, M10)


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
