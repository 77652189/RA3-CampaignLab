"""EnemyFilter.Include: predict enemy HARVESTER leaves, ENGINEER stays.

Relation control SAME_PLAYER has no own harvester and should stay.
Counters are the measured host's home/target-area tanks; no target-sort claim.
"""
from checks.engine_aipoweradv import a

CHECKS = {build: {'a': a} for build in ('aiefharv', 'aiefeng', 'aiefself')}
