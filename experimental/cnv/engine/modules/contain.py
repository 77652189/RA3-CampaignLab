"""GarrisonContain / ContestableGarrisonContain / TransportContain (step M14, ADR 0029, docs/engine/sim-modules.md 4;
moved from simgarrison.spec and the Garrisons' inside / home / added / secondary_added stores): a building's garrison
or a transport's hold. Its data is the block the port gathers up the chain (simunits.GATHERED: each attribute the
nearest that writes it, defines spelled out, the nearest PassengerFilter): ContainMax, the Allow*Inside relations,
AllowOwnPlayerInsideOverride, KillPassengersOnDeath, ObjectStatusOfContained (a TransportContain's passengers are
ENCLOSED even when it leaves it out: engine_acts_btn EV, INFERRED for the rest), a contestable one's
RequiredClearingObjectStatus, and the PassengerFilter (Rule, Include, Exclude, ExcludeThing).

It keeps the passengers in the order they came in, the status bits it gave each, the owner the building had before
the first, and the upgrades a single passenger granted through the building's listener. Who may come in (filter,
relation, room, the contest), the walk in, the ejects, the REALLYDAMAGED walk-out (ActiveBody's line) and the end
stay with the host (simgarrison.Garrisons, the garrison cell), which finds the module by interface. Its state was a
store's, never in the frame record: STATE names none."""
import re

from engine.kernel import factory, interfaces, module
from engine.ports import templates


def _yes(v, default):
    return default if v is None else v.strip().lower() == 'true'


class ContainData(module.ModuleData):
    TAG = 'GarrisonContain'

    def __init__(self, rule=None):
        self.rule = rule            # the host's dict (interfaces.Contain.rules)

    @classmethod
    def parse(cls, head, inner):
        a = dict(re.findall(r'(\w+)="([^"]*)"', head))
        fh, fi = next(templates.blocks(inner, 'PassengerFilter'), ('', ''))
        return cls({
            'tag': cls.TAG,
            'max': int(float(a.get('ContainMax') or 0)),
            'allow': {'ENEMIES': _yes(a.get('AllowEnemiesInside'), True),
                      'NEUTRAL': _yes(a.get('AllowNeutralInside'), True),
                      'ALLIES': _yes(a.get('AllowAlliesInside'), True)},
            'own': _yes(a.get('AllowOwnPlayerInsideOverride'), False),
            'kill': _yes(a.get('KillPassengersOnDeath'), False),
            'status': frozenset(a.get('ObjectStatusOfContained', '').split()) | (
                {'ENCLOSED'} if cls.TAG == 'TransportContain' else set()),
            'clearing': frozenset(a.get('RequiredClearingObjectStatus', '').split())
            if cls.TAG == 'ContestableGarrisonContain' else frozenset(),
            'rule': (templates.attr(fh, 'Rule') or 'ANY').upper(),
            'kinds': frozenset((templates.attr(fh, 'Include') or '').split()),
            'unkinds': frozenset((templates.attr(fh, 'Exclude') or '').split()),
            'exclude': frozenset(t.strip().lower() for t in re.findall(r'<ExcludeThing>([^<]*)</ExcludeThing>', fi)),
        })


class ContestableData(ContainData):
    TAG = 'ContestableGarrisonContain'


class TransportData(ContainData):
    TAG = 'TransportContain'


@factory.module('GarrisonContain')
class Garrison(module.Module, interfaces.Contain):
    """Data and the passengers; no update of its own (the host's garrison cell drives it)."""
    DATA = ContainData
    STATE = ()
    held = None         # [passenger things], in the order they came in (made on the first)
    given = None        # passenger name -> the status bits this gave it
    before = ()         # (the owner before the first passenger,); (): none kept (an owner may be None: neutral)
    boost = frozenset()  # the upgrades a single passenger granted through the listener

    def rules(self):
        return self.data.rule

    def passengers(self):
        if self.held is None:
            self.held, self.given = [], {}
        return self.held

    def let_in(self, thing, bits):
        self.passengers().append(thing)
        self.given[thing.name] = bits

    def let_out(self, thing):
        held = self.passengers()
        if thing in held:
            held.remove(thing)
        return self.given.pop(thing.name, frozenset())

    def home(self):
        """(the owner kept,), () none."""
        return self.before

    def keep_home(self, owner):
        if not self.before:
            self.before = (owner,)

    def give_home(self):
        (owner,), self.before = self.before, ()
        return owner

    def granted(self):
        return self.boost

    def set_granted(self, upgrades):
        self.boost = upgrades       # the host's set as it is (its order is the order they are taken back in)


@factory.module('ContestableGarrisonContain')
class Contestable(Garrison):
    DATA = ContestableData


@factory.module('TransportContain')
class Transport(Garrison):
    DATA = TransportData
