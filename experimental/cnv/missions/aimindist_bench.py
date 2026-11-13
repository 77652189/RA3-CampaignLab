"""TechBuilding minimum enemy distance: 0 / 2000, plus named host control.

The neutral oil replaces the target-pick host's power plant. Tech variants
only differ in MinDistanceFromEnemy. Candidate qualification and live distance
remain gaps unless independently observed; see work/re/c_mindist_report.md.
"""
import dataclasses

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


def two_candidates(name, limit):
    """Only the minimum changes: near oil has an enemy plant 200 away.

    The farther oil is over 1000 from that stationary enemy. At zero the
    closest oil to the AI base is predicted; at the retail oil threshold 350
    the farther oil is predicted. Engine instead stays home at 350; see
    work/re/c_mindist_pair_report.md. Exact boundary and qualification are gaps.
    """
    m = minimum(name, limit)
    for role, template, side in (('barracks', 'OilDerrick', 'neutral'),
                                 ('tank', 'AlliedPowerPlant', 'p1')):
        obj = m.find(m.role(role).name)
        obj.template, obj.side = template, side
        m.cast[role] = dataclasses.replace(m.cast[role], template=template, side=side)
    enemy = m.find(m.role('tank').name)
    near = m.find(m.role('plant').name)
    enemy.x, enemy.y = near.x, near.y + 200
    m.facts['minimum enemy distance'] = limit
    m.facts['expect near oil'] = 4 if limit == 0 else 0
    m.facts['expect far oil'] = 0 if limit == 0 else 4
    return m


MISSION = {
    'aimind0': lambda: minimum('CampMinZero', 0),
    'aimindhi': lambda: minimum('CampMinHigh', 2000),
    'aimindctl': lambda: minimum('CampMinCtl', 2000, named=True),
    'aimindpair0': lambda: two_candidates('CampMinPair0', 0),
    'aimindpair350': lambda: two_candidates('CampMinPair350', 350),
}
