"""A named attack after its target dies (without a team follow-up order)."""
import engine.testing.small as simsmall
from engine.ports.command import Command

GUARDIAN = 'AlliedAntiVehicleVehicleTech1'


def test_dead_named_goal_falls_back_to_the_nearest_target_on_the_next_scan(monkeypatch):
    s = simsmall.small_world([('tank', GUARDIAN, 'Player_1', 1400.0, 2400.0),
                              ('ordered', GUARDIAN, 'Soviet_1', 1570.0, 2400.0),
                              ('first', GUARDIAN, 'Soviet_1', 1400.0, 2280.0),
                              ('second', GUARDIAN, 'Soviet_1', 1400.0, 2520.0)], model=False)
    tank, ordered = s.bodies['tank'], s.bodies['ordered']
    for name in ('ordered', 'first', 'second'):
        s.bodies[name].status.add('NO_ATTACK')
    assert s.commands.do(Command('attack', units=('tank',), target='ordered')) == (True, '')
    picks = []
    deal = s.deal

    def record(dt):
        frame = s.frame_now() - 1
        picks.extend((frame, t.name) for t, _, a in s.firing if a is tank)
        deal(dt)
        if frame == 0:  # kill after the first frame's shot, within the first half-second tick
            s.destroy(ordered, '测试')

    monkeypatch.setattr(s, 'deal', record)
    s.advance(1)
    assert picks == [(frame, 'ordered') for frame in range(8)]  # cached aim, even though deal skips the dead body
    s.advance(1)
    # Second scan at frame 8. Both surviving foes are 120 away, so stable order
    # picks the first inserted. Movement clears the old goal, leaving auto-aim.
    assert picks[8:] == [(frame, 'first') for frame in range(8, 15)]
    assert tank.goal is None
