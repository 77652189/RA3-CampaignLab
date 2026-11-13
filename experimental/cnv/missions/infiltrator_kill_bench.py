"""Retail Soviet crane KILL: hostile entry and friendly refusal controls."""
from maps import probe_range
from parts import Mission


def mission():
    m = Mission(name='CampInfKill', map=probe_range, units=[])
    for role, site, side in [('enemy', 'base', 's1'), ('ally', 'high', 's2')]:
        m.put('SovietCrane', site + ' gun', side=side, role=role,
              name='Kill crane ' + role)
        m.put('AlliedInfiltrationInfantry', site + ' gun', 0, -180,
              role=role + ' spy', name='Kill spy ' + role)
    return m


MISSION = {'engine_infkill': mission}
