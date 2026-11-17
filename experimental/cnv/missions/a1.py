"""A1「金门不锁」: the mission is its plan, docs/story/plans/a1.md (compiled by plan.py; the map maps/golden.py). Change
the plan to change the level.

Published (the cast, as the checks ask for it): north bomber, south bomber (the two fuse men on the towers), deck guard
(four), south patrol (two), aa post (two), dock mag (three), dock tank (two) (the enemy's); tanya, hawk (two guardians
standing in for the Peregrine), peace (the player's).
"""
import plan


def mission(name='CampA1'):
    return plan.mission('a1', name)


# the builds this module makes (cnv/registry.py): build name -> mission factory
MISSION = {
    'a1': lambda: mission(),
}
