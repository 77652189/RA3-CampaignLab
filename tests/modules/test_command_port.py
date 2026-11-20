"""The command port (engine/ports/command.py; R3 13b): a command is names and numbers; a queued command runs when its
script line would (so moving a giver onto the port changes no timing), as itself (review 11-19 i #1); `do` gives the world what calling the
order directly gives; an unknown kind, and a kind with no route yet, are refused. The givers' guard is
tests/guards/test_ports.py."""
import gc
import weakref
from pathlib import Path

import pytest

from test_plans import small  # noqa: F401,I001  (tests/ is on the path by its conftest; puts experimental/cnv on it)
import sim  # noqa: E402
import simsmall  # noqa: E402
from engine.ports import command as command_port  # noqa: E402
from engine.ports.command import Command, Commands, ROUTED, command, event, queued, text  # noqa: E402
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
    assert port.pending() == (sim.parse_script('3 造 tank 在 inside 1')[0], queued(LINES[0], 9.0),
                              queued(LINES[2], 9.0), queued(LINES[1], ('@', 'go', 2.0)))
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
    assert s.commands.post(cmd, 0.0) == (True, '') and list(s.events) == [queued(cmd, 0.0)]
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


def _act(s, action, *a):
    from types import SimpleNamespace
    s.executor.action(action, list(a), SimpleNamespace(name='probe'))


def _team_world():
    """Team T: lead, next; outsider (Player_2) a reference named `lead` points at (review 11-19 f #1)."""
    s = simsmall.small_world([('lead', APOC, 'Player_1', 0.0, 0.0), ('next', APOC, 'Player_1', 60.0, 0.0),
                              ('outsider', APOC, 'Player_2', 900.0, 0.0)], model=False)
    for n in ('lead', 'next'):
        s.bodies[n].team = 'T'
    s.active.add('T')
    s.refs['lead'] = s.bodies['outsider']
    return s


def test_a_team_order_reaches_the_members_not_a_reference_of_their_name():
    """The units an action picked go to the port by serial (review 11-19 f #1: by name, the reference `lead` took the
    member's place); a unit the script names still reads through the reference."""
    s = _team_world()
    _act(s, 'TEAM_ALLOW_AI_AUTOACQUIRE', 'T', '1')
    _act(s, 'TEAM_STOP', 'T')
    assert [s.bodies[n].ai_acquire for n in ('lead', 'next', 'outsider')] == [True, True, False]
    stops = [r[1] for r in s.commands.issued() if r[1].kind == 'stop']
    assert stops[-1].units == (s.bodies['lead'].serial, s.bodies['next'].serial)
    _act(s, 'NAMED_STOP', 'lead')
    assert s.commands.issued()[-1][1].units == ('lead',)
    assert s.commands._units(s.commands.issued()[-1][1]) == [s.bodies['outsider']]


def test_an_empty_team_name_keeps_the_follow_up_attack():
    """TEAM_ATTACK_TEAM on the default team ('') registers the next-target look-up (review 11-19 f #2: '' was read as
    no team)."""
    s = _world()
    a = s.bodies['a']
    cmd = Command('attack', 'script', units=(a.serial,), target='foe', force=True,
                  args=(('objects', 'serial'), ('team', '')))
    assert s.commands.do(cmd) == (True, '') and s.team_targets[a.serial] == ''


def test_an_empty_selection_reads_no_flag():
    """A team / player with nobody to set reads no flag (review 11-19 f #3: a bad flag raised before any unit)."""
    s = _world()
    _act(s, 'TEAM_ALLOW_AI_AUTOACQUIRE', 'nobody', '')
    _act(s, 'PLAYER_ALLOW_AI_AUTOACQUIRE', 'Player_9', '')
    assert not s.commands.issued()


def test_a_turned_down_press_or_missing_address_is_refused():
    """The record says what the world did (review 11-19 f #4): a press at a target gone, a map capture nobody goes on,
    a dead unit's power; a route that needs its object refuses a missing one before the order call (f #5)."""
    s = _world()
    press = Command('power', 'script', units=('a',), target='gone', args=OBJ + (('via', 'wfire'), ('button', 'Command_X')))
    assert s.commands.do(press)[0] is False
    assert s.commands.do(Command('capture', 'script', units=('missing',), target='foe', args=OBJ))[0] is False
    s.bodies['b'].alive = False
    assert s.commands.do(Command('power', units=('b',), power='Command_X', place='@500,0'))[0] is False
    assert s.commands.do(Command('unpack', 'script', units=('missing',), place='@500,0',
                                 args=OBJ + (('button', 'Command_X'),))) == (False, 'no unit to unpack')
    assert s.commands.do(Command('build', 'script', player='Player_1', template=APOC, target='missing',
                                 args=OBJ + (('press', True),))) == (False, '找不到工厂 missing')


