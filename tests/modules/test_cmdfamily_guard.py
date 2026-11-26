"""Guard area hands off to idle acquisition and the stance's return rule."""
import pytest

import engine.testing.small as simsmall
import engine.orders.order as simorder
from engine.ports.command import Command

GUARDIAN = 'AlliedAntiVehicleVehicleTech1'
HOME = (1400.0, 2400.0)


@pytest.mark.parametrize(('stance', 'returns'), [(0, True), (1, False)], ids=['guard', 'aggressive'])
def test_guard_area_uses_idle_scan_and_stance_after_quarry_dies(stance, returns):
    s = simsmall.small_world([('tank', GUARDIAN, 'Player_1', *HOME),
                              ('foe', GUARDIAN, 'Soviet_1', 1620.0, 2400.0)], model=False)
    tank, foe = s.bodies['tank'], s.bodies['foe']
    tank.angle = 0.0
    foe.status.add('NO_ATTACK')
    s.reveal_all = True
    s.areas['post'] = [(1380, 2380), (1420, 2380), (1420, 2420), (1380, 2420)]
    assert s.commands.do(Command('stance', units=('tank',), args=(('stance', stance),))) == (True, '')
    assert s.commands.do(Command('guard', units=('tank',), place='post')) == (True, '')
    assert tank.mode == 'idle' and not tank.path  # already inside the area
    s.advance(1)
    assert s.frame_now() == 8 and tank.chase is None and (tank.x, tank.y) == HOME
    s.advance(1)
    # frame 8 is the first coarse scan after the opening-frame idle gate.
    # 220 is beyond cannon reach but within sight plus the target's radius.
    assert s.frame_now() == 15 and tank.chase is foe and tank.home == HOME
    assert tank.x > HOME[0]

    s.world.kill(foe, '测试')
    simorder.fight(s, simorder.Peers(s))
    assert tank.chase is None
    if returns:
        assert (tank.home, tank.dest, tank.auto_to) == (HOME, HOME, HOME) and tank.path
    else:
        assert tank.home is None and tank.dest == (foe.x, foe.y) and not tank.path


def test_idle_scan_counts_a_slots_other_lines():
    # A387 h_c: Tanya's held pistol cannot hit a tank; her slot's C4 line can, so idle she goes after one in sight
    s = simsmall.small_world([('tanya', 'AlliedCommandoTech1', 'Player_1', *HOME),
                              ('foe', 'SovietAntiVehicleVehicleTech1', 'Soviet_1', HOME[0] + 150, HOME[1])])
    tanya, foe = s.bodies['tanya'], s.bodies['foe']
    foe.status.add('NO_ATTACK')
    s.reveal_all = True
    s.advance(1)
    s.advance(1)                            # frame 15: the second scan after the opening-frame gate
    assert tanya.chase is foe and tanya.path
