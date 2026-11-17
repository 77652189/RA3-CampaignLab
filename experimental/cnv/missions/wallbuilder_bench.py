"""WallBuilder initialization controls; full construction/connection remains unmeasured."""
import os
import re

import labpaths
from maps import festival
from parts import Mission, Unit


def wall(mode):
    name = 'CNVWall' + mode.title()
    with open(os.path.join(labpaths.SDK3, 'SageXML', 'Allied', 'Structures',
                           'AlliedWallPiece.xml'), encoding='utf-8-sig') as f:
        xml = f.read()
    xml = xml.replace('id="AlliedWallPiece"', f'id="{name}"', 1)
    pattern = r'<WallBuilderBehavior\b.*?</WallBuilderBehavior>'
    assert len(re.findall(pattern, xml, re.S)) == 1
    module = re.search(pattern, xml, re.S).group()
    if mode == 'none':
        replacement = ''
    else:
        replacement = module.replace('MaxNumSegments="10"',
                                     'MaxNumSegments="10" StartInSecondaryModel="%s"' %
                                     ('true' if mode == 'segment' else 'false'))
    xml = re.sub(pattern, lambda _: replacement, xml, flags=re.S)
    return Unit(name, xml, what='WallBuilder initialization ' + mode)


def mission():
    units = [wall(mode) for mode in ('hub', 'segment', 'none')]
    m = Mission(name='CampWallInit', map=festival, units=units, facts={})
    for i, unit in enumerate(units):
        m.put(unit.id, 'west field', 0, (i - 1) * 300, role=('hub', 'segment', 'none')[i],
              name='UNIT - Wall ' + ('hub', 'segment', 'none')[i])
    return m


MISSION = {'engine_wallinit': mission}
