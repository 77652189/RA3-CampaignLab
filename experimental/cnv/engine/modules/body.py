"""The Body family (ActiveBody, ImmortalBody, PropBody, ManagerBody, ManagedActiveBody, ManagedImmortalBody,
HighlanderBody: the 7 Body tags of the retail XML -- RA3 has no StructureBody; step B2, ADR 0029,
docs/engine/sim-modules.md 4): what a thing's health is made of.

Step B2a gave the port (simunits.module_blocks, its BODY rule) and the data; step B2b the module, one a thing
(interfaces.Body, of ONE). Its state is the body's old fields hp / max_hp / health_floor (STATE: the frame record
unchanged); sim.Body reads them, and immortal / prop, through read-only forwards (Body.FORWARDS). Every change of
health goes through set_health (B1's one write, moved here): attempt_damage (down to the floor; a prop takes none),
attempt_healing (at most the maximum), set_percent (a script's health). What the host still works out when it makes
the thing (Sim.add -> make): the health (an immortal's: the block's MaxHealth; else fight's hp, else the block's; a
guess when none), a ManagerBody's proxy (HB_Bridge_02: immortal, its floor 1 % of the centre piece's health,
INFERRED) and a PropBody's death to a script kill (simunits.prop_death). Kept from the readers it replaced (the refactor
line's census of step B2a, 3448 retail + 520 own templates, no difference): only an ImmortalBody is
immortal (not a ManagedImmortalBody, nor a HighlanderBody); a Body removing a PropBody stays a prop.

Step B3 moved the last damage (last_hit / last_by: who hit it last, the Generals ActiveBody's last DamageInfo; written
by every hit through set_last_damage) and the Indestructible panel flag here (the Generals ActiveBody holds it too);
the callers still skip an indestructible target themselves, as before (script damage goes through: engine_scripts7
panel). Kept on the thing, as the engine model has them (its body reads them off the object): armor (the
template's ArmorSet, swapped by a toggle state or the frozen armour), taken / shielded (the modifier pool's ARMOR
product and INVULNERABLE + UNDER_IRON_CURTAIN bits, written beside the status and `dealt`: simmodifier) and
immune_until (the Iron Curtain's protection, a stand-in for its status bits).

The port hands the block of the nearest non-empty <Body> up the chain with its '=$' defines spelled out, so the
MaxHealth here is a number or a literal written with an equals sign ('=50000': am_futuretech_02 / 03,
am_alliedfuturetechhq, ny_chronolibertystatue; '=55000' am_futuretech_01)."""
import math

from engine.kernel import factory, interfaces, module
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


class Body(module.Module, interfaces.Body):
    """No update cell of its own. hp / max_hp / health_floor: the names the body's fields had (100 / 100 / 1 until
    the host makes it, as the fields' defaults); immortal, prop: what the forwards of those names read. A thing whose
    template has no Body block gets an ActiveBody attached (Sim.add, World.attach: made by __init__, no on_create)."""
    DATA = BodyData
    STATE = ('hp', 'max_hp', 'health_floor', 'last_hit', 'last_by', 'indestructible', 'read_until')
    IMMORTAL = False            # health changes cannot take it below its floor
    PROP = False                # no health: takes no damage, its percent reads 0 (engine_propbody a)
    hp = max_hp = 100.0

    def __init__(self, thing, data, world=None):
        super().__init__(thing, data, world)
        self.set_health(100.0, 100.0, tell=False)      # on the module itself: the frame record reads its own fields
        self.health_floor = 1.0     # an immortal's: 1 HP; a ManagerBody proxy's: 1 % of its health (INFERRED)
        self.immortal, self.prop = self.IMMORTAL, None
        self.last_hit = self.last_by = None     # step B3: the last damage's player and object (set_last_damage)
        self.indestructible = False
        self.read_until = None      # step B4a: killed by NAMED_DAMAGE in this frame -- its bits still read

    def make(self, hp, floor=None, death=None):
        self.set_health(hp, hp, tell=False)
        if floor is not None:
            self.immortal, self.health_floor = True, floor
        self.prop = (death or 'stays') if self.PROP else None

    def kind(self):
        return self.TAGS[0]

    def health(self):
        return self.hp

    def max_health(self):
        return self.max_hp

    def floor(self):
        return self.health_floor

    def is_immortal(self):
        return self.immortal

    def prop_death(self):
        return self.prop

    def percent(self):
        return 100.0 * self.hp / self.max_hp if self.max_hp and not self.prop else 0.0

    def set_health(self, hp, max_hp=None, tell=True):
        was, self.max_hp, self.hp = self.hp, self.max_hp if max_hp is None else max_hp, hp
        if tell:
            self.thing.health_moved(was, hp)

    def attempt_damage(self, amount):
        if not self.prop:
            self.set_health(max(self.health_floor if self.immortal else 0.0, self.hp - amount))

    def attempt_healing(self, amount):
        self.set_health(min(self.max_hp, self.hp + amount))

    def set_percent(self, pct):
        self.set_health(max(self.health_floor if self.immortal else -math.inf, self.max_hp * float(pct) / 100.0))

    def last_damage(self):
        return self.last_hit, self.last_by

    def set_last_damage(self, player, by=None):
        self.last_hit, self.last_by = player, by

    def is_indestructible(self):
        return self.indestructible

    def set_indestructible(self, flag):
        self.indestructible = bool(flag)

    def bits_read_until(self):
        return self.read_until

    def set_bits_read_until(self, frame):
        self.read_until = frame


@factory.module('ActiveBody')
class ActiveBody(Body):
    pass


@factory.module('ImmortalBody')
class ImmortalBody(Body):
    IMMORTAL = True


@factory.module('PropBody')
class PropBody(Body):
    PROP = True


@factory.module('ManagerBody')
class ManagerBody(Body):
    """HB_Bridge_02's whole proxy only (Sim.add); its bridge pieces, shared health and repair: a gap."""


@factory.module('ManagedActiveBody')
class ManagedActiveBody(Body):
    pass


@factory.module('ManagedImmortalBody')
class ManagedImmortalBody(Body):
    """Read as not immortal, as the reader it replaced (immortal_body named ImmortalBody alone): not benched."""


@factory.module('HighlanderBody')
class HighlanderBody(Body):
    pass
