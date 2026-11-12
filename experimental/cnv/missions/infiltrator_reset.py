"""Retail Iron Curtain RESET: separate enemy and friendly owners, powered pads."""
from maps import probe_range
from parts import Mission


def mission():
    m = Mission(name='CampInfReset', map=probe_range, units=[])
    for role, lane, side in (('enemy', 'base', 's1'), ('ally', 'high', 's2')):
        m.put('SovietSuperWeapon', lane + ' gun', side=side,
              role=role, name='Reset building ' + role)
        m.put('SovietPowerPlant', lane + ' gun', 350, 0, side=side,
              role=role + ' plant', name='Reset plant ' + role)
        m.put('AlliedInfiltrationInfantry', lane + ' gun', 0, -180,
              role=role + ' spy', name='Reset spy ' + role)
    return m


MISSION = {'engine_infreset': mission}
