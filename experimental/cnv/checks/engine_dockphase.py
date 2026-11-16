"""D165: E152's QueueDock check, unchanged, on the ra3ext copy of the bench (missions/dockphase_bench.py).

The phases come from ra3ext's `dock:` lines (teamlog.dock_phases), not from counters.
"""
from checks.engine_queuedock import check

CHECKS = {'dockphase': {'a': check}, 'dockphaseoff': {'a': check}}
