"""WeaponSetUpdate's data (engine/modules/weaponset.py, step W1): each WeaponSlot*'s <Weapon> lines read from a
block of the template data port, and the readers on it (simunits.fight / declared_weapons / weapon_sets /
template_weapons, simcoverage.declared_picks) answering as before but for what the port does not read: a slot in an
XML comment, a block the template Removes (the SDK compiler reads neither). Kept on purpose: a unit whose own file
writes no WeaponSetUpdate holds no weapon (it inherits one: a gap Sim.add notes). Rules: docs/engine/weaponset.md;
on the bench: checks/engine_weaponset.py."""
from test_plans import small  # noqa: F401,I001  (tests/ is on the path by its conftest; puts experimental/cnv on it)
import simcoverage  # noqa: E402
import simunits  # noqa: E402
from engine.modules import weaponset  # noqa: E402

CANNON, PAINTER = 'AlliedAntiVehicleVehicleTech1Cannon', 'AlliedAntiVehicleVehicleTech1TargetPainter'
SET = (f'<WeaponSlotTurret ID="1"><Weapon Ordering="SECONDARY_WEAPON" Template="{PAINTER}" '
       f'ObjectStatus="GENERIC_TOGGLE_STATE"/><Weapon Ordering="PRIMARY_WEAPON" Template="{CANNON}" '
       f'ForbiddenObjectStatus="GENERIC_TOGGLE_STATE"/></WeaponSlotTurret>'
       f'<WeaponSlotHardpoint ID="2"><Weapon Ordering="PRIMARY_WEAPON" Template="X" Upgrade="Up_A Up_B"/>'
       f'<Weapon Ordering="TERTIARY_WEAPON" Template="Y"/><Weapon Ordering="SECONDARY_WEAPON" Template="Z" '
       f'ObjectStatus="S"/></WeaponSlotHardpoint>')


def _keys(weapons):
    return None if weapons is None else [w.get('weapon_key') for w in weapons]


def _tank(name, behaviors, up=''):
    inherit = f' inheritFrom="{up}"' if up else ''
    return (f'<GameObject id="{name}"{inherit} Side="Allies" EditorSorting="UNIT" KindOf="VEHICLE"><Body>'
            f'<ActiveBody id="ModuleTag_Body" MaxHealth="500"/></Body><Behaviors>{behaviors}</Behaviors></GameObject>')


def test_the_data_reads_each_slot_and_its_lines():
    d = weaponset.WeaponSetUpdateData.parse(' id="ModuleTag_WeaponSetUpdate"', SET)
    turret, hard = d.slots
    assert (turret.kind, hard.kind) == ('WeaponSlotTurret', 'WeaponSlotHardpoint')
    painter, cannon = turret.lines
    assert (painter.template, painter.ordering, painter.status, painter.forbidden) == \
        (PAINTER, 'SECONDARY_WEAPON', {'GENERIC_TOGGLE_STATE'}, frozenset())
    assert cannon.primary and cannon.forbidden == {'GENERIC_TOGGLE_STATE'} and not painter.primary
    assert hard.lines[0].upgrades == ('Up_A', 'Up_B')
    assert hard.lines[0].need == {weaponset.UPGRADE_BIT + 'up_a', weaponset.UPGRADE_BIT + 'up_b'}
    assert d.picks() == [CANNON, 'X']                  # the PRIMARY line, wherever it stands in the slot
    assert d.conditioned()
    # the AI's template rate: slots by kind (Hardpoint first), lines by Ordering, none with an Upgrade / ObjectStatus
    assert [x.template for x in d.counted()] == ['Y', CANNON]


