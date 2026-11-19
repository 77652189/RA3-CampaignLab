"""The command port (engine/ports/command.py; R3 13b): a command is names and numbers; a queued command is the script
event its line reads as (so moving a giver onto the port changes no timing); `do` gives the world what calling the
order directly gives; an unknown kind, and a kind with no route yet, are refused; nothing in a run reads the record
(`issued`: R2's condition for leaving it out of a snapshot). The givers' guard is tests/guards/test_ports.py."""
import ast
from pathlib import Path

import pytest

from test_plans import small  # noqa: F401,I001  (tests/ is on the path by its conftest; puts experimental/cnv on it)
import sim  # noqa: E402
import simsmall  # noqa: E402
from engine.ports.command import Command, Commands, ROUTED, command, event, text  # noqa: E402
from engine.ports.observe import Observe  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
APOC = 'SovietAntiVehicleVehicleTech3'
LINES = [Command('attack_move', units=('guardian',), place='approach 1'),
         Command('move', units=('名字含 -AlliedAnti',), place='@1200,-340'),
         Command('attack', units=('tank 2',), target='bunker'),
         Command('power', units=('engineer',), power='freeze', place='inside 1'),
         Command('capture', units=('engineer',), target='derrick'),
         Command('build', template='AlliedAntiInfantryInfantry', target='barracks'),
         Command('buy_science', args=(('science', 'SCIENCE_X'),))]


@pytest.mark.parametrize('cmd', LINES, ids=lambda c: c.kind)
def test_a_command_is_its_script_line(cmd):
    """event(cmd, at) is what parse_script makes of `at text(cmd)`, timed or waiting on a flag; and back."""
    assert sim.parse_script(f'95.5 {text(cmd)}') == [event(cmd, 95.5)]
    assert sim.parse_script(f'phase2+3 {text(cmd)}') == [event(cmd, ('@', 'phase2', 3.0))]
    assert command(event(cmd, 1.0), cmd.by) == cmd


def test_god_hand_lines_are_not_commands():
    for line in ('5 造 tank 在 inside 1', '5 血量 tank 50%', '5 旗标 go 1', '5 删除 tank', '5 占领 derrick'):
        (e,) = sim.parse_script(line)
        assert command(e) is None, line


def test_a_command_holds_names_and_numbers_only():
    s = simsmall.small_world([('a', APOC, 'Player_1', 0.0, 0.0)], model=False)
    with pytest.raises(TypeError):
        Command('attack', units=(s.bodies['a'],), target='b')
    with pytest.raises(TypeError):
        Command('move', units=('a',), args=(('then', print),))
    with pytest.raises(ValueError):
        Command('move', by='someone')
    Command('move', by='ai:Player_2', units=('a', 'b'), pos=(1.0, 2), args=(('on_grid', True), ('face', 1.57)))


def test_unknown_and_unrouted_kinds_are_refused():
    s = simsmall.small_world([('a', APOC, 'Player_1', 0.0, 0.0)], model=False)
    port = Commands(s)
    assert port.do(Command('teleport', units=('a',)))[0] is False
    ok, why = port.post(Command('hunt', units=('a',)), 5.0)
    assert not ok and 'no route' in why and not s.events
    assert set(ROUTED) < port.kinds() and len(port.kinds()) == 22
    assert [r[2] for r in port.issued()] == [False, False]


def test_post_queues_as_the_line_and_pending_keeps_the_order():
    s = simsmall.small_world([('a', APOC, 'Player_1', 0.0, 0.0)], model=False)
    port = Commands(s)
    port.post(LINES[0], 9.0)
    port.post(LINES[1], ('@', 'go', 2.0))
    port.post_line('3 造 tank 在 inside 1')
    port.post(LINES[2], 9.0)
    assert port.pending() == (sim.parse_script('3 造 tank 在 inside 1')[0], event(LINES[0], 9.0),
                              event(LINES[2], 9.0), event(LINES[1], ('@', 'go', 2.0)))
    assert [r[1].kind for r in port.issued()] == ['attack_move', 'move', 'attack']     # the 造 line is no command


def _pair():
    objs = [('a', APOC, 'Player_1', 0.0, 0.0), ('b', APOC, 'Player_1', 60.0, 0.0), ('foe', APOC, 'Player_2', 900.0, 0.0)]
    return simsmall.small_world(objs, model=False), simsmall.small_world(objs, model=False)


def _states(s):
    obs = Observe(s)
    return {b.name: obs.state(b) for b in obs.things()}


@pytest.mark.parametrize('kind', ['attack_move', 'move', 'attack'])
def test_do_gives_the_world_what_the_order_call_gives(kind):
    port_world, direct = _pair()
    if kind == 'attack':
        cmd = Command('attack', units=('a',), target='foe', force=True)     # the small world has no foes
        direct.order_attack(direct.bodies['a'], 'foe', True)
    elif kind == 'move':
        cmd = Command('move', units=('a',), place='@400,300')
        direct.order_group([direct.bodies['a']], '@400,300', False, on_grid=True)
    else:
        cmd = Command('attack_move', units=('a',), place='@400,300')
        direct.order_move(direct.bodies['a'], '@400,300', True, on_grid=True)
    assert Commands(port_world).do(cmd) == (True, '')
    idle, _ = _pair()
    for s in (port_world, direct, idle):
        for _ in range(30):
            s.step()
            s.t = round(s.t + sim.DT, 3)
    assert _states(port_world) == _states(direct)
    assert _states(port_world)['a'] != _states(idle)['a']          # the order did something


def test_a_refused_build_says_why():
    s, _ = _pair()
    ok, why = Commands(s).do(Command('build', template=APOC, target='nowhere'))
    assert not ok and why == '找不到工厂 nowhere'


def test_nothing_in_a_run_reads_the_record():
    """`issued()` is written, never read, outside the port and the tests (R2 13a: so a snapshot leaves it out)."""
    readers = []
    for p in sorted((ROOT / 'experimental').rglob('*.py')):
        if p.name == 'command.py' or 'archive' in p.parts:
            continue
        for n in ast.walk(ast.parse(p.read_text(encoding='utf-8'))):
            if isinstance(n, ast.Attribute) and n.attr in ('issued', '_issued'):
                readers.append((p.name, n.lineno))
    assert readers == []
