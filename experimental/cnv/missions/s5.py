"""S5「巴拿马之锁」: the mission is its plan, docs/story/plans/s5.md (compiled by plan.py), on A5's map from the
other side. Change the plan to change the level.

Published (the cast, as the checks ask for it): digger, conscript, hammer (the player's); control room, control
guard, control tank, ramp guns, fleet 1-3, west yard ... west guard (the enemy's).
"""
import plan


def mission(name='CampS5'):
    return plan.mission('s5', name)
