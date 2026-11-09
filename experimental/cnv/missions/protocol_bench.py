"""Engine probe mission (protocol points, checks/engine_protocol.py): no units of its own needed -- the scripts set and
read the players' protocol points. The island map with batch 1's cast (missions/scripts1_bench.py) under its own name."""
from missions import scripts1_bench


def mission():
    return scripts1_bench.mission(name='CampProt')


MISSION = {'engine_protocol': mission}
