"""A7「鹰派」: the mission is its plan, docs/story/plans/a7.md (compiled by plan.py; the boss is the device 自由号,
devices/carrier.py; the map maps/niagara.py). Change the plan to change the level.

Published (the cast, as the checks ask for it): carrier, station, station guard, east barracks / factory /
airfield, east aa, east guard (the enemy's); loyal 1 / 2 (+ troops), traitor (+ troops) (the outposts' sides);
mcv, guardian, ifv, engineer (the player's). Marks: carrier home, the landing points (base edge, base ore, front),
station, route 1-2, north exit ...; facts: jump every, warning, stay, jump delay, first jump, 段 自由号来了.
"""
import plan


def mission(name='CampA7'):
    return plan.mission('a7', name)
