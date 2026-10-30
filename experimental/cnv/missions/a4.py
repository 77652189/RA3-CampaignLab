"""A4「冰雕里的兵」: the mission is its plan, docs/story/plans/a4.md (compiled by plan.py; its mechanics are the
devices 车队 and 冰雕广场, devices/convoy.py and devices/ice_plazas.py). Change the plan to change the level.

The rework (docs/design/a4-redesign.md, on maps/sapporo.py) is a4.md since 2026-10-28. before(): the level as the
user played it before the rework (2026-10-27/28, on maps/festival.py), frozen in missions/a4_before.md -- the build
the plaza and convoy devices' bench checks (checks/a4_before.py) were tuned on, kept for them.

Published (the cast, as the checks ask for it): truck 1-3, engineer 1-2, guardian ... (the player's); sculpture k-i,
troop k-i-n ... (the enemy's). Marks: exit, seal 1-3, pass 1-2, halt ...
"""
import os

import plan

BEFORE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'a4_before.md')


def mission(name='CampA4'):
    return plan.mission('a4', name)


def before(name='CampA4B'):
    return plan.Compiler(plan.load(BEFORE), name).compile()
