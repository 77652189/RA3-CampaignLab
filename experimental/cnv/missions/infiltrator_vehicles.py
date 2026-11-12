"""Existing-unit controls for retail vehicle-factory infiltration."""
from maps import probe_range
from parts import Mission


def mission():
    m = Mission(name='CampInfVeh', map=probe_range, units=[])
    for role, lane, side in (('enemy', 'base', 's1'), ('ally', 'high', 's2')):
        m.put('AlliedWarFactory', lane + ' gun', side=side,
              role=role, name='Vehicle factory ' + role)
        m.put('AlliedInfiltrationInfantry', lane + ' gun', 0, -180,
              role=role + ' spy', name='Vehicle spy ' + role)
    for role, template, lane, side in (
            ('vehicle', 'AlliedAntiVehicleVehicleTech1', 'removed', 's1'),
            ('infantry', 'AlliedEngineer', 'switch', 's1'),
            ('third', 'AlliedAntiVehicleVehicleTech1', 'low', 's3')):
        m.put(template, lane + ' gun', side=side, role=role, name='Vehicle marker ' + role)
    return m


MISSION = {'engine_infveh': mission}
