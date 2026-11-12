"""C-line CreateUnits slots: identical Guardian opener, minimum slot size 1 / 3.

The opener, not CreateUnits, supplies exactly three Guardians. Four unrelated
Peacekeepers are available at wake. Only the CreateUnits minimum differs;
TeamTemplate.MinUnits stays 1. This separates slot readiness from overall size.
"""
from missions.aiteamfilter_bench import mission as team_mission
from missions.aiskirm_bench import ai_map


def mission(minimum):
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
    return m


MISSION = {'aicr1': lambda: mission(1), 'aicr3': lambda: mission(3)}
