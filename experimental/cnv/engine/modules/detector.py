"""StealthDetectorUpdate (E156, bench 2026-11-15, checks/engine_detector.readings.toml): an object that shows its
enemies within DetectionRange (its vision when 0) whom an aura hides -- they carry INVISIBLE_DETECTED and can be shot
while it holds (Sim.cloaked asks sees). ExtraRequiredKindOf / ExtraForbiddenKindOf narrow whom it shows.

Data only: no update, no state. The host takes it every tick, not on DetectionRate; the bench's first reveal comes
~7 s in (the detector's first scans see the target before it hides), here at the first tick (a mismatch reading).
Not read: CanDetectWhileContained / Garrisoned (no retail detector writes them), DetectionRate."""
from engine.kernel import factory, interfaces, module
from engine.ports import templates


class DetectorData(module.ModuleData):
    def __init__(self, reach=0.0, need=frozenset(), forbid=frozenset()):
        self.reach, self.need, self.forbid = reach, need, forbid    # DetectionRange (0: the vision); the KindOf sets

    @classmethod
    def parse(cls, head, inner):
        return cls(templates.num(templates.attr(head, 'DetectionRange'), 0.0),
                   templates.words(head, 'ExtraRequiredKindOf'), templates.words(head, 'ExtraForbiddenKindOf'))


@factory.module('StealthDetectorUpdate')
class Detector(module.Module, interfaces.Detector):
    DATA = DetectorData

    def sees(self, target, relation):
        """An alive holder shows an ENEMIES target of the kinds within reach, centre to centre."""
        me, d = self.thing, self.data
        if not me.alive or relation != 'ENEMIES' or not d.need <= target.kinds or d.forbid & target.kinds:
            return False
        return (target.x - me.x) ** 2 + (target.y - me.y) ** 2 <= (d.reach or me.vision) ** 2
