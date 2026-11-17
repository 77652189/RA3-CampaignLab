"""E189: standalone retail substructure, only-module deletion control.

AlliedConstructionYardRepairBay has 500 HP and an empty SubStructureBehavior.
The retail yard's SubStructureBuild is commented out. These map-placed bays
are explicitly NOT proven children of the separately placed yard.
Predict both start at 100%, take scripted 100 damage at f90 to 80%, and
survive deletion of the unrelated yard at f150. Freeze four HUD rows at
f240: frame / on HP / off HP / yard survival = 240 / 80 / 80 / 0.
This tests the standalone control, not parent binding or child cleanup.
Parent id, bind acceptance and forwarded damage remain gaps. See
work/re/e189_substructure.md. No synthetic SubStructureBuild is enabled.
MEASURED a PASS: f59=100/100/1, f120=80/80/1, f240=80/80/0.
The named public Sim replay matches the final four readings unchanged.
"""
import re
from pathlib import Path

import labpaths
from maps import probe_range
from model import Mission, Script, Test, Unit

HOST = 'AlliedConstructionYardRepairBay'


def mission():
    m = Mission(name='CampSubE', map=probe_range, units=[])
    source = (Path(labpaths.SDK3) / f'SageXML/Allied/Structures/{HOST}.xml').read_text(encoding='utf-8-sig')
    for tag, site in [('On', 'base gun'), ('Off', 'high gun')]:
        ident = 'CNVE189' + tag
        xml = source.replace(f'id="{HOST}"', f'id="{ident}"', 1)
        if tag == 'Off':
            xml, count = re.subn(r'<SubStructureBehavior\b[^>]*/>', '', xml)
            assert count == 1
        m.units.append(Unit(ident, xml))
        m.put(ident, site, role=tag, name='E189 ' + tag)
    m.put('AlliedConstructionYard', 'removed gun', role='yard', name='E189 yard')
    return m


def check(m):
    t = Test()
    t.counters = [('E189Frame', 'frame'), ('E189On', 'original'),
                  ('E189Off', 'control'), ('E189Yard', 'yard')]
    t.scripts = [
        Script('Test - clock', [('COUNTER', 'E189Frame', 0, 240)],
               [('INCREMENT_COUNTER', 1, 'E189Frame')], once=False),
        Script('Test - damage', [('COUNTER', 'E189Frame', 2, 90)],
               [('NAMED_DAMAGE', m.role(tag).name, 100) for tag in ('On', 'Off')]),
        Script('Test - yard removal', [('COUNTER', 'E189Frame', 2, 150)],
               [('NAMED_DELETE', m.role('yard').name)])]
    for tag in ('On', 'Off'):
        t.scripts.append(Script('Test - health ' + tag, [('COUNTER', 'E189Frame', 0, 241)],
            [('SET_UNIT_HEALTH_PERCENTAGE_TO_COUNTER', m.role(tag).name, 'E189' + tag)], once=False))
    t.scripts.extend([
        Script('Test - yard alive', [('NAMED_NOT_DESTROYED', m.role('yard').name)],
               [('SET_COUNTER', 'E189Yard', 1)], once=False),
        Script('Test - yard gone', [('NAMED_DESTROYED', m.role('yard').name)],
               [('SET_COUNTER', 'E189Yard', 0)], once=False)])
    t.expect = [('frame', 0, 'ever==', 240), ('original', 0, 'ever==', 80),
                ('control', 0, 'ever==', 80), ('yard', 0, 'ever==', 0)]
    t.bench = [('bench_watch', dict(seconds=100, every=1, sheet=False, lines=4, until='c1>=240'))]
    return t


MISSION = {'engine_substructure_e': mission}
CHECKS = {'engine_substructure_e': {'a': check}}