def test_a_slot_without_primary_holds_its_first_and_always_count_wins():
    d = weaponset.WeaponSetUpdateData.parse('', '<WeaponSlotContained ID="1"><Weapon Ordering="SECONDARY_WEAPON" '
                                                'Template="A" ObjectStatus="S" ConquerMetricsAlwaysCount="true"/>'
                                                '<Weapon Ordering="SECONDARY_WEAPON" Template="B"/></WeaponSlotContained>')
    assert d.picks() == ['A'] and [x.template for x in d.counted()] == ['A']
    plain = weaponset.WeaponSetUpdateData.parse('', '<WeaponSlotTurret ID="1"><Weapon Template="A"/></WeaponSlotTurret>')
    assert not plain.conditioned() and plain.picks() == ['A']


def test_the_readers_take_the_port_blocks():
    own = {'CNV_TestTank': _tank('CNV_TestTank', f'<WeaponSetUpdate id="ModuleTag_WeaponSetUpdate">{SET}'
                                                 f'</WeaponSetUpdate>')}
    assert _keys(simunits.fight('CNV_TestTank', own)['weapons']) == [CANNON]     # X is no weapon of the table
    assert simunits.declared_weapons('CNV_TestTank', own) == [CANNON, 'X']
    assert simcoverage.declared_picks('CNV_TestTank', own) == [CANNON, 'X']
    sets = simunits.weapon_sets('CNV_TestTank', own)
    assert _keys(simunits.pick_weapons(sets, set())) == [CANNON]
    assert _keys(simunits.pick_weapons(sets, {'GENERIC_TOGGLE_STATE'})) == []     # the painter cannot hurt
    assert _keys(simunits.template_weapons('CNV_TestTank', own)) == [CANNON]


def test_a_commented_slot_and_a_removed_set_are_not_read():
    """The Guardian's second turret is in an XML comment: the readers before named its painter twice."""
    commented = _tank('CNV_TestTank', f'<WeaponSetUpdate id="ModuleTag_WeaponSetUpdate">{SET[:SET.index("<WeaponSlotH")]}'
                                      f'<!-- <WeaponSlotTurret ID="9"><Weapon Ordering="PRIMARY_WEAPON" Template="{CANNON}"/>'
                                      f'</WeaponSlotTurret> --></WeaponSetUpdate>')
    assert simunits.declared_weapons('CNV_TestTank', {'CNV_TestTank': commented}) == [CANNON]
    assert len(simunits.weapon_sets('CNV_TestTank', {'CNV_TestTank': commented})) == 1
    # a Century bomber carrying infantry Removes the bomber's set: no weapon named (before: the bomb, a gap)
    assert simunits.declared_weapons('Camp_AlliedBomberAircraft_Infantry_1') == []
    assert simunits.declared_weapons('AlliedBomberAircraft')


def test_a_unit_whose_file_writes_no_set_holds_no_weapon():
    """Kept from read_fight: the weapons are read only where the unit's own file writes a WeaponSetUpdate -- the
    tutorial tank inherits the Guardian's, holds none, and its XML still names the cannon (Sim.add's gap)."""
    assert simunits.fight('Tutorial_AlliedTech1Tank')['weapons'] == []
    assert simunits.declared_weapons('Tutorial_AlliedTech1Tank') == [CANNON]
    assert _keys(simunits.fight('AlliedAntiVehicleVehicleTech1')['weapons']) == [CANNON]
    up = _tank('CNV_TestBase', f'<WeaponSetUpdate id="ModuleTag_WeaponSetUpdate">{SET}</WeaponSetUpdate>')
    child = _tank('CNV_TestChild', '', up='CNV_TestBase')
    own = {'CNV_TestBase': up + child, 'CNV_TestChild': child}
    assert simunits.fight('CNV_TestChild', own)['weapons'] == []
    assert simunits.declared_weapons('CNV_TestChild', own) == [CANNON, 'X']


def test_a_retail_units_weapons_are_read_once_in_the_cache_shape():
    a, b = simunits.fight('AlliedAntiAirShip'), simunits.fight('AlliedAntiAirShip')
    assert a['weapons'] is b['weapons'] and a['weapons']
    assert all(isinstance(p, list) for w in a['weapons'] for p in w.get('ai_parts') or [])
