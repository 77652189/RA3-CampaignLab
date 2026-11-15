"""E151: retail capturable flags and directly placed engineers."""
import re
from pathlib import Path

import labpaths
from maps import probe_range
from parts import Mission, Unit


def mission():
    m = Mission(name='CampCapE', map=probe_range, units=[])
    sdk = Path(labpaths.SDK3) / 'SageXML'
    xml = (sdk / 'Allied/Units/AlliedEngineer.xml').read_text(encoding='utf-8-sig')
    xml = xml.replace('id="AlliedEngineer"', 'id="CNVE151Off"', 1)
    # Keep the power declaration; remove only the capture update module.
    declaration = '<SpecialPower id="ModuleTag_CaptureSpecialPower" SpecialPowerTemplate="SpecialPowerCaptureControlPoint" UpdateModuleStartsAttack="true" />'
    xml, n = re.subn(r'<xi:include\s+href="DATA:Includes/CaptureBehavior.xml".*?/>', declaration, xml, flags=re.S)
    assert n == 1
    m.units.append(Unit('CNVE151Off', xml))
    for tag, owner, dx in [('neutral', 'neutral', 0), ('enemy', 's1', 500),
                           ('own', 'p1', 1000), ('off', 'neutral', 1500)]:
        m.put('CaptureFlag', 'base gun', dx, 0, side=owner,
              role=tag + ' flag', name='Capture ' + tag)
        m.put('CNVE151Off' if tag == 'off' else 'AlliedEngineer',
              'base gun', dx, -90, side='p1', role=tag + ' man', name='Engineer ' + tag)
    return m


MISSION = {'engine_capture': mission}
