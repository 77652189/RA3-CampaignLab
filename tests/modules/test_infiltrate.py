"""The InfiltratorContain module (engine/modules/infiltrate.py, step M15): its block read as written (a KILL block's
inner text kept as the unmeasured-children marker), the retail structures' block read through their include
(Includes/InfiltratorContain*.xml), the measured slices entered and a port's block kept on the module, and the host
(siminfiltrator.Infiltrators) reading the first module's rule, a KILL host with siblings marked. On the bench:
engine_infpower / infvis / infkill / infport ... (tests/test_siminfiltrator*.py)."""
from test_plans import small  # noqa: F401,I001  (tests/ is on the path by its conftest; puts experimental/cnv on it)
import simsmall  # noqa: E402
import siminfiltrator  # noqa: E402
import simunits  # noqa: E402
from engine.kernel import interfaces  # noqa: E402
from engine.modules import infiltrate  # noqa: E402

TAG = 'InfiltratorContain'


def test_the_block_is_read_as_written_and_a_kill_child_marked():
    d = infiltrate.InfiltratorData.parse(' id="M" Effect="ENERGY" Amount="0.2"', '<Child/>')
    assert d.rule == {'id': 'M', 'Effect': 'ENERGY', 'Amount': '0.2'}       # a non-KILL child is not marked
    d = infiltrate.InfiltratorData.parse(' id="M" Effect="KILL"', '  ')
    assert d.rule == {'id': 'M', 'Effect': 'KILL'}
    d = infiltrate.InfiltratorData.parse(' id="M" Effect="KILL"', '<Filter/>')
    assert d.rule['_unmeasured_children'] == '<Filter/>'


def test_the_retail_structure_reads_its_include_and_is_made_with_the_module():
    (block,) = simunits.module_blocks('AlliedPowerPlant', TAG)
    rule = infiltrate.InfiltratorData.parse(*block).rule
    assert rule['Effect'] == 'ENERGY' and rule['ObjectRef'] == 'EnergyDisabler' and rule['Amount'] == '0.2'
    assert simunits.module_blocks('AlliedAntiInfantryInfantry', TAG) == []
    s = simsmall.small_world()
    plant = s.add('plant', 'AlliedPowerPlant', 'Player_1', 300.0, 300.0)
    (m,) = plant.find(interfaces.Infiltrate)
    assert m.rules() is s.infiltrators.spec(plant) and m.rules() == rule
    assert not m.entered('money') and m.blocked_until() == 0
    m.mark('money')
    assert m.entered('money') and not m.entered('kill')
    assert s.infiltrators.entered(plant, 'money') and s.infiltrators.module(plant) is m
    s.infiltrators.mark(plant, 'kill')
    assert m.entered('kill')
    m.block(250)
    assert m.blocked_until() == 250
    other = s.add('plant2', 'AlliedPowerPlant', 'Player_1', 500.0, 300.0)       # the marks are each thing's
    assert not s.infiltrators.entered(other, 'money')
    gi = s.add('gi', 'AlliedAntiInfantryInfantry', 'Player_1', 400.0, 300.0)
    assert gi.find(interfaces.Infiltrate) == () and s.infiltrators.spec(gi) is None
    assert s.infiltrators.module(gi) is None


def test_the_crane_kill_rule_and_a_sibling_marked_by_the_host():
    rule = siminfiltrator.spec('SovietCrane')
    assert rule['Effect'] == 'KILL' and '_unmeasured_siblings' not in rule and '_unmeasured_children' not in rule
    block = '<InfiltratorContain id="A" Effect="KILL" Amount="1.5"/>'
    own = {'CNVTwoKill': '<GameObject id="CNVTwoKill" inheritFrom="SovietCrane"><Behaviors>' + block
           + '<InfiltratorContain id="B" Effect="KILL"/></Behaviors></GameObject>'}
    rule = siminfiltrator.spec('CNVTwoKill', own)
    assert rule['id'] == 'A' and rule['_unmeasured_siblings'] == 2
    own = {'CNVOneKill': '<GameObject id="CNVOneKill" inheritFrom="SovietCrane"><Behaviors>' + block
           + '</Behaviors></GameObject>'}
    assert '_unmeasured_siblings' not in siminfiltrator.spec('CNVOneKill', own)    # the nearest template's alone
    assert siminfiltrator._rule({'Effect': 'VISION'}, 2) == {'Effect': 'VISION'}  # only a KILL host is marked


SLICES = {'vehicle': 'AlliedWarFactory', 'money': 'AlliedRefinery', 'kill': 'SovietCrane',
          'paralyze': 'AlliedTechStructure', 'reset': 'SovietSuperWeapon', 'aircraft': 'AlliedAirfield',
          'infantry': 'AlliedBarracks', 'ship': 'AlliedNavalYard'}


def test_a_real_entry_marks_the_building_and_a_second_spy_is_turned_away():
    """Each measured slice: the first human spy that walks in is consumed and the building's module marked; a second
    is not sent (a repeat entry is a gap, the spy stays) -- the marks the tests above set by hand, made by an entry."""
    for slice_, template in SLICES.items():
        s = simsmall.small_world()
        target = s.add('t', template, 'Player_2', 1000.0, 1000.0)
        s.wallet.credit('Player_2', 5000)
        first, second = (s.add(n, 'AlliedInfiltrationInfantry', s.human, 1000.0, 1000.0) for n in ('spy1', 'spy2'))
        s.relations[target.owner, s.human] = 'Enemy'
        s.infiltrators.send(first, target)
        first.path = []
        s.infiltrators.tick()
        assert not first.alive and s.infiltrators.entered(target, slice_), slice_
        s.infiltrators.send(second, target)
        assert second.alive and not s.infiltrators.going, slice_
