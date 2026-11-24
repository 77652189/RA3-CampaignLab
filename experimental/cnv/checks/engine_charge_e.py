"""E213: ChargeWeaponUpdate -- retail's one use, the Wave-Force tower JapanBaseDefenseAdvanced (ChargeTime 5 s,
OverChargeTime 2 s, OverChargePercent 40 %, not while IS_FIRING_WEAPON / IS_RELOADING_WEAPON; its beam: PreAttackDelay
3 s, ClipSize 1, ClipReload 0.2 s, LineDamage 350, range 350).

Two clones for p1, On the retail XML, Off without the module; two SovietPowerPlant feed them (POWERED, -75 each;
placed, so no StructureUnpackUpdate). Each holds fire (NO_ATTACK) until GO (16 s: charged and over-charged whatever
the power-up takes), then is told to attack an s1 SovietPowerPlantAdvanced (4000, holding fire) 300 north.
Prediction, one of: the charge stands for the PreAttackDelay (On's first loss ~0 frames after GO, Off's ~45), or it
scales the first shot's damage (On 1.4 x Off's loss), or neither (presentation, the same).
Variants (11-24, the partial charge): b GO 60 (4 s idle: short of ChargeTime), c GO 90 (6 s: charged, short of the
over-charge). Prediction (a charge either is or is not, so is the over-charge): b as Off (48 frames, 89 %), c On's
frames at Off's damage (89 %); a pre-attack cut by the part charged would read b ~12 frames, an over-charge in
proportion c 86 % (1.2 x 437.5).
Counters: frame (stops at END = GO + 150), On / Off = the target's health % x 1000 at its first loss + the frames from
GO to it, End = On's target health % x 1000 + Off's at END.
"""
import re
from pathlib import Path

import labpaths
from maps import probe_range
from parts import Mission, Script, Test, Unit, status

HOST, TAG, TARGET = 'JapanBaseDefenseAdvanced', 'ChargeWeaponUpdate', 'SovietPowerPlantAdvanced'
GO, LONG = 240, 150


def mission(scan=True):
    m = Mission(name='CampChargeE' if scan else 'CampChargeN', map=probe_range, units=[])
    source = (Path(labpaths.SDK3) / 'SageXML/Japan/Structures' / (HOST + '.xml')).read_text(encoding='utf-8-sig')
    if not scan:    # engine_charge_n: no idle scan, the turret stays on the target's bearing (a/b's frames over?)
        source, n = re.subn(r'MaxIdleScanAngle="[^"]*"', 'MaxIdleScanAngle="0.0"', source)
        assert n == 1, n
    for k in (1, 2):
        m.put('SovietPowerPlant', f'power {k}', 0.0, 0.0, role=f'pp{k}', name=f'E213 pp{k}')
    for arm, dx in [('On', 0.0), ('Off', 700.0)]:
        ident = 'CNVE213' + arm
        xml = source.replace(f'id="{HOST}"', f'id="{ident}"', 1)
        if arm == 'Off':
            xml, n = re.subn(rf'\s*<{TAG}\b.*?</{TAG}>', '', xml, flags=re.S)
            assert n == 1, n
        m.units.append(Unit(ident, xml))
        m.put(ident, 'base gun', dx, 0.0, role=arm, name='E213 ' + arm, angle=1.570796)
        m.put(TARGET, 'base gun', dx, 300.0, side='s1', role=arm + ' target', name='E213 ' + arm + ' target',
              angle=3.141593)
    return m


def check(m, go=GO):
    end = go + LONG
    t = Test()
    t.counters = [('E213Frame', '完成帧'), ('E213On', '原版'), ('E213Off', '删模块'), ('E213End', '终血')]
    t.scripts = [Script('Test - clock', [('COUNTER', 'E213Frame', 0, end)],
                        [('INCREMENT_COUNTER', 1, 'E213Frame')], once=False),
                 Script('Test - reveal', [], [('MAP_REVEAL_ALL_PERM', m.player('p1'))])]
    for arm in ('On', 'Off'):
        shooter, target = m.role(arm).name, m.role(arm + ' target').name
        wait, hp = 'E213W' + arm, 'E213H' + arm
        t.scripts += [
            Script('Test - quiet ' + arm, [], [
                ('UNIT_CHANGE_OBJECT_STATUS', shooter, status('NO_ATTACK'), 1),
                ('UNIT_CHANGE_OBJECT_STATUS', target, status('NO_ATTACK'), 1)]),
            Script('Test - go ' + arm, [('COUNTER', 'E213Frame', 2, go)], [
                ('UNIT_CHANGE_OBJECT_STATUS', shooter, status('NO_ATTACK'), 0),
                ('NAMED_ATTACK_NAMED', shooter, target)]),
            Script('Test - wait ' + arm, [('COUNTER', 'E213Frame', 3, go), ('COUNTER', 'E213Frame', 0, end),
                                          ('UNIT_HEALTH', target, 3, 100)],
                   [('INCREMENT_COUNTER', 1, wait)], once=False),
            Script('Test - first ' + arm, [('COUNTER', 'E213Frame', 3, go), ('UNIT_HEALTH', target, 0, 100)], [
                ('SET_UNIT_HEALTH_PERCENTAGE_TO_COUNTER', target, 'E213' + arm),
                ('COUNTER_MATH_VALUE', 'E213' + arm, 2, 1000),
                ('COUNTER_MATH_COUNTER', 'E213' + arm, 0, wait)]),
            Script('Test - end ' + arm, [('COUNTER', 'E213Frame', 2, end)], [
                ('SET_UNIT_HEALTH_PERCENTAGE_TO_COUNTER', target, hp),
                ('COUNTER_MATH_COUNTER', 'E213End', 0, hp)])]
        if arm == 'On':     # On's share x 1000 before Off's is added (scripts run in order; no arm named here)
            t.scripts.append(Script('Test - end shift', [('COUNTER', 'E213Frame', 2, end)],
                                    [('COUNTER_MATH_VALUE', 'E213End', 2, 1000)]))
    t.expect = [('完成帧', 0, 'ever==', end), ('原版', 0, 'ever>=', 1000), ('删模块', 0, 'ever>=', 1000)]
    t.bench = [('bench_camera', dict(x=1150, y=550, look=False)),
               ('bench_watch', dict(seconds=end // 15 + 25, every=1, sheet=False, lines=4))]
    return t


_GOS = {'a': check, 'b': lambda m: check(m, 60), 'c': lambda m: check(m, 90), 'd': lambda m: check(m, 75)}
MISSION = {'engine_charge_e': mission, 'engine_charge_n': lambda: mission(scan=False)}
CHECKS = {'engine_charge_e': _GOS, 'engine_charge_n': _GOS}
CONTROL_ARMS = {'engine_charge_e': ('On', 'Off'), 'engine_charge_n': ('On', 'Off')}
