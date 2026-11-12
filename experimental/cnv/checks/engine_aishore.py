"""MaxDistanceToShore: 2000 leaves, 1 stays; ordinary structure control leaves.

Only the primary pair's distance limit differs. Original expectations are
retained if the host fails; see work/re/c_shore_report.md for interpretation.
"""
from checks.engine_aipoweradv import a

CHECKS = {build: {'a': a} for build in ('aishorehi', 'aishorelo', 'aishorectl')}
