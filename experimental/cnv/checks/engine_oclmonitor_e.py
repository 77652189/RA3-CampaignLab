"""E222: OCLMonitorUpdate -- what Natasha's bombing-run monitor does when she changes target.

Retail: SovietCommandoTech1 has ModuleTag_BombingRunMonitor (Options MASTER RELEASE_WHEN_MASTER_CHANGES_TARGET) next
to its OCLSpecialPower BombingRun (OCL_SovietBombingRun: a ParabolicCurve TRACK_TARGET_OBJECT, InitialDelay 3.5 s,
ApproachTime 1.5 s, Soviet_BombingRun -- which carries an OCLMonitorUpdate with no options); her
SovietCommandoCallBombingRun (PreAttackDelay 0.5 s per target, FiringDuration 1 s, unlimited clip, no damage of its
own) fires the power through a SpecialPowerNugget, and SpecialPowerBombingRun has no ReloadTime. The bomber's bomb
(99999, radius 5) kills either target.

Three clones of Natasha, one per lane (base / high / order, 1 500 apart, each with its own construction yard for the
OCL's secondary location): On as retail, Mid with Options="MASTER" only, Off with the monitor taken out. At GO she
attacks target A (200 north), at SWITCH target B (150 east of A).

Prediction: MASTER keeps one bomber per master -- no new call while it lives; RELEASE_WHEN_MASTER_CHANGES_TARGET lets
it go on the switch, so On and Off call B's bomber at once (B's first loss about 5.5 s after SWITCH) and Mid only once
the first bomber is gone. Counters (each arm): A's frames from GO to its first loss x 1000 + B's from SWITCH to its
first loss (both stop at END); gate: target alive at END, A / B = 1 / 2 (On), 4 / 8 (Mid), 16 / 32 (Off).
Variants: n no switch, s she stops (NO_ATTACK + NAMED_STOP) at SWITCH. Read (11-24): as predicted, and the bomber let
go drops nothing -- also with MASTER alone when she stops attacking (the readings file).
"""
import re
from pathlib import Path

import labpaths
from checks.engine_missile import target
from maps import probe_range
from parts import Mission, Script, Test, Unit, status

GO, SWITCH, END = 30, 30 + 67, 30 + 400
ARMS = {'On': ('base', 1), 'Mid': ('high', 4), 'Off': ('order', 16)}    # arm: (lane, gate weight of A)
HOST, TAG = 'SovietCommandoTech1', 'OCLMonitorUpdate'
TARGET = 'CNVE222Target'


def mission(letter='E'):
    m = Mission(name='CampOCLMon' + letter,map=probe_range, units=[target(TARGET, health=5000)])
    source = (Path(labpaths.SDK3) / 'SageXML/Soviet/Units' / (HOST + '.xml')).read_text(encoding='utf-8-sig')
    for arm, (lane, _) in ARMS.items():
        ident = 'CNVE222' + arm
        xml = source.replace(f'id="{HOST}"', f'id="{ident}"', 1)
        for key, value in re.findall(r'<Define\s+name="([^"]+)"\s+value="([^"]+)"\s*/>', xml):
            xml = xml.replace('=$' + key, value).replace('$' + key, value)    # "=$X" is an expression
        xml = re.sub(r'<Defines>.*?</Defines>', '', xml, flags=re.S)
        monitor = re.compile(rf'\s*<{TAG}\s+id="ModuleTag_BombingRunMonitor".*?/>', re.S)
        if arm == 'Mid':
            xml, n = monitor.subn(f'\n\t\t\t<{TAG} id="ModuleTag_BombingRunMonitor" Options="MASTER" />', xml)
        else:
            xml, n = monitor.subn('', xml) if arm == 'Off' else (xml, 1)
        assert n == 1, (arm, n)
        m.units.append(Unit(ident, xml))
        site = lane + ' gun'
        m.put(ident, site, side='p1', role=arm, name='E222 ' + arm, angle=1.570796)
        m.put(TARGET, site, 0.0, 200.0, side='s1', role=arm + ' A', name='E222 ' + arm + ' A', angle=4.712389)
        m.put(TARGET, site, 150.0, 200.0, side='s1', role=arm + ' B', name='E222 ' + arm + ' B', angle=4.712389)
        m.put('SovietConstructionYard', site, -400.0, -200.0, side='p1', name='E222 ' + arm + ' yard')
    m.spawns |= {'Soviet_BombingRun', 'SovietBombingRunBombProjectile'}
    return m


