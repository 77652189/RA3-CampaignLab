"""J3「白鹭城下」: the mission is its plan, docs/story/plans/j3.md (compiled by plan.py). Change the plan to change the
level.

Published (the cast, as the checks ask for it): yuriko, crane, ninja (the player's); town patrol, gate tank / turret
/ guard, archive, archive guard, castle barracks, castle factory (the enemy's).
"""
import plan


def mission(name='CampJ3'):
    return plan.mission('j3', name)
