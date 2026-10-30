"""Can the map's scripts play the player's side? (missions/drive_bench.py; ADR 0010's graybox runs a level unattended
under a "playstyle script" and reads the verdict off the counters.)

prod: the player's barracks and 6000 money, a variant waking (or not) whatever might make it build -- read: money
  spent, infantry made (the control, drive_idle, shows what a barracks does alone: nothing);
cmds: the three order kinds on the player's own units -- one Guardian moved by name, one told to attack a Hammer by
  name, then the whole default team attack-moved at the front;
run: a playstyle script end to end -- the team attack-moves every ORDER_EVERY s, one Guardian is given at the base
  every GIVE_EVERY s (what a barracks would make), a flag stops the clock when one side is gone. Read at the end:
  enemy Hammers left, our Guardians left, seconds, Guardians given.
"""
from parts import NOT, Script, Test, counted, kindof, square

WHOLE = 'Test Whole Map'
GUARDIAN, HAMMER = 'AlliedAntiVehicleVehicleTech1', 'SovietAntiVehicleVehicleTech1'


def base(m):
    t = Test()
    t.scripts.append(Script('Test - start', [], [('MAP_REVEAL_ALL_PERM', m.player('p1')),
                                                 ('PLAYER_SET_MONEY', m.player('p1'), m.facts['money'])]))
    t.areas[WHOLE] = square(2500.0, 2500.0, 2600.0)
    return t


def production(wake):
    """wake: the actions that start the experiment at 3 s, from the mission and the test ([] = the control)."""
    def check(m):
        t, p1 = base(m), m.player('p1')
        t.waypoints['Test Base'] = m.site('base yard')
        t.scripts.append(Script('Test - go timer', [], [('SET_MILLISECOND_TIMER', 'Test Go', 3.0)]))
        acts = wake(p1)
        if acts:
            t.scripts.append(Script('Test - wake', [('TIMER_EXPIRED', 'Test Go')], acts))
        t.counters.append(('Test_Money', '资金'))
        t.scripts.append(Script('Test - money', [], [('SET_PLAYER_MONEY_TO_COUNTER', p1, 'Test_Money')], once=False))
        counted('Test_Infantry', '我方步兵', t, area=WHOLE, kind=kindof('INFANTRY'))
        counted('Test_Guardians', '守护者', t, template=GUARDIAN)
        counted('Test_Power', '电厂', t, template='AlliedPowerPlant')
        if acts:
            t.expect += [('资金', 4, 'ever<', m.facts['money'] - 500), ('我方步兵', 4, 'ever>=', 1)]
        else:
            t.expect += [('资金', 4, '==', m.facts['money']), ('我方步兵', 4, '==', 0)]
        t.bench = [('bench_watch', dict(seconds=80, every=5, sheet=False, lines=len(t.counters)))]
        return t
    return check


def ai_wake(p1):
    return [('SKIRMISH_AI_START', p1), ('SKIRMISH_AI_MAKE_BASE', p1, 'Test Base')]


def enable_wake(p1):
    return [('PLAYER_ENABLE_UNIT_CONSTRUCTION', p1), ('PLAYER_ENABLE_BASE_CONSTRUCTION', p1)]


