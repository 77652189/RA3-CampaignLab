"""Engine line D round 108: checks/engine_aipathbanks.py's check on the ra3ext builds (missions/aipathx_bench.py).

The expectations are C's pre-registered ones (they FAILed on 2026-11-13); this build is for the `ptt:` lines in
the run's ra3ext.log, read in work/re (handoff-c.md PathToTarget).
"""
from checks.engine_aipathbanks import check

CHECKS = {name: {'a': check} for name in ('aipclandx', 'aipcamphx')}
