"""LevelUpUpgrade (engine_levelup a / b / c; moved from simlevel.rules and the body's level_modules in step M12, ADR 0029,
docs/engine/sim-modules.md 4): an upgrade module that, given its trigger, raises its thing's rank by LevelsToGain up to
LevelCap, once until a removal of the trigger rearms it (Permanent=true: the removal not benched, a gap).

It keeps only whether a grant has it in force; the rank it gave is the thing's own (the engine's ExperienceTracker is
the Object's, not a module's: Body.level_rank), and the grant's algorithm -- the rank table, the veterancy upgrades and
the elite health -- stays in simlevel.receive, told by the host's upgrade grant (Sim._upgrade), as before the move.
Not an interfaces.Upgrade: the kernel's broadcast (Thing.upgrades_moved) would act at modify, not at the grant.

Its state is shown in the frame record by the body's forward `level_modules` (the ids of those in force): several of
these on one thing record as one field, so RECORDED names none (its STATE: `on`)."""
from engine.kernel import factory, interfaces, module
from engine.ports import templates


class LevelUpData(module.ModuleData):
    def __init__(self, mid=None, triggers=frozenset(), gain=0, cap=0, permanent=False):
        self.mid = mid                  # its module id
        self.triggers = triggers        # the TriggeredBy elements' upgrade names (not an attribute: the old reader's)
        self.gain = gain                # LevelsToGain
        self.cap = cap                  # LevelCap
        self.permanent = permanent      # Permanent

    @classmethod
    def parse(cls, head, inner):
        return cls(templates.attr(head, 'id'), templates.names('', inner, 'TriggeredBy'),
                   int(templates.attr(head, 'LevelsToGain', '0')), int(templates.attr(head, 'LevelCap', '0')),
                   templates.attr(head, 'Permanent', 'false').lower() == 'true')


@factory.module('LevelUpUpgrade')
class LevelUp(module.Module, interfaces.Create, interfaces.LevelUp):
    DATA = LevelUpData
    STATE = ('on',)
    RECORDED = ()

    def on_create(self, frame):
        self.on = False         # a grant has it in force (a removal of its trigger rearms it)

    def on_build_complete(self):
        pass

    def module_id(self):
        return self.data.mid

    def rules(self):
        d = self.data
        return d.triggers, d.gain, d.cap, d.permanent

    def active(self):
        return getattr(self, 'on', False)

    def set_active(self, on):
        self.on = bool(on)
