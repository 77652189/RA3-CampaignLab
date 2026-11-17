"""Independent retail naval infiltration, with legal water/land controls."""
from maps import infiltrator_batch
from parts import Mission


def mission():
    m = Mission(name='CampInfShip', map=infiltrator_batch, units=[])
    for role, site, side in (('enemy', 'ship', 's3'), ('ally', 'ship friend', 's5')):
        m.put('AlliedNavalYard', site, side=side, role=role, name='Ship ' + role)
        m.put('AlliedInfiltrationInfantry', site, 0, -180,
              role=role + ' spy', name='Ship ' + role + ' spy')
    for role, template, site, side in (
            ('match', 'AlliedAntiAirShip', 'ship marker', 's3'),
            ('wrong', 'AlliedAntiVehicleVehicleTech1', 'air marker', 's3'),
            ('third', 'AlliedAntiAirShip', 'port far', 's6')):
        m.put(template, site, side=side, role=role, name='Ship ' + role)
    return m


MISSION = {'engine_infship': mission}
