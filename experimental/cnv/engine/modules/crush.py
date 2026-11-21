"""CrusherInfo (bench 2026-11-06 engine_crush, docs/engine/crush.md; moved from simunits.crush in step M3, ADR 0029,
docs/engine/sim-modules.md 4): a thing's CrusherLevel (what it drives over; 0: nothing) and CrushableLevel (None: it
cannot be crushed). Crushed when the crusher's level is strictly greater (crush.md: 30 against 30 and 20 against 20
live). Each level is the nearest template's up the inheritance chain that writes it (the template data port reads
CrusherInfo merged: simunits.MERGED) -- the Hammer's own 20 over BaseVehicle's 10.

Data only: no update, no state. Who crushes what stays outside (the movement: locomotion.crush over the swept
footprint and its topple contact, simpath.claims' spot search, simcrush for the AI)."""
from engine.kernel import factory, interfaces, module
from engine.ports import templates


def _level(head, name):
    v = templates.attr(head, name)
    return None if v is None else int(templates.num(v))


class CrushData(module.ModuleData):
    def __init__(self, crusher=0, crushable=None):
        self.crusher = crusher          # CrusherLevel; 0 when the data writes none
        self.crushable = crushable      # CrushableLevel; None: cannot be crushed

    @classmethod
    def parse(cls, head, inner):
        return cls(_level(head, 'CrusherLevel') or 0, _level(head, 'CrushableLevel'))


@factory.module('CrusherInfo')
class Crush(module.Module, interfaces.Crush):
    """The levels of its data (the names the body's fields had: crusher, crushable)."""
    DATA = CrushData

    def crusher_level(self):
        return self.data.crusher

    def crushable_level(self):
        return self.data.crushable