def commands(m):
    """g1 walks to the west field by name, g2 attacks the Hammer by name (its health drops), at 40 s the whole team
    attack-moves at the front (the Hammer dies, g3 who stood still joins in)."""
    t = base(m)
    team, enemy = m.team('p1'), m.player('s1')
    g1, g2, g3 = (m.role(f'guardian {k}').name for k in (1, 2, 3))
    hammer = m.role('hammer 1').name
    t.waypoints['Test Move'] = m.site('west field')
    t.waypoints['Test Front'] = m.site('front')
    t.areas['Test Move Area'] = square(*m.site('west field'), 120.0)
    t.scripts += [Script('Test - timers', [], [('SET_MILLISECOND_TIMER', 'Test Named', 3.0),
                                               ('SET_MILLISECOND_TIMER', 'Test Team', 40.0)]),
                  Script('Test - named', [('TIMER_EXPIRED', 'Test Named')],
                         [('MOVE_NAMED_UNIT_TO', g1, 'Test Move'), ('NAMED_ATTACK_NAMED', g2, hammer)]),
                  Script('Test - team', [('TIMER_EXPIRED', 'Test Team')],
                         [('ATTACK_MOVE_TEAM_TO', team, 'Test Front')])]
    counted('Test_Moved', '走到了', t, named=g1, area='Test Move Area')
    counted('Test_Hammer', '铁锤血量', t, health=hammer)
    counted('Test_Hammers', '铁锤数', t, template=HAMMER, player=enemy)
    counted('Test_Guardians', '守护者', t, template=GUARDIAN)
    t.expect += [('走到了', 5, 'ever==', 1, 40.0), ('铁锤血量', 5, 'ever<', 100, 40.0), ('铁锤数', 40, 'ever==', 0)]
    t.bench = [('bench_watch', dict(seconds=100, every=5, sheet=False, lines=len(t.counters), until='c3==0'))]
    return t


def run(m):
    t = base(m)
    f, team, enemy = m.facts, m.team('p1'), m.player('s1')
    t.waypoints['Test Enemy'] = m.site('front')
    t.waypoints['Test Give'] = m.site('base edge', -80, 0)
    over = ('FLAG', 'Test Over', 1, NOT)
    t.scripts += [
        Script('Test - timers', [], [('SET_MILLISECOND_TIMER', 'Test Order', 3.0), ('SET_MILLISECOND_TIMER', 'Test Give', f['give every']),
                                     ('SET_MILLISECOND_TIMER', 'Test Tick', 1.0)]),
        Script('Test - order', [('TIMER_EXPIRED', 'Test Order'), over], [('ATTACK_MOVE_TEAM_TO', team, 'Test Enemy')], once=False),
        Script('Test - order again', [('TIMER_EXPIRED', 'Test Order')], [('SET_MILLISECOND_TIMER', 'Test Order', f['order every'])], once=False),
        Script('Test - give', [('TIMER_EXPIRED', 'Test Give'), over],
               [('CREATE_UNNAMED_ON_TEAM_AT_WAYPOINT', GUARDIAN, team, 'Test Give'), ('INCREMENT_COUNTER', 1, 'Test_Given')], once=False),
        Script('Test - give again', [('TIMER_EXPIRED', 'Test Give')], [('SET_MILLISECOND_TIMER', 'Test Give', f['give every'])], once=False),
        Script('Test - clock', [('TIMER_EXPIRED', 'Test Tick'), over], [('INCREMENT_COUNTER', 1, 'Test_Time')], once=False),
        Script('Test - clock again', [('TIMER_EXPIRED', 'Test Tick')], [('SET_MILLISECOND_TIMER', 'Test Tick', 1.0)], once=False),
        Script('Test - won', [('COUNTER', 'Test_Time', 3, 3), ('COUNTER', 'Test_Enemy', 2, 0)], [('SET_FLAG', 'Test Over', 1)]),
        Script('Test - lost', [('COUNTER', 'Test_Time', 3, 3), ('COUNTER', 'Test_Ours', 2, 0)], [('SET_FLAG', 'Test Over', 1)])]
    counted('Test_Enemy', '敌方铁锤', t, template=HAMMER, player=enemy)
    counted('Test_Ours', '我方守护者', t, template=GUARDIAN)
    t.counters += [('Test_Time', '用时'), ('Test_Given', '补兵数')]
    t.expect += [('敌方铁锤', 20, 'ever==', 0), ('用时', 20, 'ever>=', 20)]
    watch = dict(seconds=120, every=5, sheet=False, lines=len(t.counters), until='c1==0|c2==0')
    t.bench = [('bench_watch', watch)] * 3
    return t
