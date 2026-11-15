"""E158 RadarBehavior: isolated retail dish / module-removal HUD control.

Prediction (INFERRED, before bench): without the native PlayerSpellBook
RadarBehavior, the minimap works only with the dish's module, and stops after
the dish is deleted at 12 seconds. The second build removes only that module.
No reveal-all, radar UI toggle, or injected effect state is used. Four counters
measure frame, dish survival, support survival and sufficient power, NOT radar.
Saved full frames must be inspected for the independent minimap output.
SpellBook is linked over retail under its own id; no other radar host is placed.
This diagnostic alone does not register module coverage. See work/re/e158_radar.md.

MEASURED 2026-11-15: both prerequisites PASS. On: f151=1/1/1,
minimap terrain; f303=0/1/1, Allied emblem. Off: f149=1/1/1,
f308=0/1/1, emblem both times. Named model provider replay passes;
PLAYER_HAS_POWER script replay is a separate strict xfail.
"""
import re
from pathlib import Path

import labpaths
from maps import probe_range
from model import Mission, Script, Test, Unit


def without_radar(xml):
    xml, count = re.subn(r'<RadarBehavior\b[^>]*/>', '', xml)
    assert count == 1
    return xml


def mission(enabled=True):
    m = Mission(name='CampRadarE' if enabled else 'CampRadarOffE', map=probe_range,
                facts={'radar_module': enabled})
    sage = Path(labpaths.SDK3) / 'SageXML'
    spellbook = (sage / 'System/PlayerSpellBook.xml').read_text(encoding='utf-8-sig')
    m.assets.append(('E158SpellBook.xml', without_radar(spellbook), 'GameObject:PlayerSpellBook'))
    m.replaces.append('GameObject:PlayerSpellBook')
    source = (sage / 'Allied/Structures/AlliedRadarDish.xml').read_text(encoding='utf-8-sig')
    ident = 'CNVE158Radar'
    source = source.replace('id="AlliedRadarDish"', f'id="{ident}"', 1)
    m.units.append(Unit(ident, source if enabled else without_radar(source)))
    m.put(ident, 'base gun', role='dish', name='E158 dish')
    m.put('AlliedConstructionYard', 'base gun', 0, 650, role='yard', name='E158 yard')
    m.put('AlliedPowerPlant', 'base gun', 400, 0, role='power', name='E158 power')
    return m


def check(m):
    t = Test()
    t.counters = [('E158Frame', '帧数'), ('E158Dish', '宿主量'),
                  ('E158Support', '前置量'), ('E158Power', '供电量')]
    t.scripts = [
        Script('Test - E158 start', [], [('SET_MILLISECOND_TIMER', 'E158 delete', 12.)]),
        Script('Test - E158 frame', [], [('INCREMENT_COUNTER', 1, 'E158Frame')], once=False),
        Script('Test - E158 clear', [], [('SET_COUNTER', c, 0) for c, _ in t.counters[1:]], once=False),
        Script('Test - E158 dish', [('NAMED_NOT_DESTROYED', m.role('dish').name)],
               [('SET_COUNTER', 'E158Dish', 1)], once=False),
        Script('Test - E158 support', [('NAMED_NOT_DESTROYED', m.role('yard').name),
                                      ('NAMED_NOT_DESTROYED', m.role('power').name)],
               [('SET_COUNTER', 'E158Support', 1)], once=False),
        Script('Test - E158 powered', [('PLAYER_HAS_POWER', m.player('p1'))],
               [('SET_COUNTER', 'E158Power', 1)], once=False),
        Script('Test - E158 delete', [('TIMER_EXPIRED', 'E158 delete')],
               [('NAMED_DELETE', m.role('dish').name)]),
    ]
    t.expect = [('宿主量', 5, '==', 1, 10), ('宿主量', 16, '==', 0, 20),
                ('前置量', 5, '==', 1, 20), ('供电量', 5, '==', 1, 20)]
    t.bench = [('bench_watch', dict(seconds=24, every=1, sheet=False, lines=4))]
    return t


MISSION = {'engine_radar': mission, 'engine_radaroff': lambda: mission(False)}
CHECKS = {name: {'a': check} for name in MISSION}
