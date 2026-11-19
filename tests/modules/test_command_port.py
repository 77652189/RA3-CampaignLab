"""The command port (engine/ports/command.py; R3 13b): a command is names and numbers; a queued command is the script
event its line reads as (so moving a giver onto the port changes no timing); `do` gives the world what calling the
order directly gives; an unknown kind, and a kind with no route yet, are refused. The givers' guard is
tests/guards/test_ports.py."""
from pathlib import Path

import pytest

from test_plans import small  # noqa: F401,I001  (tests/ is on the path by its conftest; puts experimental/cnv on it)
import sim  # noqa: E402
import simsmall  # noqa: E402
from engine.ports import command as command_port  # noqa: E402
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
         Command('buy_science', args=(('science', 'SCIENCE_X'),)),
         # the fields only some lines carry (review 11-19 d #3): a forced attack, a build / science in a player's name
         Command('attack', units=('tank 2',), target='名字含 bunker', force=True),
         Command('build', player='Player_2', template='AlliedAntiInfantryInfantry', target='barracks 2'),
         Command('buy_science', player='Player_2', args=(('science', 'SCIENCE_X'),))]


def _port():
    return Commands(simsmall.small_world([('a', APOC, 'Player_1', 0.0, 0.0)], model=False))


@pytest.mark.parametrize('cmd', LINES, ids=lambda c: c.kind)
def test_a_command_is_its_script_line(cmd):
    """event(cmd, at) is what parse_script makes of `at text(cmd)`, timed or waiting on a flag; and back."""
    assert sim.parse_script(f'95.5 {text(cmd)}') == [event(cmd, 95.5)]
    assert sim.parse_script(f'phase2+3 {text(cmd)}') == [event(cmd, ('@', 'phase2', 3.0))]
    assert command(event(cmd, 1.0), cmd.by) == cmd


@pytest.mark.parametrize('cmd', [Command('move', units=('a',), place='@1,1', force=True),
                                 Command('move', player='Player_2', units=('a',), place='@1,1'),
                                 Command('move', units=('a',), pos=(1.0, 1.0)),
                                 Command('attack', units=('a',), target='b', args=(('objects', True),))],
                         ids=['force', 'player', 'pos', 'args'])
def test_post_refuses_what_its_line_cannot_carry(cmd):
    """Nothing is queued short (review 11-19 d #3): a field the kind's line has no word for is a refusal."""
    port = _port()
    ok, why = port.post(cmd, 1.0)
    assert not ok and 'carries' in why and port.pending() == ()


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
    ok, why = port.post(Command('sell', units=('a',)), 5.0)
    assert not ok and 'no route' in why and not s.events
    ok, why = port.post(Command('hunt', units=('a',)), 5.0)          # routed, but no script line carries it
    assert not ok and 'not queued' in why and not s.events
    assert set(ROUTED) < port.kinds() and len(port.kinds()) == 23
    assert [r[2] for r in port.issued()] == [False, False, False]


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
    port.drop_pending()                                     # a play handing the run over: nothing still to come
    assert port.pending() == () and not s.events and not s.anchored


def test_post_line_gives_what_it_queued_and_refuses_a_run_switch():
    s = simsmall.small_world([('a', APOC, 'Player_1', 0.0, 0.0)], model=False)
    port = Commands(s)
    assert port.post_line('4 走 a 去 @10,10') == tuple(sim.parse_script('4 走 a 去 @10,10'))
    with pytest.raises(command_port.RunSwitch):
        port.post_line('不打')
    with pytest.raises(ValueError):
        port.post_line('4 乱写 a')
    assert port.pending() == tuple(sim.parse_script('4 走 a 去 @10,10'))
    # each check before anything is queued (review 11-19 d #6): a line holding a run switch, or more than one event
    # where one is asked, queues none of it
    for line, one in (('0 走 a 去 @500,300; 不打', False), ('0 走 a 去 @500,300; 0 派 a 去 @800,300', True)):
        with pytest.raises(ValueError):
            port.post_line(line, one=one)
        assert port.pending() == tuple(sim.parse_script('4 走 a 去 @10,10')), line
    assert len(port.post_line('0 走 a 去 @500,300; 0 派 a 去 @800,300')) == 2


def _run_frames(s, n=1):
    for _ in range(n):
        s.step()
        s.t = round(s.t + sim.DT, 3)


def test_a_queued_forced_attack_is_the_one_given_now():
    """A forced attack queued reaches the unit as the same order given now (review 11-19 d #3: it went in as a plain
    attack, and an ally is no plain attack's target)."""
    goals = []
    for route in ('post', 'do'):
        s = simsmall.small_world([('a', APOC, 'Player_1', 0.0, 0.0), ('ally', APOC, 'Player_1', 300.0, 0.0)],
                                 model=False)
        cmd = Command('attack', units=('a',), target='ally', force=True)
        assert (s.commands.post(cmd, 0.0) if route == 'post' else s.commands.do(cmd)) == (True, '')
        _run_frames(s)
        goals.append(None if s.bodies['a'].goal is None else s.bodies['a'].goal.name)
    assert goals == ['ally', 'ally']
    assert [r[1] for r in s.commands.issued()][-1].force


