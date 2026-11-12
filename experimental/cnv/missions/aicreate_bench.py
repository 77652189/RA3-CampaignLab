"""C-line CreateUnits slots: identical Guardian opener, minimum slot size 1 / 3.

The opener, not CreateUnits, supplies exactly three Guardians. Four unrelated
Peacekeepers are available at wake. Only the CreateUnits minimum differs;
TeamTemplate.MinUnits stays 1. This separates slot readiness from overall size.
"""
import os

import labpaths
from missions.aiteamfilter_bench import mission as team_mission
from missions.aiskirm_bench import ai_map
from parts import Unit


def mission(minimum, observe=False):
    m = team_mission(f'CampAICr{minimum}', tanks=0, inf=4, late=3, max_units=3)
    m.map = ai_map(m.map, library=False)
    m.map.TEAMS['create team'] = f'{m.player("s1")}/CNVStateTF_SimpleAttack_0_0'
    filename, xml, asset = m.assets[0]
    xml = xml.replace('</TeamTemplate>',
                      f'<CreateUnits UnitName="AlliedAntiVehicleVehicleTech1" '
                      f'MinUnits="{minimum}" MaxUnits="3"/></TeamTemplate>')
    m.assets[0] = filename, xml, asset
    m.facts['create minimum'] = minimum
    m.facts['home radius'] = 450.0
    m.cnv_units = ('AlliedAntiVehicleVehicleTech1', 'AlliedAntiInfantryInfantry')
    if observe:
        # Same passive carrier as D's engine_aiteams.host_unit; keep content here
        # so the C check consumes only the mission interface (G5).
        plant, host = 'AlliedPowerPlant', 'CNVCreateTeamsHost'
        with open(os.path.join(labpaths.SDK3, 'SageXML', 'Allied', 'Structures', plant + '.xml'),
                  encoding='utf-8') as f:
            xml = f.read()
        assert xml.count(f'id="{plant}"') == 1 and xml.count('<Behaviors>') == 1
        xml = xml.replace(f'id="{plant}"', f'id="{host}"').replace(f'EditorName="{plant}"', f'EditorName="{host}"')
        xml = xml.replace('<Behaviors>', '<Behaviors>\n'
                          '  <DeletionUpdate id="ModuleTag_CNVTeams" MinFrames="15" MaxFrames="4000"/>')
        m.units.append(Unit(host, xml, names=dict(unit=host),
                            what='被动队伍日志电厂：每15帧记录AI队员和激活状态', params=dict(of=plant, every=15)))
        m.put(host, 'east base', 250.0, 400.0, side='s1', role='teams host')
        m.name, m.ext = f'CampAICr{minimum}C', True
    return m


MISSION = {'aicr1': lambda: mission(1), 'aicr3': lambda: mission(3),
           'aicr1c': lambda: mission(1, observe=True), 'aicr3c': lambda: mission(3, observe=True)}
