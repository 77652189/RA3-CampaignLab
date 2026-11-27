"""E151: retail capturable flags and directly placed engineers."""
import re
from pathlib import Path

import labpaths
from maps import probe_range
from parts import Mission, Unit


def off_engineer():
    """The retail AlliedEngineer as CNVE151Off, its CaptureSpecialAbilityUpdate removed."""
    sdk = Path(labpaths.SDK3) / 'SageXML'
    xml = (sdk / 'Allied/Units/AlliedEngineer.xml').read_text(encoding='utf-8-sig')
    xml = xml.replace('id="AlliedEngineer"', 'id="CNVE151Off"', 1)
    # Keep the power declaration; remove only the capture update module.
    declaration = '<SpecialPower id="ModuleTag_CaptureSpecialPower" SpecialPowerTemplate="SpecialPowerCaptureControlPoint" UpdateModuleStartsAttack="true" />'
    xml, n = re.subn(r'<xi:include\s+href="DATA:Includes/CaptureBehavior.xml".*?/>', declaration, xml, flags=re.S)
    assert n == 1
    return Unit('CNVE151Off', xml)


def mission():
    m = Mission(name='CampCapE', map=probe_range, units=[off_engineer()])
    for tag, owner, dx in [('neutral', 'neutral', 0), ('enemy', 's1', 500),
                           ('own', 'p1', 1000), ('off', 'neutral', 1500)]:
        m.put('CaptureFlag', 'base gun', dx, 0, side=owner,
              role=tag + ' flag', name='Capture ' + tag)
        m.put('CNVE151Off' if tag == 'off' else 'AlliedEngineer',
              'base gun', dx, -90, side='p1', role=tag + ' man', name='Engineer ' + tag)
    return m


# A403 (checks/engine_capture.check_off): each lane's engineer on a half-health neutral CNVCapPlant.
OFF = {'base': 'AlliedEngineer', 'high': 'CNVE151Off', 'order': 'AlliedEngineer', 'removed': 'CNVE151Off'}


def off_plant():
    """AlliedPowerPlant as CNVCapPlant, its EngineerContain's CanEnterFilter (three engineers named) + CNVE151Off:
    bench 1 (CampCapOffA_mcp_1127_081833) the retail plant refused the clone by name."""
    sdk = Path(labpaths.SDK3) / 'SageXML'
    contain = (sdk / 'Includes/GenericEngineerContain.xml').read_text(encoding='utf-8-sig').split('?>', 1)[1]
    contain = contain.replace('</CanEnterFilter>', '<IncludeThing>CNVE151Off</IncludeThing></CanEnterFilter>')
    xml = (sdk / 'Allied/Structures/AlliedPowerPlant.xml').read_text(encoding='utf-8-sig')
    xml, n = re.subn(r'<xi:include\s+href="DATA:Includes/GenericEngineerContain.xml"\s*/>', contain,
                     xml.replace('id="AlliedPowerPlant"', 'id="CNVCapPlant"', 1))
    assert n == 1
    return Unit('CNVCapPlant', xml)


def off_mission():
    m = Mission(name='CampCapOff', map=probe_range, units=[off_engineer(), off_plant()])
    for lane, engineer in OFF.items():
        m.put('CNVCapPlant', lane + ' gun', side='neutral', role=lane, name='Plant ' + lane)
        m.put(engineer, lane + ' gun', 0, -180, role=lane + ' man', name='Man ' + lane)
    return m


MISSION = {'engine_capture': mission, 'engine_capoff': off_mission}
