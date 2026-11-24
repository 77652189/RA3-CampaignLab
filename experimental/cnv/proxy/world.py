"""The proxy player's one seam to a world: what it sees (Observation) and what it may do (Order).

The decision layer (proxy/player.py) never touches a world's objects; a world -- the fake one in proxy/fake.py for
unit tests, simproxy.SimWorld on the plan simulator (experimental/cnv/simproxy.py: the kernel's ports only, ADR 0033 3)
-- implements World:

    observe() -> Observation      what a human player would know right now (fogged: only `seen` enemies)
    issue(order) -> bool          one order a human could give with the mouse; False = the world refused it
    step(frames) -> None          let the world run (the runner, player.play, calls it between decisions)
    losses() -> [Loss]            optional, for the playtest report only: every death so far (the score screen)

Enemies are Things (what a human reads off an object of someone else's: kinds, place, cost, which domains its
guns hit); threat() sums them round a target. Own units carry what a player sees on the unit card (health, powers, range).
Unit kinds are the five a player counters by: infantry, vehicle, air, ship, structure (kind_of maps KindOf onto them).
"""
import dataclasses
from typing import Optional, Protocol

KINDS = ('infantry', 'vehicle', 'air', 'ship', 'structure')
THREAT_RADIUS = 400.0               # INFERRED: how far round a target a player counts the guns he would walk into


@dataclasses.dataclass
class Thing:
    """An object the player sees that is not his: owner ('' = civilian), KindOf and ObjectStatus, where it stands,
    whether on water, its build cost (value), the domains its guns hit ('ground' 'air' 'water'), whether it is
    shooting at the player's side."""
    id: int
    owner: str
    template: str = ''
    kindof: frozenset = frozenset()
    status: frozenset = frozenset()
    x: float = 0.0
    y: float = 0.0
    water: bool = False
    value: float = 0.0
    hits: frozenset = frozenset()
    attacking_us: bool = False


def threat(things, enemies, t, domain='ground', radius=THREAT_RADIUS):
    """The value of the things of `enemies` within `radius` of t whose guns hit `domain` (INFERRED: what a human
    weighs his army against before going -- the cost of the guns there, not their damage)."""
    r2 = radius ** 2
    return sum(o.value for o in things if domain in o.hits and o.owner in enemies
               and (o.x - t.x) ** 2 + (o.y - t.y) ** 2 <= r2)


def kind_of(thing):
    """A Thing's (or Mine's) counter kind from its KindOf (INFERRED mapping; RA3 KindOf names)."""
    k = thing.kindof
    if 'STRUCTURE' in k:
        return 'structure'
    if 'AIRCRAFT' in k:
        return 'air'
    if 'INFANTRY' in k:
        return 'infantry'
    if getattr(thing, 'water', False) or 'SHIP' in k:
        return 'ship'
    return 'vehicle'


@dataclasses.dataclass
class Mine:
    """One of the player's own units as the player sees it."""
    id: int
    template: str
    kindof: frozenset = frozenset()
    x: float = 0.0
    y: float = 0.0
    health: float = 100.0
    max_health: float = 100.0
    cost: int = 0
    weapon_range: float = 0.0
    sight: float = 300.0
    good_against: frozenset = frozenset()     # counter kinds its weapons are made for (Offer.good_against)
    powers: tuple = ()                        # the unit's own abilities (player.py does not use them)
    busy: str = ''                            # the world's word for its current order: '' idle, 'move', 'attack'
    rates: dict = dataclasses.field(default_factory=dict)   # Offer.rates
    speed: float = 0.0                        # map units a second (0 = unknown); the player times its walks with it
    reloading: frozenset = frozenset()        # its powers (commands) still reloading: the button is greyed, a click
                                              # on them is refused (CampaignLab Sim.order_power)

    @property
    def fraction(self):
        return self.health / self.max_health if self.max_health else 0.0


@dataclasses.dataclass
class Offer:
    """Something the player can build right now (a sidebar button that is lit)."""
    template: str
    kindof: frozenset
    cost: int
    good_against: frozenset                   # proxy/matchup.py from the data (weapon x armour); roles_from_name without
    seconds: float = 10.0
    rates: dict = dataclasses.field(default_factory=dict)   # kind -> enemy value destroyed per second (matchup.rates);
                                                            # {} = unknown: the player then buys the cheapest fit


