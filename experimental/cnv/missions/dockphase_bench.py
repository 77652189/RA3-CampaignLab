"""D165: E152's QueueDock bench with ra3ext loaded -- same-frame dock phases (`dock:` lines) and, for the off
arm, why the run stops (`exc:` lines). Only the names and ext differ from queuedock_bench."""
from missions.queuedock_bench import mission as _queuedock


def mission(enabled=True):
    m = _queuedock(enabled)
    m.name = 'CampDockD' if enabled else 'CampDockOffD'
    m.ext, m.ext_logs = True, ('dock',)
    return m


MISSION = {'dockphase': mission, 'dockphaseoff': lambda: mission(False)}