def test_a_script_toggle_and_pack_do_what_the_button_does():
    """Behaviour the givers' static guard cannot see (review 11-19 f, guard mutations): a toggle the world steps is
    noted as switched (its answer read the right way round), and a yard's pack puts the MCV in its place the same frame
    (the replacement, not a new build)."""
    s = simsmall.small_world([('gi', 'AlliedAntiInfantryInfantry', 'Player_1', 0.0, 0.0),
                              ('yard', 'AlliedConstructionYard', 'Player_1', 600.0, 600.0)], model=False)
    _act(s, 'NAMED_USE_COMMANDBUTTON_ABILITY', 'gi', 'Command_ToggleRiotShieldSpecialPower')
    assert s.commands.issued()[-1][2] is True
    assert s.log[-1][1:] == ('技能', 'gi 按 Command_ToggleRiotShieldSpecialPower 切换状态')
    yard = s.bodies['yard']
    _act(s, 'NAMED_USE_COMMANDBUTTON_ABILITY', 'yard', 'Command_PackAlliedMCV')
    assert s.bodies['yard'].template == 'AlliedMCV' and not yard.alive


def test_a_name_ending_in_a_tail_reads_as_the_name():
    """A line's tail `强制` / `由 P` is the name's own end when the whole is a name here (review 11-19 g #2: objects
    `enemy 强制` and `f 由 Player_2` read as a forced attack on `enemy` and a build at `f` in Player_2's name); a
    command whose line would read as another here is neither written nor posted."""
    s = simsmall.small_world([('a', APOC, 'Player_1', 0.0, 0.0), ('enemy', APOC, 'Player_1', 300.0, 0.0),
                              ('enemy 强制', APOC, 'Player_2', 600.0, 0.0), ('f', APOC, 'Player_1', 0.0, 300.0),
                              ('f 由 Player_2', APOC, 'Player_1', 300.0, 300.0)], model=False)
    asked = []
    s.order_build = lambda player, tmpl, factory=None, press=False: asked.append((player, factory.name)) or True
    s.commands.post_line('0 攻击 a 打 enemy 强制')
    s.commands.post_line('0 生产 AlliedAntiInfantryInfantry 在 f 由 Player_2')
    _run_frames(s)
    done = [r[1] for r in s.commands.issued() if r[3] != 'posted']
    assert done == [Command('attack', units=('a',), target='enemy 强制'),
                    Command('build', template='AlliedAntiInfantryInfantry', target='f 由 Player_2')]
    # not forced: no goal (the small world has no foes; forced, `a` went for its own side's `enemy`)
    assert s.bodies['a'].goal is None and asked == [('Player_1', 'f 由 Player_2')]
    for cmd in (Command('attack', units=('a',), target='enemy 强制'), Command('attack', units=('a',), target='a', force=True)):
        assert s.commands.line(cmd) == text(cmd)
    forced = Command('attack', units=('a',), target='enemy', force=True)
    with pytest.raises(ValueError):
        s.commands.line(forced)             # no line says it here (autoplay writes none) -- posted, it is itself:
    assert s.commands.post(forced, 1.0) == (True, '') and s.events[-1] == queued(forced, 1.0)


def _tails_world():
    s = simsmall.small_world([('a', APOC, 'Player_1', 0.0, 0.0), ('enemy', APOC, 'Player_1', 300.0, 0.0),
                              ('f', APOC, 'Player_1', 0.0, 300.0)], model=False)
    asked = []
    s.order_build = lambda player, tmpl, factory=None, press=False: asked.append((player, factory.name)) or True
    return s, asked


def test_a_posted_command_is_not_read_again_when_it_runs():
    """A posted command runs as posted though a name its line would read as appears meanwhile (review 11-19 i #1: a
    forced attack on `enemy` went to a new `enemy 强制`, a build in Player_2's name at `f` to a new `f 由 Player_2`
    in Player_1's); it is noted as its line's event."""
    s, asked = _tails_world()
    attack = Command('attack', units=('a',), target='enemy', force=True)
    build = Command('build', player='Player_2', template='AlliedAntiInfantryInfantry', target='f')
    assert s.commands.post(attack, 0.0) == (True, '') and s.commands.post(build, 0.0) == (True, '')
    for name, x in (('enemy 强制', 600.0), ('f 由 Player_2', 900.0)):
        s.add(name, APOC, 'Player_2', x, 0.0)
    _run_frames(s)
    done = [r[1:3] for r in s.commands.issued() if r[3] != 'posted']
    assert done == [(attack, True), (build, True)]
    assert s.bodies['a'].goal is s.bodies['enemy'] and asked == [('Player_2', 'f')]
    notes = [x for _, k, x in s.log if k == '剧本']
    assert '攻击 a enemy 强制' in notes and '生产 AlliedAntiInfantryInfantry f 由 Player_2' in notes


