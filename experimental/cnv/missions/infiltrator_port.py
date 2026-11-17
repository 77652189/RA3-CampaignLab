"""Independent retail port VISION and second-entry blocking controls."""
from maps import infiltrator_batch
from parts import Mission


def mission():
    m = Mission(name='CampInfPort', map=infiltrator_batch, units=[])
    for role, site, side in (('enemy', 'port', 's4'), ('ally', 'infantry', 's5')):
        m.put('CA_PortStructure', site, side=side, role=role, name='Port ' + role)
        m.put('AlliedInfiltrationInfantry', site, 0, -180,
              role=role + ' spy', name='Port ' + role + ' spy')
    m.put('AlliedInfiltrationInfantry', 'port', -180, 0,
          role='second', name='Port second spy')
    for role, site, dx, dy, side in (
            ('match', 'port', 0, 550, 's4'),
            ('third', 'port', 200, 550, 's6'),
            ('wrong', 'infantry marker', 0, 0, 's4')):
        m.put('AlliedEngineer', site, dx, dy, side=side,
              role=role, name='Port ' + role)
    return m


MISSION = {'engine_infport': mission}
