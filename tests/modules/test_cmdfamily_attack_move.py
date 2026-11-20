"""Coarse movement queues aim at the frame where the unit crosses weapon range."""
import math

import pytest

import simsmall
from engine.ports.command import Command

GUARDIAN = 'AlliedAntiVehicleVehicleTech1'


def test_attack_move_aims_on_the_first_frame_inside_range(monkeypatch):
    s = simsmall.small_world([('tank', GUARDIAN, 'Player_1', 1400.0, 2400.0),
                              ('foe', GUARDIAN, 'Soviet_1', 1625.0, 2400.0)], model=False)
    tank, foe = s.bodies['tank'], s.bodies['foe']
    foe.status.add('NO_ATTACK')
    s.reveal_all = True
    tank.angle = 0.0
    assert s.commands.do(Command('attack_move', units=('tank',), pos=(1850.0, 2400.0),
                                 args=(('objects', True),))) == (True, '')
    point = tank.dest
    # The foe starts outside chase sight. The straight move crosses the two-circle
    # firing boundary, nudged 1e-6 inside by range_entry. Deal follows aim on
    # that frame, after scripts advance the public clock by one.
    assert 225.0 - foe.radius > tank.sight
    centre_reach = 150.0 - 5.0 + tank.radius + foe.radius  # Guardian cannon AttackRange less UNDERSIZE
    crossing = (225.0 - centre_reach + 1e-6) / tank.speed
    first = math.ceil(crossing * s.fps)
    assert first == 7
    aimed = []
    deal = s.deal

    def record(dt):
        aimed.append((s.frame_now() - 1, [target.name for target, _, a in s.firing if a is tank]))
        deal(dt)

    monkeypatch.setattr(s, 'deal', record)
    s.advance(1)
    # Frames 0..7 fall below 0.5 s at 15 Hz.
    assert aimed == [(frame, [] if frame < first else ['foe']) for frame in range(8)]
    assert tank.x == pytest.approx(foe.x - centre_reach + 1e-6)
    assert (tank.dest, tank.engaged, tank.chase, tank.goal) == (point, True, None, None)
    assert tank.path  # interrupted the walk without replacing its destination
