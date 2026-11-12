"""C Expansion: two ore fields as candidate hypotheses and one ordinary named object.

Only HeuristicType differs (Expansion / NamedObject). BaseSelection is identical.
The fields are NOT established legal expansion candidates: commands/team state
must establish selection before any candidate rule can be promoted.
"""
import types

import resources
from missions.aiskirm_bench import ai_map
from missions.aitargetpick_bench import mission as target_mission
from missions.aiteams_bench import HOST, host_unit


def mission(expansion=True):
    name = 'CampAIExp' if expansion else 'CampAIExpCtl'
    m = target_mission(name, [('ClosestStructureHeuristic', None)], (0, 0, 0, 4))
    cp = types.ModuleType(m.map.__name__)
    cp.__dict__.update(vars(m.map))
    resource_sites = resources.sites(cp.FIELDS)
    cp.SITES = {k: v for k, v in cp.SITES.items() if k not in resource_sites}
    cp.FIELDS = [f for f in cp.FIELDS if f.name in ('east', 'bluff')]
    cp.SITES.update(resources.sites(cp.FIELDS))
    cp.OBJECTS = [o for o in cp.OBJECTS if o.template != 'OreNode']
    cp.OBJECTS += resources.objects(cp.FIELDS, node_facing=resources.MEASURED)
    m.map = ai_map(cp, library=False)
    filename, xml, asset = m.assets[0]
    kind = 'Expansion' if expansion else 'NamedObject'
    heuristic = f'''  <AITargetingHeuristic id="CNVExpansion" HeuristicType="{kind}"
      Name="UNIT - CNV TP Plant" MinDistanceFromEnemy="0" SearchRange="5000" Location="Land">
      <BaseSelection PreferredBaseTypes="MAIN_BASE" PreferredNotBaseTypes="CAPTURED"
                     SortOrder="PREFER_OLDEST"/>
    </AITargetingHeuristic>
'''
    xml = xml.replace('<AIStrategicStateDefinition ', heuristic + '<AIStrategicStateDefinition ', 1)
    xml = xml.replace('TargetHeuristic="ClosestStructureHeuristic"', 'TargetHeuristic="CNVExpansion"')
    m.assets[0] = filename, xml, asset
    m.units.append(host_unit())
    m.put(HOST, 'east base', 250, 400, side='s1', role='teams host')
    m.ext = True
    m.facts['expansion'] = expansion
    m.facts['candidate east'] = (4300.0, 2860.0)
    m.facts['candidate bluff'] = (3273.0, 1173.0)
    return m


MISSION = {'aiexpc': lambda: mission(True), 'aiexpctl': lambda: mission(False)}
