"""AttachUpdate (bench engine_attach a; moved from simunits.attach_modules in step M7, ADR 0029,
docs/engine/sim-modules.md 4): what an AttachNugget of its thing's weapon may stick it to -- the direct teleport /
stick / status subset only.

A block is supported when it has no inner XML, its Flags hold STICK_TO_PARENT and TELEPORT and nothing beyond those
and ONE_ATTACH_PER_PARENT, and its attributes are no more than id, Flags, Range, CloseEnoughRange, ParentStatus and
AttachedObjectStatus; anything else is False (unsupported), so recognising a module id cannot silently implement
leech, death, repair, idle-detach or autonomous scanning. Several inherited groups and the distance boundary are
unbenched.

Data only: no update, no state. Who attaches stays outside (the combat family's AttachNugget: simdamage, reading the
rules through the body's attachment_rules forward; the attachments themselves: Sim.attachments)."""
import re

from engine.kernel import factory, interfaces, module
from engine.ports import templates

FLAGS = frozenset({'STICK_TO_PARENT', 'TELEPORT'})
MORE_FLAGS = frozenset({'ONE_ATTACH_PER_PARENT'})
ATTRS = frozenset({'id', 'Flags', 'Range', 'CloseEnoughRange', 'ParentStatus', 'AttachedObjectStatus'})


class AttachData(module.ModuleData):
    def __init__(self, id=None, rule=False):
        self.id = id                    # its module id (what an AttachNugget names)
        self.rule = rule                # {flags, range, child, parent}, or False: a shape not modelled

    @classmethod
    def parse(cls, head, inner):
        flags = set(templates.attr(head, 'Flags', 'STICK_TO_PARENT TELEPORT USE_GEOMETRY').split())
        if (inner.strip() or not FLAGS <= flags or flags - FLAGS - MORE_FLAGS
                or set(re.findall(r'(\w+)\s*=', head)) - ATTRS):
            return cls(templates.attr(head, 'id'), False)
        return cls(templates.attr(head, 'id'), dict(
            flags=flags, range=templates.num(templates.attr(head, 'Range')),
            # engine_attach_nocoll n: NO_COLLISIONS listed there is never given (alone or in either order)
            child=set(templates.attr(head, 'AttachedObjectStatus', '').split()) - {'NO_COLLISIONS'} | {'ATTACHED'},
            parent=set(templates.attr(head, 'ParentStatus', '').split())))


@factory.module('AttachUpdate')
class Attach(module.Module, interfaces.Attach):
    """Its module id and rule (the shape simunits.attach_modules gave: {flags, range, child, parent} or False)."""
    DATA = AttachData

    def module_id(self):
        return self.data.id

    def rule(self):
        return self.data.rule
