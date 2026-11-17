"""B-line AllowRecruitUnitsInCombat pair: a fighting Guardian inserted first, an idle one second.

aisort_bench's set-up (one SimpleAttack team, MaxUnits 1, SortByDistance written false -- its default is on -- so
the first fitting unit is taken). The first
candidate ('fighter') stands 100 from a player Guardian (both AttackRange 150, VisionRange 200), so the two shoot at
each other from the start; a script holds both at full health every frame until the player's tank is deleted at
`fight ends`. The second candidate ('idle') stands ~560 from the fight, out of sight. Only the team's
AllowRecruitUnitsInCombat differs. Prediction (the recruit gate's read rule): off -> the fighter is refused while
its target is in range, the idle one goes; on -> the fighter is taken (first), the idle one stays home.
"""
from missions.aiteamfilter_bench import mission as team_mission, TANK
from missions.aiskirm_bench import ai_map
from parts import Script

FIGHT_ENDS = 30.0


def mission(allow):
    m = team_mission(f'CampAICombat{int(allow)}', tanks=0, inf=0, max_units=1,
                     kinds='IncludeKindOf="VEHICLE"')
    m.map = ai_map(m.map, library=False)
    candidates = []
    for identity, dy in (('fighter', 160.0), ('idle', -300.0)):
        o = m.put(TANK, 'east base', -50.0, dy, side='s1', angle=3.1416,
                  name=f'UNIT - CNV Combat {identity}', role=f'candidate {identity}')
        candidates.append((identity, o.name, (o.x, o.y)))
    foe = m.put(TANK, 'east base', -50.0, 260.0, name='UNIT - CNV Combat foe', role='player foe')
    fighter = candidates[0][1]
    m.scripts += [
        Script('CNV Combat - hold health', [], [('UNIT_SET_HEALTH', fighter, 100.0),
                                                ('UNIT_SET_HEALTH', foe.name, 100.0)], once=False),
        Script('CNV Combat - end timer', [], [('SET_MILLISECOND_TIMER', 'CNV Combat End', FIGHT_ENDS)]),
        Script('CNV Combat - end', [('TIMER_EXPIRED', 'CNV Combat End')], [('NAMED_DELETE', foe.name)])]
    m.cnv_candidates = tuple(candidates)
    m.facts |= {'allow in combat': int(allow), 'departure radius': 80.0, 'fight ends': FIGHT_ENDS}
    filename, xml, asset = m.assets[0]
    xml = xml.replace('<TeamTemplate ', f'<TeamTemplate SortByDistance="false" '
                      f'AllowRecruitUnitsInCombat="{str(allow).lower()}" ')
    m.assets[0] = filename, xml, asset
    return m


MISSION = {'aicombat0': lambda: mission(False), 'aicombat1': lambda: mission(True)}
