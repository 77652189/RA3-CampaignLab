"""EnemySearchDistanceVisionMultiplier: aipas1 geometry, only the search multiplier differs.

Four Peacekeepers follow a named far plant. The side plant is 250 west of their route,
outside base vision 200. Both builds enable passive engagement and use identical units,
scripts and micro settings. Prediction: multiplier 1.5 finds and attacks the side plant;
0.25 (search radius 50) passes it and reaches the far plant before attacking the side one.
This probes passive-target collection, not fog visibility or hostile-target acquisition.
"""
from missions import airetreat_bench as ar


def mission(name, multiplier):
    return ar.mission(name, side=True, EngagePassiveTargets='true',
                      EnemySearchDistanceVisionMultiplier=str(multiplier))


MISSION = {
    'aisrchhi': lambda: mission('CampAISrchHi', 1.5),
    'aisrchlo': lambda: mission('CampAISrchLo', 0.25),
}
