"""E211: two modules the data says only draw -- each host cloned twice, the retail XML and the module taken out.

AimWeapon (AimLow/HighThreshold, AimNear/FarDistance; retail: the Javelin and the Flak Trooper) sets AIM_HIGH,
and in the SDK only Draws ConditionsYes read AIM_HIGH. Build engine_aimweapon_e: a Javelin fires on a hovering
Twinblade 100 east (its _Aircraft launcher, range 300), On with the module, Off without.

ConvergingLaserState (a LaserState: four beams closing on the target; retail: the Athena and the Hammer's leeched
Athena gun) has SweepWeapon / SweepFXList, unset in both retail uses; the Athena's damage is its OCL's cannon
effect (checks/engine_ocl.py). Build engine_convlaser_e: an Athena fires on a Soviet advanced power plant 300
north, Off without its four ConvergingLaserState (one module kind, four copies: the arm contract takes one
element, so this build is not in CONTROL_ARMS).

Prediction: each pair the same -- the frames from the order to the first loss and the health at the freeze. The
target holds fire; the shooter is held until GO. Counters: frame (stops at END), On / Off = health % x 1000 +
frames waiting for the first loss, gate bits: the arm's model condition (AIM_HIGH / FIRING_OR_PREATTACK_A) ever
on 1 / 2, both targets alive at END 4 / 8. AimWeapon: 1 4 8 = 13 (Off never AIM_HIGH); the laser's trigger is the
weapon's own condition, both arms: 15.
"""
import re
from pathlib import Path

import labpaths
from maps import probe_range
from parts import Mission, Script, Test, Unit, status

GO = 30
CASES = {   # build: (mission, SDK file, host, module tag, copies, target, target dx dy, condition, END)
    'engine_aimweapon_e': ('CampAimWpnE', 'Allied/Units/AlliedAntiVehicleInfantry.xml', 'AlliedAntiVehicleInfantry',
                           'AimWeapon', 1, 'SovietAntiGroundAircraft', (100.0, 0.0), 'AIM_HIGH', GO + 90),
    'engine_convlaser_e': ('CampConvLsrE', 'Allied/Units/AlliedAntiStructureVehicle.xml', 'AlliedAntiStructureVehicle',
                           'ConvergingLaserState', 4, 'SovietPowerPlantAdvanced', (0.0, 300.0),
                           'FIRING_OR_PREATTACK_A', GO + 200),
}


def mission(build, swap=False, late=False):
    name, path, host, tag, copies, target, (tx, ty), _, _ = CASES[build]
    m = Mission(name=name[:-1] + ('S' if swap else 'O' if late else 'E'), map=probe_range, units=[])
    source = (Path(labpaths.SDK3) / 'SageXML' / path).read_text(encoding='utf-8-sig')
    for arm, dx in [('On', 700.0 * swap), ('Off', 700.0 * (not swap))][::-1 if late else 1]:
        ident = 'CNVE211' + arm
        xml = source.replace(f'id="{host}"', f'id="{ident}"', 1)
        for key, value in re.findall(r'<Define\s+name="([^"]+)"\s+value="([^"]+)"\s*/>', xml):
            xml = xml.replace('$' + key, value)
        xml = re.sub(r'<Defines>.*?</Defines>', '', xml, flags=re.S)
        if arm == 'Off':
            xml, n = re.subn(rf'\s*<{tag}\b.*?(?:/>|</{tag}>)', '', xml, flags=re.S)
            assert n == copies, (tag, n)
        m.units.append(Unit(ident, xml))
        m.put(ident, 'base gun', dx, 0.0, role=arm, name='E211 ' + arm, angle=1.570796)
        m.put(target, 'base gun', dx + tx, ty, side='s1', role=arm + ' target', name='E211 ' + arm + ' target',
              angle=3.141593)
    return m


def check(m, build):
    *_, condition, end = CASES[build]
    t = Test()
    t.counters = [('E211Frame', '完成帧'), ('E211On', '原版'), ('E211Off', '删模块'), ('E211Gate', '前置位')]
    t.scripts = [Script('Test - clock', [('COUNTER', 'E211Frame', 0, end)],
                        [('INCREMENT_COUNTER', 1, 'E211Frame')], once=False),
                 Script('Test - reveal', [], [('MAP_REVEAL_ALL_PERM', m.player('p1'))])]
    for arm, weight in [('On', 1), ('Off', 2)]:
        shooter, target = m.role(arm).name, m.role(arm + ' target').name
        wait = 'E211W' + arm        # the arm tag after a capital: contract.arm_drift pairs the two arms by it
        t.scripts += [
            Script('Test - quiet ' + arm, [], [
                ('UNIT_CHANGE_OBJECT_STATUS', shooter, status('NO_ATTACK'), 1),
                ('UNIT_CHANGE_OBJECT_STATUS', target, status('NO_ATTACK'), 1)]),
            Script('Test - go ' + arm, [('COUNTER', 'E211Frame', 2, GO)], [
                ('UNIT_CHANGE_OBJECT_STATUS', shooter, status('NO_ATTACK'), 0),
                ('NAMED_ATTACK_NAMED', shooter, target)]),
            Script('Test - wait ' + arm, [('COUNTER', 'E211Frame', 3, GO), ('COUNTER', 'E211Frame', 0, end),
                                          ('UNIT_HEALTH', target, 3, 100)],
                   [('INCREMENT_COUNTER', 1, wait)], once=False),
            Script('Test - condition ' + arm, [('COUNTER', 'E211Frame', 3, GO), ('COUNTER', 'E211Frame', 0, end),
                                               ('UNIT_HAS_MODELCONDITION', shooter, condition)],
                   [('INCREMENT_COUNTER', weight, 'E211Gate')]),
            Script('Test - end ' + arm, [('COUNTER', 'E211Frame', 2, end)], [
                ('SET_UNIT_HEALTH_PERCENTAGE_TO_COUNTER', target, 'E211' + arm),
                ('COUNTER_MATH_VALUE', 'E211' + arm, 2, 1000),
                ('COUNTER_MATH_COUNTER', 'E211' + arm, 0, wait)]),
            Script('Test - alive ' + arm, [('COUNTER', 'E211Frame', 2, end), ('NAMED_NOT_DESTROYED', target)],
                   [('INCREMENT_COUNTER', 4 * weight, 'E211Gate')])]
    t.expect = [('完成帧', 0, 'ever==', end), ('前置位', 0, 'ever==', 13 if condition == 'AIM_HIGH' else 15)]
    t.bench = [('bench_camera', dict(x=1150, y=550, look=False)),
               ('bench_watch', dict(seconds=end // 15 + 25, every=1, sheet=False, lines=4))]
    return t


VARIANTS = {k: {} for k in CASES} | {b[:-1] + 's': {'swap': True} for b in CASES} | \
    {b[:-1] + 'o': {'late': True} for b in CASES}   # s: the arms trade places; o: the control's objects made first
MISSION = {v: (lambda v=v: mission(v[:-1] + 'e', **VARIANTS[v])) for v in VARIANTS}
CHECKS = {v: {'a': lambda m, v=v: check(m, v[:-1] + 'e')} for v in VARIANTS}
CONTROL_ARMS = {v: ('On', 'Off') for v in VARIANTS if v.startswith('engine_aimweapon')}
