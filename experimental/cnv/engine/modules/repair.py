"""RepairUpdate (step M13, ADR 0029, docs/engine/sim-modules.md 4; moved from simrepair.Repairs' rules / active /
refused stores and simunits.repair_update / repair_measured_config): a structure's paid repair, distinct from
AutoHeal. Its data is the block's HealAmountPerSecond (10), Toggleable (true), RepairableWhenDead (false) and
PercentOfBuildCostToRebuildInfo (50 % each state), and whether the block is the measured shape -- nothing outside
those, but SelfAudio. The retail structures take the block from Includes/GenericBuildingRepair.xml (the port reads
the includes for this tag: simunits.INCLUDED).

It keeps the repair under way and whether a disturbed one refused it for the run; who may repair (the AI's
difficulty gate, its money latch), the cost and the healing stay with the host's loop (simrepair.Repairs.due, the
repairs cell), which finds the module by interface. Its state was a store's, never in the frame record: RECORDED
names none."""
import re

from engine.kernel import factory, interfaces, module
from engine.ports import templates

STATES = ('Pristine', 'Damaged', 'ReallyDamaged', 'Rubble')
ATTRS = frozenset({'HealAmountPerSecond', 'Toggleable', 'RepairableWhenDead'})
COST = 'PercentOfBuildCostToRebuildInfo'


def _names(head):
    return set(re.findall(r'([\w:]+)\s*=', head))


class RepairData(module.ModuleData):
    def __init__(self, rule=None, measured=False):
        self.rule = rule            # {'rate', 'toggleable', 'dead', 'cost': four fractions}
        self.measured = measured    # the block has no field outside those (the measured shape)

    @classmethod
    def parse(cls, head, inner):
        cost, _ = next(templates.blocks(inner, COST), ('', ''))
        rule = {'rate': templates.num(templates.attr(head, 'HealAmountPerSecond'), 10),
                'toggleable': templates.attr(head, 'Toggleable', 'true').lower() == 'true',
                'dead': templates.attr(head, 'RepairableWhenDead', 'false').lower() == 'true',
                'cost': tuple(templates.num(templates.attr(cost, s), 50) / 100 for s in STATES)}
        measured = (not _names(head) - {'xmlns', 'id'} - ATTRS
                    and not set(re.findall(r'<(?!/)(\w+)', inner)) - {COST, 'SelfAudio'}
                    and all(not _names(h) - set(STATES) for h, _ in templates.blocks(inner, COST)))
        return cls(rule, bool(measured))


@factory.module('RepairUpdate')
class Repair(module.Module, interfaces.Repair):
    """Data, the repair under way and the refusal; no update of its own (the host's repairs cell drives it)."""
    DATA = RepairData
    STATE = ('running', 'stopped')
    RECORDED = ()
    running = None      # the host's dict of the repair under way (owner, cost, r, money, hp, last_hp); None: none
    stopped = False     # a disturbed repair refused it for the run

    def rules(self):
        return self.data.rule

    def measured(self):
        return self.data.measured

    def job(self):
        return self.running

    def set_job(self, job):
        self.running = job

    def refused(self):
        return self.stopped

    def refuse(self):
        self.running, self.stopped = None, True
