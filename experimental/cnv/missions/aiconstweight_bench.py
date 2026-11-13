"""C: ConstantHeuristic.Weight zero/one control, same map and personality.

Retail uses explicit 0, 0.5, 0.75 and 1. Only the zero versus positive
eligibility boundary is measured here; relative positive draw odds remain gap.
Prediction at s40: Weight=0 infantry home/total=4/4; Weight=1=0/4.
Unregistered Guardians remain home in both. No money or enemy combat units.
"""
from missions import aistate_bench as setup


def mission(weight):
    m = setup.mission('CampAIWt' + str(weight), near=True, gate='const')
    filename, xml, asset = m.assets[0]
    xml = xml.replace(setup._state('CNVStateTank', setup.FLAG_TANK, setup.TANK, 'const'), '')
    xml = xml.replace('    <StrategicState id="CNVStateTank" State="CNVStateTank"/>', '')
    xml = xml.replace('<ConstantHeuristic/>', f'<ConstantHeuristic Weight="{weight}"/>')
    m.assets[0] = filename, xml, asset
    m.facts.update({'constant weight': weight, 'expect infantry home': 4 if weight == 0 else 0})
    return m


MISSION = {'aicwzero': lambda: mission(0), 'aicwone': lambda: mission(1)}
