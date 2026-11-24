"""E225: MagneticEffectUpdate -- the Assault Destroyer's black-hole armor (AlliedAntiNavyShipTech1, 19 of the 27 levels).

Retail: Radius 200, on while GENERIC_TOGGLE_STATE (its ToggleStatusSpecialAbilityUpdate's second state, pressed by
Command_ToggleMagneticArmor; AttributeModifier_MagneticArmor ARMOR 65 %); its filter takes ENEMIES of kind PROJECTILE /
SMALL_MISSILE / INFANTRY / VEHICLE not MAGNETIZED. The XML's comment: a BezierProjectile is turned to hit it, anything
else has its weapon's target forced onto it.

Two lanes, each a p1 Guardian (the VIP, NO_ATTACK) with a retail destroyer DX east, DY north of it, and two s1 Hammer
tanks (cannon 150) 500 north of the VIP ordered at it at SHOOT -- they stop within 200 of the destroyer. Lane On's
destroyer is pressed at PRESS, both NO_ATTACK from HOLD (its own guns would meet the tanks first).
Prediction: On's VIP stays 100 while its destroyer is hurt; Off's VIP is hurt first. Counters: VIP and destroyer health.
A V4 lane (450 north, out of the 200: only its rockets come through) did not tell the arms apart -- with the toggle off
its rockets hit the destroyer too, neither VIP was hurt (CampMagnetEB_mcp_1124_143711), so the bending is not read.
"""
from maps import probe_range
from parts import Mission, Script, Test, counted

SHIP, VIP, HAMMER = 'AlliedAntiNavyShipTech1', 'AlliedAntiVehicleVehicleTech1', 'SovietAntiVehicleVehicleTech1'
TOGGLE = 'Command_ToggleMagneticArmor'
DX, DY = 40.0, 120.0
PRESS, HOLD, SHOOT, END = 15, 20, 30, 15 * 30
LANES = {'On': 'base', 'Off': 'high'}


def mission():
    m = Mission(name='CampMagnetE', map=probe_range, units=[])
    for arm, lane in LANES.items():
        m.put(VIP, f'{lane} gun', side='p1', role=f'vip {arm}', name=f'E225 VIP {arm}', angle=1.5708)
        m.put(SHIP, f'{lane} gun', DX, DY, side='p1', role=f'ship {arm}', name=f'E225 Ship {arm}', angle=1.5708)
        for k, sx in enumerate((-30, 30)):
            m.put(HAMMER, f'{lane} gun', sx, 500, side='s1', role=f'shooter {arm} {k + 1}',
                  name=f'E225 Hammer {arm}{k + 1}', angle=4.7124)
    return m


def check(m):
    t = Test()
    for part, label in (('Vip', '要人'), ('Ship', '舰')):
        for arm, word in (('On', '开'), ('Off', '关')):
            counted(f'E225{part}{arm}', word + label, t, health=m.role(f'{part.lower()} {arm}').name)
    t.scripts += [Script('Test - clock', [('COUNTER', 'E225Frame', 0, END)],
                         [('INCREMENT_COUNTER', 1, 'E225Frame')], once=False),
                  Script('Test - start', [], [('MAP_REVEAL_ALL_PERM', m.player('p1'))] +
                         [('UNIT_CHANGE_OBJECT_STATUS', m.role(f'vip {arm}').name, 'NO_ATTACK', 1) for arm in LANES]),
                  Script('Test - press', [('COUNTER', 'E225Frame', 2, PRESS)],
                         [('NAMED_USE_COMMANDBUTTON_ABILITY', m.role('ship On').name, TOGGLE)]),
                  Script('Test - hold', [('COUNTER', 'E225Frame', 2, HOLD)],
                         [('UNIT_CHANGE_OBJECT_STATUS', m.role(f'ship {arm}').name, 'NO_ATTACK', 1) for arm in LANES]),
                  Script('Test - shoot', [('COUNTER', 'E225Frame', 2, SHOOT)],
                         [('NAMED_ATTACK_NAMED', r.name, m.role(f'vip {arm}').name) for arm in LANES
                          for r in m.roles(f'shooter {arm}')])]
    t.expect = [('开要人', 0, '==', 100)]
    t.bench = [('bench_camera', dict(x=1550, y=650, look=False)),
               ('bench_watch', dict(seconds=END // 15 + 5, every=1, sheet=False, lines=4))]
    return t


MISSION = {'engine_magnet_e': mission}
CHECKS = {'engine_magnet_e': {'a': check}}
