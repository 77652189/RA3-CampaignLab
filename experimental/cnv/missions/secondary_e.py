"""E174: retail multigunner listener, with a single-module deletion control."""
import re
from pathlib import Path

import labpaths
from maps import probe_range
from model import Mission, Unit


def mission(enabled=True):
    m = Mission(name='CampSecondOnE' if enabled else 'CampSecondOffE',
                map=probe_range, units=[], facts={'enabled': enabled})
    xml = (Path(labpaths.SDK3) / 'SageXML/Allied/Structures/AlliedBaseDefense.xml').read_text(encoding='utf-8-sig')
    if not enabled:
        xml, n = re.subn(r'<xi:include\s+href="DATA:Includes/InfantryFighting/IF_SecondaryObjectListener.xml"\s*/>', '', xml)
        assert n == 1
    ident = 'AlliedBaseDefense'
    m.units.append(Unit(ident, xml))
    m.assets.append((ident + '.xml', xml, 'GameObject:' + ident))
    m.replaces.append('GameObject:' + ident)
    m.put(ident, 'base gun', role='host', name='E174 Host')
    m.put('AlliedEngineer', 'base gun', 0, 100, role='crew', name='E174 Crew')
    m.put('AlliedPowerPlant', 'power 1', role='power')
    return m


MISSION = {'engine_secondon_e': mission, 'engine_secondoff_e': lambda: mission(False)}
