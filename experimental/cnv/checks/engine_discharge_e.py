"""E177: retail Waveforce premature discharge versus single-module removal.

Both attack at script frame 45, press the retail discharge button at 75.
The weapon has a four-second preattack delay. Predict that the original
hits before the removal control; both must eventually hit their targets.
First-hit counters and cast-event bits freeze at 210. No damage/clock
rule is fitted from this prediction. See work/re/e177_discharge.md.
MEASURED: on freezes 210/76/0/1, off 210/0/109/0. The original
off cast==1 prediction below failed and is retained. Sim hits at 47
in both arms; two strict xfails preserve this dispatch/preattack gap.
"""
import re
from pathlib import Path

import labpaths
from maps import probe_range
from parts import Mission, Script, Test, Unit, status


def mission(enabled=True):
    m = Mission(facts={'enabled': enabled}, name='CampDisch' + ('OnE' if enabled else 'OffE'), map=probe_range, units=[])
    source = (Path(labpaths.SDK3) / 'SageXML/Japan/Units/JapanAntiStructureVehicle.xml').read_text(encoding='utf-8-sig')
    for tag, lane in [('On' if enabled else 'Off', 'base')]:
        ident = 'CNVE177' + tag
        xml = source.replace('id="JapanAntiStructureVehicle"', f'id="{ident}"', 1)
        if tag == 'Off':
            xml, n = re.subn(r'<PrematureDischargeSpecialPower\b[^>]*/>', '', xml)
            assert n == 1
        # Publishing the button permits observation; it does not prove acceptance.
        m.units.append(Unit(ident, xml, abilities={
            'fire': 'Command_JASV_FireKiCannon',
            'power': 'SpecialPower_JASV_FireKiCannon'}))
        m.put(ident, lane + ' gun', role=tag, name='E177 ' + tag, angle=1.570796)
        m.put('AlliedPowerPlant', lane + ' gun', 0, 350, side='s1',
              role=tag + ' target', name='E177 ' + tag + ' target')
    return m


def check(m):
    tags = ['On' if m.facts['enabled'] else 'Off']
    t = Test()
    t.counters = [('E177Frame', '完成帧'), ('E177On', '原版首伤'),
                  ('E177Off', '对照首伤'), ('E177Cast', '施放观测')]
    t.scripts = [
        Script('Test - reveal', [], [('MAP_REVEAL_ALL_PERM', m.player('p1'))]),
        Script('Test - clock', [('COUNTER', 'E177Frame', 0, 210)],
               [('INCREMENT_COUNTER', 1, 'E177Frame')], once=False),
        Script('Test - discharge', [('COUNTER', 'E177Frame', 2, 75)], [
            ('NAMED_USE_COMMANDBUTTON_ABILITY', m.role(tag).name, 'Command_JASV_FireKiCannon')
            for tag in tags]),
        Script('Test - cast seen', [('PLAYER_TRIGGERED_SPECIAL_POWER', m.player('p1'),
                                   'SpecialPower_JASV_FireKiCannon')],
               [('INCREMENT_COUNTER', 1, 'E177Cast')])]
    for tag in tags:
        gun, target = m.role(tag).name, m.role(tag + ' target').name
        t.scripts += [
            Script('Test - quiet ' + tag, [], [
                ('UNIT_CHANGE_OBJECT_STATUS', gun, status('NO_ATTACK'), 1)]),
            Script('Test - attack ' + tag, [('COUNTER', 'E177Frame', 2, 45)], [
                ('UNIT_CHANGE_OBJECT_STATUS', gun, status('NO_ATTACK'), 0),
                ('NAMED_ATTACK_NAMED', gun, target)]),
            Script('Test - first hit ' + tag, [('COUNTER', 'E177Frame', 0, 210),
                ('UNIT_HEALTH', target, 0, 100)], [
                ('SET_COUNTER_TO_COUNTER', 'E177' + tag, 'E177Frame'),
                ('UNIT_CHANGE_OBJECT_STATUS', gun, status('NO_ATTACK'), 1)])]
    t.expect = [('完成帧', 0, 'ever==', 210), ('原版首伤' if m.facts['enabled'] else '对照首伤', 0, 'ever>=', 1), ('施放观测', 0, 'ever==', 1)]
    t.bench = [('bench_watch', dict(seconds=55, every=1, sheet=False, lines=4))]
    return t


MISSION = {'dischargeon_e': mission, 'dischargeoff_e': lambda: mission(False)}
CHECKS = {name: {'a': check} for name in MISSION}
