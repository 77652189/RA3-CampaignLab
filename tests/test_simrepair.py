"""RepairUpdate data guard; the failed bench is NOT a repair comparison pass."""
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location('simbench_repair', ROOT / 'experimental/cnv/simbench.py')
_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_module)


def test_repair_update_defaults_do_not_claim_the_failed_activation_as_implemented():
    import build
    import sim
    import engine.data.units as simunits
    import inventory
    m, t, _ = build.resolve('engine_repair', 'a')
    e = sim.Sim(m, t)
    e.advance(15 * 100)
    plant, control = (e.body(m.role(role).name) for role in ('repair', 'control'))
    assert plant.hp == control.hp == 500
    assert e.money[plant.owner] == 5000
    key = inventory.MODULE, 'Behaviors/RepairUpdate'
    assert inventory.NOTES[key][0] == inventory.BENCHED
    assert inventory.BENCHED_TESTS[key].startswith('tests/test_simrepair_ai.py::')
    assert 'gap：玩家入口' in inventory.NOTES[key][1]
    assert ('repair HP', 90, '==', 100, 100) in t.expect  # keep the failed prediction visible
    # The include and inherited copy must both supply the schema defaults (the port reads RepairUpdate's includes).
    from engine.modules import repair

    def rule(template, own=None):
        return [repair.RepairData.parse(*b).rule for b in simunits.module_blocks(template, 'RepairUpdate', own)]
    assert rule('AlliedPowerPlant') == [{'rate': 10, 'toggleable': True, 'dead': False, 'cost': (.5,) * 4}]
    own = {'RepairChild': '<GameObject id="RepairChild" inheritFrom="AlliedPowerPlant"/>'}
    assert rule('RepairChild', own) == rule('AlliedPowerPlant')
    assert rule('AlliedAntiInfantryInfantry') == []
