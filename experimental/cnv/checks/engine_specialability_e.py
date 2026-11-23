"""E176: retail shinobi pack status versus SpecialAbilityUpdate removal.

XML prediction: both smoke modifiers set NON_AUTOACQUIRABLE for 10s;
only the original sets UNATTACKABLE during its .5s PackTime. Press f45,
latch each status once, freeze final live/status observations at f240.
Predicted four HUD readings: 240 / 13 / 4 / 4. Exact phase boundaries,
stored-order restoration and other hosts/options remain gaps.
MEASURED a PASS: s14..59 frozen 240 / 13 / 4 / 4. Both smoke modifiers
were observed; only On ever had UNATTACKABLE, both clear and alive at f240.
The existing public Sim reproduces these readings without a rule change.

Check b (E208): the same press mid-walk 300 east (Speed 75, ordered f2, pressed f20), plus a Raw twin whose module
keeps all but Options="RECONSTITUTE_STORED_COMMAND". Prediction: Off walks on (~60 script frames to the goal); On
stands its .5 s PackTime then walks on (~8 frames later); Raw stands for good (not there by f150).
"""
import re
from pathlib import Path

import labpaths
from maps import probe_range
from parts import Mission, Script, Test, Unit, square, status


def mission():
    m = Mission(name='CampSpecAbilE', map=probe_range, units=[])
    source = (Path(labpaths.SDK3) / 'SageXML/Japan/Units/JapanInfiltrationInfantry.xml').read_text(encoding='utf-8-sig')
    for tag, site in [('On', 'base gun'), ('Off', 'high gun'), ('Raw', 'order gun')]:
        ident = 'CNVE176' + tag
        xml = source.replace('id="JapanInfiltrationInfantry"', f'id="{ident}"', 1)
        if tag == 'Off':
            xml, n = re.subn(r'<SpecialAbilityUpdate\b[^>]*/>', '', xml, flags=re.S)
            assert n == 1
        if tag == 'Raw':        # check b: the module with all but its Options
            xml, n = re.subn(r'(<SpecialAbilityUpdate\b[^>]*?)\s+Options="RECONSTITUTE_STORED_COMMAND"', r'\1', xml)
            assert n == 1
        m.units.append(Unit(ident, xml, abilities={'smoke': 'Command_SmokeBombSpecialPower'}))
        m.put(ident, site, role=tag, name='E176 ' + tag)
        m.waypoint('goal ' + tag, 'E176 Goal ' + tag, site, 300, 0)
    return m


def check(m):
    t = Test()
    t.counters = [('E176Frame', '完成帧'), ('E176Ever', '曾有状态'),
                  ('E176On', '原版终态'), ('E176Off', '对照终态')]
    t.scripts = [
        Script('Test - reveal', [], [('MAP_REVEAL_ALL_PERM', m.player('p1'))]),
        Script('Test - clock', [('COUNTER', 'E176Frame', 0, 240)],
               [('INCREMENT_COUNTER', 1, 'E176Frame')], once=False),
        Script('Test - smoke', [('COUNTER', 'E176Frame', 2, 45)], [
            ('NAMED_USE_COMMANDBUTTON_ABILITY', m.role(tag).name, m.ability(tag, 'smoke'))
            for tag in ('On', 'Off')])]
    for tag, weight in [('On', 1), ('Off', 2)]:
        name = m.role(tag).name
        for bit, state in [(1, 'UNATTACKABLE'), (4, 'NON_AUTOACQUIRABLE')]:
            cond = ('UNIT_HAS_OBJECT_STATUS', name, status(state))
            t.scripts.append(Script('Test - ever ' + tag + state,
                [('COUNTER', 'E176Frame', 3, 45), ('COUNTER', 'E176Frame', 0, 240), cond],
                [('INCREMENT_COUNTER', bit * weight, 'E176Ever')]))
            t.scripts.append(Script('Test - final ' + tag + state,
                [('COUNTER', 'E176Frame', 2, 240), cond],
                [('INCREMENT_COUNTER', 2 if state == 'UNATTACKABLE' else 1, 'E176' + tag)]))
        t.scripts.append(Script('Test - final live ' + tag,
            [('COUNTER', 'E176Frame', 2, 240), ('NAMED_NOT_DESTROYED', name)],
            [('INCREMENT_COUNTER', 4, 'E176' + tag)]))
    t.expect = [('完成帧', 0, 'ever==', 240), ('曾有状态', 0, 'ever==', 13),
                ('原版终态', 0, 'ever==', 4), ('对照终态', 0, 'ever==', 4)]
    t.bench = [('bench_watch', dict(seconds=58, every=1, sheet=False, lines=4))]
    return t


def walk(m):
    """E208, per arm: script frames it walks before it is in the 40-square goal 300 east (to f150), + 1000 once it
    is UNATTACKABLE; the smoke pressed at f20 mid-walk."""
    t = Test()
    t.counters = [('E176Frame', '帧'), ('E176WalkOn', '原版走'), ('E176WalkOff', '对照走'), ('E176WalkRaw', '无恢复走')]
    t.scripts = [Script('Test - reveal', [], [('MAP_REVEAL_ALL_PERM', m.player('p1'))]),
                 Script('Test - clock', [('COUNTER', 'E176Frame', 0, 150)],
                        [('INCREMENT_COUNTER', 1, 'E176Frame')], once=False)]
    for tag in ('On', 'Off', 'Raw'):
        name, area = m.role(tag).name, 'E176 Goal ' + tag
        t.areas[area] = square(*m.point('goal ' + tag), 40)
        t.scripts += [
            Script('Test - go ' + tag, [('COUNTER', 'E176Frame', 2, 2)],
                   [('MOVE_NAMED_UNIT_TO', name, m.mark('goal ' + tag))]),
            Script('Test - smoke ' + tag, [('COUNTER', 'E176Frame', 2, 20)],
                   [('NAMED_USE_COMMANDBUTTON_ABILITY', name, m.ability(tag, 'smoke'))]),
            Script('Test - walk ' + tag, [('COUNTER', 'E176Frame', 3, 1), ('COUNTER', 'E176Frame', 0, 150),
                                         ('NAMED_INSIDE_AREA', name, area, 'NOT')],
                   [('INCREMENT_COUNTER', 1, 'E176Walk' + tag)], once=False),
            Script('Test - ever ' + tag, [('UNIT_HAS_OBJECT_STATUS', name, status('UNATTACKABLE'))],
                   [('INCREMENT_COUNTER', 1000, 'E176Walk' + tag)])]
    t.expect = [('帧', 0, 'ever==', 150)]
    t.bench = [('bench_watch', dict(seconds=30, every=1, sheet=False, lines=4))]
    return t


MISSION = {'engine_specialability_e': mission}
CHECKS = {'engine_specialability_e': {'a': check, 'b': walk}}
CONTROL_ARMS = {'engine_specialability_e': ('On', 'Off')}
