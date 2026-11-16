"""Throwaway native kill-credit scene for C's counter action probe."""
from maps import probe_border
from parts import Mission


def mission():
    m = Mission(name='CampKillCount', map=probe_border, units=[], facts={})
    for side, dx in (('p1', 0.), ('s5', 1800.)):
        for i, template in enumerate(('SovietAntiInfantryInfantry',
                                      'SovietAntiInfantryInfantry',
                                      'AlliedAntiVehicleVehicleTech1')):
            for role, kind, owner, x in ((f'{side} gun {i}', 'AlliedAntiVehicleVehicleTech1', side, dx),
                                          (f'{side} victim {i}', template, 's4', dx+130.)):
                m.put(kind, 'stop row', x, -2300.+i*650., side=owner,
                      angle=0., name='CNV Kill '+role, role=role)
    for i, role in enumerate(('script', 'alive')):
        m.put('SovietAntiInfantryInfantry', 'stop row', 3500., -2300.+i*650.,
              side='s4', angle=0., name='CNV Kill '+role, role=role)
    return m


MISSION = {'engine_killcount': mission}
