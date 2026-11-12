"""Priority fallback contrast: plant/barracks/tank/home counters at s40.

aitopon predicts 0/0/0/4; aitopoff and positive host aitopctl 0/4/0/0.
The host keeps targets alive; explicit s4=30, p1=10 priorities are set at wake.
Evidence: work/re/c_toponly_report.md. No same-frame priority readback claimed.
"""
from checks.engine_aitargetpick import a

CHECKS = {build: {'a': a} for build in ('aitopon', 'aitopoff', 'aitopctl')}