def test_a_whole_name_is_read_as_written():
    """The whole word group, its spaces as written, is the name when the world has it (review 11-19 i #4: `enemy  强制`
    with two spaces read as a forced attack on `enemy`); not a name: its tail, the rest stripped."""
    s, _ = _tails_world()
    s.add('enemy  强制', APOC, 'Player_2', 600.0, 0.0)
    (e,) = sim.parse_script('0 攻击 a 打 enemy  强制')
    assert s.commands.command(e) == Command('attack', 'script', units=('a',), target='enemy  强制')
    (e,) = sim.parse_script('0 攻击 a 打 f  强制')
    assert s.commands.command(e) == Command('attack', 'script', units=('a',), target='f', force=True)
    (e,) = sim.parse_script('0 生产 X 在 f  由  Player_2')
    assert s.commands.command(e) == Command('build', 'script', player='Player_2', template='X', target='f')


def test_a_line_capture_refused_by_the_world_is_refused():
    """A line's capture the order call turns down (a tank cannot capture) is no success (review 11-19 i #3)."""
    s = simsmall.small_world([('tank', APOC, 'Player_1', 0.0, 0.0),
                              ('building', 'AlliedBarracks', 'Player_2', 300.0, 0.0)], model=False)
    s.commands.post_line('0 占领 tank 进 building')
    _run_frames(s)
    (rec,) = [r for r in s.commands.issued() if r[3] != 'posted']
    assert rec[2] is False and s.bodies['tank'].goal is None and s.bodies['building'].owner == 'Player_2'


def test_a_team_button_presses_its_members_not_a_reference_of_their_name():
    """TEAM_USE_COMMANDBUTTON_ABILITY gives the button to the members it picked (review 11-19 i #2: a reference `lead`
    pointing at another player's Peacekeeper took lead's press)."""
    import simact_ability
    pk = 'AlliedAntiInfantryInfantry'
    s = simsmall.small_world([('lead', pk, 'Player_1', 0.0, 0.0), ('other', pk, 'Player_2', 300.0, 0.0)],
                             model=False)
    s.bodies['lead'].team = 'T'
    s.refs['lead'] = s.bodies['other']
    s.members = lambda team: [s.bodies['lead']] if team == 'T' else []
    simact_ability.team_use_commandbutton_ability(s, 'TEAM_USE_COMMANDBUTTON_ABILITY',
                                                  ['T', 'Command_ToggleRiotShieldSpecialPower'], None)
    rec = s.commands.issued()[-1]
    assert rec[1].units == (s.bodies['lead'].serial,) and rec[1].arg('objects') == 'serial' and rec[2] is True
    assert 'GENERIC_TOGGLE_STATE' in s.bodies['lead'].status and 'GENERIC_TOGGLE_STATE' not in s.bodies['other'].status


def test_the_proxy_players_click_reaches_his_units_not_a_reference_of_their_name():
    """simproxy.SimWorld.issue gives the units it picked (alive, his) by serial (review 11-19 h #1: by name, a script
    reference `a` pointing at an enemy took a's move; the attack and the transform went astray the same way)."""
    import simproxy
    from types import SimpleNamespace
    s = simsmall.small_world([('a', APOC, 'Player_1', 1250.0, 2500.0), ('b', APOC, 'Player_1', 1300.0, 2500.0),
                              ('enemy', APOC, 'Player_2', 1350.0, 2500.0), ('t', APOC, 'Player_2', 1600.0, 2500.0)],
                             model=False)
    s.refs['a'] = s.bodies['enemy']
    w = object.__new__(simproxy.SimWorld)
    w.sim = w.world = s
    w.peers, w.me, w.refused = simproxy.Peers(s), 'Player_1', []
    w.things = {i: s.bodies[n] for i, n in {1: 'a', 2: 'b', 3: 'enemy', 4: 't'}.items()}
    w.control = lambda: True
    order = SimpleNamespace(kind='move', units=(1, 2, 3, 9), pos=(1450.0, 2700.0), target=None, power='', template='')
    assert w.issue(order)
    issued = s.commands.issued()[-1][1]
    assert issued.units == (s.bodies['a'].serial, s.bodies['b'].serial) and issued.arg('objects') == 'serial'
    assert s.bodies['a'].move_to is not None and s.bodies['enemy'].move_to is None
    assert w.issue(SimpleNamespace(kind='attack', units=(1, 2), target=4, pos=None, power='', template=''))
    assert s.commands.issued()[-1][1].units == (s.bodies['a'].serial, s.bodies['b'].serial)


