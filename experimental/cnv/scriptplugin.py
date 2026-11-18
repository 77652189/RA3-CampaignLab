"""The private model's script core as a plug-in to the script executor port (engine/ports/scripts.py, step P1;
ADR 0033 item 2: optional, the public executor engine/script/executor.py is the real one). An adapter: it imports
only engine.ports (tests/guards/test_kernel.py) and is handed the model's loaded scripts module (sim.engine_model
finds and loads it; step Z moves that loader out to a plug-in entry).

plug(scripts) is the model's Engine with the simulator's World: every action it runs itself is told to the world
first (World.core: a flag's scene, caption, ending; an objective; a countdown shown; something changed); a random
timer runs to its latest, as the beat sheet counts. Counters / Timers are the model's one counter-and-timer table as
the simulator's counters and timers."""
import collections.abc

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


class Counters(collections.abc.MutableMapping):
    """The engine's one counter / timer table as the simulator's counters: a plain counter's value by name."""

    def __init__(self, eng):
        self.eng = eng

    def __getitem__(self, k):
        c = self.eng.counters[k]
        if c[1]:
            raise KeyError(k)
        return c[0]

    def __setitem__(self, k, v):
        self.eng.counter(k)[0] = v

    def __delitem__(self, k):
        del self.eng.counters[k]

    def __iter__(self):
        return (k for k, c in self.eng.counters.items() if not c[1])

    def __len__(self):
        return sum(1 for _ in self)


class Timers(collections.abc.Mapping):
    """... and as its timers: a running countdown's mission second it runs out at (at or before now once out)."""

    def __init__(self, sim, fps):
        self.sim, self.fps = sim, fps

    def __getitem__(self, k):
        c = self.sim.eng.counters[k]
        if not c[1]:
            raise KeyError(k)
        return self.sim.t + c[0] / self.fps

    def __iter__(self):
        return (k for k, c in self.sim.eng.counters.items() if c[1])

    def __len__(self):
        return sum(1 for _ in self)
