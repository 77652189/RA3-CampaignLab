"""The SpecialPowerModule family's reload (step M8, ADR 0029, docs/engine/sim-modules.md 4; moved from the body's
`ready_at` dict): one module a block of any SpecialPowerModule tag, serving the SpecialPowerTemplate its block names.
It keeps the frame its power's reload ends; every cast -- the script's too -- starts it anew (RA3 1.13, read in the
program). How long a reload is (simunits.power_rules: the SpecialPowerTemplate's ReloadTime) and what
a cast does stay with the callers (simact_ability, simorder, simmicro) until the cast is a module's.

Its state is shown in the frame record by the body's forward `ready_at` ({power: frame} of the modules a cast
started; simpower.ready_at): several of these on one thing record as one field, so STATE names none of them.
A thing whose template has no block for a power cast on it (35 retail template / power pairs: ReplaceSelf's packs,
the player spell book's nearest-template blocks, the structures' PlayerPowerManager powers; and simmicro's Bonzai,
keyed by its command) is given one then (simpower.start_reload, World.attach), as the body's dict took any key."""
from engine.kernel import factory, interfaces, module
from engine.ports import templates

# The SpecialPowerModule tags of the retail XML (the Generals SpecialPowerModule family and RA3's own: the index's
# tags ending in SpecialPower)
TAGS = ('SpecialPower', 'OCLSpecialPower', 'MovementSpecialPower', 'DominateEnemySpecialPower',
        'RecallUnitsSpecialPower', 'StoreObjectsSpecialPower', 'TeleportStoredObjectsSpecialPower',
        'TeleportToCasterSpecialPower', 'PlayerUpgradeSpecialPower', 'ReturnToProducerSpecialPower',
        'ActivateModuleSpecialPower', 'AssignSlavesTargetObjectSpecialPower', 'GiveProductionBonusSpecialPower',
        'PrematureDischargeSpecialPower', 'ReturnToDockSpecialPower')


class SpecialPowerData(module.ModuleData):
    def __init__(self, power=None):
        self.power = power          # SpecialPowerTemplate: the power it serves

    @classmethod
    def parse(cls, head, inner):
        return cls(templates.attr(head, 'SpecialPowerTemplate'))


@factory.module(*TAGS)
class SpecialPower(module.Module, interfaces.SpecialPower):
    """Data and a reload frame; no update of its own (a reload is over once the frame passes it)."""
    DATA = SpecialPowerData
    STATE = ()
    ready = None        # the frame its reload ends; None: no cast started one

    def power(self):
        return self.data.power

    def ready_at(self):
        return self.ready

    def set_ready_at(self, frame):
        self.ready = frame