def _proxy(objs):
    import simproxy
    s = simsmall.small_world(objs, model=False)
    s.relations[('Player_1', 'Player_2')] = s.relations[('Player_2', 'Player_1')] = 'Enemy'
    w = object.__new__(simproxy.SimWorld)
    w.sim = w.world = s
    w.peers, w.me, w.refused = simproxy.Peers(s), 'Player_1', []
    w.ids, w.names, w.things = {}, {}, weakref.WeakValueDictionary()
    w.control = lambda: True
    return s, w


def test_the_proxy_players_attack_reaches_the_target_he_clicked():
    """The clicked target goes to the port by serial (review 11-19 j #1: by name, a reference `target` pointing at
    another enemy took the goal, one pointing at his own unit turned the attack down -- the proxy still said yes)."""
    from types import SimpleNamespace
    for other in ('other', 'same'):
        s, w = _proxy([('same', APOC, 'Player_1', 1250.0, 2500.0), ('target', APOC, 'Player_2', 1400.0, 2500.0),
                       ('other', APOC, 'Player_2', 1600.0, 2500.0)])
        me, t = w._id(s.bodies['same']), w._id(s.bodies['target'])
        s.refs['target'] = s.bodies[other]
        assert w.issue(SimpleNamespace(kind='attack', units=(me,), target=t, pos=None, power='', template=''))
        assert s.bodies['same'].goal is s.bodies['target'], other


def test_an_old_proxy_id_is_not_a_new_object_of_its_name():
    """An id is its object's (review 11-19 j #2: ids were per name, so the id of a deleted `same` moved, attacked and
    transformed the new `same` made in its place, and the new one went on under the old id)."""
    from types import SimpleNamespace
    s, w = _proxy([('same', APOC, 'Player_1', 1250.0, 2500.0), ('foe', APOC, 'Player_2', 1600.0, 2500.0)])
    old, foe = w._id(s.bodies['same']), w._id(s.bodies['foe'])
    s.bodies['same'].alive = False
    del s.bodies['same']
    new = s.add('same', APOC, 'Player_1', 1290.0, 2500.0)
    move = SimpleNamespace(kind='move', units=(old,), pos=(1450.0, 2700.0), target=None, power='', template='')
    assert not w.issue(move) and new.move_to is None
    assert not w.issue(SimpleNamespace(kind='attack', units=(old,), target=foe, pos=None, power='', template=''))
    assert new.goal is None and w._id(new) not in (old, foe)
    assert w.issue(SimpleNamespace(kind='move', units=(w._id(new),), pos=(1450.0, 2700.0), target=None, power='',
                                   template='')) and new.move_to is not None


def _ai(kind, b, **kw):
    args = (('objects', 'serial'),) + kw.pop('args', ())
    return Command(kind, 'ai:Player_1', units=(b.serial,), args=args, **kw)


def _ran(*worlds):
    for s in worlds:
        for _ in range(30):
            s.step()
            s.t = round(s.t + sim.DT, 3)


def test_the_ais_orders_give_what_its_calls_gave():
    """simai / simpullback (R3 13f-1) give by serial: a member re-sent (its target dropped, a form-up slot's facing),
    a pursuit's threat as the goal alone, a structure set down -- each what the old call gave."""
    port_world, direct = _pair()
    a, d = port_world.bodies['a'], direct.bodies['a']
    a.goal, d.goal = port_world.bodies['foe'], direct.bodies['foe']
    assert port_world.commands.do(_ai('attack_move', a, pos=(400.0, 300.0),
                                      args=(('drop_target', True), ('face', 1.25)))) == (True, '')
    d.goal = None
    direct.order_move(d, (400.0, 300.0), True, face=1.25)
    assert port_world.commands.do(_ai('attack', port_world.bodies['b'], target='foe',
                                      args=(('goal_only', True),))) == (True, '')
    direct.bodies['b'].goal = direct.bodies['foe']
    cmd = Command('place', 'ai:Player_1', player='Player_1', template=APOC, pos=(700.0, 500.0),
                  args=(('name', '#ai 3 x'), ('team', '')))
    assert port_world.commands.do(cmd) == (True, '')
    made = direct.add('#ai 3 x', APOC, 'Player_1', 700.0, 500.0, by='skirmish AI', at=direct.t, team='')
    if direct.blocks(made):
        direct.reblock()
    direct.change()
    assert _states(port_world) == _states(direct)
    assert port_world.bodies['b'].goal is port_world.bodies['foe'] and port_world.bodies['b'].move_to is None
    _ran(port_world, direct)
    assert _states(port_world) == _states(direct)


