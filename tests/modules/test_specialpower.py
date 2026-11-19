"""The SpecialPower modules (engine/modules/specialpower.py, step M8): one a block of any SpecialPowerModule tag --
SpecialPower, OCLSpecialPower, MovementSpecialPower, DominateEnemySpecialPower, RecallUnitsSpecialPower,
StoreObjectsSpecialPower, TeleportStoredObjectsSpecialPower, TeleportToCasterSpecialPower, PlayerUpgradeSpecialPower,
ReturnToProducerSpecialPower, ActivateModuleSpecialPower, AssignSlavesTargetObjectSpecialPower,
GiveProductionBonusSpecialPower, PrematureDischargeSpecialPower, ReturnToDockSpecialPower -- keeping the frame its
power's reload ends; the body's ready_at forwarded as {power: frame} of the reloads started, {} before any. The bench
replay of a script's cast starting the retail reload: test_super_a_scripts_cast_starts_the_retail_reload
(tests/test_simbench.py)."""
import pytest

from test_plans import small  # noqa: F401,I001  (tests/ is on the path by its conftest; puts experimental/cnv on it)
from engine.modules import specialpower  # noqa: E402

COLLIDER, CANNON = 'AlliedSuperWeaponAdvanced', 'SpecialPowerParticleCannon'


def test_every_tag_is_named_here_and_reads_its_power():
    src = open(__file__, encoding='utf-8').read().split('import pytest', 1)[0]
    assert all(tag in src for tag in specialpower.TAGS)
    assert len(specialpower.TAGS) == 15
    assert specialpower.SpecialPowerData.parse(' id="M" SpecialPowerTemplate="SpecialPowerX"', '').power == 'SpecialPowerX'
    assert specialpower.SpecialPowerData.parse(' id="M"', '').power is None


def _collider():
    import simsmall
    e = simsmall.small_world()
    e.add('collider', COLLIDER, 'Player_1', 300.0, 300.0)
    return e, e.bodies['collider']


def test_a_template_gets_one_module_a_block_and_no_reload_before_a_cast():
    import sim
    e, b = _collider()
    mods = b.find(sim.kernel_interfaces.SpecialPower)
    # the retail proton collider: a SpecialPower and an OCLSpecialPower block, both for the cannon
    assert sorted((type(m).__name__, m.power()) for m in mods) == [('SpecialPower', CANNON)] * 2
    assert all(m.ready_at() is None for m in mods)
    assert b.ready_at == {}
    with pytest.raises(AttributeError):
        b.ready_at = {CANNON: 1}


def test_a_reload_started_is_on_every_module_of_its_power_and_refuses_the_click_until_over():
    import sim
    import simpower
    e, b = _collider()
    now = e.frame_now()
    simpower.start_reload(e, b, CANNON, now + 100)
    assert [m.ready_at() for m in b.find(sim.kernel_interfaces.SpecialPower)] == [now + 100, now + 100]
    assert b.ready_at == {CANNON: now + 100}
    assert e.order_power(b, CANNON, (b.x + 500, b.y))[1] == 'reloading'
    simpower.start_reload(e, b, CANNON, now + 30)       # every cast starts it anew
    assert b.ready_at == {CANNON: now + 30}
    e.advance(30)
    assert e.order_power(b, CANNON, (b.x + 500, b.y))[1] != 'reloading'


def test_a_power_no_block_serves_gets_a_module_attached():
    import sim
    import simpower
    e, b = _collider()
    simpower.start_reload(e, b, 'Command_X', 77)
    simpower.start_reload(e, b, 'Command_X', 88)        # the attached one is found again, not a second
    assert b.ready_at == {'Command_X': 88}
    assert [m.power() for m in b.find(sim.kernel_interfaces.SpecialPower)].count('Command_X') == 1
    e.add('plain', 'AlliedMiner', 'Player_1', 500.0, 300.0)
    p = e.bodies['plain']
    assert p.ready_at == {}
    simpower.start_reload(e, p, CANNON, 5)
    assert p.ready_at == {CANNON: 5}


# --- AssignSlavesTargetObjectSpecialPower (step M13): a SpecialPower with a dispatch, its healing in the assignments
# cell. The bench replay: tests/test_simassignslaves.py (E67 / E181).

class _Drones:
    """A SpawnBehavior stand-in: the drones it made."""

    def __init__(self, *alive):
        self.kids = [type('Drone', (), {'alive': a})() for a in alive]

    def children(self):
        return self.kids


class _World:
    def __init__(self):
        self.woken, self.gaps, self.used = [], [], set()

    def wake(self, module, frame=None):
        self.woken.append(module)

    def gap(self, kind, name, what=''):
        self.gaps.append((kind, name))


