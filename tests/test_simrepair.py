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
    import simunits
    import inventory
    m, t, _ = build.resolve('engine_repair', 'a')
    e = sim.Sim(m, t)
    e.advance(15 * 100)
    plant, control = (e.body(m.role(role).name) for role in ('repair', 'control'))
    assert plant.hp == control.hp == 500
    assert e.money[plant.owner] == 5000
    assert inventory.NOTES[inventory.MODULE, 'Behaviors/RepairUpdate'][0] == inventory.TODO
    assert (inventory.MODULE, 'Behaviors/RepairUpdate') not in inventory.BENCHED_TESTS
    assert ('repair HP', 90, '==', 100, 100) in t.expect  # keep the failed prediction visible
    # The include and inherited copy must both supply the schema defaults.
    rule = simunits.repair_update('AlliedPowerPlant')
    assert rule == {'rate': 10, 'toggleable': True, 'dead': False, 'cost': (.5,) * 4}
    own = {'RepairChild': '<GameObject id="RepairChild" inheritFrom="AlliedPowerPlant"/>'}
    assert simunits.repair_update('RepairChild', own) == rule
    assert simunits.repair_update('AlliedAntiInfantryInfantry') is None
