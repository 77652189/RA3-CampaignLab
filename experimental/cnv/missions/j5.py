"""J5「敌人的敌人」: the mission is its plan, docs/story/plans/j5.md (compiled by plan.py). Change the plan to change the
level.

Published (the cast, as the checks ask for it): observatory, yuriko, shikigami, loan tank, warrior (the player's);
merc barracks, merc factory, merc power, merc refinery, merc guard (the enemy's).
"""
import plan


def mission(name='CampJ5'):
    return plan.mission('j5', name)
