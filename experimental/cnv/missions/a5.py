"""A5「巴拿马之锁」: the mission is its plan, docs/story/plans/a5.md (compiled by plan.py). Change the plan to change
the level.

Published (the cast, as the checks ask for it): fleet 1-3, carrier, beacon, guardian, riptide (the player's);
control room, control guard, control tesla, ramp guns, south gate, north gate, bridge guard, east ... (the enemy's).
"""
import plan


def mission(name='CampA5'):
    return plan.mission('a5', name)
