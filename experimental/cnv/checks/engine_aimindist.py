"""Tech minimum-distance contrast: oil/barracks/tank/home at s40.

The oil uses the host's plant counter. Predicted zero/control: 4/0/0/0;
2000: 0/0/0/4. Counters establish movement, not live candidate distance.
Original evidence: work/re/c_mindist_report.md.
"""
from checks.engine_aitargetpick import a

CHECKS = {build: {'a': a} for build in ('aimind0', 'aimindhi', 'aimindctl')}
