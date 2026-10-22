"""A8 tests (were make_campa8.py's CNV_TEST=1 / lose).

jump: the player's carrier jumps next to platform 1 at 5 s and should carry the four Guardians there and fight
  (a trigger area around the landing point counts the Guardians that arrived).
lose: the carrier starts at 1 % health next to platform 1's Bullfrog: shot down within seconds, Mission Lost.
"""
from maps import island
from missions import a8
from parts import Script, Test, counted, square
from checks.liberty import EARLY, jumps


def jump(m):
    t = Test()
    jumps(t, a8.CARRIER, m.names['power'], 'Test Jump Target', a8.NEAR_P1, at=5.0)
    counted('Test Guardians', '守护者', t, template=a8.GUARDIAN)
    counted('Test Carrier', '自由号', t, template=m.names['unit'])
    t.areas['Test Platform 1'] = square(*a8.NEAR_P1, 250.0)
    counted('Test At P1', '守护者到平台', t, template=a8.GUARDIAN, area='Test Platform 1')
    t.expect += [('自由号', 20, '==', 1), ('守护者', 20, '>=', 3), ('守护者到平台', 0, '==', 0, 5.0 - EARLY),
                 ('守护者到平台', 12, 'ever>=', 3)]
    t.bench = [('bench_watch', dict(seconds=25, every=5, sheet=False))]
    return t


TEAM = 'Player_1/teamPlayer_1'                 # the player's default team: everything placed for them, built units too
ENEMY = 'Soviet_1'
WHOLE = 'Test Whole Island'
ORDER_EVERY = 8.0                               # seconds between repeated attack-move orders (new units join in)
JUMP_RELOAD = 46.0                              # the A8 carrier's 45 s reload, plus a second
GUARD_AREA = 350.0                              # half-side of the area around a platform its escort is counted in


def near(k):
    """The waypoint west of platform k the assault aims at."""
    x, y = a8.PLATFORMS[k]
    return (x - 250.0, y - 50.0)


def assault(m):
    """units.md 5.6 check: the same scripted assault with and without the carrier (a8 / a8_control), compared on
    time and losses. Every ORDER_EVERY seconds the player's whole team attack-moves to the first platform still
    standing -- and once no Hammer is left in the area around it, attacks the platform by name; with the carrier,
    it also jumps there each time its reload allows. The mission's own end (won / lost)
    is taken out, so the counters stay up: platforms left, enemy vehicles, our vehicles, the carrier."""
    carrier = any(o.name == a8.CARRIER for o in m.objects)
    m.scripts = [s for s in m.scripts if s.name not in ('CNV A8 - Win', 'CNV A8 - Lost')]
    t = Test()
    t.areas[WHOLE] = square(*island.CENTER, island.RADIUS + 300)
    order, ready = 'Test - order tick', 'Test - jump ready'
    t.scripts.append(Script('Test - start', [], [('MAP_REVEAL_ALL_PERM', 'Player_1'), ('SET_MILLISECOND_TIMER', order, 6.0),
                                                 ('SET_MILLISECOND_TIMER', ready, 5.0)]))
    for k in range(len(a8.PLATFORMS)):
        wp, area = f'Test Platform {k + 1}', f'Test Around Platform {k + 1}'
        t.waypoints[wp] = near(k)
        t.areas[area] = square(*a8.PLATFORMS[k], GUARD_AREA)
        stage = [('NAMED_NOT_DESTROYED', a8.P_NAMES[k])] + [('NAMED_DESTROYED', a8.P_NAMES[j]) for j in range(k)]
        hammers = lambda op: ('PLAYER_HAS_COMPARISON_UNIT_TYPE_IN_TRIGGER_AREA', ENEMY, op, 0,  # noqa: E731
                              'SovietAntiVehicleVehicleTech1', area)
        # attack-move only engages units (bench 2026-10-21: the escort died, then everyone idled at the waypoint,
        # the platform untouched): fight the escort first, then attack the platform itself by name
        t.scripts += [Script(f'Test - attack {k + 1}', [('TIMER_EXPIRED', order), hammers(4)] + stage,
                             [('ATTACK_MOVE_TEAM_TO', TEAM, wp)], once=False),
                      Script(f'Test - attack {k + 1} platform', [('TIMER_EXPIRED', order), hammers(2)] + stage,
                             [('TEAM_ATTACK_NAMED', TEAM, a8.P_NAMES[k])], once=False)]
        if carrier:
            t.scripts.append(Script(f'Test - jump {k + 1}', [('TIMER_EXPIRED', ready)] + stage,
                                    [('NAMED_FIRE_SPECIAL_POWER_AT_WAYPOINT', a8.CARRIER, m.names['power'], wp),
                                     ('SET_MILLISECOND_TIMER', ready, JUMP_RELOAD),
                                     ('SHOW_MILITARY_CAPTION', 'SCRIPT:CNVTEST_JUMP', 5.0)]))
    t.scripts.append(Script('Test - order again', [('TIMER_EXPIRED', order)],
                            [('SET_MILLISECOND_TIMER', order, ORDER_EVERY)], once=False))   # after the orders above
    t.strings['SCRIPT:CNVTEST_JUMP'] = 'TEST：自由号跃迁'
    # by template owned (the KindOf-in-area counts read 20 for 12 vehicles on the first run: see build.kinds)
    counted('Test Platforms', '平台剩余', t, template='AlliedPowerPlant', player=ENEMY)
    counted('Test Hammers', '敌方铁锤', t, template='SovietAntiVehicleVehicleTech1', player=ENEMY)
    counted('Test Guardians', '守护者', t, template=a8.GUARDIAN)
    if carrier:
        counted('Test Carrier', '自由号', t, template=m.names['unit'])
    else:
        counted('Test IFVs', '多功能车', t, template='AlliedAntiAirVehicleTech1')
    t.expect += [('平台剩余', 0, 'ever==', 0)]               # 5.6: winnable with and without it
    watch = dict(seconds=100, every=5, sheet=False, lines=len(t.counters), until='c1==0')
    # the camera on platform 1: a frame shows what happens there, should the numbers need explaining
    t.bench = [('bench_camera', dict(x=a8.PLATFORMS[0][0] - 150, y=a8.PLATFORMS[0][1], look=False))]
    t.bench += [('bench_watch', watch)] * 3
    return t


def lose(m):
    """At 1 % health the carrier waits at home, then jumps next to platform 1's Bullfrog at 5 s (starting there,
    it died before the bench was in the mission). Read: it is there first, then the mission ends (Mission Lost
    ends it at once, the counters go with it: a 0 is never shown; nothing else ends it within 20 s)."""
    m.find(a8.CARRIER).props['objectInitialHealth'] = 1
    t = Test()
    jumps(t, a8.CARRIER, m.names['power'], 'Test Bullfrog', (a8.PLATFORMS[0][0] - 60, a8.PLATFORMS[0][1] - 120), at=5.0)
    counted('Test Carrier', '自由号', t, template=m.names['unit'])
    t.expect += [('自由号', 0, 'ever==', 1), ('ENDED', 5, '', None)]
    t.bench = [('bench_watch', dict(seconds=20, every=1, sheet=False))]
    return t
