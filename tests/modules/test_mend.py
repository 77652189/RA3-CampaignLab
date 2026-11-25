"""The repair gun (engine/combat/host.mend, E174, checks/engine_secondary_e.readings.toml): it mends a hurt friendly
vehicle in reach -- not while its host may not fire, NO_ATTACK or EMP (review 109 #2)."""
import pytest

import engine.testing.small as simsmall


@pytest.mark.parametrize('stop, mended', [(None, True), ('NO_ATTACK', False), ('EMP', False)])
def test_a_repair_gun_mends_only_while_its_host_may_fire(stop, mended):
    s = simsmall.small_world([('host', 'AlliedAntiVehicleVehicleTech1', 'Player_1', 1400.0, 2400.0),
                              ('hurt', 'AlliedAntiVehicleVehicleTech1', 'Player_1', 1440.0, 2400.0)], model=False)
    host, hurt = s.bodies['host'], s.bodies['hurt']
    host.weapons.append({'type': 'HEALING', 'dps': 37.5, 'range': 100.0})
    hurt.damage(hurt.max_hp / 2)
    if stop == 'NO_ATTACK':
        host.status.add('NO_ATTACK')
    elif stop == 'EMP':
        s.act('NAMED_SET_DISABLED', ['host', 'EMP', 1], None)
    s.advance(15)
    assert (hurt.hp > hurt.max_hp / 2) is mended
