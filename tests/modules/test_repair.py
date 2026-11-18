"""The RepairUpdate module (engine/modules/repair.py, step M13): its block read with the schema defaults (10 HP/s,
toggleable, not when dead, 50 % of the cost each state), the measured shape told apart (no field outside those but
SelfAudio), the retail structures' block read through their include (Includes/GenericBuildingRepair.xml), and the
repair under way / the refusal kept on the module, which the host's loop (simrepair.Repairs.due) finds by interface.
On the bench: repairai / repairq / repairt / repairzero (tests/test_simrepair_ai.py)."""
from test_plans import small  # noqa: F401,I001  (tests/ is on the path by its conftest; puts experimental/cnv on it)
import simsmall  # noqa: E402
import simunits  # noqa: E402
from engine.kernel import interfaces  # noqa: E402
from engine.modules import repair  # noqa: E402

DEFAULT = {'rate': 10, 'toggleable': True, 'dead': False, 'cost': (.5,) * 4}


def test_the_block_is_read_with_the_schema_defaults_and_its_shape_told():
    d = repair.RepairData.parse(' id="ModuleTag_RepairUpdate"', '')
    assert d.rule == DEFAULT and d.measured
    d = repair.RepairData.parse(' id="R" HealAmountPerSecond="25" Toggleable="false" RepairableWhenDead="true"',
                                '<PercentOfBuildCostToRebuildInfo Pristine="10" Damaged="20" ReallyDamaged="30" '
                                'Rubble="40"/><SelfAudio Sound="x"/>')
    assert d.rule == {'rate': 25, 'toggleable': False, 'dead': True, 'cost': (.1, .2, .3, .4)} and d.measured
    assert not repair.RepairData.parse(' id="R" RepopThreshold="50%"', '').measured        # an attribute not read
    assert not repair.RepairData.parse(' id="R"', '<Other/>').measured                       # a child not read
    assert not repair.RepairData.parse(' id="R"', '<PercentOfBuildCostToRebuildInfo Other="1"/>').measured


def test_the_retail_structure_reads_its_include_and_is_made_with_the_module():
    (block,) = simunits.module_blocks('AlliedPowerPlant', 'RepairUpdate')
    assert repair.RepairData.parse(*block).rule == DEFAULT
    assert simunits.module_blocks('AlliedAntiInfantryInfantry', 'RepairUpdate') == []
    s = simsmall.small_world()
    plant = s.add('plant', 'AlliedPowerPlant', 'Player_1', 300.0, 300.0)
    (m,) = plant.find(interfaces.Repair)
    assert m.rules() == DEFAULT and m.measured() and m.job() is None and not m.refused()
    m.set_job({'owner': 'Player_1'})
    assert m.job() == {'owner': 'Player_1'}
    m.refuse()
    assert m.job() is None and m.refused()
    infantry = s.add('gi', 'AlliedAntiInfantryInfantry', 'Player_1', 400.0, 300.0)
    assert infantry.find(interfaces.Repair) == ()
