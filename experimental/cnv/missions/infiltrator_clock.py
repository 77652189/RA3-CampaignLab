"""Two independent retail vision filters, separated hosts and distant markers."""
from maps import infiltrator_batch
from parts import Mission


def mission():
    m = Mission(name='CampInfClock', map=infiltrator_batch, units=[])
    for lane, host, marker, site, target, side in (
            ('air', 'AlliedAirfield', 'AlliedSupportAircraft', 'air', 'air marker', 's1'),
            ('vehicle', 'AlliedWarFactory', 'AlliedAntiVehicleVehicleTech1',
             'infantry', 'infantry marker', 's2')):
        m.put(host, site, side=side, role=lane, name=lane + ' clock host')
        m.put('AlliedInfiltrationInfantry', site, 0, -180,
              role=lane + ' spy', name=lane + ' clock spy')
        m.put(marker, target, side=side, role=lane + ' match', name=lane + ' clock match')
    return m


MISSION = {'engine_infclock': mission}
