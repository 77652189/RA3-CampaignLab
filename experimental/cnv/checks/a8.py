"""A8 tests (were make_campa8.py's CNV_TEST=1 / lose). They ask the mission for everything: its cast (carrier,
guardian, platform 1-3, hammer ...), the carrier's published jump, the sites its parts stand on, the map's players.

jump: the player's carrier jumps next to platform 1 at 5 s and should carry the four Guardians there and fight
  (a trigger area around the landing point counts the Guardians that arrived).
lose: the carrier starts at 1 % health next to platform 1's Bullfrog: shot down within seconds, Mission Lost.
"""
from parts import Script, Test, counted, square
from checks.liberty import EARLY, jumps


def near(m, part):
    """The point west of a cast part (a platform) an assault aims at: 250 west, 50 north of its site."""
    return m.site(m.role(part).site, -250, -50)


def jump(m):
    t = Test()
    to = near(m, 'platform 1')
    jumps(t, m.role('carrier').name, m.ability('carrier', 'jump'), 'Test Jump Target', to, at=5.0)
    guardian = m.role('guardian').template
    counted('Test Guardians', '守护者', t, template=guardian)
    counted('Test Carrier', '自由号', t, template=m.role('carrier').template)
    t.areas['Test Platform 1'] = square(*to, 250.0)
    counted('Test At P1', '守护者到平台', t, template=guardian, area='Test Platform 1')
    t.expect += [('自由号', 20, '==', 1), ('守护者', 20, '>=', 3), ('守护者到平台', 0, '==', 0, 5.0 - EARLY),
                 ('守护者到平台', 12, 'ever>=', 3)]
    t.bench = [('bench_watch', dict(seconds=25, every=5, sheet=False))]
    return t


WHOLE = 'Test Whole Island'
ORDER_EVERY = 8.0                               # seconds between repeated attack-move orders (new units join in)
JUMP_RELOAD = 46.0                              # the A8 carrier's 45 s reload, plus a second
GUARD_AREA = 350.0                              # half-side of the area around a platform its escort is counted in


def assault(m):
    """units.md 5.6 check: the same scripted assault with and without the carrier (a8 / a8_control), compared on
    time and losses. Every ORDER_EVERY seconds the player's whole team attack-moves to the first platform still
    standing -- and once no Hammer is left in the area around it, attacks the platform by name; with the carrier,
    it also jumps there each time its reload allows. The mission's own endings are taken out, so the counters
    stay up: platforms left, enemy vehicles, our vehicles, the carrier."""
    carrier = 'carrier' in m.cast
    m.drop_endings()
    team, enemy, hammer = m.team('p1'), m.player('s1'), m.role('hammer').template
    platforms = m.roles('platform')
    t = Test()
    island = m.where('island')
    t.areas[WHOLE] = square(island.x, island.y, island.r + 300)
    order, ready = 'Test - order tick', 'Test - jump ready'
    t.scripts.append(Script('Test - start', [], [('MAP_REVEAL_ALL_PERM', m.player('p1')),
                                                 ('SET_MILLISECOND_TIMER', order, 6.0),
                                                 ('SET_MILLISECOND_TIMER', ready, 5.0)]))
    for k, p in enumerate(platforms):
        wp, area = f'Test Platform {k + 1}', f'Test Around Platform {k + 1}'
        t.waypoints[wp] = near(m, f'platform {k + 1}')
        t.areas[area] = square(*m.site(p.site), GUARD_AREA)
        stage = [('NAMED_NOT_DESTROYED', p.name)] + [('NAMED_DESTROYED', q.name) for q in platforms[:k]]
        hammers = lambda op: ('PLAYER_HAS_COMPARISON_UNIT_TYPE_IN_TRIGGER_AREA', enemy, op, 0, hammer, area)  # noqa: E731
        # attack-move only engages units (bench 2026-10-21: the escort died, then everyone idled at the waypoint,
        # the platform untouched): fight the escort first, then attack the platform itself by name
        t.scripts += [Script(f'Test - attack {k + 1}', [('TIMER_EXPIRED', order), hammers(4)] + stage,
                             [('ATTACK_MOVE_TEAM_TO', team, wp)], once=False),
                      Script(f'Test - attack {k + 1} platform', [('TIMER_EXPIRED', order), hammers(2)] + stage,
                             [('TEAM_ATTACK_NAMED', team, p.name)], once=False)]
        if carrier:
            t.scripts.append(Script(f'Test - jump {k + 1}', [('TIMER_EXPIRED', ready)] + stage,
                                    [('NAMED_FIRE_SPECIAL_POWER_AT_WAYPOINT', m.role('carrier').name,
                                      m.ability('carrier', 'jump'), wp),
                                     ('SET_MILLISECOND_TIMER', ready, JUMP_RELOAD),
                                     ('SHOW_MILITARY_CAPTION', 'SCRIPT:CNVTEST_JUMP', 5.0)]))
    t.scripts.append(Script('Test - order again', [('TIMER_EXPIRED', order)],
                            [('SET_MILLISECOND_TIMER', order, ORDER_EVERY)], once=False))   # after the orders above
    t.strings['SCRIPT:CNVTEST_JUMP'] = 'TEST：自由号跃迁'
    # by template owned (the KindOf-in-area counts read 20 for 12 vehicles on the first run: see build.kinds)
    counted('Test Platforms', '平台剩余', t, template=platforms[0].template, player=enemy)
    counted('Test Hammers', '敌方铁锤', t, template=hammer, player=enemy)
    counted('Test Guardians', '守护者', t, template=m.role('guardian').template)
    if carrier:
        counted('Test Carrier', '自由号', t, template=m.role('carrier').template)
    else:
        counted('Test IFVs', '多功能车', t, template=m.role('ifv').template)
    t.expect += [('平台剩余', 0, 'ever==', 0)]               # 5.6: winnable with and without it
    watch = dict(seconds=100, every=5, sheet=False, lines=len(t.counters), until='c1==0')
    # the camera on platform 1: a frame shows what happens there, should the numbers need explaining
    x, y = m.site(platforms[0].site)
    t.bench = [('bench_camera', dict(x=x - 150, y=y, look=False))]
    t.bench += [('bench_watch', watch)] * 3
    return t


def lose(m):
    """At 1 % health the carrier waits at home, then jumps next to platform 1's Bullfrog at 5 s (starting there,
    it died before the bench was in the mission). Read: it is there first, then the mission ends (Mission Lost
    ends it at once, the counters go with it: a 0 is never shown; nothing else ends it within 20 s)."""
    m.find(m.role('carrier').name).props['objectInitialHealth'] = 1
    t = Test()
    jumps(t, m.role('carrier').name, m.ability('carrier', 'jump'), 'Test Bullfrog',
          m.site(m.role('platform 1').site, -60, -120), at=5.0)
    counted('Test Carrier', '自由号', t, template=m.role('carrier').template)
    t.expect += [('自由号', 0, 'ever==', 1), ('ENDED', 5, '', None)]
    t.bench = [('bench_watch', dict(seconds=20, every=1, sheet=False))]
    return t
