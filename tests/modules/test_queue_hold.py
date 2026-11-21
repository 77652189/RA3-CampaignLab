"""Production's rules no bench reading test holds (each kept by a mutation: R3 family close): the player's unit
construction gate (the per-template one is engine_production g's), put's clear-first, the replacement 6 frames on."""
import pytest

from test_plans import small  # noqa: F401,I001  (puts experimental/cnv on the path)
from engine.ports.command import Command  # noqa: E402
from engine.testing.small import small_world  # noqa: E402

PLAYER = 'Player_1'
ENGINEER = 'AlliedEngineer'


def test_the_players_gate_keeps_the_paid_head_and_waiting_jobs_until_reenabled():
    s = small_world([('factory', 'AlliedBarracks', PLAYER, 600, 600),
                     ('plant', 'AlliedPowerPlant', PLAYER, 900, 600)], model=False)
    f = s.bodies['factory']
    s.money[PLAYER] = 1000
    assert s.commands.do(Command('build', player=PLAYER, template=ENGINEER)) == (True, '')
    s.production.due(1)
    head, = s.production.queues[f.serial]
    assert head['paid'] == 4 and s.money[PLAYER] == 996  # ceil(500/150)
    s.act('PLAYER_DISABLE_UNIT_CONSTRUCTION', [PLAYER], None)
    s.act('NAMED_USE_COMMANDBUTTON_ABILITY', [f.name, 'Command_ConstructAlliedEngineer'], None)
    waiting = s.production.queues[f.serial][1]
    s.production.due(20)
    assert s.production.queues[f.serial] == [head, waiting]
    assert head['progress'] == pytest.approx(100 / 150) and head['paid'] == 4 and s.money[PLAYER] == 996
    s.act('PLAYER_ENABLE_UNIT_CONSTRUCTION', [PLAYER], None)
    s.production.due(21)
    assert head['progress'] == pytest.approx(200 / 150)
    assert head['paid'] == 7 and s.money[PLAYER] == 993  # ceil(2*500/150), with the original $4 still paid
    assert waiting['progress'] == waiting['paid'] == 0


def test_put_clears_first_so_the_factory_goes_last_and_none_leaves_no_queue():
    p = small_world(model=False).production
    p.queue(1, {'a': 1})
    p.queue(2, {'b': 1})
    p.put(1, [{'c': 1}])
    assert list(p.queues.items()) == [(2, [{'b': 1}]), (1, [{'c': 1}])]   # due runs factories in this order
    p.put(2, [])
    assert list(p.queues) == [1]


def test_a_replacement_lands_6_frames_after_the_builder_got_there():
    s = small_world()
    mcv = s.add('mcv', 'AlliedMCV', PLAYER, 300.0, 300.0)
    mcv.replace, mcv.building = True, ('AlliedConstructionYard', (300.0, 300.0), 50.0)
    assert s.production.at_site(mcv, 0.0)
    got = s.frame_now()
    s.production.put_down(got + 5)
    assert s.bodies['mcv'] is mcv
    s.production.put_down(got + 6)
    assert s.bodies['mcv'].template == 'AlliedConstructionYard'
