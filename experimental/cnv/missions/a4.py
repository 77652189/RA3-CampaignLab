"""A4「冰雕里的兵」: the mission is its plan, docs/story/plans/a4.md (compiled by plan.py; its mechanics are the
devices 车队 and 冰雕广场, devices/convoy.py and devices/ice_plazas.py). Change the plan to change the level.

Published (the cast, as the checks ask for it): truck 1-3, engineer 1-2, guardian, riptide (the player's);
sculpture k-i, troop k-i-n, demo sculpture, north barracks, north guard, harbour ambush, harbour guard (the
enemy's). Marks: exit, seal 1-3, pass 1-2, halt, harbour ...; facts: convoy leaves, tick, 段 第一程.
"""
import plan


def mission(name='CampA4'):
    return plan.mission('a4', name)
