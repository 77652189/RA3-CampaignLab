"""ForbiddenObjectStatus contrasts; work/re/c_forbidmask_report.md.

Script-set status bits, not real ability modifiers. The original two-bit mask
is tested with each bit separately and both together. Real invulnerability,
aircraft and submerged targets remain gaps.
"""
from missions.aitargetpick_bench import mission
from model import Script


def forbid(name, filtered, flagged, mask=None, status_name='UNDER_IRON_CURTAIN'):
    expected = (0, 4, 0, 0) if filtered and flagged else (4, 0, 0, 0)
    m = mission(name, [('CNVForbid', None)], expected)
    statuses = status_name.split()
    m.facts['status set'] = int(flagged) * sum(
        2 if s == 'UNATTACKABLE' else 1 for s in statuses)
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
        ('UNIT_CHANGE_OBJECT_STATUS', m.role('plant').name, s, int(flagged))
        for s in statuses]))
    return m


MISSION = {
    'aiforbidnone': lambda: forbid('CampForbidNone', False, True),
    'aiforbidset': lambda: forbid('CampForbidSet', True, True),
    'aiforbidclear': lambda: forbid('CampForbidClr', True, False),
    'aifmasknone': lambda: forbid('CampMaskNone', False, True, ''),
    'aifmaskiron': lambda: forbid('CampMaskIron', True, True, 'UNDER_IRON_CURTAIN'),
    'aifmaskboth': lambda: forbid('CampMaskBoth', True, True, 'UNATTACKABLE UNDER_IRON_CURTAIN'),
    'aifunanone': lambda: forbid('CampUnaNone', False, True, '', 'UNATTACKABLE'),
    'aifunasingle': lambda: forbid('CampUnaSingle', True, True, 'UNATTACKABLE', 'UNATTACKABLE'),
    'aifunaboth': lambda: forbid('CampUnaBoth', True, True, 'UNATTACKABLE UNDER_IRON_CURTAIN', 'UNATTACKABLE'),
    'aifdualnone': lambda: forbid('CampDualNone', False, True, '', 'UNATTACKABLE UNDER_IRON_CURTAIN'),
    'aifdualboth': lambda: forbid('CampDualBoth', True, True, 'UNATTACKABLE UNDER_IRON_CURTAIN', 'UNATTACKABLE UNDER_IRON_CURTAIN'),
}
