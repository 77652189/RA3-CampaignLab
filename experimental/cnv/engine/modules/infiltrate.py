"""InfiltratorContain (step M15, ADR 0029, docs/engine/sim-modules.md 4; moved from siminfiltrator.spec and the
Infiltrators' rules / *_hosts / port_blocked_until stores): a building a spy may enter. Its data is the block's
attributes as written (Effect, Duration, Amount, ObjectRef, the filters ...), read by the host's measured slices
(siminfiltrator.Infiltrators.*_rule); a KILL block with inner text keeps it as `_unmeasured_children` (E205: the
measured one has none) so the host rejects it rather than dropping a filter.

It keeps which measured slices have taken a spy here once (the host gaps a second entry: E128 / E138 / E193-E200)
and, for a blocking port (E201), the frame till which another spy is turned away. Who may enter, the walk in, the
effect (the observers, the energy cut, the paralysis, the money) and the spy's end stay with the host
(siminfiltrator.Infiltrators, the infiltrators cell), which finds the module by interface. Its state was a store's,
never in the frame record: STATE names none."""
import re

from engine.kernel import factory, interfaces, module


class InfiltratorData(module.ModuleData):
    def __init__(self, rule=None):
        self.rule = rule            # the host's dict: {attribute: value} as written, + _unmeasured_children

    @classmethod
    def parse(cls, head, inner):
        rule = dict(re.findall(r'(\w+)="([^"]*)"', head))
        if rule.get('Effect') == 'KILL' and inner.strip():
            rule['_unmeasured_children'] = inner
        return cls(rule)


@factory.module('InfiltratorContain')
class Infiltrator(module.Module, interfaces.Infiltrate):
    """Data, the slices already entered and the port's block; no update of its own (the host's cell drives it)."""
    DATA = InfiltratorData
    STATE = ()
    marks = frozenset()     # the measured slices ('kill', 'money', ...) a spy has entered here
    until = 0               # a blocking port: another spy is turned away before this frame

    def rules(self):
        return self.data.rule

    def entered(self, slice_):
        return slice_ in self.marks

    def mark(self, slice_):
        self.marks = self.marks | {slice_}

    def blocked_until(self):
        return self.until

    def block(self, frame):
        self.until = frame
