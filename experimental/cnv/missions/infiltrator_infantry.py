"""One retail infantry infiltration configuration, with separated controls."""
from maps import infiltrator_batch
from parts import Mission


def mission():
    m = Mission(name='CampInfFoot', map=infiltrator_batch, units=[])
    for role, site, side in (('enemy', 'infantry', 's2'), ('ally', 'infantry friend', 's5')):
        m.put('AlliedBarracks', site, side=side, role=role, name='Infantry ' + role)
        m.put('AlliedInfiltrationInfantry', site, 0, -180,
              role=role + ' spy', name='Infantry ' + role + ' spy')
    for role, template, site, side in (
            ('match', 'AlliedEngineer', 'infantry marker', 's2'),
            ('wrong', 'AlliedAntiVehicleVehicleTech1', 'air marker', 's2'),
            ('third', 'AlliedEngineer', 'port marker', 's6')):
        m.put(template, site, side=side, role=role, name='Infantry ' + role)
    return m


MISSION = {'engine_inffoot': mission}
