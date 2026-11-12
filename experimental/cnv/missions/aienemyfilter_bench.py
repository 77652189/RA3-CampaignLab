"""EnemyNearby EnemyFilter.Include contrast; see work/re/c_enemyfilter_report.md.

Reuse the measured near-miner host; only Include changes in the primary pair.
SAME_PLAYER is a relationship control without an own harvester.
"""
from missions.aipoweradv_bench import mission


def filtered(name, include, relationship, expected):
    gate = ('<EnemyNearbyHeuristic Distance="700.0" EnemyNearby="true">'
            f'<EnemyFilter Relationship="{relationship}" Rule="ANY" Include="{include}"/>'
            '</EnemyNearbyHeuristic>')
    return mission(name, 4, 0, miner='ai base', gate=gate, expect=expected)


MISSION = {
    'aiefharv': lambda: filtered('CampEFHarv', 'HARVESTER', 'ENEMIES', 1),
    'aiefeng': lambda: filtered('CampEFEng', 'ENGINEER', 'ENEMIES', 0),
    'aiefself': lambda: filtered('CampEFSelf', 'HARVESTER', 'SAME_PLAYER', 0),
}
