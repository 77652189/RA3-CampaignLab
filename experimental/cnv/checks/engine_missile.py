"""Engine unit test: a homing missile (ADR 0019 layer 2, wish list item 2, batch "homing"; docs/engine/missile.md) --
how long retail's V4 rocket (BezierProjectile) takes to land at two distances, what one hit takes off, and whether
FlightPathAdjustDistPerSecond makes it follow a target that jumps aside while it flies.

On the range probe map (maps/probe_range.py, flat) four lanes 1500 apart, each one shooter of the player's (p1, facing
north, so no turning) and one enemy target (s1, target(): a Hammer with TARGET_HP health, held with NO_ATTACK, so a
500 hit is a few percent) straight north of it:

  near   retail V4 (SovietAntiStructureVehicle)   target at NEAR
  far    retail V4                                target at FAR
  dodge  retail V4 (homing 10 / s)                target at FAR, teleported DODGE east at ORDER + JUMP
  home   CNV_MslHome: the V4 with its rocket's FlightPathAdjustDistPerSecond raised to HOME_ADJUST
                                                  target at FAR, teleported the same way

The shooters hold fire (NO_ATTACK) until ORDER, when each is freed and told to attack its target. Each lane's
counter (four lines, the bench reads all): frames from the order until its target's health first drops below
100 % (one a frame), plus 1000 for every percent it has started to lose (health < 100, < 99, ...) -- so 5073 =
first hit 73 frames (4.9 s at 15 fps) after the order, 4-5 % lost.
A counter still climbing past the far lane's frames means the first rocket missed. The script engine counts, so the
reading does not depend on the bench's clock (the bench's seconds run 1-2 s ahead of the timers).

Read (测, 2026-11-05, docs/engine/missile.md 1):
  miss   run CampMslMiss_mcp_1105_074535: near 5108, far 5108 (first hit 108 frames after the order at 250 and at 450
         alike, 5 % a hit), dodge 5117, home 5116 (the jump at +30 frames came before the launch: both hit); later
         hits about every 6.5 s. (Runs 1-2 that morning set the targets' health by script and read 60000 from s1:
         NAMED_SET_MAX_HEALTH keeps the current health -- hence target().)
  flight run CampMslFlight_mcp_1105_074901: near / far never saw their rocket (the type-in-area count does not count
         it); dodge 5210, home 5212: jumped at +90 frames (JUMP_LATE), the first rocket of both missed -- homing 300
         did not follow a 150 jump ~1.2 s before impact.
"""
import os
import re

import labpaths
from maps import probe_range
from parts import Mission, Script, Test, Unit, square

SAGE = os.path.join(labpaths.SDK3, 'SageXML')
V4, TARGET = 'SovietAntiStructureVehicle', 'SovietAntiVehicleVehicleTech1'
V4_WEAPON, V4_ROCKET = 'SovietAntiStructureVehicleV4Rocket', 'SovietAntiStructureVehicleV4RocketProjectile'
HOME, HOME_WEAPON, HOME_ROCKET = 'CNV_MslHome', 'CNV_MslHomeRocket', 'CNV_MslHomeProjectile'
HOME_ADJUST = 300.0
NEAR, FAR, DODGE = 250.0, 450.0, 150.0
TARGET_HP, TARGET_ID = 10000.0, 'CNV_MslTarget'
ORDER, JUMP, RUN = 3.0, 2.0, 30.0
LANES = {'near': ('base gun', V4, NEAR, False), 'far': ('high gun', V4, FAR, False),
         'dodge': ('order gun', V4, FAR, True), 'home': ('removed gun', HOME, FAR, True)}
LABELS = {'near': '近靶', 'far': '远靶', 'dodge': '躲靶', 'home': '追靶'}
LOST_MAX = 60                       # percent steps counted (a hit of 500 on 10 000 is 5 % before armor)


def _sub1(x, old, new):
    assert x.count(old) == 1, (old[:60], x.count(old))
    return x.replace(old, new, 1)


