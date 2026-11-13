"""TimeToKeepTargetMin fixed-duration observation, E123.

Read target_orders/keep_passes from CNVTeams; counters only establish the
existing carrier's live micro path. Clock acceptance is in test_ai_keep_target.
See work/re/e123_keep_target.md for prediction and raw evidence.
"""
from checks.engine_aimicro import probe_engage_clock

CHECKS = {'aikeeptwo': {'a': probe_engage_clock}}
