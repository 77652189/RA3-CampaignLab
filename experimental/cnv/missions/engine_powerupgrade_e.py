"""E175: isolated retail turbine hosts and module-only deletion controls."""
import re
from pathlib import Path
import labpaths
from maps import probe_range
from model import Mission, Unit

UP = 'Upgrade_PowerPlantTurbine'
ROWS = [('normalon', 'p1', 'base gun', False, True),
        ('normaloff', 's1', 'high gun', False, False),
        ('advancedon', 's2', 'removed gun', True, True),
        ('advancedoff', 's3', 'switch gun', True, False)]


def mission():
    m = Mission(name='CampPwrUpE', map=probe_range, units=[])
    for tag, side, site, advanced, enabled in ROWS:
        template = 'SovietPowerPlant' + ('Advanced' if advanced else '')
        if not enabled:
            xml = (Path(labpaths.SDK3) / f'SageXML/Soviet/Structures/{template}.xml').read_text(
                encoding='utf-8-sig')
            xml, n = re.subn(r'<PowerUpgrade\b[^>]*>.*?</PowerUpgrade>', '', xml, flags=re.S)
            assert n == 1
            ident = template + 'E175Off'
            xml = xml.replace(f'id="{template}"', f'id="{ident}"', 1)
            m.units.append(Unit(ident, xml))
            template = ident
        m.put(template, site, side=side, role=tag, name='E175 ' + tag)
    return m


MISSION = {'engine_powerupgrade_e': mission}
