"""The private model's script core as a plug-in to the script executor port (engine/ports/scripts.py, step P1;
ADR 0033 item 2: optional, the public executor engine/script/executor.py is the real one). An adapter: it imports
only engine.ports (tests/guards/test_kernel.py) and is handed the model's loaded scripts module (sim.engine_model
finds and loads it; step Z moves that loader out to a plug-in entry).

plug(scripts) is the model's Engine with the simulator's World: every action it runs itself is told to the world
first (World.core: a flag's scene, caption, ending; an objective; a countdown shown; something changed); a random
timer runs to its latest, as the beat sheet counts. Its one counter-and-timer table is the simulator's counters and
timers through simexec.Counters / Timers, as the public executor's is."""
from engine.ports import scripts as port


def plug(scripts):
    class SimEngine(scripts.Engine, port.Executor):
        """The model's engine, the world (World) watching the core actions it runs itself."""
        script = None

        def action(self, name, a, s=None):
            self.script = s
            self.world.core(self, name, a, s)
            if name == 'SET_RANDOM_MSEC_TIMER':
                name, a = 'SET_MILLISECOND_TIMER', (a[0], a[2])
            elif name == 'COUNTER_MATH_COUNTER' and scripts.as_int(a[1]) not in (0, 1):
                self.world.assumed(f'COUNTER_MATH_COUNTER code {a[1]}')
            super().action(name, a, s)
    return SimEngine

