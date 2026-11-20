"""WeaponSetUpdate's data (engine/modules/weaponset.py, step W1): each WeaponSlot*'s <Weapon> lines read from a
block of the template data port, and the readers on it (simunits.fight / declared_weapons / weapon_sets /
template_weapons, simcoverage.declared_picks) answering as before but for what the port does not read: a slot in an
XML comment, a block the template Removes (the SDK compiler reads neither). Kept on purpose: a unit whose own file
writes no WeaponSetUpdate holds no weapon (it inherits one: a gap Sim.add notes). Rules: docs/engine/weaponset.md;
on the bench: checks/engine_weaponset.py. Step W2 (below): the WeaponSet module holds a thing's weapons and slots,
armed by Sim.add, written back by the modifier pass, read through the body's forwards and in the frame record."""
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
    by_order = weaponset.WeaponSetUpdateData.parse('', '<WeaponSlotTurret ID="1"><Weapon Ordering="TERTIARY_WEAPON" '
                                                   'Template="A"/><Weapon Ordering="SECONDARY_WEAPON" Template="B"/>'
                                                   '</WeaponSlotTurret>')
    assert [x.template for x in by_order.counted()] == ['B']        # the Ordering ranks, not the XML order


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
    # a retail unit with fight data whose file writes none: the Rushmore head's laser stays unread (3 such)
    assert simunits.fight('MR_LaserMtRushmore_Jefferson_Ready')['weapons'] == []
    assert simunits.declared_weapons('MR_LaserMtRushmore_Jefferson_Ready') == ['MountRushmoreHeadEyeWeapon']
    up = _tank('CNV_TestBase', f'<WeaponSetUpdate id="ModuleTag_WeaponSetUpdate">{SET}</WeaponSetUpdate>')
    child = _tank('CNV_TestChild', '', up='CNV_TestBase')
    own = {'CNV_TestBase': up + child, 'CNV_TestChild': child}
    assert simunits.fight('CNV_TestChild', own)['weapons'] == []
    assert simunits.declared_weapons('CNV_TestChild', own) == [CANNON, 'X']
    # a WeaponSetUpdate only in an XML comment of its own file is none: the parent's weapons stay unread
    commented = _tank('CNV_TestChild', '<!-- <WeaponSetUpdate id="ModuleTag_WeaponSetUpdate"/> -->', up='CNV_TestBase')
    own = {'CNV_TestBase': up + commented, 'CNV_TestChild': commented}
    assert simunits.fight('CNV_TestChild', own)['weapons'] == []


def test_a_retail_units_weapons_are_read_once_in_the_cache_shape():
    a, b = simunits.fight('AlliedAntiAirShip'), simunits.fight('AlliedAntiAirShip')
    assert a['weapons'] is b['weapons'] and a['weapons']
    assert all(isinstance(p, list) for w in a['weapons'] for p in w.get('ai_parts') or [])


# --- step W2: the module holds the thing's weapons and slots ------------------------------------------------------

def _world():
    import simsmall
    return simsmall.small_world([('tank', 'AlliedAntiVehicleVehicleTech1', 'Player_1', 0.0, 0.0),
                                 ('plant', 'SovietPowerPlant', 'Player_1', 300.0, 0.0),
                                 ('tut', 'Tutorial_AlliedTech1Tank', 'Player_1', 600.0, 0.0)])


def test_the_module_holds_what_sim_add_armed_and_the_body_reads_it_through_forwards():
    import pytest
    import simrecord
    from engine.kernel import interfaces
    s = _world()
    tank, plant, tut = s.bodies['tank'], s.bodies['plant'], s.bodies['tut']
    m = tank.find(interfaces.WeaponSet)
    assert isinstance(m, weaponset.WeaponSet) and m.data.slots          # its block's data (W1's)
    assert tank.weapons is m.held() and _keys(tank.weapons) == [CANNON]
    assert tank.slots is m.choices() is s._wsets['AlliedAntiVehicleVehicleTech1']    # the painter toggle: by status
    state = simrecord.body_state(tank)
    assert state['weapons'] is m.held() and state['slots'] is m.choices()     # the record's names, as on the body
    with pytest.raises(AttributeError):
        tank.weapons = []
    with pytest.raises(AttributeError):
        tank.slots = None
    # no block and no weapons: no module, the old defaults
    assert plant.find(interfaces.WeaponSet) is None and plant.weapons == [] and plant.slots is None
    assert simrecord.body_state(plant)['weapons'] == [] and simrecord.body_state(plant)['slots'] is None
    # an inherited block (the port's) but no weapon read (fight's own-file rule): a module holding none
    t = tut.find(interfaces.WeaponSet)
    assert t is not None and t.held() == [] and t.choices() is None and tut.weapons == []


def test_the_modifier_pass_writes_the_status_pick_back_to_the_module():
    from engine.kernel import interfaces
    s = _world()
    tank = s.bodies['tank']
    m = tank.find(interfaces.WeaponSet)
    tank.script_status.add('GENERIC_TOGGLE_STATE')          # the painter's line: no gun of its own
    s.modify(tank)
    assert m.held() == [] and tank.weapons == []
    tank.script_status.discard('GENERIC_TOGGLE_STATE')
    s.modify(tank)
    assert _keys(m.held()) == [CANNON] and tank.weapons is m.held()


def test_equip_attaches_a_module_only_to_a_thing_that_has_something_to_hold():
    from engine.kernel import interfaces
    s = _world()
    plant = s.bodies['plant']
    assert weaponset.equip(s.world, plant, [], None) is None and plant.find(interfaces.WeaponSet) is None
    gun = simunits.fight('AlliedAntiVehicleVehicleTech1')['weapons']
    m = weaponset.equip(s.world, plant, gun, None)
    assert plant.find(interfaces.WeaponSet) is m and plant.weapons is gun and plant.slots is None
    assert ('WeaponSetUpdate', '') in s.world.late[plant.serial]       # a snapshot's thing gets it again
    again = weaponset.equip(s.world, plant, [], None)                      # one module: armed again
    assert again is m and plant.weapons == [] and len(s.world.late[plant.serial]) == 1


