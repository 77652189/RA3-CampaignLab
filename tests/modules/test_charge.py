"""ChargeWeaponUpdate (engine/modules/charge.py; bench checks/engine_charge_e.py a-c): the Wave-Force tower's next
attack's first shot skips the part of its 3 s pre-attack it has charged (idle / ChargeTime 5 s); idle OverChargeTime
2 s more, that shot deals 40 % more. The host asks at a clip clock's fresh start (WeaponSet.start_clip,
Sim.shots_due)."""
from test_plans import small  # noqa: F401,I001  (tests/ is on the path by its conftest; puts experimental/cnv on it)
import pytest  # noqa: E402

from engine.modules import weaponset  # noqa: E402


def _tower(at):
    import engine.testing.small as simsmall
    s = simsmall.small_world([('tower', 'JapanBaseDefenseAdvanced', 'Player_1', 0.0, 0.0)])
    s.t = at
    b = s.bodies['tower']
    return s, b, b.weapons[0]


@pytest.mark.parametrize('idle, first, factor', [(4.0, 0, 1.0), (6.0, 1, 1.0), (7.0, 1, 1.4)])
def test_an_idle_tower_cuts_its_pre_attack_by_its_charge_and_hits_harder_overcharged(idle, first, factor):
    s, b, w = _tower(idle)
    assert s.shots_due(b, w, 0.5) == first          # charged: the shot one frame on; 4 s: 0.6 s of the 3 s left
    assert weaponset.boost(b, w) == pytest.approx(factor)
    assert weaponset.boost(b, w) == 1.0             # spent by the first volley


def test_the_charge_runs_from_the_last_cycles_end_not_the_making():
    s, b, w = _tower(10.0)
    assert s.shots_due(b, w, 0.5) == 1
    weaponset.boost(b, w)
    s.t = 15.0      # the window [10, 10.5) began a second cycle at ~10.4 (it ends ~13.7): 1.3 s charged, not 15
    assert s.shots_due(b, w, 0.5) == 0 and weaponset.boost(b, w) == 1.0