def check(m, switch=True):
    t = Test()
    t.counters = [('E222On', '原版'), ('E222Mid', '只MASTER'), ('E222Off', '删模块'), ('E222Gate', '存活位')]
    t.scripts = [Script('Test - clock', [('COUNTER', 'E222Frame', 0, END)],
                        [('INCREMENT_COUNTER', 1, 'E222Frame')], once=False),
                 Script('Test - reveal', [], [('MAP_REVEAL_ALL_PERM', m.player('p1'))])]
    for arm, (_, weight) in ARMS.items():
        natasha, a, b = (m.role(arm + r).name for r in ('', ' A', ' B'))
        t.scripts += [
            Script('Test - quiet ' + arm, [], [('UNIT_CHANGE_OBJECT_STATUS', who, status(s), 1) for who, s in (
                (natasha, 'NO_ATTACK'), (natasha, 'IMMOBILE_ALLOW_ROTATE'),     # run 1: IMMOBILE, she never turned to B
                (a, 'NO_ATTACK'), (a, 'IMMOBILE'), (b, 'NO_ATTACK'), (b, 'IMMOBILE'))]),
            Script('Test - go ' + arm, [('COUNTER', 'E222Frame', 2, GO)], [
                ('UNIT_CHANGE_OBJECT_STATUS', natasha, status('NO_ATTACK'), 0), ('NAMED_ATTACK_NAMED', natasha, a)])]
        if switch:
            t.scripts.append(Script('Test - switch ' + arm, [('COUNTER', 'E222Frame', 2, SWITCH)], {
                'e': [('NAMED_ATTACK_NAMED', natasha, b)],
                's': [('UNIT_CHANGE_OBJECT_STATUS', natasha, status('NO_ATTACK'), 1), ('NAMED_STOP', natasha)]}[switch]))
        for who, start, wait in ((a, GO, 'E222WA' + arm), (b, SWITCH, 'E222WB' + arm)):
            t.scripts.append(Script(f'Test - wait {arm} {who[-1]}', [
                ('COUNTER', 'E222Frame', 3, start), ('COUNTER', 'E222Frame', 0, END), ('UNIT_HEALTH', who, 3, 100)],
                [('INCREMENT_COUNTER', 1, wait)], once=False))
        t.scripts += [
            Script('Test - end ' + arm, [('COUNTER', 'E222Frame', 2, END)], [
                ('COUNTER_MATH_COUNTER', 'E222' + arm, 0, 'E222WA' + arm),
                ('COUNTER_MATH_VALUE', 'E222' + arm, 2, 1000),
                ('COUNTER_MATH_COUNTER', 'E222' + arm, 0, 'E222WB' + arm)]),
            Script('Test - alive A ' + arm, [('COUNTER', 'E222Frame', 2, END), ('NAMED_NOT_DESTROYED', a)],
                   [('INCREMENT_COUNTER', weight, 'E222Gate')]),
            Script('Test - alive B ' + arm, [('COUNTER', 'E222Frame', 2, END), ('NAMED_NOT_DESTROYED', b)],
                   [('INCREMENT_COUNTER', 2 * weight, 'E222Gate')])]
    t.expect = [('原版', 0, 'ever>', 0)]
    t.bench = [('bench_camera', dict(x=2300, y=500, look=False)),
               ('bench_watch', dict(seconds=END // 15 + 25, every=1, sheet=False, lines=4))]
    return t


VARIANTS = {'engine_oclmon_e': 'E', 'engine_oclmon_n': 'N', 'engine_oclmon_s': 'S'}   # n: no switch; s: stopped
MISSION = {v: (lambda v=v: mission(VARIANTS[v])) for v in VARIANTS}
CHECKS = {v: {'a': lambda m, v=v: check(m, v[-1] if v[-1] in 'es' else None)} for v in VARIANTS}
