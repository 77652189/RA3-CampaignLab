"""S2「西伯利亚快车」: the mission is its plan, docs/story/plans/s2.md (compiled by plan.py; its trains are the
device 列车, devices/train.py). Change the plan to change the level.

Published (the cast, as the checks ask for it): armoured, sickle, conscript (the player's); cryo, birch / river /
east guards and turrets (the enemy's).
"""
import plan


def mission(name='CampS2'):
    return plan.mission('s2', name)
