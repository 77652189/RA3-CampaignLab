"""Three isolated retail firing lanes for the PARALYZE attack consumer."""
from maps import probe_range
from parts import Mission


def mission(host='AlliedTechStructure', name='CampInfAtk'):
    m = Mission(name=name, map=probe_range, units=[])
    for role, site, side in [('enemy', 'base', 's1'), ('ally', 'high', 's2')]:
        m.put(host, site + ' gun', side=side, role=role,
              name='Attack tech ' + role)
        m.put('AlliedInfiltrationInfantry', site + ' gun', 0, -180,
              role=role + ' spy', name='Attack spy ' + role)
    for role, lane, template, side in [
            ('included', 'removed', 'AlliedAntiVehicleVehicleTech3', 's1'),
            ('excluded', 'switch', 'AlliedAntiVehicleVehicleTech1', 's1'),
            ('third', 'low', 'AlliedAntiVehicleVehicleTech3', 's3')]:
        m.put(template, lane + ' gun', side=side, role=role,
              name='Attack car ' + role)
        m.put('AlliedWarFactory', lane + ' gun', 0, 180,
              role=role + ' target', name='Attack target ' + role)
    return m


def soviet_mission():
    return mission('SovietTechStructure', 'CampInfASov')


MISSION = {'engine_infpatk': mission, 'engine_infasov': soviet_mission}
