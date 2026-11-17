"""A3「格林尼治时差」: the mission is its plan, docs/story/plans/a3.md (compiled by plan.py; the map maps/greenwich.py, the
time-stop zone devices/stasis.py). Change the plan to change the level.

Published (the cast, as the checks ask for it): peace, guardian (the player's start platoon), civ a (the observatory's
crowd), eng (the Future Tech engineers), civ c (the church's people), frozen ally (a platoon inside ring 1), frozen soviet
(the enemy squad inside ring 1, the enemy's); device 时停区 (the five rings 一 ... 五: which are on).
"""
import plan


def mission(name='CampA3'):
    return plan.mission('a3', name)


# the builds this module makes (cnv/registry.py): build name -> mission factory
MISSION = {
    'a3': lambda: mission(),
}
