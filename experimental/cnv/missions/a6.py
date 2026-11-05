"""A6「古代的服务器」: the mission is its plan, docs/story/plans/a6.md (compiled by plan.py; the map maps/stonehenge.py).
Change the plan to change the level.

Published (the cast, as the checks ask for it): tower a (the outer ring's tower), tower i (three, the inner platform's),
site power (the enemy's power plant on the ring), dog (three), sentry (four), pack (the dogs' and sentries' 守 groups
are the enemy's); tanya, athena (two), guardian (two), peace (the player's).
"""
import plan


def mission(name='CampA6'):
    return plan.mission('a6', name)


# the builds this module makes (cnv/registry.py): build name -> mission factory
MISSION = {
    'a6': lambda: mission(),
}
