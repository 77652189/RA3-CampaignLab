"""Engine probe mission (protocol points, checks/engine_protocol.py): no units of its own needed -- the scripts set and
read the players' protocol points. The island map with batch 1's cast (scripts1_mission) under its own name."""
from benches.script.control.scenes import scripts1_mission


def mission():
    return scripts1_mission(name='CampProt')


MISSION = {'engine_protocol': mission}