def test_a_queued_command_is_the_one_given():
    """post queues the command as given, not its line read back: an unnamed object's `#0` (a comment in a line)
    still gets its order (simui replays events, not lines)."""
    s = simsmall.small_world([('a', APOC, 'Player_1', 300.0, 300.0)], model=False)
    cmd = Command('capture', units=('a',), target='#0')
    assert s.commands.post(cmd, 0.0) == (True, '') and list(s.events) == [event(cmd, 0.0)]
    assert command(s.events[0], 'player') == cmd


def _autoplay():
    import importlib.util
    import sys
    spec = importlib.util.spec_from_file_location('autoplay', ROOT / 'experimental' / 'autoplay' / 'autoplay.py')
    if 'autoplay' not in sys.modules:
        mod = importlib.util.module_from_spec(spec)
        sys.modules['autoplay'] = mod
        spec.loader.exec_module(mod)
    return sys.modules['autoplay']


def test_a_run_line_reads_as_its_replay_does():
    """autoplay's Orders queue the line they record (review 11-19 d #4): unit `a` told to use `x y` reads, run and
    replay alike, as `a x` told to use `y`; and a push that does not read as one event queues nothing (#6)."""
    from types import SimpleNamespace
    ap = _autoplay()
    s = simsmall.small_world([('a', APOC, 'Player_1', 300.0, 300.0), ('a x', APOC, 'Player_1', 450.0, 300.0)],
                             model=False)
    _, out = ap.attach(s, SimpleNamespace(escort=()))
    asked = []
    s.order_power = lambda b, power, pos: asked.append((b.name, power)) or (True, None)
    out.power(s.bodies['a'], 'x y', (800, 300))
    assert list(s.events) == sim.parse_script('\n'.join(out.lines))
    _run_frames(s)
    assert asked == [('a x', 'y')]
    for line in ('走 a 去 @500,300; 不打', '走 a 去 @500,300; 0 派 a 去 @800,300'):
        with pytest.raises(ValueError):
            out.push(0, line)
    assert not s.events and len(out.lines) == 1


def test_do_power_answers_the_worlds_refusal():
    """`do` of a power the unit has not: the world refuses (order_power's (False, why)) and so does the port (review
    11-19 d #7: it recorded a success)."""
    s = simsmall.small_world([('a', APOC, 'Player_1', 300.0, 300.0)], model=False)
    cmd = Command('power', units=('a',), power='Command_ReviewMissing', place='@500,300')
    want = s.order_power(s.bodies['a'], cmd.power, (500.0, 300.0))
    assert want[0] is False
    assert s.commands.do(cmd) == want
    assert s.commands.issued()[-1][2:] == want


def _world():
    objs = [('a', APOC, 'Player_1', 0.0, 0.0), ('b', APOC, 'Player_1', 60.0, 0.0), ('foe', APOC, 'Player_2', 900.0, 0.0)]
    return simsmall.small_world(objs, model=False)


def _pair():
    return _world(), _world()


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
    idle = _world()
    for s in (port_world, direct, idle):
        for _ in range(30):
            s.step()
            s.t = round(s.t + sim.DT, 3)
    assert _states(port_world) == _states(direct)
    assert _states(port_world)['a'] != _states(idle)['a']          # the order did something


OBJ = (('objects', True),)
SCRIPT_ORDERS = {      # a map script's order (R3 13d-1: simact_order) -> what the action called before
    'move each': (Command('move', 'script', units=('a',), place='@400,300', args=OBJ + (('on_grid', True),)),
                  lambda s, a, b: s.order_move(a, '@400,300', False, on_grid=True)),
    'attack_move group': (Command('attack_move', 'script', units=('a', 'b'), pos=(400.0, 300.0),
                                  args=OBJ + (('group', True),)),
                          lambda s, a, b: s.order_group([a, b], (400.0, 300.0), True)),
    'attack team': (Command('attack', 'script', units=('a',), target='foe', force=True, args=OBJ + (('team', 'T'),)),
                    lambda s, a, b: (s.order_attack(a, 'foe', True), s.team_targets.__setitem__(a.serial, 'T'))),
    'missing unit': (Command('attack', 'script', units=('nobody',), target='foe', args=OBJ),
                     lambda s, a, b: s.order_attack(None, 'foe')),
    'stop': (Command('stop', 'script', units=('a',), args=OBJ), lambda s, a, b: s.order_stop(a)),
    'idle': (Command('idle', 'script', units=('a', 'b'), args=OBJ), lambda s, a, b: (s.stand(a), s.stand(b))),
    'flee': (Command('flee', 'script', units=('a',), args=OBJ), lambda s, a, b: s.flee_start(a)),
    'auto_acquire': (Command('auto_acquire', 'script', units=('a',), args=OBJ + (('on', True),)),
                     lambda s, a, b: setattr(a, 'ai_acquire', True)),
    'stance': (Command('stance', 'script', units=('a',), args=OBJ + (('stance', 3),)),
               lambda s, a, b: (setattr(a, 'hold_paused', isinstance(a.goal, type(a))), setattr(a, 'hold_fire', True),
                                setattr(a, 'stance', 3))),
    # the proxy player's clicks (R3 13e: simproxy.SimWorld.issue): a selection's move drops their targets first
    'proxy move': (Command('attack_move', 'proxy', units=('a', 'b'), pos=(400.0, 300.0),
                           args=OBJ + (('group', True), ('on_grid', True), ('drop_target', True))),
                   lambda s, a, b: (setattr(a, 'goal', None), setattr(b, 'goal', None),
                                    s.order_group([a, b], (400.0, 300.0), True, on_grid=True))),
}


