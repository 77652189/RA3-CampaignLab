"""UnderAttackBy land/water contrast after a real hit on the aiunderatk plant.

INFERRED prediction: the land slot selects the attacking Hammer, the water
slot does not. Wake at 4s, after the early automatic hits measured by D164;
verify the actual hit and selection frames rather than assuming this timing.
Evidence: work/re/c_underattackby_fight_report.md.
"""
from missions.aiunderattack_bench import mission as underattack


def mission(water=False):
    m = underattack()
    m.name = 'CampUAByW' if water else 'CampUAByL'
    asset, xml, ref = m.assets[0]
    heuristic = 'UnderAttackByWaterEnemyHeuristic' if water else 'UnderAttackByLandEnemyHeuristic'
    xml = xml.replace('TargetHeuristic="CNVUnderAttack"', f'TargetHeuristic="{heuristic}"', 1)
    m.assets[0] = asset, xml, ref
    start = next(s for s in m.scripts if s.name == 'CNV AI - Start')
    start.do = [(a[0], a[1], 4.0) if a[:2] == ('SET_MILLISECOND_TIMER', 'CNV AI Wake') else a
                for a in start.do]
    return m


MISSION = {'aiuabl': mission, 'aiuabw': lambda: mission(True)}