def home_v4(id=HOME, adjust=HOME_ADJUST):
    """Retail's V4 under `id`, its rocket weapon swapped for a copy whose projectile is retail's V4 rocket with
    FlightPathAdjustDistPerSecond = adjust (retail 10). Nothing else differs (ADR 0016 G5: the probe builds it)."""
    x = open(os.path.join(SAGE, 'Soviet', 'Units', V4 + '.xml'), encoding='utf-8').read()
    x = _sub1(x, f'id="{V4}"', f'id="{id}"')
    x = re.sub(rf'EditorName="{V4}"', f'EditorName="{id}"', x)
    x = _sub1(x, f'Template="{V4_WEAPON}"', f'Template="{HOME_WEAPON}"')
    w = open(os.path.join(SAGE, 'GlobalData', 'Weapon.xml'), encoding='utf-8').read()
    s = re.search(rf'\t*<WeaponTemplate\s+id="{V4_WEAPON}".*?</WeaponTemplate>\n', w, re.S).group(0)
    s = _sub1(s, f'id="{V4_WEAPON}"', f'id="{HOME_WEAPON}"')
    # its parent ScatterableWeapon (Weapon.xml) is not in our stream; it only adds a scatter while SHRINK_EFFECT
    s = _sub1(s, 'inheritFrom="ScatterableWeapon"', '')
    s = _sub1(s, f'ProjectileTemplate="{V4_ROCKET}"', f'ProjectileTemplate="{HOME_ROCKET}"')
    x = _sub1(x, '</AssetDeclaration>', s + '</AssetDeclaration>')
    p = open(os.path.join(SAGE, 'Soviet', 'Props', V4_ROCKET + '.xml'), encoding='utf-8').read()
    # the file's second GameObject is retail's heroic variant (inherits the rocket): not ours, dropped
    p, k = re.subn(rf'\s*<GameObject\s+inheritFrom="{V4_ROCKET}".*?</GameObject>', '', p, flags=re.S)
    assert k == 1, k
    p = _sub1(p, f'id="{V4_ROCKET}"', f'id="{HOME_ROCKET}"')
    p = _sub1(p, f'EditorName="{V4_ROCKET}"', f'EditorName="{HOME_ROCKET}"')
    p = _sub1(p, 'FlightPathAdjustDistPerSecond="10.0"', f'FlightPathAdjustDistPerSecond="{adjust:.1f}"')
    fname = HOME_ROCKET + '.xml'
    return Unit(id, x, files={fname: p}, also=[fname], link=[f'WeaponTemplate:{HOME_WEAPON}'],
                names=dict(unit=id, weapon=HOME_WEAPON, rocket=HOME_ROCKET),
                what=f'追踪加强的 V4（探针）：导弹每秒修正 {adjust:g}（原版 10），其余同原版',
                params=dict(adjust=adjust))


def target(id=TARGET_ID, health=TARGET_HP):
    """Retail's Hammer under `id` with MaxHealth = health (retail 550): a 500 hit is a few percent. Built in the XML:
    by script it did not work (run 2, 11-05: NAMED_SET_MAX_HEALTH(.., 10000, 1) then UNIT_SET_HEALTH(.., 100) left
    the Hammer below 41 % from the start)."""
    x = open(os.path.join(SAGE, 'Soviet', 'Units', TARGET + '.xml'), encoding='utf-8').read()
    x = _sub1(x, f'id="{TARGET}"', f'id="{id}"')
    x = _sub1(x, f'EditorName="{TARGET}"', f'EditorName="{id}"')
    x = _sub1(x, 'MaxHealth="550"', f'MaxHealth="{health:.1f}"')
    return Unit(id, x, names=dict(unit=id), what=f'{health:g} 血的锤子坦克（探针靶子），其余同原版',
                params=dict(health=health))


def mission():
    m = Mission(name='CampMsl', map=probe_range, units=[home_v4(), target()], facts={})
    for lane, (site, tpl, d, jumps) in LANES.items():
        L = lane.title()
        m.put(tpl, site, side='p1', role=f'{lane} shooter', name=f'UNIT - CNV Msl {L} Shooter')
        m.put(TARGET_ID, site, 0, d, side='s1', role=f'{lane} target', name=f'UNIT - CNV Msl {L} Target')
        if jumps:
            m.waypoint(f'{lane} jump', f'CNV Msl {L} Jump', site, DODGE, d)
    m.spawns |= {V4_ROCKET, HOME_ROCKET}          # the shooters make them: the flight check counts them
    return m