def test_the_ais_refused_orders():
    s = _world()
    a = s.bodies['a']
    assert s.commands.do(_ai('enter', a, target='nowhere', args=(('via', 'garrison'),)))[0] is False
    assert s.commands.do(_ai('enter', a, target='foe', args=(('via', 'door'),)))[0] is False
    assert s.commands.do(_ai('attack', a, target='nowhere', args=(('goal_only', True),)))[0] is False
    assert s.commands.do(_ai('unpack', a, pos=(1.0, 2.0), args=(('send', False),)))[0] is False   # no unpack button
    gone = Command('unpack', 'ai:Player_1', units=(10 ** 6,), pos=(1.0, 2.0), args=(('objects', 'serial'),))
    assert s.commands.do(gone) == (False, 'no unit to unpack')
    a.goal = s.bodies['foe']
    assert s.commands.do(_ai('attack', a, args=(('goal_only', True),))) == (True, '') and a.goal is None


def test_team_teleport_status_and_stance_reach_the_members_not_a_reference_of_their_name():
    """TEAM_TELEPORT_TO_WAYPOINT / TEAM_CHANGE_OBJECT_STATUS / TEAM_SET_STANCE run the unit action on the member they
    picked (11-19 same-name sweep S2: by name, the reference `lead` took lead's teleport, status bit and stance)."""
    s = _team_world()
    _act(s, 'TEAM_TELEPORT_TO_WAYPOINT', 'T', '@400,300')
    _act(s, 'TEAM_CHANGE_OBJECT_STATUS', 'T', 'UNATTACKABLE', 1)
    _act(s, 'TEAM_SET_STANCE', 'T', '3')
    lead, out = s.bodies['lead'], s.bodies['outsider']
    assert (lead.x, lead.y) == (400.0, 300.0) and (out.x, out.y) == (900.0, 0.0)
    assert 'UNATTACKABLE' in lead.script_status and 'UNATTACKABLE' not in out.script_status
    assert lead.hold_fire and not out.hold_fire
    assert s.commands.issued()[-1][1].units == (s.bodies['next'].serial,)
    assert {'UNIT_TELEPORT_TO_WAYPOINT', 'UNIT_CHANGE_OBJECT_STATUS'} <= s.ra3_only


def test_team_attack_team_and_its_follow_up_take_the_member_not_a_reference_of_its_name():
    """TEAM_ATTACK_TEAM gives the nearest member by serial, and the fight's next pick when it dies is the member
    itself (11-19 same-name sweep S2: by name, references `lead` / `next` pointing at a decoy took both)."""
    s = simsmall.small_world([('atk', APOC, 'Player_2', 0.0, 600.0), ('lead', APOC, 'Player_1', 0.0, 0.0),
                              ('next', APOC, 'Player_1', 60.0, 0.0), ('decoy', APOC, 'Player_1', 900.0, 0.0)],
                             model=False)
    s.relations[('Player_1', 'Player_2')] = s.relations[('Player_2', 'Player_1')] = 'Enemy'
    s.bodies['atk'].team = 'A'
    for n in ('lead', 'next'):
        s.bodies[n].team = 'T'
    s.active |= {'A', 'T'}
    s.refs['lead'] = s.refs['next'] = s.bodies['decoy']
    _act(s, 'TEAM_ATTACK_TEAM', 'A', 'T')
    atk = s.bodies['atk']
    assert atk.goal is s.bodies['lead'] and s.commands.issued()[-1][1].arg('target_serial') == s.bodies['lead'].serial
    s.destroy(s.bodies['lead'], '测试')
    _run_frames(s)
    assert atk.goal is s.bodies['next']


def test_a_player_power_is_cast_by_the_object_it_picked_not_a_reference_of_its_name():
    """PLAYER_FIRE_SPECIAL_POWER_AT_WAYPOINT casts from the object it found (11-19 same-name sweep S2: by name, the
    reference `lead` pointing at another player's unit cast in its place)."""
    s = simsmall.small_world([('lead', 'JapanAntiInfantryVehicle', 'Player_1', 0.0, 0.0),
                              ('other', APOC, 'Player_2', 900.0, 0.0)], model=False)
    s.refs['lead'] = s.bodies['other']
    _act(s, 'PLAYER_FIRE_SPECIAL_POWER_AT_WAYPOINT', 'Player_1', 'SpecialPower_JAIV_Transform', '@400,300')
    assert [c[1] for c in s.casts] == ['Player_1']


