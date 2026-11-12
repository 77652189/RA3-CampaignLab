"""Minimal retail VISION scene; all placement belongs to the mission layer."""
from maps import probe_range
from parts import Mission


def mission():
    m = Mission(name='CampInfVis', map=probe_range, units=[])
    for role, lane, side in (('enemy', 'base', 's1'), ('ally', 'high', 's2')):
        m.put('AlliedConstructionYard', lane + ' gun', side=side,
              role=role, name='Vision yard ' + role)
        m.put('AlliedInfiltrationInfantry', lane + ' gun', 0, -180,
              role=role + ' spy', name='Vision spy ' + role)
    for role, lane, dy, side in (('near', 'base', 700, 's1'),
                                 ('far', 'removed', 0, 's1'),
                                 ('control', 'low', 0, 's3')):
        m.put('AlliedEngineer', lane + ' gun', 0, dy, side=side,
              role=role, name='Vision marker ' + role)
    return m


MISSION = {'engine_infvis': mission}
