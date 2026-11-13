"""C Expansion: two ore fields as candidate hypotheses and one ordinary named object.

Only HeuristicType differs (Expansion / NamedObject). BaseSelection is identical.
The aibsold/aibsnew pair instead keeps Expansion and only switches SortOrder.
The aibncap/aibnnone pair only switches PreferredNotBaseTypes.
The fields are NOT established legal expansion candidates: commands/team state
must establish selection before any candidate rule can be promoted.
"""
import types

import resources
from parts import Script
from missions.aiskirm_bench import ai_map
from missions.aitargetpick_bench import mission as target_mission
from missions.aiteams_bench import HOST, host_unit


def mission(expansion=True, sort_order=None, preferred_not=None):
    name = 'CampAIExp' if expansion else 'CampAIExpCtl'
    if sort_order:
        name = {'PREFER_OLDEST': 'CampAIBSOld', 'PREFER_NEWEST': 'CampAIBSNew'}[sort_order]
    if preferred_not is not None:
        name = {'CAPTURED': 'CampAIBNCap', '': 'CampAIBNNone'}[preferred_not]
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
    if sort_order:
        m.assets[0] = filename, xml.replace('SortOrder="PREFER_OLDEST"',
                                          f'SortOrder="{sort_order}"'), asset
        m.facts['base sort order'] = sort_order
    if preferred_not is not None:
        filename, xml, asset = m.assets[0]
        m.assets[0] = filename, xml.replace('PreferredNotBaseTypes="CAPTURED"',
                                          f'PreferredNotBaseTypes="{preferred_not}"'), asset
        m.facts['base preferred not'] = preferred_not
    m.units.append(host_unit())
    m.put(HOST, 'east base', 250, 400, side='s1', role='teams host')
    m.ext = True
    m.facts['expansion'] = expansion
    m.facts['candidate east'] = (4300.0, 2860.0)
    m.facts['candidate bluff'] = (3273.0, 1173.0)
    return m


def dual(sort_order):
    """Two real yards with distinct creation times; only SortOrder differs.

    INFERRED: script-created yards become eligible separate MAIN_BASEs. The
    contrast tests this hypothesis; two ore fields alone did not establish it.
    """
    m = mission(True, sort_order)
    m.name = 'CampBS2Old' if sort_order == 'PREFER_OLDEST' else 'CampBS2New'
    m.facts['dual bases'] = True
    # The second yard stands beside the bluff ore, away from the ore node.
    m.waypoint('new yard', 'CNV BS New Yard', 'bluff refinery', -300, 0)
    m.spawns.add('AlliedConstructionYard')
    filename, xml, asset = m.assets[0]
    xml = xml.replace('<ConstantHeuristic/>', '<ScriptedFlagHeuristic FlagName="CNV BS Active"/>')
    m.assets[0] = filename, xml, asset
    m.scripts += [
        Script('BS timers', [], [('SET_MILLISECOND_TIMER', 'CNV BS New', 12.0),
                                 ('SET_MILLISECOND_TIMER', 'CNV BS Start', 18.0)]),
        Script('BS new yard', [('TIMER_EXPIRED', 'CNV BS New')],
               [('CREATE_NAMED_ON_TEAM_AT_WAYPOINT', 'UNIT - CNV BS New Yard',
                 'AlliedConstructionYard', m.team('s1'), m.mark('new yard'))]),
        Script('BS activate', [('TIMER_EXPIRED', 'CNV BS Start')],
               [('SET_FLAG', '/CNV BS Active', 1)])]
    return m


MISSION = {'aibs2old': lambda: dual('PREFER_OLDEST'),
           'aibs2new': lambda: dual('PREFER_NEWEST'),
           'aiexpc': lambda: mission(True), 'aiexpctl': lambda: mission(False),
           'aibsold': lambda: mission(True, 'PREFER_OLDEST'),
           'aibsnew': lambda: mission(True, 'PREFER_NEWEST'),
           'aibncap': lambda: mission(preferred_not='CAPTURED'),
           'aibnnone': lambda: mission(preferred_not='')}
