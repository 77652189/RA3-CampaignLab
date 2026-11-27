"""Minimal retail VISION scene; all placement belongs to the mission layer."""
from maps import infiltrator_batch, probe_range
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


def trio():
    """Allied / Soviet / Japan enemy yards 2000 apart on one map, a spy 180 south and a same-owner marker 700 north
    of each (2000+ from the other yards: outside their 1000 shroud clearing)."""
    m = Mission(name='CampInfVis3', map=infiltrator_batch, units=[])
    for k, side in enumerate(('Allied', 'Soviet', 'Japan')):
        lane = side.lower()
        m.put(side + 'ConstructionYard', 'air', 2000 * k, 0, side='s1', role=lane, name='Vision3 yard ' + lane)
        m.put('AlliedInfiltrationInfantry', 'air', 2000 * k, -180, role=lane + ' spy', name='Vision3 spy ' + lane)
        m.put('AlliedEngineer', 'air', 2000 * k, 700, side='s1', role=lane + ' near', name='Vision3 near ' + lane)
    return m


MISSION = {'engine_infvis': mission, 'engine_infvis3': trio}
