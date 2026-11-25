"""C: initial tech ownership below/above retail's 75% fair-share gate.

Retail Allied/Japan/SovietBaseStates use 75%, 100%, 125%, Above=false.
Four OilDerricks (one map-neutral, three placed here). C's first prediction (two active players: 50 / 100 %) read
4/0/4 on both; B 11-25 (SWEEP, aitechsn): every owner's derricks over 4, x the map's 7 declared players + 1 = 8 --
own=1 -> 200 %, own=2 -> 400 %. Three independent states each; equality and a zero total are gaps.
"""
import math
import types

from missions import aistate_bench as setup


SWEEP = ((180, False), (375, False), (1000, False))


def mission(high, gates=((75, False), (75, True), (125, False)), name=None, others='p1'):
    """gates: the three states' (PercentOfFairShare, Above). B 11-25 SWEEP (aitechsl / aitechsh): all Above=false at
    180 / 375 / 1000 %, a state on (units away, home 0) iff share < its percent -- C's two runs read share >= 125 % for
    both; the sweep tells 7 map players x 1/4, 2/4 (175 / 350 %) from a total of the one neutral derrick (200 / 400 %)
    and from a divide by zero (none on). others: the side of the placed derricks not ours (aitechsn: neutral --
    a total of neutral ones only 1/3 x 2 = 67 %, 8 players x 1/4 still 200 %). work/re/b1125_techshare.md."""
    m = setup.mission(name or ('CampAITechH' if high else 'CampAITechL'), near=True)
    filename, xml, asset = m.assets[0]
    units = (setup.INF, setup.TANK, 'SovietAntiGroundAircraft')
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
        m.put('OilDerrick', site, side='s1' if k < (2 if high else 1) else others,
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
    m.cnv_tech_home = tuple(4 * (100 * m.facts['tech own'] / 4 * 8 >= p) ^ (4 * a) for p, a in gates)  # B 11-25
    return m


MISSION = {'aitechlow': lambda: mission(False), 'aitechhigh': lambda: mission(True),
           'aitechsl': lambda: mission(False, SWEEP, 'CampAITechSL'), 'aitechsh': lambda: mission(True, SWEEP, 'CampAITechSH'),
           'aitechsn': lambda: mission(False, ((60, False), (180, False), (375, False)), 'CampAITechSN', 'neutral')}