def missile_test(m):
    t = Test()

    def n(part):
        return m.role(part).name

    targets = [n(f'{lane} target') for lane in LANES]
    shooters = [n(f'{lane} shooter') for lane in LANES]
    start = [('MAP_REVEAL_ALL_PERM', m.player('p1'))]
    start += [('UNIT_CHANGE_OBJECT_STATUS', tg, 'NO_ATTACK', 1) for tg in targets]
    # the shooters hold fire until the order (a V4 picks an enemy in reach by itself)
    start += [('UNIT_CHANGE_OBJECT_STATUS', s, 'NO_ATTACK', 1) for s in shooters]
    start += [('SET_MILLISECOND_TIMER', 'Test Order', ORDER), ('SET_MILLISECOND_TIMER', 'Test Jump', ORDER + JUMP)]
    t.scripts.append(Script('Test - start', [], start))
    t.scripts.append(Script('Test - order', [('TIMER_EXPIRED', 'Test Order')],
                            [('UNIT_CHANGE_OBJECT_STATUS', s, 'NO_ATTACK', 0) for s in shooters]
                            + [('NAMED_ATTACK_NAMED', n(f'{lane} shooter'), n(f'{lane} target')) for lane in LANES]
                            + [('SET_FLAG', 'Test Ordered', 1)]))
    t.scripts.append(Script('Test - jump', [('TIMER_EXPIRED', 'Test Jump')],
                            [('UNIT_TELEPORT_TO_WAYPOINT', n(f'{lane} target'), m.mark(f'{lane} jump'))
                             for lane, (_, _, _, jumps) in LANES.items() if jumps]))
    for lane in LANES:
        c, tg = f'CNV_Msl_{lane.title()}', n(f'{lane} target')
        t.counters.append((c, LABELS[lane]))
        t.scripts.append(Script(f'Test - {c} frames', [('FLAG', 'Test Ordered', 1), ('UNIT_HEALTH', tg, 2, 100)],
                                [('INCREMENT_COUNTER', 1, c)], once=False))
        t.scripts += [Script(f'Test - {c} lost {k}', [('UNIT_HEALTH', tg, 0, 100 - k + 1)],
                             [('INCREMENT_COUNTER', 1000, c)]) for k in range(1, LOST_MAX + 1)]
    # a measurement: the readings are written up in docs/engine/missile.md; the expectation only says the run went
    t.expect = [(LABELS['near'], 0, 'ever>=', 1000, RUN - 2)]
    t.bench = [('bench_watch', dict(seconds=RUN, every=1, sheet=False, lines=4))]
    return t


# --- flight: when does the rocket leave, how long does it fly, does it follow? ----------------------------------
# miss (run 3) hit near and far alike 108 frames after the order and the jump (2 s) came before the launch. Here the
# rocket itself is watched: the player's objects of the rocket's template in the lane's trigger area (FLY_R around
# the shooter-target midpoint, on the ground: INFERRED 2D) -- from the order until one shows up ("launch"), then
# while it is there ("flight", the first rocket only: a lane is done once it is gone).
#   near / far  launch frames + 1000 x flight frames
#   dodge / home  the jump happens JUMP_AFTER s after that lane's rocket shows up (or at ORDER + JUMP_LATE without
#               one); counter as in miss: frames to the first hit + 1000 per percent lost
FLY_R, JUMP_AFTER, JUMP_LATE, FLIGHT_RUN = 500.0, 0.5, 6.0, 20.0
FLIGHT_LABELS = {'near': '近发飞', 'far': '远发飞', 'dodge': '躲靶', 'home': '追靶'}


def _rocket(lane):
    return HOME_ROCKET if LANES[lane][1] == HOME else V4_ROCKET