@dataclasses.dataclass
class Choke:
    """A place where a level's coming threat can be stopped with a ground power (an ice wall in a street's mouth), as
    a human sees it: the briefing and the map say where the threat comes out (`source`) and where it can be blocked
    (`pos`); the on-screen countdown says when it comes (`at`, the frame it runs out; None = no countdown running);
    the player sees whether something already blocks it (`blocked`). The world says which power does it and which of
    the player's templates have that power. The proxy decides when and which (player._blocks); the level only fills
    this list, so nothing in the decision is written for one level."""
    name: str
    pos: tuple                                # (x, y) where the power goes
    source: tuple                             # (x, y) where the threat comes out
    at: Optional[int] = None                  # frame the threat comes
    power: str = ''                           # Order.power for the blocking power
    by: frozenset = frozenset()               # templates that have it
    blocked: bool = False
    build: float = 0.0                        # seconds the power takes to raise the block once the unit stands there
                                              # (the build bar the player saw the first time); 0 = unknown


@dataclasses.dataclass
class Observation:
    frame: int
    me: str
    money: int
    home: tuple                               # (x, y): where the player's base is, where the wounded go
    mine: list                                # [Mine], combat units and builders; buildings are not listed
    seen: list                                # [ai.targets.Thing] enemies and neutrals in sight now
    offers: list = dataclasses.field(default_factory=list)   # [Offer]
    enemies: frozenset = frozenset()          # enemy player names (Thing.owner)
    leads: list = dataclasses.field(default_factory=list)    # [(x, y)] places worth a look (briefing, map, minimap)
    chokes: list = dataclasses.field(default_factory=list)   # [Choke] where a coming threat can be blocked
    escort: bool = False                      # home is something the level asks to keep alive (a convoy): the army
                                              # stays round it (player._pick_target, Style.escort_reach)
    cinematic: bool = False                   # a scene is playing and the player has no control (a human cannot
                                              # give orders then): the proxy only watches
    healing: bool = True                      # the level has somewhere the wounded heal (a repair depot, auto-heal,
                                              # a medic); without it pulling back never brings a unit back
    counters: dict = dataclasses.field(default_factory=dict)  # enemy template -> counter kinds it is made to kill
                                              # (the unit card / encyclopedia; Matchup); missing -> roles_from_name
    blips: list = dataclasses.field(default_factory=list)    # [(frame, x, y)] minimap flashes of the last moments
                                              # (a script's radar event: a wave made in the fog still flashes there)


@dataclasses.dataclass
class Order:
    kind: str                                 # 'move' | 'attack_move' (fight whatever is in range on the way, to pos)
                                              # | 'attack' | 'build' | 'power'
    units: tuple = ()                         # Mine ids
    target: Optional[int] = None              # Thing id ('attack', a targeted 'power')
    pos: Optional[tuple] = None               # (x, y) ('move', a ground 'power')
    template: Optional[str] = None            # 'build'
    power: Optional[str] = None               # 'power': the UnitPowerInfo.command


@dataclasses.dataclass(frozen=True)
class Loss:
    """One unit or building that died, either side: what the end-of-game score screen tells a human player, so the
    playtest report (proxy/report.py) may read it without the player having cheated. kind is kind_of's word."""
    frame: int
    owner: str
    template: str
    kind: str
    cost: int = 0


class World(Protocol):
    def observe(self) -> Observation: ...
    def issue(self, order: Order) -> bool: ...
    def step(self, frames: int) -> None: ...
    # optional: losses() -> [Loss], every death so far (the score screen); proxy/report.py reads it when present


ROLE_WORDS = (('AntiInfantry', 'infantry'), ('AntiVehicle', 'vehicle'), ('AntiAir', 'air'),
              ('AntiStructure', 'structure'), ('AntiNaval', 'ship'), ('AntiShip', 'ship'))


def roles_from_name(template):
    """What a retail template is made to kill, from its name (AlliedAntiInfantryVehicle -> {'infantry'}).
    INFERRED stand-in for a world without the SDK library: the retail templates name their role; the data's answer
    (the weapons' damage against each armour) is proxy/matchup.py, which a world adapter gives instead when it can.
    The two disagree where the name undersells a unit: the data has the Javelin (AlliedAntiVehicleInfantry) good
    against air too, the Mecha Tengu (JapanAntiInfantryVehicle) best against air."""
    return frozenset(kind for word, kind in ROLE_WORDS if word in template)
