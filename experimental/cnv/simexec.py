"""L6 the world's side of the script executor port (engine/ports/scripts.py, step P1): what the simulator answers an
executor -- the public one (engine/script/executor.py) or the private model's plug-in (scriptplugin.py) -- through
the port's `World`. Moved off Sim (its condition / action / this_player / update / difficulty, and the core actions
the model's SimEngine reported) as a pure move; the rules stay where they were (simcond / simact by name)."""
from engine.ports import scripts as port
import simcond
from simscript import RA3_ONLY

# core actions the plug-in runs itself that the world still watches (World.core): the timeline's notes on them ...
SEEN_CORE = {'SET_FLAG', 'SET_MISSION_OBJECTIVE_STATUS', 'DISPLAY_COUNTDOWN_TIMER',
             'MARK_MISSION_OBJECTIVE_COMPLETED', 'MARK_MISSION_OBJECTIVE_NOT_COMPLETED'}
# ... and the ones that only change something (the quiet clock: Sim.change)
CHANGES = {'INCREMENT_COUNTER', 'DECREMENT_COUNTER', 'SET_MILLISECOND_TIMER', 'SET_RANDOM_MSEC_TIMER'}


class SimWorld(port.World):
    """The port's World over a Sim: conditions by name (simcond.cond), actions by name (Sim.act: simshow and simui
    override it)."""

    def __init__(self, sim):
        self.sim = sim

    def condition(self, eng, name, args):
        if name in RA3_ONLY:
            self.sim.ra3_only.add(name)
        return simcond.cond(self.sim, name, port.this_player(eng, args))

    def action(self, eng, name, args):
        self.sim.act(name, port.this_player(eng, args), eng.script)

    def update(self, eng):
        """Units move and fight in step(), once a DT tick."""

    def difficulty(self, side):
        return None                             # the run's level ('difficulty side')

    def core(self, eng, name, args, script):
        if name in SEEN_CORE:
            self.sim.act(name, list(args), script)
        elif name in CHANGES:
            self.sim.change()

    def assumed(self, what):
        self.sim.used.add(what)