def flight_test(m):
    t = Test()

    def n(part):
        return m.role(part).name

    p1 = m.player('p1')
    targets = [n(f'{lane} target') for lane in LANES]
    shooters = [n(f'{lane} shooter') for lane in LANES]
    start = [('MAP_REVEAL_ALL_PERM', p1)]
    start += [('UNIT_CHANGE_OBJECT_STATUS', x, 'NO_ATTACK', 1) for x in targets + shooters]
    start += [('SET_MILLISECOND_TIMER', 'Test Order', ORDER)]
    t.scripts.append(Script('Test - start', [], start))
    t.scripts.append(Script('Test - order', [('TIMER_EXPIRED', 'Test Order')],
                            [('UNIT_CHANGE_OBJECT_STATUS', s, 'NO_ATTACK', 0) for s in shooters]
                            + [('NAMED_ATTACK_NAMED', n(f'{lane} shooter'), n(f'{lane} target')) for lane in LANES]
                            + [('SET_FLAG', 'Test Ordered', 1), ('SET_MILLISECOND_TIMER', 'Test Late', JUMP_LATE)]))
    for lane, (site, _, d, jumps) in LANES.items():
        L, c = lane.title(), f'CNV_MslF_{lane.title()}'
        area, seen, done = f'Test Fly {L}', f'Test Seen {L}', f'Test Done {L}'
        x, y = m.site(site, 0, d / 2)
        t.areas[area] = square(x, y, FLY_R)
        there = ('PLAYER_HAS_COMPARISON_UNIT_TYPE_IN_TRIGGER_AREA', p1, 3, 1, _rocket(lane), area)
        gone = ('PLAYER_HAS_COMPARISON_UNIT_TYPE_IN_TRIGGER_AREA', p1, 2, 0, _rocket(lane), area)
        t.counters.append((c, FLIGHT_LABELS[lane]))
        t.scripts.append(Script(f'Test - {c} seen', [('FLAG', 'Test Ordered', 1), there],
                                [('SET_FLAG', seen, 1)] +
                                ([('SET_MILLISECOND_TIMER', f'Test Jump {L}', JUMP_AFTER)] if jumps else [])))
        if jumps:
            jump = [('UNIT_TELEPORT_TO_WAYPOINT', n(f'{lane} target'), m.mark(f'{lane} jump'))]
            t.scripts.append(Script(f'Test - jump {L}', [('TIMER_EXPIRED', f'Test Jump {L}')], jump))
            t.scripts.append(Script(f'Test - jump {L} late', [('TIMER_EXPIRED', 'Test Late'), ('FLAG', seen, 0)],
                                    jump))
            tg = n(f'{lane} target')
            t.scripts.append(Script(f'Test - {c} frames', [('FLAG', 'Test Ordered', 1), ('UNIT_HEALTH', tg, 2, 100)],
                                    [('INCREMENT_COUNTER', 1, c)], once=False))
            t.scripts += [Script(f'Test - {c} lost {k}', [('UNIT_HEALTH', tg, 0, 100 - k + 1)],
                                 [('INCREMENT_COUNTER', 1000, c)]) for k in range(1, LOST_MAX + 1)]
            continue
        t.scripts.append(Script(f'Test - {c} launch', [('FLAG', 'Test Ordered', 1), ('FLAG', seen, 0)],
                                [('INCREMENT_COUNTER', 1, c)], once=False))
        t.scripts.append(Script(f'Test - {c} flight', [('FLAG', seen, 1), ('FLAG', done, 0), there],
                                [('INCREMENT_COUNTER', 1000, c)], once=False))
        t.scripts.append(Script(f'Test - {c} done', [('FLAG', seen, 1), gone], [('SET_FLAG', done, 1)]))
    t.expect = [(FLIGHT_LABELS['near'], 0, 'ever>=', 1, FLIGHT_RUN - 2)]
    t.bench = [('bench_watch', dict(seconds=FLIGHT_RUN, every=1, sheet=False, lines=4))]
    return t


# the builds this module makes and their checks (cnv/registry.py)
MISSION = {'engine_missile': mission}
CHECKS = {'engine_missile': {'miss': missile_test, 'flight': flight_test}}
