"""SlowDeathBehavior (step B5a, ADR 0029, docs/engine/sim-modules.md 4; moved from the body's `lies` / `linger`, read
by simunits.slow_death, and the crush's `linger = lies`): one module a SlowDeath block. A killed body lies dying --
NAMED_DYING, still in the game's name cache where it fell -- its DestructionDelay (bench 11-06 engine_crush: a crushed
conscript, 8.5 s, lay 127 frames; a plant killed by script was gone the next frame).

What the simulator keeps of it (E228): a death lies the delay of the first block (module order, the template data
port) whose DieMuxData takes it -- its DeathTypes / DeathTypesForbidden the death type, its RequiredStatus /
ExemptStatus the thing's status (module.DieMux; a block without the child element: its own attributes) -- and LINGER,
0, without one, or when a DestroyDie takes it too (gone with the frame, Generals destroyObject; INFERRED: no bench has
both). Bench: a crushed conscript (CRUSHED), a Peacekeeper the Chronosphere's insta-kill took (engine_teleport b),
an engineer UNIT_KILL_ALL_IN_AREA killed (engine_sighted, 7.5 s) all lie; a Guardian (10-28 probe death) and a plant,
DestroyDie alone, do not. A commented-out block is not read (the SDK compiler reads no XML comments). `lies` (the
body's, read by the ToppleUpdate and the health counter) stays the first block whose attributes name no DeathTypes /
DeathFlags. SinkDelay, Fade and the probability weights are not read (several blocks taking one death: the first).

Decided in step B5a: a lying body's Destroy modules are told at its death, not when its lie ends (the private
model's SlowDeath calls destroyObject after the DestructionDelay). INFERRED and kept: what it leaves out of the
fight -- passengers, slaves, a spawner's children -- is let go at its death by the Die / Destroy modules all the same.

The B5 review fix (e #7, the coordinator's ruling 11-19): the lie is set before the Die broadcast (begin, called by
the host's simbody.Life._out ahead of every Die module, as the old sim.crush_along set `linger` before the kill), so
every Die module reads this death's lie, an earlier one too; it is no Die module itself. INFERRED: in Generals the
SlowDeathBehavior begins in its own onDie, in module order."""
from engine.kernel import factory, interfaces, module
from engine.ports import templates

LINGER = 0.0                    # seconds a death lies that no SlowDeath takes: gone from areas and counts at once
                                # (bench 2026-10-28, probe death: a Guardian, DestroyDie alone)


class SlowDeathData(module.ModuleData, module.DieMux):
    def __init__(self, delay=0.0, plain=True, types=frozenset({'ALL'}), forbidden=frozenset(),
                 required=frozenset(), exempt=frozenset()):
        self.delay = delay          # DestructionDelay, seconds (0 for a DestroyDie: gone with the frame)
        self.plain = plain          # its attributes name no DeathTypes / DeathFlags: the body's `lies`
        self.types, self.forbidden, self.required, self.exempt = types, forbidden, required, exempt

    @classmethod
    def parse(cls, head, inner):
        mux, w = templates.child(inner, 'DieMuxData') or head, templates.words
        return cls(templates.secs(templates.attr(head, 'DestructionDelay')),
                   'DeathFlags' not in head and 'DeathTypes' not in head, w(mux, 'DeathTypes', 'ALL'),
                   w(mux, 'DeathTypesForbidden'), w(mux, 'RequiredStatus'), w(mux, 'ExemptStatus'))


@factory.module('SlowDeath')
class SlowDeath(module.Module, interfaces.SlowDeath):
    """No update: told of its thing's death before the Die modules (begin), it sets how long this death lies
    (`linger`, None when its DieMux does not take the death; read by the body's forward: Sim.present / dying)."""
    DATA = SlowDeathData
    STATE = ('linger',)
    RECORDED = ()
    linger = None

    def begin(self, info):
        d = self.data
        if d.takes(info.death) and d.holds(module.status_now(self.thing) if info.status is None else info.status):
            self.linger = d.delay

    def lies(self):
        return self.data.delay

    def lie(self):
        return self.linger

    def is_plain(self):
        return self.data.plain

    def cut(self, lain):
        if self.linger is not None:
            self.linger = min(self.linger, lain)


@factory.module('DestroyDie')
class DestroyDie(SlowDeath):
    """A DestroyDie block: a death its DieMux takes lies 0 -- gone with the frame, whatever a SlowDeath says."""

    def is_plain(self):
        return False


def _plain(mods):
    return next((m for m in mods if m.is_plain()), None)


def lies(mods):
    """The body's `lies` (its forward): the first plain module's DestructionDelay, 0.0 without one."""
    m = _plain(mods)
    return m.lies() if m else 0.0


def linger(mods):
    """The body's `linger` (its forward): how long its death lies -- 0 when a DestroyDie took it, else the first
    SlowDeath that did, else LINGER."""
    took = [m.lie() for m in mods if m.lie() is not None]
    return 0.0 if 0.0 in took else next(iter(took), LINGER)
