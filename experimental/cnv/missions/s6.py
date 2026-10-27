"""S6「拜科努尔」: the mission is its plan, docs/story/plans/s6.md (compiled by plan.py). Change the plan to change the
level.

Published (the cast, as the checks ask for it): launch tower, jammer, hammer, coil (the player's); east barracks,
east factory, east power, east refinery, east guard (the enemy's).
"""
import plan


def mission(name='CampS6'):
    return plan.mission('s6', name)
