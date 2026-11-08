"""A2 checks (the plan's, docs/story/plans/a2.md).

win: the whole run at 1/20 of its time (every timer the plan sets is cut to a twentieth: the three phases end after 9 s
  each), then the far bank's rocket cars are razed by test script in the last phase: the goals complete, the mission
  is won (ended, and no lost flag). The waves fire at the same fast pace but have the length of the road to walk (the
  dam holds for the minute this takes); the player's part (what to send against which wave) is the live play's.
lose: two of the dam's three sections razed by test script: the mission ends lost ("the dam fell"), the lost flag
  0 before.
splash: the player's splash on the neutral dam (the plan's `待做` 1): an Athena gun at dam west and a Hammer tank at
  dam mid each shoot an enemy power plant standing 50 beside (touching) the section. Bench 2026-11-04: the Athena's
  beam takes the dam with it (health 100 -> 25 -> 2; at 90 beside it did not), the Hammer's shell does not (100 all run,
  its target gone). So the player's own splash hurts the dam only through the Athena. Counters: dam west and mid health
  and the two targets'.
frog: the plan's Bullfrogs (`待做` 3): three of them from the river mouth ordered at dam east as the plan's wave is
  (NAMED_ATTACK_NAMED): they come up under the dam's south cliff but do not hurt it (the dam stays whole). `ray`
  (three Stingrays, tesla guns) and `dread` (one Dreadnought) are the same run with other ships: the same answer.
"""
from parts import Obj, Script, Test
from model import counted, square

SCALE = 20.0
PHASE = 180.0 / SCALE                      # one phase of the plan: 3:00
RAZE_AT = 3 * PHASE + 4.0                  # the last phase has begun (the bench's seconds start a little after the mission's)
WIN_BY = RAZE_AT + 14.0
FIRST, SECOND = 8.0, 10.0
LOSE_BY = SECOND + 14.0


def lost_counter(t):
    """A counter for the lost flag the plan's Lose scripts set ('Mission Lost'), so an end reads as won or lost."""
    t.counters.append(('Test Lost', '输了'))
    t.scripts += [Script('Test - lost zero', [], [('SET_COUNTER', 'Test Lost', 0)], once=False),
                  Script('Test - lost on', [('FLAG', 'Mission Lost', 1)], [('SET_COUNTER', 'Test Lost', 1)], once=False)]


def raze(t, name, k, at):
    timer = f'Test Raze {k}'
    t.scripts += [Script(f'Test - raze set {k}', [], [('SET_MILLISECOND_TIMER', timer, at)]),
                  Script(f'Test - raze {k}', [('TIMER_EXPIRED', timer)], [('NAMED_KILL', name)])]


def win(m):
    for s in m.scripts:
        s.do = [(a[0], a[1], a[2] / SCALE) if a[0] == 'SET_MILLISECOND_TIMER' else a for a in s.do]
    t = Test()
    for k, r in enumerate(m.roles('rocket')):
        raze(t, r.name, k, RAZE_AT + 0.5 * k)
    lost_counter(t)
    # the counters vanish when the mission ends: the lost flag can only be read before the end
    t.expect += [('输了', 0, '==', 0, RAZE_AT - 2), ('ENDED', WIN_BY, '', None)]
    t.bench = [('bench_watch', dict(seconds=WIN_BY, every=3, sheet=False, lines=len(t.counters)))]
    return t


def real(m):
    """win at the plan's own pace (nothing compressed): the three phases are 3:00 each, the rocket cars razed by test
    script 4 s into the last. For simulators that read the presentation (simshow: is a K1 of the compressed win only
    the compression?); the bench would take 9 minutes, so no bench run is declared."""
    t = Test()
    at = 3 * 180.0 + 4.0
    for k, r in enumerate(m.roles('rocket')):
        raze(t, r.name, k, at + 0.5 * k)
    lost_counter(t)
    t.expect += [('输了', 0, '==', 0, at - 2), ('ENDED', at + 14.0, '', None)]
    t.bench = [('bench_watch', dict(seconds=at + 14.0, every=10, sheet=False, lines=len(t.counters)))]
    return t


def lose(m):
    t = Test()
    raze(t, m.role('dam w').name, 0, FIRST)
    raze(t, m.role('dam m').name, 1, SECOND)
    lost_counter(t)
    t.expect += [('输了', 0, '==', 0, FIRST - 3), ('ENDED', LOSE_BY, '', None)]
    t.bench = [('bench_watch', dict(seconds=LOSE_BY, every=2, sheet=False, lines=len(t.counters)))]
    return t


