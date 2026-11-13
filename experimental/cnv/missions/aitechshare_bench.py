"""C: initial tech ownership below/above retail's 75% fair-share gate.

Retail Allied/Japan/SovietBaseStates use 75%, 100%, 125%, Above=false.
Four OilDerricks (one map-neutral, three placed here), two active players:
own=1 -> 50% of fair share; own=2 -> 100% (player denominator INFERRED).
Three independent states: below75 / above75 / below125. Predicted home
counts low=0/4/0, high=4/0/0. This distinguishes a normalized fair share
from the raw owned fraction. Equality, zero total and extra players are gaps.
"""
import math
import types

from missions import aistate_bench as setup


def mission(high):
    m = setup.mission('CampAITechH' if high else 'CampAITechL', near=True)
    filename, xml, asset = m.assets[0]
    units = (setup.INF, setup.TANK, 'SovietAntiGroundAircraft')
    gates = ((75, False), (75, True), (125, False))
    states = []
    for i, (unit, (percent, above)) in enumerate(zip(units, gates)):
        sid = f'CNVTechShare{i}'
        state = setup._state(sid, '', unit, gate='const')
        state = state.replace('<ConstantHeuristic/>',
            f'<TechBuildingShareHeuristic PercentOfFairShare="{percent}%" Above="{str(above).lower()}"/>')
        state = state.replace('ClosestStructureHeuristic', 'CNVTechTarget')
        state = state.replace('LAND AMPHIBIOUS', 'LAND AMPHIBIOUS AIR')
        states.append(state)
    start = xml.index('  <AIStrategicStateDefinition ')
    end = xml.index('  <AIPersonalityDefinition ')
    target = ('  <AITargetingHeuristic id="CNVTechTarget" HeuristicType="EnemyStructure" '
              'SortType="Distance" VitalKindOf="FS_POWER" RequireUniqueTarget="false"/>\n')
    xml = xml[:start] + target + '\n'.join(states) + '\n' + xml[end:]
    xml = xml.replace('    <StrategicState id="CNVStateInf" State="CNVStateInf"/>\n'
                      '    <StrategicState id="CNVStateTank" State="CNVStateTank"/>',
                      '\n'.join(f'    <StrategicState id="CNVTechShare{i}" State="CNVTechShare{i}"/>'
                                for i in range(3)))
    m.assets[0] = filename, xml, asset
    for k in range(4):
        m.put(units[2], 'east base', 100, -100 + 70*k, side='s1',
              name=f'UNIT - Tech Heli {k}', role=f'tech heli {k}')
    m.cnv_units = units
    m.spawns.update((*units, 'OilDerrick'))
    # The fourth derrick is already in map.OBJECTS, neutral and unchanged.
    for k, site in enumerate(('outpost 1', 'outpost 2', 'outpost 3')):
        m.put('OilDerrick', site, side='s1' if k < (2 if high else 1) else 'p1',
              name=f'UNIT - Tech Oil {k}')
    # Initial map resources, not a scripted capture or a camp emplacement.
    # A local map copy also keeps the shared measured map unchanged.
    layout = types.ModuleType(m.map.__name__)
    layout.__dict__.update(vars(m.map))
    layout.OBJECTS = list(m.map.OBJECTS) + m.objects[-3:]
    layout.SCENERY = [o for o in m.map.SCENERY if all(
        math.dist((o.x, o.y), (d.x, d.y)) >= 250 for d in m.objects[-3:])]
    m.objects = m.objects[:-3]
    m.map = layout
    m.facts.update({'tech own': 2 if high else 1, 'tech total': 4})
    m.cnv_tech_home = (4, 0, 0) if high else (0, 4, 0)
    return m


MISSION = {'aitechlow': lambda: mission(False), 'aitechhigh': lambda: mission(True)}
