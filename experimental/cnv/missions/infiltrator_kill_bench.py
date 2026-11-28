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


def recycle_mission(allied=False, *, apocalypse=False):
    source = Path(labpaths.SDK3, 'SageXML/Soviet/Structures/SovietCrane.xml')
    xml = source.read_text(encoding='utf-8-sig')
    template = 'CNVCraneNoRecycle'
    xml = xml.replace('id="SovietCrane"', f'id="{template}"', 1)
    xml, removed = re.subn(r'<SlaughterHordeContain\b.*?</SlaughterHordeContain>', '', xml, flags=re.S)
    assert removed == 1
    name = 'CampRecycleAl' if allied else 'CampRecycle'
    if apocalypse:
        name = 'CampRecycleAp'
    m = Mission(name=name, map=probe_range, units=[Unit(template, xml)], ext=True)
    lanes = [('on', 'base gun', 'SovietCrane', 'p1'), ('off', 'high gun', template, 'p1')]
    if allied:
        lanes.append(('ally', 'order gun', 'SovietCrane', 's2'))
    if apocalypse:
        lanes.append(('apoc', 'order gun', 'SovietCrane', 'p1'))
    for tag, site, crane, side in lanes:
        m.put(crane, site, side=side, name=f'Crane {tag}', role=f'crane {tag}')
        tank = 'SovietAntiVehicleVehicleTech3' if apocalypse and tag != 'on' else 'SovietAntiVehicleVehicleTech1'
        m.put(tank, site, 0, 200, name=f'Tank {tag}', role=f'tank {tag}')
        m.waypoint(tag, f'Crane pad {tag}', site)
    return m


MISSION = {'engine_infkill': mission, 'engine_cranerecycle': recycle_mission,
           'engine_cranerecycleally': lambda: recycle_mission(allied=True),
           'engine_cranerecycleapoc': lambda: recycle_mission(apocalypse=True)}
