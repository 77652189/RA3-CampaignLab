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


MISSION = {
    'aimind0': lambda: minimum('CampMinZero', 0),
    'aimindhi': lambda: minimum('CampMinHigh', 2000),
    'aimindctl': lambda: minimum('CampMinCtl', 2000, named=True),
}
