"""EnemyNearby EnemyFilter.Include contrast; see work/re/c_enemyfilter_report.md.

Reuse the measured near-miner host; only Include changes in the primary pair.
SAME_PLAYER is a relationship control without an own harvester.
aiefall / aiefnone: the aiefeng filter (Include ENGINEER) with Rule ALL / NONE -- does the Rule reach EnemyNearby?
"""
from missions.aipoweradv_bench import mission


def filtered(name, include, relationship, expected, rule='ANY'):
    gate = ('<EnemyNearbyHeuristic Distance="700.0" EnemyNearby="true">'
            f'<EnemyFilter Relationship="{relationship}" Rule="{rule}" Include="{include}"/>'
            '</EnemyNearbyHeuristic>')
    return mission(name, 4, 0, miner='ai base', gate=gate, expect=expected)


MISSION = {
    'aiefharv': lambda: filtered('CampEFHarv', 'HARVESTER', 'ENEMIES', 1),
    'aiefeng': lambda: filtered('CampEFEng', 'ENGINEER', 'ENEMIES', 0),
    'aiefself': lambda: filtered('CampEFSelf', 'HARVESTER', 'SAME_PLAYER', 0),
    'aiefall': lambda: filtered('CampEFAll', 'ENGINEER', 'ENEMIES', 1, rule='ALL'),
    'aiefnone': lambda: filtered('CampEFNone', 'ENGINEER', 'ENEMIES', 0, rule='NONE'),
}