def test_a_line_attack_and_capture_go_at_the_object_picked_not_a_reference_of_its_name():
    """A line's attack / capture order the object `pick` found, as it is (11-19 same-name sweep S3: read again by its
    name, the reference `target` pointing at another enemy took the attack, and one pointing at a tank turned the
    capture down)."""
    s = simsmall.small_world([('tank', APOC, 'Player_1', 0.0, 0.0), ('eng', 'SovietEngineer', 'Player_1', 0.0, 60.0),
                              ('target', 'AlliedBarracks', 'Player_2', 400.0, 0.0),
                              ('decoy', APOC, 'Player_2', 900.0, 0.0)], model=False)
    s.relations[('Player_1', 'Player_2')] = s.relations[('Player_2', 'Player_1')] = 'Enemy'
    s.refs['target'] = s.bodies['decoy']
    assert s.commands.do(Command('attack', units=('tank',), target='target')) == (True, '')
    assert s.commands.do(Command('capture', units=('eng',), target='target')) == (True, '')
    assert s.bodies['tank'].goal is s.bodies['eng'].goal is s.bodies['target']


def test_the_ais_enter_into_a_dead_building_is_refused():
    """garrison.send sends no one into a dead building, and the port says so (review 11-19 k #4: it recorded a
    success); into a living one it is a success."""
    s = simsmall.small_world([('eng', 'SovietEngineer', 'Player_1', 0.0, 0.0),
                              ('hut', 'AlliedBarracks', 'Player_1', 400.0, 0.0)], model=False)
    eng, hut = s.bodies['eng'], s.bodies['hut']
    enter = _ai('enter', eng, target='hut', args=(('via', 'garrison'), ('target_serial', hut.serial)))
    hut.alive = False
    assert s.commands.do(enter)[0] is False and s.garrison.going == {}
    assert s.commands.issued()[-1][2] is False
    hut.alive = True
    assert s.commands.do(enter) == (True, '') and s.garrison.going == {eng.serial: (eng, hut)}


def test_the_players_power_is_cast_by_the_object_he_picked_not_a_reference_of_its_name():
    """order_power (the proxy player's ground power) casts from the object itself (11-19 same-name sweep S4: by name,
    the reference `cannon` pointing at another player's unit cast in its place)."""
    s = simsmall.small_world([('cannon', 'AlliedSuperWeaponAdvanced', 'Player_1', 0.0, 0.0),
                              ('other', APOC, 'Player_2', 900.0, 0.0)], model=False)
    s.refs['cannon'] = s.bodies['other']
    assert s.order_power(s.bodies['cannon'], 'SpecialPowerParticleCannon', (500.0, 300.0)) == (True, None)
    assert [c[1] for c in s.casts] == ['Player_1']


def test_a_sequential_scripts_this_object_is_the_unit_queued_not_a_reference_of_its_name():
    """A sequential script's <This Object> is the unit it was queued on (11-19 same-name sweep S5: by its name, the
    reference `lead` pointing at another unit took the step's move); the reference reads as before after the step."""
    import parts
    s = sim.Sim(parts.Mission(name='T', map=simsmall.island, scripts=[
        parts.Script('seqtask', [], [('MOVE_NAMED_UNIT_TO', '<This Object>', 'dest')], once=False)]), model=False)
    for name in list(s.bodies):
        s.world.drop(s.bodies.pop(name))
    lead = s.add('lead', 'AlliedAntiInfantryInfantry', 'Player_1', 300.0, 300.0)
    other = s.add('other', 'AlliedAntiInfantryInfantry', 'Player_1', 300.0, 600.0)
    s.waypoints['dest'] = (600.0, 300.0)
    s.act('UNIT_EXECUTE_SEQUENTIAL_SCRIPT', ['lead', 'seqtask'], None)
    s.refs['lead'] = other
    s.seq_due()
    assert (lead.move_to, other.move_to, s.refs['lead']) == ((600.0, 300.0), None, other)


def test_the_proxy_does_not_keep_the_objects_it_saw():
    """An object the proxy saw (gave an id) is reclaimed once the world lets go of it, its id row with it (review
    11-19 m: 30 same-name replacements seen kept 30 objects alive); an old id still orders nothing."""
    s, w = _proxy([])
    seen = []
    for _ in range(30):
        b = s.add('same', APOC, 'Player_1', 1250.0, 2500.0)
        seen.append(weakref.ref(b))
        w._id(b)
    del b
    gc.collect()
    assert (sum(r() is not None for r in seen), len(w.ids), len(w.things)) == (1, 1, 1)
    assert w._body(1) is None and max(w.names) == 30