SPLASH_RUN = 50.0
HAMMER = 'SovietAntiVehicleVehicleTech1'
PLANT = 'SovietPowerPlant'


def splash(m):
    t = Test()
    p1 = m.player('p1')
    ath = m.role('athena').template
    dams = {k: m.role(f'dam {k}').name for k in 'wme'}
    shots = [('w', ath, (-350.0, 0.0), 'athena'), ('m', HAMMER, (-250.0, 0.0), 'hammer')]
    orders = []
    for k, tpl, (dx, dy), who in shots:
        dam = m.find(dams[k])
        gun, target = f'UNIT - Test Splash {who}', f'UNIT - Test Splash target {who}'
        t.objects.append(Obj(tpl, dam.x + dx, dam.y + dy, side='p1', name=gun, site=m.role(f'dam {k}').sites[0]))
        t.objects.append(Obj(PLANT, dam.x, dam.y + 50.0, side='s1', name=target, site=m.role(f'dam {k}').sites[0]))
        orders.append(('NAMED_ATTACK_NAMED', gun, target))
        counted(f'Test Target {who}', f'靶{who}血', t, health=target)
    for k in 'wm':                              # (counters.MAX_LINES is four: the control, dam east, is not shown)
        counted(f'Test Dam {k}', f'坝{k}血', t, health=dams[k])
    t.scripts += [Script('Test - splash start', [], [('MAP_REVEAL_ALL_PERM', p1), ('SET_MILLISECOND_TIMER', 'Test Splash Go', 6.0)]),
                  Script('Test - splash go', [('TIMER_EXPIRED', 'Test Splash Go')], orders)]
    t.expect += [('靶hammer血', 0, 'ever<=', 2, SPLASH_RUN), ('坝w血', 0, 'ever<=', 30, SPLASH_RUN),
                 ('坝m血', 0, '==', 100, SPLASH_RUN)]
    t.bench = [('bench_watch', dict(seconds=SPLASH_RUN, every=5, sheet=False, lines=len(t.counters)))]
    return t


FROG_RUN = 80.0
FROG = 'SovietAntiAirShip'


def frog(m, tpl=FROG, count=3):
    t = Test()
    p1 = m.player('p1')
    dam = m.find(m.role('dam e').name)
    names = [f'UNIT - Test Frog {k}' for k in range(count)]
    for k, n in enumerate(names):
        t.objects.append(Obj(tpl, *m.site('river mouth', 0.0, 60.0 * k), side='s1', name=n, site='river mouth'))
    t.areas['Test Foot'] = square(dam.x, 1090.0, 140.0)           # the river just below the dam's south edge (y 1150)
    t.areas['Test Start'] = square(*m.site('river mouth'), 260.0)
    t.areas['Test Mid'] = square(3000.0, 1000.0, 300.0)
    counted('Test Frog start', '牛蛙0在河口', t, named=names[0], area='Test Start')
    counted('Test Frog mid', '牛蛙0在河中', t, named=names[0], area='Test Mid')
    counted('Test Frog foot', '牛蛙0在坝脚', t, named=names[0], area='Test Foot')
    counted('Test Dam e', '坝e血', t, health=dam.name)
    t.scripts += [Script('Test - frog start', [], [('MAP_REVEAL_ALL_PERM', p1), ('SET_MILLISECOND_TIMER', 'Test Frog Go', 4.0)]),
                  Script('Test - frog go', [('TIMER_EXPIRED', 'Test Frog Go')],
                         [('NAMED_ATTACK_NAMED', n, dam.name) for n in names])]
    # bench 2026-11-04: nothing from the water hurts the dam, whichever ship (frog, 'ray', 'dread'): the frogs and the
    # Stingrays come up under the cliff and stand there (the dam is on the high ground, low ground does not see it:
    # principles P26), the Dreadnought refuses the order and stays at the river mouth. The dam is read whole all run.
    t.expect += [('坝e血', 0, '==', 100, FROG_RUN)]
    t.bench = [('bench_watch', dict(seconds=FROG_RUN, every=5, sheet=False, lines=len(t.counters)))]
    return t


# the checks per build (cnv/registry.py): build name -> {check name: check(mission) -> Test}
CHECKS = {
    'a2': {'win': win, 'real': real, 'lose': lose, 'splash': splash, 'frog': frog,
           'ray': lambda m: frog(m, 'SovietAntiNavyShipTech1'),
           'dread': lambda m: frog(m, 'SovietAntiStructureShip', 1)},
}
