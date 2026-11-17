"""Engine line D round 108: C's river-bank PathToTarget probe (aiopath_bench.disconnected) with ra3ext on, so the
run's ra3ext.log carries one `ptt:` line per PathToTargetHeuristic evaluation (condition, locomotor list, both
base points, path result and code, the branch that decided). Same mission otherwise; read back by
checks/engine_aipathx.py (C's check unchanged).
"""
from missions import aiopath_bench


def probed(amphibious):
    m = aiopath_bench.disconnected(amphibious)
    m.name = 'CampPCAmphX' if amphibious else 'CampPCLandX'
    m.ext = True
    return m


MISSION = {'aipclandx': lambda: probed(False), 'aipcamphx': lambda: probed(True)}
