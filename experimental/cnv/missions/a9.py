"""A9「布鲁塞尔，1927」: the mission is its plan, docs/story/plans/a9.md (compiled by plan.py; the map maps/brussels.py, the
nine balls units/tower_ball.py driven by the rhythm device). Change the plan to change the level.

Published (the cast, as the checks ask for it): ball 1-9 (the tower's balls, the enemy's), spectrum, xtank, peace, peace
tower (the enemy's west gate and plaza guard), soviet tank, kirov (the third side, held back at the east bridge);
beacon, lag, javelin, guardian, tanya (the player's); devices 首亮 / 轮一 / 轮二 / 轮三 (节律: which ball is lit).
"""
import plan


def mission(name='CampA9'):
    return plan.mission('a9', name)


# the builds this module makes (cnv/registry.py): build name -> mission factory
MISSION = {
    'a9': lambda: mission(),
}
