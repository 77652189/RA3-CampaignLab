"""C-line SortByDistance pair: far Guardian inserted first, near second.

One SimpleAttack team, capacity one, identical candidates/target/wake in both
builds. Candidate-to-target distances differ from candidate-to-yard ordering.
The check observes named departures, not an unresolved dynamic team counter.
"""
from missions.aiteamfilter_bench import mission as team_mission, TANK
from missions.aiskirm_bench import ai_map


def mission(sort):
    m = team_mission(f'CampAISort{int(sort)}', tanks=0, inf=0, max_units=1,
                     kinds='IncludeKindOf="VEHICLE"')
    m.map = ai_map(m.map, library=False)
    candidates = []
    for identity, dx in (('far', -50.0), ('near', -350.0)):
        o = m.put(TANK, 'east base', dx, 160.0, side='s1', angle=3.1416,
                  name=f'UNIT - CNV Sort {identity}', role=f'candidate {identity}')
        candidates.append((identity, o.name, (o.x, o.y)))
    target = next(o for o in m.objects if o.name == m.role('player target').name)
    m.cnv_candidates = tuple(candidates)
    m.cnv_target = (target.x, target.y)
    m.facts |= {'sort by distance': int(sort), 'departure radius': 80.0}
    filename, xml, asset = m.assets[0]
    xml = xml.replace('<TeamTemplate ', f'<TeamTemplate SortByDistance="{str(sort).lower()}" ')
    m.assets[0] = filename, xml, asset
    return m


MISSION = {'aisort0': lambda: mission(False), 'aisort1': lambda: mission(True)}
