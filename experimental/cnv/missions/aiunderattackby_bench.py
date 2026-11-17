"""UnderAttackBy land/water contrast after a real hit on the aiunderatk plant.

INFERRED prediction: the land slot selects the attacking Hammer, the water
slot does not. Wake is set to 4s, but the measured first selection precedes it:
Land has no target at f16, takes a real hit source at f19 after the f18 hit.
Water only publishes f16, so its post-hit rejection remains unproved.
Evidence: work/re/c_underattackby_resume_report.md.
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
