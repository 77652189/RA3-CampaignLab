"""ForbiddenObjectStatus contrasts; work/re/c_forbidmask_report.md.

Script-set UNDER_IRON_CURTAIN only, not a real Iron Curtain modifier.
The original two-bit mask is tested with only IRON set. Other status
combinations, real invulnerability, aircraft and submerged targets remain gaps.
"""
from missions.aitargetpick_bench import mission
from model import Script


def forbid(name, filtered, flagged, mask=None):
    expected = (0, 4, 0, 0) if filtered and flagged else (4, 0, 0, 0)
    m = mission(name, [('CNVForbid', None)], expected)
    m.facts['status set'] = int(flagged)
    forbidden = mask if mask is not None else ('UNDER_IRON_CURTAIN' if filtered else '')
    if mask is not None:
        m.facts['read unattackable'] = 1
    heuristic = ('<AITargetingHeuristic id="CNVForbid" HeuristicType="EnemyStructure" '
                 'SortType="Distance" VitalKindOf="STRUCTURE" RequireUniqueTarget="true" '
                 f'ForbiddenObjectStatus="{forbidden}"/>')
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
    'aifmasknone': lambda: forbid('CampMaskNone', False, True, ''),
    'aifmaskiron': lambda: forbid('CampMaskIron', True, True, 'UNDER_IRON_CURTAIN'),
    'aifmaskboth': lambda: forbid('CampMaskBoth', True, True, 'UNATTACKABLE UNDER_IRON_CURTAIN'),
}
