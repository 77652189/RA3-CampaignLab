"""E182: retail pack/deploy cycle, with/without only MCV storage.

Prediction before bench: both empty-payload cycles complete (mask 15), the
name survives (1), and no configured child appears (0). This does NOT measure
storage: retail SubStructureBuild is commented out. COPY_UPGRADES remains
untouched and upgrade preservation cannot identify this module's effect.
Four HUD rows expose frame, completed stages, named survival, and child mask;
none exposes stored child count, parent binding, or save/restore acceptance.
See work/re/e182_substorage.md. No synthetic child/upgrade is introduced.

E243 (bench 11-25, watched to f450): on and off both complete the two cycles
(15 at f440 / f443), alive 1 and child 0 throughout -- the module stores
nothing in retail (不涉及, inventory.py); readings in engine_substorage.readings.toml.
"""
import re
from pathlib import Path

import labpaths
from maps import probe_range
from model import Mission, Script, Test

NAME = 'E182 yard'
YARD, MCV = 'AlliedConstructionYard', 'AlliedMCV'
# AlliedCrane, the cut SubStructureBuild's third child, is not counted: since spawns compile from the SDK XML (11-17),
# its FXListBehavior Replace of ModuleTag_DieSound crashes BinaryAssetBuilder (IndexOutOfRange in NodeJoiner)
CHILDREN = ('AlliedRadarDish', 'AlliedConstructionYardRepairBay')


def mission(enabled=True):
    m = Mission(name='CampStoreOn' if enabled else 'CampStoreOff', map=probe_range,
                facts={'storage': enabled})
    source = (Path(labpaths.SDK3) / 'SageXML/Allied/Units/AlliedMCV.xml').read_text(encoding='utf-8-sig')
    if not enabled:
        source, count = re.subn(r'<SubStructureStorageBehavior\b[^>]*/>', '', source)
        assert count == 1
    m.assets.append(('E182MCV.xml', source, 'GameObject:AlliedMCV'))
    m.replaces.append('GameObject:AlliedMCV')
    m.spawns |= {MCV, *CHILDREN}
    m.put(YARD, 'base gun', role='yard', name=NAME)
    m.waypoint('deploy', 'E182 deploy', 'base gun')
    return m


def check(m):
    t = Test()
    t.counters = [('E182Frame', '帧数'), ('E182Stage', '完成量'),
                  ('E182Alive', '存活量'), ('E182Child', '子体量')]
    times = (1., 8., 16., 23.)
    samples = (5., 13., 20., 29.)
    t.scripts.append(Script('Test - E182 start', [],
        [('SET_MILLISECOND_TIMER', f'E182 order {i}', at) for i, at in enumerate(times)]))
    t.scripts.append(Script('Test - E182 frame', [], [('INCREMENT_COUNTER', 1, 'E182Frame')], once=False))
    for i in range(4):
        action = (('NAMED_USE_COMMANDBUTTON_ABILITY', NAME, 'Command_PackAlliedMCV') if i % 2 == 0 else
                  ('NAMED_USE_COMMANDBUTTON_ABILITY_AT_WAYPOINT', NAME, 'Command_UnPackAlliedMCV', m.mark('deploy')))
        t.scripts.append(Script(f'Test - E182 order {i}', [('TIMER_EXPIRED', f'E182 order {i}')], [action]))
        t.scripts.append(Script(f'Test - E182 sample {i}',
            [('COUNTER', 'E182Frame', 2, int(samples[i] * 15)),
             ('PLAYER_HAS_OBJECT_COMPARISON', m.player('p1'), 3, 1, MCV if i % 2 == 0 else YARD)],
            [('INCREMENT_COUNTER', 2 ** i, 'E182Stage')]))
    t.scripts.append(Script('Test - E182 clear', [], [('SET_COUNTER', 'E182Alive', 0),
                                                                  ('SET_COUNTER', 'E182Child', 0)], once=False))
    t.scripts.append(Script('Test - E182 alive', [('NAMED_NOT_DESTROYED', NAME)],
                           [('SET_COUNTER', 'E182Alive', 1)], once=False))
    for i, child in enumerate(CHILDREN):
        t.scripts.append(Script(f'Test - E182 child {i}',
            [('PLAYER_HAS_OBJECT_COMPARISON', m.player('p1'), 3, 1, child)],
            [('INCREMENT_COUNTER', 2 ** i, 'E182Child')], once=False))
    t.expect = [('完成量', 29.5, '==', 15, 60), ('存活量', 3, '==', 1, 60), ('子体量', 3, '==', 0, 60)]
    t.bench = [('bench_watch', dict(seconds=60, every=1, sheet=False, lines=4, until='c1>=450'))]
    return t


MISSION = {'engine_substorage_on': mission, 'engine_substorage_off': lambda: mission(False)}
CHECKS = {name: {'a': check} for name in MISSION}

CONTROLS = {'engine_substorage_off': 'engine_substorage_on'}