def test_the_ais_fill_arms_an_unknown_templates_body_through_its_module(monkeypatch):
    """simbody.fill (the skirmish AI's factory made a template simunits does not know): the weapons of the template
    without its last '_' part, held by the body's WeaponSet -- one attached when it has none."""
    import types
    import simbody
    from engine.kernel import interfaces
    s = _world()
    lib = types.SimpleNamespace(template=lambda name: types.SimpleNamespace(kinds=('VEHICLE',)))
    monkeypatch.setattr(simbody.importlib, 'import_module',
                        lambda name: types.SimpleNamespace(normal_speed=lambda lib, tpl: 60.0))
    plant = s.bodies['plant']                       # no WeaponSet: stands in for the unknown template's body
    plant.template, plant.guessed = 'AlliedAntiVehicleVehicleTech1_Ground', ['all']
    simbody.fill(s, plant, lib)
    m = plant.find(interfaces.WeaponSet)
    assert m is not None and _keys(plant.weapons) == [CANNON] and plant.speed == 60.0
    assert plant.guessed == ['all: simai.fill']


# --- step W3: each weapon's firing state is the shooter's WeaponSet's ---------------------------------------------

BAZOOKA = 'JapanAntiVehicleInfantryPlasmaBazooka'      # PreAttackType PER_TARGET with a PreAttackDelay


def test_the_clip_clock_is_the_shooters_by_weapon_key_and_a_copy_shares_it():
    from engine.kernel import interfaces
    s = _world()
    tank, tut = s.bodies['tank'], s.bodies['tut']
    m = tank.find(interfaces.WeaponSet)
    gun = tank.weapons[0]
    assert s.shots_due(tank, gun, 1.0) >= 1
    clock = m.clip_clock(CANNON)
    assert clock is not None and list(m.clocks) == [CANNON]
    s.shots_due(tank, dict(gun), 1.0)              # a range refresh's copy: the same clock, not a second one
    assert list(m.clocks) == [CANNON] and m.clip_clock(CANNON) is clock
    assert tut.find(interfaces.WeaponSet).clocks is None and 'clocks' not in vars(s)    # not the host's any more
    keyless = {k: v for k, v in gun.items() if k != 'weapon_key'}
    plant = s.bodies['plant']                       # no module: one attached; a keyless weapon's key is its slot
    s.shots_due(plant, keyless, 1.0)
    assert list(plant.find(interfaces.WeaponSet).clocks) == [-1] and plant.weapons == []


def test_a_per_target_weapon_gates_only_its_shooter_and_that_target():
    from engine.kernel import interfaces
    s = _world()
    tank, plant, tut = s.bodies['tank'], s.bodies['plant'], s.bodies['tut']
    pre = simunits.weapon_table(s.own)[BAZOOKA]['pre']
    ready = s.t + simunits._frames(pre) / simunits.FPS
    w = {'weapon_key': BAZOOKA}
    s.first_shot(tank, w, plant)
    m = tank.find(interfaces.WeaponSet)
    assert m.pre_lock(BAZOOKA) == (plant, ready) and ready > s.t
    assert weaponset.gate(tank, plant) == ready
    assert weaponset.gate(tank, tut) == 0.0 and weaponset.gate(tut, plant) == 0.0 and weaponset.gate(plant, tank) == 0.0
    s.t += 1.0
    s.first_shot(tank, w, plant)                    # the same target: no new wait
    assert m.pre_lock(BAZOOKA) == (plant, ready) and weaponset.gate(tank, plant) == ready
    s.first_shot(tank, w, tut)                      # a new one: waits again, the old target's gate stays as it was
    assert m.pre_lock(BAZOOKA) == (tut, ready + 1.0) and weaponset.gate(tank, tut) == ready + 1.0
    assert weaponset.gate(tank, plant) == ready
    assert not hasattr(s, 'pre_locks') and not hasattr(s, 'fire_gate')


def test_the_firing_state_is_left_out_of_the_frame_record_and_kept_by_a_snapshot():
    import simrecord
    import simsmall
    import simsnap
    from engine.kernel import interfaces
    objects = [('tank', 'AlliedAntiVehicleVehicleTech1', 'Player_1', 0.0, 0.0),
               ('plant', 'SovietPowerPlant', 'Player_1', 300.0, 0.0)]
    source, target = simsmall.small_world(objects, model=False), simsmall.small_world(objects, model=False)
    tank, plant = source.bodies['tank'], source.bodies['plant']
    source.shots_due(tank, tank.weapons[0], 1.0)
    source.first_shot(tank, {'weapon_key': BAZOOKA}, plant)
    state = simrecord.body_state(tank)
    assert 'weapons' in state and not {'clocks', 'pre_locks', 'fire_gate'} & set(state)
    saved = simsnap.snapshot(source)
    assert not simsnap.unclassified(source)
    simsnap.restore(target, saved)
    m, t = tank.find(interfaces.WeaponSet), target.bodies['tank'].find(interfaces.WeaponSet)
    assert t.clocks == m.clocks and t.clocks is not m.clocks
    assert t.pre_lock(BAZOOKA)[0] is target.bodies['plant'] and t.pre_lock(BAZOOKA)[1] == m.pre_lock(BAZOOKA)[1]
    assert weaponset.gate(target.bodies['tank'], target.bodies['plant']) == weaponset.gate(tank, plant) > 0
    assert simsnap.snapshot(target) == saved