def test_goal_only_with_a_serial_and_no_name_takes_that_target():
    """The AI's goal_only by serial alone sets that goal (review 11-19 m: without a name the target was dropped)."""
    s = simsmall.small_world([('a', APOC, 'Player_1', 0.0, 0.0), ('t', APOC, 'Player_2', 400.0, 0.0)], model=False)
    t = s.bodies['t']
    assert s.commands.do(_ai('attack', s.bodies['a'], args=(('goal_only', True), ('target_serial', t.serial)))) \
        == (True, '')
    assert s.bodies['a'].goal is t


def test_an_attack_on_ones_own_side_is_refused_by_the_port():
    """A plain attack at one's own side is turned down by the world, and the port says so (review 11-19 m: it said
    yes); forced, it goes."""
    s = simsmall.small_world([('a', APOC, 'Player_1', 0.0, 0.0), ('mate', APOC, 'Player_1', 400.0, 0.0)],
                             model=False)
    mate = s.bodies['mate']
    attack = _ai('attack', s.bodies['a'], target='mate', args=(('target_serial', mate.serial),))
    assert s.commands.do(attack)[0] is False and s.bodies['a'].goal is None
    assert s.commands.do(Command('attack', units=('a',), target='mate'))[0] is False
    assert s.commands.do(Command('attack', units=('a',), target='mate', force=True)) == (True, '')
    assert s.bodies['a'].goal is mate


def _brain(s, player='Player_1'):
    """A bare Brain of `player` on the small world: its Thing ids and outlets, no model."""
    import simai
    host = simai.SimAI(s, lib=object(), data=object())
    br = object.__new__(simai.Brain)
    br.host, br.world, br.peers, br.player, br.ids, br.hp = host, s, host.peers, player, {}, {}
    return br, simai


def test_the_ais_attack_and_capture_take_the_object_it_saw_not_a_reference_of_its_name():
    """The AI's Thing id is its object's, and its attack / capture go at that object by serial (11-19 same-name sweep
    S6: ids were per name and orders went by name, so the reference `target` pointing at another enemy took the
    attack and the capture, and a building made again under the old one's name took its id)."""
    from types import SimpleNamespace
    s = simsmall.small_world([('tank', APOC, 'Player_1', 0.0, 0.0), ('eng', 'SovietEngineer', 'Player_1', 0.0, 60.0),
                              ('target', 'AlliedBarracks', 'Player_2', 400.0, 0.0),
                              ('decoy', APOC, 'Player_2', 900.0, 0.0)], model=False)
    s.relations[('Player_1', 'Player_2')] = s.relations[('Player_2', 'Player_1')] = 'Enemy'
    s.refs['target'] = s.bodies['decoy']
    br, simai = _brain(s)
    target, tank, eng = s.bodies['target'], s.bodies['tank'], s.bodies['eng']
    tid = br.tid(target)
    br.order(simai.Unit(tank, br.peers), 'attack', tid)
    br.act(SimpleNamespace(members=[simai.Unit(eng, br.peers)]), 'Engineer', SimpleNamespace(id=tid))
    assert tank.goal is eng.goal is target
    assert s.commands.issued()[-1][1].arg('target_serial') == target.serial
    tank.goal = None
    target.alive = False
    del s.bodies['target']
    again = s.add('target', 'AlliedBarracks', 'Player_2', 400.0, 0.0)
    assert br.body_of(tid) is None and br.tid(again) != tid
    br.order(simai.Unit(tank, br.peers), 'attack', tid)
    assert tank.goal is None


def test_the_ais_micro_fires_and_dodges_with_the_unit_it_viewed_not_a_reference_of_its_name():
    """The micro outlets take the object the view was made of (11-19 same-name sweep S6b: `fire_unit` read
    `world.body(u.name)` and `dodge_move` matched team members by name, so the reference `lead` pointing at another
    miner of the same player fired that miner's armour, and a team still holding the old `lead` moved that one)."""
    from types import SimpleNamespace
    import simai
    if not simai.available():
        pytest.skip('ra3model.ai unavailable')
    s = simsmall.small_world([('lead', 'SovietMiner', 'Player_1', 0.0, 0.0),
                              ('decoy', 'SovietMiner', 'Player_1', 300.0, 0.0)], model=False)
    old, decoy = s.bodies['lead'], s.bodies['decoy']
    del s.bodies['lead']
    lead = s.add('lead', 'SovietMiner', 'Player_1', 0.0, 100.0)
    s.refs['lead'] = decoy
    host = simai.SimAI(s)
    br = object.__new__(simai.Brain)
    br.host, br.world, br.peers, br.player, br.ids, br.hp = host, s, host.peers, 'Player_1', {}, {}
    br.view, br.aim_of, br.fired, br.frame = SimpleNamespace(things=[], enemies=frozenset()), lambda b, r: None, [], 0
    team = SimpleNamespace(members=[simai.Unit(old, br.peers), simai.Unit(lead, br.peers)])
    mu = next(u for u in br.micro_team(None, 0, team).units if u.pos == (0.0, 100.0))
    br.fire_unit(None, 'k', mu, SimpleNamespace(command='Command_ToggleArmorUp'))
    assert lead.armor_up and not decoy.armor_up and not old.armor_up
    br.dodge_move(SimpleNamespace(teams=SimpleNamespace(teams={'k': team})), 'k', mu, (0.0, 300.0))
    assert br.peers.commands.issued()[-1][1].units == (lead.serial,)


