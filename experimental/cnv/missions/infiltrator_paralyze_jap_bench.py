"""PARALYZE entry and existing-unit filter controls for one retail Japanese tech center."""
from maps import probe_range
from parts import Mission


def mission():
    m = Mission(name='CampInfPJap', map=probe_range, units=[])
    for role, site, side in [('enemy', 'base', 's1'), ('ally', 'high', 's2')]:
        m.put('JapanTechStructure', site + ' gun', side=side, role=role,
              name='Paralyze tech ' + role)
        m.put('AlliedInfiltrationInfantry', site + ' gun', 0, -180,
              role=role + ' spy', name='Paralyze spy ' + role)
    for role, template, side, offset in [
            ('included', 'AlliedAntiVehicleVehicleTech3', 's1', -100),
            ('excluded', 'AlliedAntiVehicleVehicleTech1', 's1', 100),
            ('third', 'AlliedAntiVehicleVehicleTech3', 's3', 300)]:
        m.put(template, 'removed gun', offset, 0, side=side,
              role=role, name='Paralyze marker ' + role)
    return m


MISSION = {'engine_infpjap': mission}
