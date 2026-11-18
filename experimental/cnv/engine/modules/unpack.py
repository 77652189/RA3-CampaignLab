"""StructureUnpackUpdate (RA3 1.13; bench engine_powerdef, engine_sell c; moved from the
body's `unpack_end` field in step M10, ADR 0029, docs/engine/sim-modules.md 4): a structure made in the run unpacks
before it works -- adds no power, does not fire, cannot be sold -- for its UnpackTime x 15 frames, rounded, stretched
by its owner's power factor v then: trunc((1 - v) F + F). The host works the end out (Sim.add: the factor is the
players family's) and sets it; a structure the map places, or one with no UnpackTime, never unpacks.

UnpackTime is the nearest template's block's (the template data port), a '=$NAME' value spelled out from the defines
(simunits.EXPANDED); the same on every retail template and the own templates of every build as the reader it
replaced (simunits.unpack_frames, work/logs/m10_check.log)."""
from engine.kernel import factory, interfaces, module
from engine.ports import templates

FPS = 15                        # the game's logic frames a second


class UnpackData(module.ModuleData):
    def __init__(self, frames=0):
        self.frames = frames        # UnpackTime x 15, rounded (0: none)

    @classmethod
    def parse(cls, head, inner):
        v = templates.attr(head, 'UnpackTime')
        return cls(int(round(templates.secs(v.lstrip('=')) * FPS)) if v else 0)


@factory.module('StructureUnpackUpdate')
class Unpack(module.Module, interfaces.Unpack):
    """Its unpacking's end, no update of its own (the frame's readers compare it with the frame now). unpack_end: the
    frame it is unpacked by (None: it never unpacked; the name the body's field had, so the frame record is
    unchanged)."""
    DATA = UnpackData
    STATE = ('unpack_end',)
    unpack_end = None

    def frames(self):
        return self.data.frames

    def end_frame(self):
        return self.unpack_end

    def set_end(self, frame):
        self.unpack_end = frame
