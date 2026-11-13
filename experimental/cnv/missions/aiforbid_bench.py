"""ForbiddenObjectStatus single-bit contrast; work/re/c_forbid_report.md.

Script-set UNDER_IRON_CURTAIN only, not a real Iron Curtain modifier. No
claim about invulnerability, multi-bit logic, aircraft or submerged targets.
"""
from missions.aitargetpick_bench import mission
from model import Script


def forbid(name, filtered, flagged):
    expected = (0, 4, 0, 0) if filtered and flagged else (4, 0, 0, 0)
    m = mission(name, [('CNVForbid', None)], expected)
    m.facts['status set'] = int(flagged)
    heuristic = ('<AITargetingHeuristic id="CNVForbid" HeuristicType="EnemyStructure" '
                 'SortType="Distance" VitalKindOf="STRUCTURE" RequireUniqueTarget="true" '
                 f'ForbiddenObjectStatus="{"UNDER_IRON_CURTAIN" if filtered else ""}"/>')
    asset, xml, ref = m.assets[0]
    xml = xml.replace('<AIStrategicStateDefinition ', heuristic + '\n  <AIStrategicStateDefinition ', 1)
    m.assets[0] = asset, xml, ref
    m.scripts.append(Script('CNV forbid status', [], [
        ('UNIT_CHANGE_OBJECT_STATUS', m.role('plant').name, 'UNDER_IRON_CURTAIN', int(flagged))]))
    return m


MISSION = {
    'aiforbidnone': lambda: forbid('CampForbidNone', False, True),
    'aiforbidset': lambda: forbid('CampForbidSet', True, True),
    'aiforbidclear': lambda: forbid('CampForbidClr', True, False),
}
