"""The schedule (docs/engine/sim-modules.md 4): the update modules, by frame cell. At its cell a module runs when its
wake frame has come, by its class's ORDER, then in the order the modules were added (the order things are made);
update returns the frames until it runs again, or SLEEP (out of the running until World.wake). Only update modules
are held: nothing scans every object every frame."""
from engine.kernel import interfaces


class Schedule:
    def __init__(self):
        self.cells = {}         # PHASE -> {module: wake frame, None asleep}
        self.seq = {}           # module -> the order it was added in

    def add(self, module, frame):
        """Hold an update module from `frame` (one made this frame runs when its cell comes this frame)."""
        if not isinstance(module, interfaces.Update) or module.PHASE is None:
            raise TypeError(f'{type(module).__name__} is not an Update with a PHASE')
        self.seq[module] = len(self.seq)
        self.cells.setdefault(module.PHASE, {})[module] = frame

    def remove(self, module):
        self.cells.get(module.PHASE, {}).pop(module, None)
        self.seq.pop(module, None)

    def wake(self, module, frame):
        """Run it at `frame`: an earlier wake wins over a later one; woken twice for one frame it runs once. One no
        longer held (its thing left the world) stays out."""
        cell = self.cells.get(module.PHASE, {})
        if module not in cell:
            return
        now = cell[module]
        if now is None or frame < now:
            cell[module] = frame

    def run(self, phase, frame):
        """Advance the modules of one cell whose wake frame has come; -> how many ran."""
        cell = self.cells.get(phase)
        if not cell:
            return 0
        due = sorted((m for m, at in cell.items() if at is not None and at <= frame),
                     key=lambda m: (m.ORDER, self.seq[m]))
        for m in due:
            n = m.update(frame)
            if n is interfaces.SLEEP:
                cell[m] = None
            elif n < 1:
                raise ValueError(f'{type(m).__name__}.update gave {n} (at least 1, or SLEEP)')
            else:
                cell[m] = frame + n
        return len(due)

    def awake(self, phase):
        """{module: wake frame} of a cell, the sleeping ones left out."""
        return {m: at for m, at in self.cells.get(phase, {}).items() if at is not None}
