"""E153 ActivateModuleSpecialPower: retail Athena button, single-module control.

XML prediction before bench: press at 5s; on gains GENERIC_TOGGLE_STATE and
IGNORING_STEALTH for 20s; off gains neither. Both hosts remain alive.
No forced effect bits, weapon nugget, production or recruitment is involved.
Evidence latches: pre-press both off=1; on active/off inactive=2; on later
inactive=4, with the latter requiring the active observation first. Predict 7.
Exact activation frame is observed, not assumed. See work/re/e153_activate.md.
MEASURED 2026-11-15 PASS: f76..371 on/off=111/100; f379=100/100;
f424 evidence=7, f531 both alive and inactive. Named replay also asserts
actual f152=111/100 and f379=100/100. Only linked status lifetime is modelled;
absorption, damage cap, early termination, repeated presses and other links
remain gaps. No SpecialPowerNugget dispatch coverage is claimed.
"""
import re
from pathlib import Path

import labpaths
from maps import probe_range
from parts import Mission, Script, Test, Unit, status


def mission():
    m = Mission(name='CampActE', map=probe_range, units=[])
    source = (Path(labpaths.SDK3) / 'SageXML/Allied/Units/AlliedAntiStructureVehicle.xml').read_text(encoding='utf-8-sig')
    for tag, site in [('on', 'base gun'), ('off', 'high gun')]:
        ident = 'CNVE153Athena' + tag
        xml = source.replace('id="AlliedAntiStructureVehicle"', f'id="{ident}"', 1)
        if tag == 'off':
            xml, n = re.subn(r'<ActivateModuleSpecialPower\b.*?</ActivateModuleSpecialPower>', '', xml, flags=re.S)
            assert n == 1
        m.units.append(Unit(ident, xml, abilities={'shield button': 'Command_ToggleShieldSphere'}))
        m.put(ident, site, side='p1', role=tag, name='E153 ' + tag)
    return m


def check(m):
    t = Test()
    t.counters = [('E153Frame', '帧数'), ('E153on', '激活'),
                  ('E153off', '对照'), ('E153Evidence', '证据')]
    t.scripts = [Script('Test - E153 start', [], [
        ('MAP_REVEAL_ALL_PERM', m.player('p1')),
        ('SET_MILLISECOND_TIMER', 'E153Press', 5.0)]),
        Script('Test - E153 frame', [], [('INCREMENT_COUNTER', 1, 'E153Frame')], once=False),
        Script('Test - E153 press', [('TIMER_EXPIRED', 'E153Press')], [
            ('NAMED_USE_COMMANDBUTTON_ABILITY', m.role(tag).name, m.ability(tag, 'shield button'))
            for tag in ('on', 'off')])]
    for tag in ('on', 'off'):
        name, counter = m.role(tag).name, 'E153' + tag
        t.scripts.append(Script('Test - E153 clear ' + tag, [], [('SET_COUNTER', counter, 0)], once=False))
        for bit, state in [(1, 'GENERIC_TOGGLE_STATE'), (10, 'IGNORING_STEALTH')]:
            t.scripts.append(Script('Test - E153 ' + tag + state,
                [('UNIT_HAS_OBJECT_STATUS', name, status(state))],
                [('INCREMENT_COUNTER', bit, counter)], once=False))
        t.scripts.append(Script('Test - E153 alive ' + tag, [('NAMED_NOT_DESTROYED', name)],
            [('INCREMENT_COUNTER', 100, counter)], once=False))
    for tag, bit, conds in [
        ('before', 1, [('COUNTER', 'E153Frame', 2, 45), ('COUNTER', 'E153on', 2, 100), ('COUNTER', 'E153off', 2, 100)]),
        ('active', 2, [('COUNTER', 'E153on', 2, 111), ('COUNTER', 'E153off', 2, 100)]),
        ('expired', 4, [('COUNTER', 'E153Frame', 3, 420), ('FLAG', 'E153 active', 1),
                       ('COUNTER', 'E153on', 2, 100), ('COUNTER', 'E153off', 2, 100)])]:
        t.scripts.append(Script('Test - E153 evidence ' + tag, conds,
            [('INCREMENT_COUNTER', bit, 'E153Evidence'), ('SET_FLAG', 'E153 ' + tag, 1)]))
    t.expect = [('帧数', 0, 'ever>=', 450), ('对照', 0, '==', 100),
                ('激活', 7, 'ever==', 111, 22), ('证据', 28, 'ever==', 7)]
    t.bench = [('bench_watch', dict(seconds=32, every=0.5, sheet=False, lines=4))]
    return t


MISSION = {'engine_activate': mission}
CHECKS = {'engine_activate': {'a': check}}
