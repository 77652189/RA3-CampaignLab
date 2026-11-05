"""A8「海上发布会」: the mission is its plan, docs/story/plans/a8.md (compiled by plan.py). Change the plan to change
the level. The old hand-written rough (the player's Liberty against three power plants with Hammers and Bullfrogs, kept
for units.md 5.6's with-and-without-the-carrier comparison) is missions/a8_rough.py, builds a8_rough / a8_rough_control.

Published (the cast, as the checks ask for it): carrier, guardian, factory, power (the player's); platform 1-3, gun
north / mid / south (the swell turrets, two each), aa north / mid / south (the enemy's); device 浪 (节律: the swell).
"""
import plan


def mission(name='CampA8'):
    return plan.mission('a8', name)


# the builds this module makes (cnv/registry.py): build name -> mission factory
MISSION = {
    'a8': lambda: mission(),
}
