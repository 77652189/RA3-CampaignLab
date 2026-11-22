"""TechBuilding minimum enemy distance: 0 / 2000, plus named host control.

The neutral oil replaces the target-pick host's power plant. Tech variants
only differ in MinDistanceFromEnemy. Candidate qualification and live distance
remain gaps unless independently observed; see work/re/c_mindist_report.md.
"""
import dataclasses
import math
import types

from missions.aitargetpick_bench import mission


def minimum(name, limit, named=False):
    expected = (4, 0, 0, 0) if limit == 0 or named else (0, 0, 0, 4)
    m = mission(name, [('CNVMinEnemy', None)], expected)
    target = m.find(m.role('plant').name)
    target.template, target.side = 'OilDerrick', 'neutral'
    m.cast['plant'] = dataclasses.replace(m.cast['plant'], template='OilDerrick', side='neutral')
    asset, xml, ref = m.assets[0]
    kind = 'NamedObject' if named else 'TechBuilding'
    heuristic = (f'<AITargetingHeuristic id="CNVMinEnemy" HeuristicType="{kind}" '
                 f'Name="{target.name}" VitalKindOf="SUPPLY_SOURCE" '
                 f'ForbiddenKindOf="" Location="Land" SearchRange="1200" '
                 f'MinDistanceFromEnemy="{limit}"/>')
    xml = xml.replace('<AIStrategicStateDefinition ', heuristic + '\n  <AIStrategicStateDefinition ', 1)
    m.assets[0] = asset, xml, ref
    return m


def two_candidates(name, limit, clear=False, search=1200, enemy='AlliedPowerPlant'):
    """Only the minimum changes: near oil has an enemy plant 200 away.

    The farther oil is over 1000 from that stationary enemy. At zero the
    closest oil to the AI base is predicted; at the retail oil threshold 350
    the farther oil is predicted. Engine instead stays home at 350; see
    work/re/c_mindist_pair_report.md. Exact boundary and qualification are gaps.
    B 11-21 (work/re/b1121_mindist.md): not the scenery by the far oil (clear:
    still home); SearchRange 3000 takes the far oil -- at 1200 it is out of
    range from the engine's AI base point (not the yard, 1011 off) at f16.
    enemy: the p1 structure 200 from the near oil (a wall should not count).
    """
    m = minimum(name, limit)
    asset, xml, ref = m.assets[0]   # B 11-21 H7: the SearchRange the find measures from the AI base
    m.assets[0] = asset, xml.replace('SearchRange="1200"', f'SearchRange="{search}"'), ref
    for role, template, side in (('barracks', 'OilDerrick', 'neutral'),
                                 ('tank', enemy, 'p1')):
        obj = m.find(m.role(role).name)
        obj.template, obj.side = template, side
        m.cast[role] = dataclasses.replace(m.cast[role], template=template, side=side)
    enemy = m.find(m.role('tank').name)
    near = m.find(m.role('plant').name)
    enemy.x, enemy.y = near.x, near.y + 200
    m.ext, m.ext_logs = True, ('target',)  # B 11-21: tgt: lines give each oil's verdict per find
    m.facts['minimum enemy distance'] = limit
    near_ok = limit == 0 or 'Wall' in enemy.template     # the enemy-distance find skips walls (b1121_mindist.md)
    m.facts['expect near oil'] = 4 if near_ok else 0
    m.facts['expect far oil'] = 0 if near_ok else 4
    if clear:   # B 11-21: the map's civilian scenery (fences, houses, trees) within 600 of the far oil removed
        far = m.find(m.role('barracks').name)
        layout = types.ModuleType(m.map.__name__)
        layout.__dict__.update(vars(m.map))
        layout.SCENERY = [o for o in m.map.SCENERY if math.dist((o.x, o.y), (far.x, far.y)) >= 600]
        m.map = layout
    return m


def tech_kind(name, tech=True):
    """Same neutral structure/site: oil qualifies, ordinary plant does not.

    The retail ClosestTechBuildingHeuristic host has no VitalKindOf filter.
    Enemy distance is disabled to isolate the registered tech-building set;
    this does not reopen the minimum-distance or fallback probes.
    Native negative control selects the inherited far oil instead of staying
    home; preserve the original prediction. See work/re/c_techkind_report.md.
    """
    from missions.aiteams_bench import host_unit, HOST
    m = minimum(name, 0)
    asset, xml, ref = m.assets[0]
    xml = xml.replace('CNVMinEnemy', 'ClosestTechBuildingHeuristic')
    xml = xml.replace('VitalKindOf="SUPPLY_SOURCE"', 'VitalKindOf=""')
    m.assets[0] = asset, xml, ref
    if not tech:
        obj = m.find(m.role('plant').name)
        obj.template = 'AlliedPowerPlant'
        m.cast['plant'] = dataclasses.replace(m.cast['plant'], template=obj.template)
        m.facts.update({'expect plant': 0, 'expect home': 4})
    m.ext, m.ext_logs = True, ('target',)  # D174: ra3ext tgt: lines (costly, on demand)
    m.units.append(host_unit())
    m.put(HOST, 'east base', 250, 400, side='s1', role='teams host')
    return m


MISSION = {
    'aimind0': lambda: minimum('CampMinZero', 0),
    'aimindhi': lambda: minimum('CampMinHigh', 2000),
    'aimindctl': lambda: minimum('CampMinCtl', 2000, named=True),
    'aimindpair0': lambda: two_candidates('CampMinPair0', 0),
    'aimindpair350': lambda: two_candidates('CampMinPair350', 350),
    'aimindpairclr': lambda: two_candidates('CampMinPairClr', 350, clear=True),
    'aimindpairfar': lambda: two_candidates('CampMinPairFar', 350, search=3000),
    'aimindpairwal': lambda: two_candidates('CampMinPairWal', 350, search=3000, enemy='AlliedWallSegmentPiece'),
    'aitechkind': lambda: tech_kind('CampTechKind'),
    'aitechnon': lambda: tech_kind('CampTechNon', False),
}
