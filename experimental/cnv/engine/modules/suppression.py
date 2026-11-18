"""SuppressionUpdate (RA3's infantry suppression; bench 2026-11-10 engine_suppress_probe tail / lifetime / duration /
expiry, line D rounds 21 / 22, over line C's engine_suppression; moved from simunits.suppression and
simdamage.suppression_tick in step M6, ADR 0029, docs/engine/sim-modules.md 4): a man pinned down by fire.

A hit's SuppressionNugget leaves a stationary 2D field with a lifetime of its own (the host keeps them: World.
suppression_at). Every UpdateDelay, on the thing's birth phase (its first sample the frame it is made, at least
frame 1), the fields covering it are summed: at Suppressability or more it is suppressed -- entering leaves the old
end untouched, an already suppressed high sample sets the end SuppressionDuration on; only a low sample strictly
after the end clears it. Its AttributeModifierSuppressed (read by the modifier family: simmodifier) holds while it is
suppressed, and a change is told to the host to re-read the modifiers (World.modify). SUPPRESSED is a model
condition, not an object status. Fractional lifetime ceil vs nearest is still INFERRED outside the measured 1.1 s.

Its state keeps the names the body's fields had (suppression_hits / suppressed / suppressed_until / suppression_next),
so the frame record is unchanged."""
import math

from engine.kernel import factory, interfaces, module
from engine.ports import templates

FPS = 15                # the game's logic frames a second (bench 2026-10-28, probe align)


def _frames(seconds):
    """Whole frames, rounded up (engine_clip, bench 2026-11-09; the 1e-6 keeps 1.2 x 15 at 18)."""
    return int(math.ceil(seconds * FPS - 1e-6))


class SuppressionData(module.ModuleData):
    def __init__(self, threshold=0.0, every=1, duration=0, modifier=None):
        self.threshold = threshold      # Suppressability: the summed field value that suppresses
        self.every = every              # UpdateDelay in frames (at least 1): how often it samples
        self.duration = duration        # SuppressionDuration in frames: how long a refreshed sample holds it
        self.modifier = modifier        # AttributeModifierSuppressed

    @classmethod
    def parse(cls, head, inner):
        return cls(templates.num(templates.attr(head, 'Suppressability')),
                   max(1, _frames(templates.secs(templates.attr(head, 'UpdateDelay', '1s')))),
                   _frames(templates.secs(templates.attr(head, 'SuppressionDuration', '0s'))),
                   templates.attr(head, 'AttributeModifierSuppressed'))

    def rules(self):
        """{threshold, every, duration, modifier}: the shape simunits.suppression gave (simmodifier reads it)."""
        return dict(threshold=self.threshold, every=self.every, duration=self.duration, modifier=self.modifier)


@factory.module('SuppressionUpdate')
class Suppression(module.Module, interfaces.Update, interfaces.Create, interfaces.Suppression):
    """In the frame order's suppression cell, every frame: the fields covering its thing (suppression_hits), and on
    its sample frames whether it is suppressed."""
    DATA = SuppressionData
    PHASE = 'suppression'
    STATE = ('suppression_hits', 'suppressed', 'suppressed_until', 'suppression_next')
    suppressed = False

    def on_create(self, frame):
        self.suppression_hits = []      # (end frame, value) of the fields covering it at its last update
        self.suppressed_until = 0       # the end a refreshed sample set (0: none yet)
        self.suppression_next = max(1, frame)   # its next sample frame: its birth phase

    def on_build_complete(self):
        pass

    def rules(self):
        return self.data.rules()

    def hits(self):
        return self.suppression_hits

    def is_suppressed(self):
        return self.suppressed

    def until(self):
        return self.suppressed_until

    def next_sample(self):
        return self.suppression_next

    def update(self, frame):
        if not self.thing.alive:
            return 1
        d = self.data
        self.suppression_hits[:] = self.world.suppression_at(self.thing, frame)
        before = self.suppressed
        if frame >= self.suppression_next:
            self.suppression_next += ((frame - self.suppression_next) // d.every + 1) * d.every
            if sum(v for _, v in self.suppression_hits) >= d.threshold:
                if self.suppressed:
                    self.suppressed_until = frame + d.duration
                self.suppressed = True
            elif frame > self.suppressed_until:
                self.suppressed = False
        if before != self.suppressed:
            self.world.modify(self.thing)
        return 1