def test_the_ais_hunt_goes_on_with_its_member_not_a_reference_of_its_name():
    """A hunt state is its member's, by serial (11-19 same-name sweep S6b: keyed by name and read back by
    `world.body(name)`, so with the pursuit dead and the path cancelled the reference `lead` pointing at another
    tank of the same player took the walk on)."""
    from types import SimpleNamespace
    import simai
    if not simai.available():
        pytest.skip('ra3model.ai unavailable')
    s = simsmall.small_world([('lead', APOC, 'Player_1', 0.0, 0.0), ('decoy', APOC, 'Player_1', 0.0, 300.0),
                              ('foe', APOC, 'Player_2', 400.0, 0.0)], model=False)
    s.relations[('Player_1', 'Player_2')] = s.relations[('Player_2', 'Player_1')] = 'Enemy'
    lead, decoy, foe = s.bodies['lead'], s.bodies['decoy'], s.bodies['foe']
    host = simai.SimAI(s)
    br = object.__new__(simai.Brain)
    br.host, br.world, br.peers, br.player, br.ids, br.hp = host, s, host.peers, 'Player_1', {}, {}
    br.view, br.frame = SimpleNamespace(things=[], enemies=frozenset({'Player_2'})), 0
    br.order(simai.Unit(lead, br.peers), 'hunt', br.tid(foe))
    assert br.peers.commands.issued()[-1][1].units == (lead.serial,)
    foe.alive, lead.path = False, []
    s.refs['lead'] = decoy
    br.hunt_threats(1)
    last = br.peers.commands.issued()[-1][1]
    assert (last.kind, last.units, last.pos) == ('attack_move', (lead.serial,), (400.0, 0.0))


def test_the_players_power_casts_with_an_observer_tapping_the_actions():
    """An observer's tap around Sim.act passes the cast's unit on (review 11-19 n P2: the tap took three arguments and
    the ground power threw TypeError once simshow / simui hung it); both taps see the cast."""
    s = simsmall.small_world([('cannon', 'AlliedSuperWeaponAdvanced', 'Player_1', 0.0, 0.0)], model=False)
    seen = []
    Observe(s).on_act(lambda n, a, sc: seen.append(('before', n)), lambda n, a, sc: seen.append(('after', n)))
    assert s.order_power(s.bodies['cannon'], 'SpecialPowerParticleCannon', (500.0, 300.0)) == (True, None)
    assert [c[1] for c in s.casts] == ['Player_1']
    assert seen == [('before', 'NAMED_FIRE_SPECIAL_POWER_AT_WAYPOINT'), ('after', 'NAMED_FIRE_SPECIAL_POWER_AT_WAYPOINT')]


def test_the_ais_recruiting_wraps_the_new_unit_not_the_dead_one_of_its_name():
    """A recruit's Unit wrapper is its object's, by serial (review 11-19 q P2 #1: keyed by name, a `lead` made again
    after the first one died was handed the dead one's wrapper, and the AI's orders to it went to the dead body)."""
    import simai
    if not simai.available():
        pytest.skip('ra3model.ai unavailable')
    s = simsmall.small_world([('lead', APOC, 'Player_1', 0.0, 0.0)], model=False)
    old = s.bodies['lead']
    host = simai.SimAI(s)
    br = object.__new__(simai.Brain)
    br.host, br.world, br.peers, br.player, br.ids, br.hp, br.wrappers = host, s, host.peers, 'Player_1', {}, {}, {}
    first, = br.units(None, 0)
    assert first.body is old
    s.delete(old, 'test')
    again = s.add('lead', APOC, 'Player_1', 400.0, 0.0)
    now, = br.units(None, 1)
    assert now.body is again and now is not first and now.body.alive
    assert br.units(None, 2) == [now]
