"""The Body family (ActiveBody, ImmortalBody, PropBody, ManagerBody, ManagedActiveBody, ManagedImmortalBody,
HighlanderBody: the 7 Body tags of the retail XML -- RA3 has no StructureBody; step B2, ADR 0029,
docs/engine/sim-modules.md 4): what a thing's health is made of.

Step B2a: the data alone -- the port (simunits.module_blocks, its BODY rule) and this parse; no module is registered
yet, so no thing carries one (the health stays the body's fields, Sim.add reading simunits). Step B2b registers the
module (hp / max_hp / health_floor its state) under these tags.

The port hands the block of the nearest non-empty <Body> up the chain with its '=$' defines spelled out, so the
MaxHealth here is a number or a literal written with an equals sign ('=50000': am_futuretech_02 / 03,
am_alliedfuturetechhq, ny_chronolibertystatue; '=55000' am_futuretech_01)."""
from engine.kernel import module
from engine.ports import templates

TAGS = ('ActiveBody', 'ImmortalBody', 'PropBody', 'ManagerBody', 'ManagedActiveBody', 'ManagedImmortalBody',
        'HighlanderBody')


class BodyData(module.ModuleData):
    def __init__(self, max_health=None):
        self.max_health = max_health    # MaxHealth, None when the block writes none (BaseObject's DefaultBody)

    @classmethod
    def parse(cls, head, inner):
        v = templates.attr(head, 'MaxHealth')
        return cls(templates.num(v.lstrip('='), None) if v else None)
