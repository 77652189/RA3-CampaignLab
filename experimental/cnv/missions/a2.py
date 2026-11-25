"""A2「坝上风云」: the mission is its plan, docs/story/plans/a2.md (compiled by plan.py; the map maps/blackcanyon.py).
Change the plan to change the level.

Published (the cast, as the checks ask for it): dam w, dam e, dam f (the three dam sections, the player's unsellable
plants), barracks, factory, power, peace, dog, guardian, athena (the player's).
"""
import plan


def mission(name='CampA2'):
    return plan.mission('a2', name)


# the builds this module makes (cnv/registry.py): build name -> mission factory
MISSION = {
    'a2': lambda: mission(),
}
