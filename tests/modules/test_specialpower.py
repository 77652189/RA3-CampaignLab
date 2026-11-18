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
