"""TimeToKeepTargetMin fixed-duration observation, E123; RandomTargetScoreModifier 0 / 1000 on the same carrier (B).

Read target_orders/keep_passes from CNVTeams; counters only establish the
existing carrier's live micro path. Clock acceptance is in test_ai_keep_target.
See work/re/e123_keep_target.md for prediction and raw evidence.
"""
from checks.engine_aimicro import probe_engage_clock

CHECKS = {b: {'a': probe_engage_clock} for b in ('aikeeptwo', 'airands0', 'airandsx')}