def test_the_proxy_players_build_and_power_answer_the_world():
    """A sidebar build (no factory named) and a ground power / transform: refused as the world refuses -- a power only
    when every unit's is, why their refusals sorted once each (R3 13e)."""
    s, direct = _pair()
    want = direct.order_build('Player_1', APOC)
    assert s.commands.do(Command('build', 'proxy', player='Player_1', template=APOC))[0] is want
    assert want is False                                     # the small world has no factory
    whys = sorted({direct.order_power(direct.bodies[n], 'Command_ReviewMissing', (500.0, 0.0))[1] for n in 'ab'})
    cmd = Command('power', 'proxy', units=('a', 'b'), power='Command_ReviewMissing', pos=(500.0, 0.0),
                  args=OBJ + (('via', 'click'),))
    assert s.commands.do(cmd) == (False, ', '.join(whys))
    want = sorted({direct.order_transform(direct.bodies[n], 'SpecialPower_JAIV_Transform')[1] for n in 'ab'})
    cmd = Command('power', 'proxy', units=('a', 'b'), power='SpecialPower_JAIV_Transform',
                  args=OBJ + (('via', 'transform'),))
    assert s.commands.do(cmd) == (False, ', '.join(want))
    with pytest.raises(ValueError):                          # a line names its factory: a sidebar build is do's only
        text(Command('build', template=APOC))


@pytest.mark.parametrize('case', sorted(SCRIPT_ORDERS))
def test_a_script_order_gives_what_the_action_called(case):
    cmd, direct_call = SCRIPT_ORDERS[case]
    port_world, direct = _pair()
    for s in (port_world, direct):
        s.order_move(s.bodies['a'], '@200,500', False)         # an order going on: the new one replaces it
    direct_call(direct, direct.bodies['a'], direct.bodies['b'])
    assert Commands(port_world).do(cmd) == (True, '')
    assert _states(port_world) == _states(direct)
    assert port_world.team_targets == direct.team_targets and port_world.used == direct.used
    for s in (port_world, direct):
        for _ in range(30):
            s.step()
            s.t = round(s.t + sim.DT, 3)
    assert _states(port_world) == _states(direct)


@pytest.mark.parametrize('kind', ['face', 'attack_ground'])
def test_a_script_order_at_a_place(kind):
    port_world, direct = _pair()
    a = direct.bodies['a']
    direct.stand(a)
    if kind == 'face':
        a.face = __import__('math').atan2(300.0 - a.y, 400.0 - a.x)
    else:
        a.ground_fire = direct.point('@400,300')
    Commands(port_world).do(Command(kind, 'script', units=('a',), place='@400,300', args=OBJ))
    assert _states(port_world) == _states(direct)
    assert (port_world.bodies['a'].face, port_world.bodies['a'].ground_fire) == (a.face, a.ground_fire)


def test_a_script_line_order_is_the_runs_port_do():
    """Sim.happen gives a line's player order through the run's one port (R3 13c-2): the record holds it, done, as the
    player's; a god's-hand line (血量) is no command and leaves no record."""
    s = _world()
    s.happen((0.0, '走', 'a', '@400,300'))
    s.happen((0.0, '血量', 'b', 0.5))
    s.happen((0.0, '生产', APOC, 'nowhere'))
    assert [(r[1], r[2], r[3]) for r in s.commands.issued()] == [
        (Command('move', units=('a',), place='@400,300'), True, 'done'),
        (Command('build', template=APOC, target='nowhere'), False, '找不到工厂 nowhere')]


def test_a_refused_build_says_why():
    s = _world()
    ok, why = Commands(s).do(Command('build', template=APOC, target='nowhere'))
    assert not ok and why == '找不到工厂 nowhere'
