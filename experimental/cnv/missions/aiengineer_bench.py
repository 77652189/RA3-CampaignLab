"""Independent Engineer / SimpleAttack pair with one placed, named engineer.

Both lanes use the same Standard micro manager and closest enemy structure.
Only Tactic.Tactic changes; no production or script capture order intervenes.
This isolates the tactic from retail CaptureAnything micro / CreateUnits.
"""
from missions.aiteamfilter_bench import mission as team_mission
from missions.aiskirm_bench import ai_map


def mission(engineer):
    m = team_mission('CampAIEng', tanks=0, inf=1, second='AlliedEngineer',
                     max_units=1, kinds='IncludeKindOf="ENGINEER"')
    m.name = 'CampAIEng' if engineer else 'CampAIEngCtl'
    m.map = ai_map(m.map, library=False)
    filename, xml, asset = m.assets[0]
    if engineer:
        xml = xml.replace('Tactic="SimpleAttack"', 'Tactic="Engineer"')
    m.assets[0] = filename, xml, asset
    m.cnv_named = {'engineer': 'UNIT - CNV AI Riptide 1',
                   'target': m.role('player target').name}
    m.waypoint('engineer target', 'CNV Engineer Target', 'east gate', -300, 0)
    m.facts['engineer tactic'] = int(engineer)
    return m


MISSION = {'aieng': lambda: mission(True), 'aiengctl': lambda: mission(False)}
