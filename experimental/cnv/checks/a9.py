"""A9 checks (the plan's, docs/story/plans/a9.md).

win: the whole run in a few seconds: the nine balls razed one after another by test script (the player's tool, the
  beacons and the army, is not exercised: the live play does that); the three phases follow (the first ball, the
  rotation, the last three), the goals complete, the mission is won (ended, and no lost flag). It also builds the mission
  -- the balls' unit (units/tower_ball.py), the four rhythm devices -- through the real map compile.
dark: the shield on the real ball: a sentry gun at the dark ball 6 does no harm, one at the lit ball 1 does.
"""
from parts import Obj, Script, Test

KILLS = 3.0                                     # seconds between two razes
FIRST = 8.0
WIN_BY = FIRST + KILLS * 9 + 25.0


def lost_counter(t):
    """A counter for the lost flag the plan's Lose scripts set ('Mission Lost'), so an end reads as won or lost."""
    t.counters.append(('Test Lost', '输了'))
    t.scripts += [Script('Test - lost zero', [], [('SET_COUNTER', 'Test Lost', 0)], once=False),
                  Script('Test - lost on', [('FLAG', 'Mission Lost', 1)], [('SET_COUNTER', 'Test Lost', 1)], once=False)]


def win(m):
    t = Test()
    for k in range(9):
        timer = f'Test Raze {k}'
        t.scripts += [Script(f'Test - raze set {k}', [], [('SET_MILLISECOND_TIMER', timer, FIRST + KILLS * k)]),
                      Script(f'Test - raze {k}', [('TIMER_EXPIRED', timer)],
                             [('NAMED_KILL', m.role(f'ball {k + 1}').name)])]
    lost_counter(t)
    # the counters vanish when the mission ends (checks/a8.py win): the lost flag can only be read before the end
    # (the bench's seconds run some seconds ahead of the mission's: the last raze is at 32, the counter reads garbage from
    # s31 on the bench -- bench 2026-11-04 -- so the lost flag is judged until six seconds before the last raze)
    t.expect += [('输了', 0, '==', 0, FIRST + KILLS * 8 - 6), ('ENDED', WIN_BY, '', None)]
    t.bench = [('bench_watch', dict(seconds=WIN_BY, every=2, sheet=False, lines=len(t.counters)))]
    return t


GUN = 'SovietBaseDefenseGround'                # retail sentry gun: reach 300, picks no building itself -> ordered to attack
DARK_RUN = 40.0
SLACK = 3.0                                    # the bench's seconds start some seconds after the mission's


def dark(m):
    """The ball's shield on the real mission (units/tower_ball.py, docs/engine/upgrades.md 4): ball 6 is dark all run
    (only the west ball is lit before it is razed), ball 1 is lit. The player's sentry guns, one at each (placed by the
    ball, 110-170 out, ordered to attack at s6), shoot them: the dark one must not lose a point, the lit one must.
    Counters: 受伤暗 (ball 6 hurt or dead, latched), 受伤亮 (ball 1 hurt or dead, latched)."""
    t = Test()
    p1 = m.player('p1')
    pairs = {'dark': ('ball 6', (110, 0)), 'lit': ('ball 1', (-110, 0))}
    guns, balls = {}, {}
    for k, (role, (dx, dy)) in pairs.items():
        ball = m.find(m.role(role).name)
        balls[k] = ball.name
        guns[k] = f'UNIT - Test Dark Gun {k}'
        t.objects.append(Obj(GUN, ball.x + dx, ball.y + dy, side='p1', name=guns[k], site=m.role(role).site))
    # a sentry gun needs power (engine_invuln places three plants for its guns): two plants, the player's, by the guns
    for k, (role, (dx, dy)) in pairs.items():
        ball = m.find(m.role(role).name)
        t.objects.append(Obj('SovietPowerPlant', ball.x + dx * 2, ball.y + dy * 2 + 160, side='p1',
                             name=f'UNIT - Test Dark Power {k}', site=m.role(role).site))
    # the plaza's own guards (peace tower, three peacekeepers at the west shield) would shoot the guns down first
    # (bench 2026-11-04: the lit ball's gun was never seen firing): they are razed at the start
    start = [('MAP_REVEAL_ALL_PERM', p1), ('SET_MILLISECOND_TIMER', 'Test Dark Go', 6.0)]
    start += [('NAMED_KILL', r.name) for r in m.roles('peace tower')]
    t.scripts += [Script('Test - dark start', [], start),
                  Script('Test - dark go', [('TIMER_EXPIRED', 'Test Dark Go')],
                         [('NAMED_ATTACK_NAMED', guns[k], balls[k]) for k in pairs])]
    for k, label in (('dark', '受伤暗'), ('lit', '受伤亮')):
        counter, flag = f'Test Dark Hurt {k}', f'Test Dark Hit {k}'
        t.counters.append((counter, label))
        t.scripts += [Script(f'Test - dark hurt {k}', [('UNIT_HEALTH', balls[k], 0, 100)], [('SET_FLAG', flag, 1)]),
                      Script(f'Test - dark dead {k}', [('NAMED_DESTROYED', balls[k])], [('SET_FLAG', flag, 1)]),
                      Script(f'Test - dark zero {k}', [], [('SET_COUNTER', counter, 0)], once=False),
                      Script(f'Test - dark hit {k}', [('FLAG', flag, 1)], [('SET_COUNTER', counter, 1)], once=False)]
    t.expect += [('受伤暗', 0, '==', 0, DARK_RUN), ('受伤亮', 12.0, 'ever==', 1, DARK_RUN)]
    t.bench = [('bench_watch', dict(seconds=DARK_RUN, every=3, sheet=False, lines=len(t.counters)))]
    return t


# the checks per build (cnv/registry.py): build name -> {check name: check(mission) -> Test}
CHECKS = {
    'a9': {'win': win, 'dark': dark},
}
