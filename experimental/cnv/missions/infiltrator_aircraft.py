"""One retail aircraft infiltration configuration, with separated controls."""
from maps import infiltrator_batch
from parts import Mission


def mission():
    m = Mission(name='CampInfAir', map=infiltrator_batch, units=[])
    for role, site, side in (('enemy', 'air', 's1'), ('ally', 'air friend', 's5')):
        m.put('AlliedAirfield', site, side=side, role=role, name='Aircraft ' + role)
        m.put('AlliedInfiltrationInfantry', site, 0, -180,
              role=role + ' spy', name='Aircraft ' + role + ' spy')
    for role, template, site, side in (
            ('match', 'AlliedSupportAircraft', 'air marker', 's1'),
            ('wrong', 'AlliedAntiVehicleVehicleTech1', 'infantry marker', 's1'),
            ('third', 'AlliedSupportAircraft', 'ship wrong', 's6')):
        m.put(template, site, side=side, role=role, name='Aircraft ' + role)
    return m


MISSION = {'engine_infair': mission}