def _things(drones=(True,)):
    from engine.kernel import interfaces, module

    class Thing(module.Thing):
        def __init__(self, x, hp, mods=()):
            self.x, self.y, self.alive, self.owner, self.hp, self.max_hp = x, 0.0, True, 'P', hp, 480.0
            self.modules = mods

        def mend(self, amount):
            self.hp = min(self.max_hp, self.hp + amount)

    spawn = type('Spawn', (_Drones, interfaces.Spawn), {})(*drones)      # found by the Spawn interface
    w = _World()
    source = Thing(0.0, 1000.0)
    data = specialpower.AssignData.parse(' id="M" SpecialPowerTemplate="SpecialPower_TargetedRepairVehicle"', '').seal()
    m = specialpower.AssignSlaves(source, data, w)
    source.modules = (spawn, m)
    return w, source, m, Thing(100.0, 400.0)


def test_assign_reads_the_plain_shape_only():
    plain = specialpower.AssignData.parse(' id="M" SpecialPowerTemplate="SpecialPower_TargetedRepairVehicle"', '')
    assert plain.plain and plain.power == 'SpecialPower_TargetedRepairVehicle'
    assert not specialpower.AssignData.parse(' id="M" SpecialPowerTemplate="X" Other="1"', '').plain
    assert not specialpower.AssignData.parse(' id="M" SpecialPowerTemplate="X"', '<Child/>').plain
    import simsmall
    from engine.kernel import interfaces
    s = simsmall.small_world()
    factory = s.add('factory', 'AlliedWarFactory', 'Player_1', 300.0, 300.0)
    (m,) = factory.find(interfaces.Assign)
    assert m.plain() and m.power() == 'SpecialPower_TargetedRepairVehicle' and m.target() is None
    assert m in factory.find(interfaces.SpecialPower)


def test_assign_mends_rate_a_second_till_whole_then_sleeps():
    from engine.kernel import interfaces
    w, source, m, target = _things()
    m.assign(target, 20.0)
    assert m.target() is target and w.woken == [m]
    for frame in range(15):
        assert m.update(frame) == 1
    assert target.hp == pytest.approx(420.0) and 'assigned repair' in w.used
    target.hp = 479.0
    m.last = 479.0
    assert m.update(15) is interfaces.SLEEP and target.hp == 480.0 and m.target() is None and not w.gaps


@pytest.mark.parametrize('disturb', ['target moved', 'source moved', 'hp changed', 'target dead', 'owner',
                                     'no drone'])
def test_assign_stops_once_anything_moves(disturb):
    from engine.kernel import interfaces
    w, source, m, target = _things()
    m.assign(target, 20.0)
    m.update(0)
    hp = target.hp
    if disturb == 'target moved':
        target.x += 1
    elif disturb == 'source moved':
        source.y += 1
    elif disturb == 'hp changed':
        target.hp = hp = hp - 5
    elif disturb == 'target dead':
        target.alive = False
    elif disturb == 'owner':
        target.owner = 'Q'
    else:
        source.modules[0].kids[0].alive = False
    assert m.update(1) is interfaces.SLEEP and m.target() is None and target.hp == hp
    assert w.gaps == [('AssignSlavesTargetObjectSpecialPower', 'interrupted')]


def test_assign_press_keeps_its_first_target_and_one_dispatcher_a_target():
    """The host's press (simassign): a second press of a dispatching factory does not retarget it, and a target
    already healed by one is not given another (both unmeasured, deliberately not inferred)."""
    import simsmall
    from engine.kernel import interfaces
    s = simsmall.small_world()
    one = s.add('one', 'AlliedWarFactory', 'Player_1', 300.0, 300.0)
    two = s.add('two', 'AlliedWarFactory', 'Player_1', 300.0, 600.0)
    a = s.add('a', 'AlliedAntiVehicleVehicleTech1', 'Player_1', 350.0, 400.0)
    b = s.add('b', 'AlliedAntiVehicleVehicleTech1', 'Player_1', 350.0, 450.0)
    a.set_hp(100.0, tell=False)
    b.set_hp(100.0, tell=False)
    assert one.spawned_children and two.spawned_children
    assert s.assignments.press(one, 'Command_RepairVehicle', a)
    (m,) = one.find(interfaces.Assign)
    assert m.target() is a
    assert s.assignments.press(one, 'Command_RepairVehicle', b) and m.target() is a
    (n,) = two.find(interfaces.Assign)
    assert s.assignments.press(two, 'Command_RepairVehicle', a) and n.target() is None
