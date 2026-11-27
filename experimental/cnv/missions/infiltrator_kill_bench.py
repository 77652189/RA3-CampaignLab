"""Retail Soviet Crane controls for hostile infiltration and friendly recycling."""
import re
from pathlib import Path

import labpaths
from maps import probe_range
from parts import Mission, Unit


def mission():
    m = Mission(name='CampInfKill', map=probe_range, units=[])
    for role, site, side in [('enemy', 'base', 's1'), ('ally', 'high', 's2')]:
        m.put('SovietCrane', site + ' gun', side=side, role=role,
              name='Kill crane ' + role)
        m.put('AlliedInfiltrationInfantry', site + ' gun', 0, -180,
              role=role + ' spy', name='Kill spy ' + role)
    return m


def recycle_mission(allied=False):
    source = Path(labpaths.SDK3, 'SageXML/Soviet/Structures/SovietCrane.xml')
    xml = source.read_text(encoding='utf-8-sig')
    template = 'CNVCraneNoRecycle'
    xml = xml.replace('id="SovietCrane"', f'id="{template}"', 1)
    xml, removed = re.subn(r'<SlaughterHordeContain\b.*?</SlaughterHordeContain>', '', xml, flags=re.S)
    assert removed == 1
    name = 'CampRecycleAl' if allied else 'CampRecycle'
    m = Mission(name=name, map=probe_range, units=[Unit(template, xml)], ext=True)
    lanes = [('on', 'base gun', 'SovietCrane', 'p1'), ('off', 'high gun', template, 'p1')]
    if allied:
        lanes.append(('ally', 'order gun', 'SovietCrane', 's2'))
    for tag, site, crane, side in lanes:
        m.put(crane, site, side=side, name=f'Crane {tag}', role=f'crane {tag}')
        m.put('SovietAntiVehicleVehicleTech1', site, 0, 200, name=f'Tank {tag}', role=f'tank {tag}')
        m.waypoint(tag, f'Crane pad {tag}', site)
    return m


MISSION = {'engine_infkill': mission, 'engine_cranerecycle': recycle_mission,
           'engine_cranerecycleally': lambda: recycle_mission(allied=True)}
