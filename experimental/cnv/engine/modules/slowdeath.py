"""SlowDeathBehavior (step B5a, ADR 0029, docs/engine/sim-modules.md 4; moved from the body's `lies` / `linger`, read
by simunits.slow_death, and the crush's `linger = lies`): one module a SlowDeath block. A killed body lies dying --
NAMED_DYING, still in the game's name cache where it fell -- its DestructionDelay (bench 11-06 engine_crush: a crushed
conscript, 8.5 s, lay 127 frames; a plant killed by script was gone the next frame).

What the simulator keeps of it: the delay is that of the first block whose attributes name no DeathTypes /
DeathFlags (in the merged GameObject's module order, the template data port), 0 without one -- a commented-out block is
not read (the SDK compiler reads no XML comments; slow_death read 25 templates' commented-out blocks: a behaviour
change of step B5a); only a crushed body (module.Death's death CRUSHED, locomotion.crush) lies it out -- any other death lies
LINGER, 0 (bench 2026-10-28: a killed unit is gone from areas at once; INFERRED that the crush is the one death that
lies). The ToppleUpdate reads the delay for its own (engine/modules/topple.py). SinkDelay, Fade, the DieMux's death
types and the probability weights are not read.

Decided in step B5a: a lying body's Destroy modules are told at its death, not when its lie ends (the private
model's SlowDeath calls destroyObject after the DestructionDelay). INFERRED and kept: in the simulator only a crushed
body lies, and what it leaves out of the fight -- passengers, slaves -- is let go at its death by the Die modules all
the same (Contain on_die, Slaved on_die); only a crushed spawner's children would go 127 frames early (none in the
eleven recorded missions).

The B5 review fix (e #7, the coordinator's ruling 11-19): the lie is set before the Die broadcast (begin, called by
the host's simbody.Life._out ahead of every Die module, as the old sim.crush_along set `linger` before the kill), so
every Die module reads this death's lie, an earlier one too; it is no Die module itself. INFERRED: in Generals the
SlowDeathBehavior begins in its own onDie, in module order."""
from engine.kernel import factory, interfaces, module
from engine.ports import templates

LINGER = 0.0                    # seconds a death lies that is not a crush: still in the game's name cache where it fell
                                # (docs/engine/script-semantics.md 4.2) -- the bench (2026-10-28, probe death): out of
                                # the area from the reading the kill shows in; the guess was 3 s (sim.LINGER till B5a)
LIES = 'CRUSHED'                # the one death type that lies its delay out


class SlowDeathData(module.ModuleData):
    def __init__(self, delay=0.0, plain=True):
        self.delay = delay          # DestructionDelay, seconds
        self.plain = plain          # its attributes name no DeathTypes / DeathFlags: the delay the body lies

    @classmethod
    def parse(cls, head, inner):
        return cls(templates.secs(templates.attr(head, 'DestructionDelay')),
                   'DeathFlags' not in head and 'DeathTypes' not in head)


@factory.module('SlowDeath')
class SlowDeath(module.Module, interfaces.SlowDeath):
    """No update: told of its thing's death before the Die modules (begin), it sets how long this death lies
    (`linger`, read by the body's forward: Sim.present / dying). The names the body's fields had, so the frame record is unchanged: `lies` and
    `linger` are the body's forwards, RECORDED none."""
    DATA = SlowDeathData
    STATE = ('linger',)
    RECORDED = ()
    linger = LINGER

    def begin(self, info):
        if self.data.plain and info.death == LIES:
            self.linger = self.data.delay

    def lies(self):
        return self.data.delay

    def lie(self):
        return self.linger

    def is_plain(self):
        return self.data.plain


def _plain(mods):
    return next((m for m in mods if m.is_plain()), None)


def lies(mods):
    """The body's `lies` (its forward): the first plain module's DestructionDelay, 0.0 without one."""
    m = _plain(mods)
    return m.lies() if m else 0.0


def linger(mods):
    """The body's `linger` (its forward): how long its death lies -- LINGER, the crush its delay."""
    m = _plain(mods)
    return m.lie() if m else LINGER
