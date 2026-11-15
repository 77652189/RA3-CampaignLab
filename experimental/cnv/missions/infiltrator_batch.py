"""Retail hosts and legal spy entry; no substitute module configuration."""
from maps import infiltrator_batch
from parts import Mission


def mission():
    m = Mission(name='CampInfBatch', map=infiltrator_batch, units=[])
    for lane, host, marker, side in (
            ('air', 'AlliedAirfield', 'AlliedAntiInfantryAircraft', 's1'),
            ('infantry', 'AlliedBarracks', 'AlliedEngineer', 's2'),
            ('ship', 'AlliedNavalYard', 'AlliedAntiVehicleShip', 's3'),
            ('port', 'CA_PortStructure', 'AlliedEngineer', 's4')):
        for suffix, owner in (('', side), (' friend', 's5')):
            role = lane + suffix
            m.put(host, role, side=owner, role=role, name=role + ' host')
            m.put('AlliedInfiltrationInfantry', role, 0, -180,
                  role=role + ' spy', name=role + ' spy')
        m.put(marker, lane + ' marker', side=side, role=lane + ' match', name=lane + ' match')
        m.put(marker, lane + ' marker', 300, 0, side='s6',
              role=lane + ' third', name=lane + ' third')
        wrong_site = 'ship wrong' if lane == 'ship' else lane + ' marker'
        wrong = 'AlliedAntiVehicleVehicleTech1' if lane != 'port' else 'JapanAntiInfantryShip'
        m.put(wrong, 'port far' if lane == 'port' else wrong_site, 0, -250,
              side=side, role=lane + ' wrong', name=lane + ' wrong')
    m.put('AlliedInfiltrationInfantry', 'port', -180, 0,
          role='port second', name='port second')
    return m


MISSION = {'engine_infbatch': mission}
