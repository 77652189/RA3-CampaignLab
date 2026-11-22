"""E178: retail SpiderHole toggle and single-module removal.

At frame 45 both infantry press the original toggle; at 120 the isolated
infantry presses it again. The other infantry starts beside a friendly
vehicle. XML predicts toggle status 7 on entry and 0 on exit, alive bit 8.
SpiderHoleUpdate scans vehicles within radius 5 every half second; whether
that forces exit is a hypothesis, not an implemented rule. Freeze status
at 90/180 (quiet + 100 * contact), and count accepted cast observations.
No forced infantry status or health input. See work/re/e178_spider.md.
MEASURED: both arms freeze 180/1515/1508/3. Toggle snapshots replay;
cast events remain strict xfail (Sim zero). Equal status readings do not
identify the vehicle scan effect or prove the radius precondition.
"""
import re
from pathlib import Path

import labpaths
from maps import probe_range
from parts import Mission, Script, Test, Unit


def mission(enabled=True):
    tag = 'On' if enabled else 'Off'
    m = Mission(name='CampSpider' + tag, map=probe_range, units=[], facts={'enabled': enabled})
    xml = (Path(labpaths.SDK3) / 'SageXML/Japan/Units/JapanAntiVehicleInfantry.xml').read_text(encoding='utf-8-sig')
    # The same SDK file also declares an unrelated pre-burrowed retail variant.
    xml, n = re.subn(r'<GameObject\s+id="JapanAntiVehicleInfantry_Ambush".*?</GameObject>', '', xml, flags=re.S)
    assert n == 1
    ident = 'CNVE178' + tag
    xml = xml.replace('id="JapanAntiVehicleInfantry"', f'id="{ident}"', 1)
    if not enabled:
        xml, n = re.subn(r'<SpiderHoleUpdate\b.*?</SpiderHoleUpdate>', '', xml, flags=re.S)
        assert n == 1
    m.units.append(Unit(ident, xml, abilities={'toggle': 'Command_ToggleSpiderHole',
                                           'power': 'SpecialPower_ToggleSpiderHole'}))
    for role, site in [('quiet', 'base gun'), ('contact', 'order gun')]:
        m.put(ident, site, role=role, name='E178 ' + role)
    m.put('AlliedAntiVehicleVehicleTech1', 'order gun', role='vehicle', name='E178 vehicle')
    return m


def check(m):
    t = Test()
    t.counters = [('E178Frame', '完成帧'), ('E178Entry', '入洞快照'),
                  ('E178Exit', '出洞快照'), ('E178Cast', '施放观测')]
    t.scripts = [
        Script('Test - reveal', [], [('MAP_REVEAL_ALL_PERM', m.player('p1'))]),
        Script('Test - clock', [('COUNTER', 'E178Frame', 0, 180)],
               [('INCREMENT_COUNTER', 1, 'E178Frame')], once=False),
        Script('Test - enter', [('COUNTER', 'E178Frame', 2, 45)], [
            ('NAMED_USE_COMMANDBUTTON_ABILITY', m.role(role).name, 'Command_ToggleSpiderHole')
            for role in ('quiet', 'contact')]),
        Script('Test - exit', [('COUNTER', 'E178Frame', 2, 120)], [
            ('NAMED_USE_COMMANDBUTTON_ABILITY', m.role('quiet').name, 'Command_ToggleSpiderHole')]),
        Script('Test - cast', [('PLAYER_TRIGGERED_SPECIAL_POWER', m.player('p1'),
                              'SpecialPower_ToggleSpiderHole')],
               [('INCREMENT_COUNTER', 1, 'E178Cast')], once=False)]
    for frame, counter in [(90, 'E178Entry'), (180, 'E178Exit')]:
        for role, scale in [('quiet', 1), ('contact', 100)]:
            name = m.role(role).name
            bits = [(1, ('UNIT_HAS_OBJECT_STATUS', name, 'IN_SPIDER_HOLE')),
                    (2, ('UNIT_HAS_OBJECT_STATUS', name, 'IMMOBILE_ALLOW_ROTATE')),
                    (4, ('UNIT_HAS_OBJECT_STATUS', name, 'NO_ATTACK')),
                    (8, ('NAMED_NOT_DESTROYED', name))]
            for value, condition in bits:
                t.scripts.append(Script(f'Test - sample {frame} {role} {value}',
                    [('COUNTER', 'E178Frame', 2, frame), condition],
                    [('INCREMENT_COUNTER', value * scale, counter)]))
    # Prior prediction: both enter via the toggle; quiet exits by second press.
    # Contact response is deliberately not predicted until the scan is observed.
    t.expect = [('完成帧', 0, 'ever==', 180), ('入洞快照', 0, 'ever>=', 815),
                ('出洞快照', 0, 'ever>=', 808), ('施放观测', 0, 'ever>=', 2)]
    t.bench = [('bench_watch', dict(seconds=45, every=1, sheet=False, lines=4))]
    return t


MISSION = {'spideron_e': mission, 'spideroff_e': lambda: mission(False)}
CHECKS = {name: {'a': check} for name in MISSION}
CONTROLS = {'spideroff_e': 'spideron_e'}
