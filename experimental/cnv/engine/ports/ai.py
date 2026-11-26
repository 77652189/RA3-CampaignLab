"""The AI port (module_plan §4 P "AI 插件": a plug-in `tick` + the observation port + the command port; R3 13f-2): what
a skirmish AI player plugged into a world is handed beyond the world's things -- the settings the mission gives its
AI players -- and the runner that ticks it.

`Settings` is the mission's word to its AI players, as the game keeps it on the AI player itself (the scripts' AI
actions write it; the AI reads it): which players are the AI's and from when (`ai`, player -> the mission second it
was handed over), the ones paused (`ai_paused`, PLAYER_TOGGLE_SKIRMISH_AI(p, 0)), their switches (`ai_switches`,
player -> {AI_SWITCHES name: value}) and enemy priorities (`ai_priorities`, player -> [(enemy, n)]), the players
barred from building structures (`base_construction_disabled`) and the map border in play (`border`). Two writes go
the other way, as settings, not orders: the personality a player took when not the map's (`take_personality`,
PLAYER_HAS_PERSONALITY reads it) and a team-name lookup the scripts ask (`add_team_lookup`). Each is read off the
world when asked (a snapshot restored writes the world's fields anew), never copied.

`drive(world, plugin, frames)` runs the world `frames` frames on, one at a time, and after each calls
`plugin.tick(frame)` with the frame now; it stops early at an ending. Today the world is a sim.Sim and the plug-in
simai.SimAI (its `advance` hands itself here); a world with no plug-in is just advanced.

`PlayerSystems` is what a player has in the game beyond its things -- power, the build permissions, the upgrades for
sale, the production queues, the wallet -- that the AI asks before it builds or buys (R3 13f-2c). Today no module
keeps them: each forwards to the world's method of the same name, so moving them into modules changes only here.
Two of the wallet's are writes the AI makes as shortcuts, not orders: `charge` (it pays for a structure it places
at once; cmd_port.md's shortcut column) and `multiply_income` (its personality's resource multiplier, once).

What the AI still borrows on its host beyond the ports (simai.PEERS) is listed there.

A table or set read off either comes back read only and live (engine/ports/readonly.view, review 1119z P2 #2: a
plug-in that cleared `systems.queues` emptied the production queues past the command port)."""
from engine.ports.readonly import view


class Settings:
    """The mission's AI settings on one world (today a sim.Sim), read and written through."""
    __slots__ = ('_w',)

    def __init__(self, world):
        self._w = world

    @property
    def ai(self):
        """player -> the mission second the mission handed it to the skirmish AI."""
        return view(self._w.ai)

    @property
    def ai_paused(self):
        return view(self._w.ai_paused)

    @property
    def ai_switches(self):
        return view(self._w.ai_switches)

    @property
    def ai_priorities(self):
        return view(self._w.ai_priorities)

    @property
    def base_construction_disabled(self):
        return view(self._w.base_construction_disabled)

    @property
    def border(self):
        return view(self._w.border)

    @property
    def borders(self):
        """The map's border rects (x0, y0, x1, y1) in order, `border` the one in play; () for a map without."""
        return tuple(getattr(self._w.m.map, 'BORDERS', {}).values())

    @property
    def sides(self):
        """The mission's sides: side -> its setup (playerFaction, aiPersonality, ...); {} for a mission without."""
        return view(getattr(self._w.m, 'sides', None) or {})

    @property
    def facts(self):
        """The mission's facts ('dual bases', 'expansion', ...)."""
        return view(self._w.m.facts)

    @property
    def assets(self):
        """The mission's own files ((path, text, kind), ...): a probe's AI personality among them."""
        return view(getattr(self._w.m, 'assets', None) or [])

    def take_personality(self, player, personality):
        self._w.take_personality(player, personality)

    def add_team_lookup(self, look):
        self._w.add_team_lookup(look)


class PlayerSystems:
    """The players' systems on one world (today a sim.Sim): each read when asked (a snapshot restored writes the
    world anew), never copied."""
    __slots__ = ('_w',)

    def __init__(self, world):
        self._w = world

    def power(self, player):
        """(supply, demand) of the player's power."""
        return self._w.power(player)

    def power_ready(self, player, power):
        """Whether the player's spellbook power may be cast now (its protocol held, countdown run, needs standing)."""
        return self._w.spellbook_ready(player, power)

    def can_build(self, player, template, factory=None, ban=True):
        """Whether the player may build the template (its prerequisites, the mission's bans; at that factory)."""
        return self._w.can_build(player, template, factory, ban)

    def upgrade_sellers(self, player, upgrade):
        """The player's living things that sell the upgrade."""
        return self._w.upgrade_sellers(player, upgrade)

    def offers(self, player):
        """What the player's factories offer now."""
        return self._w.offers(player)

    def busy(self, factory):
        """Whether the factory has a production job queued."""
        return self._w.production.busy(factory.serial)

    def bring(self, due, structure, player, x, y, team):
        """A structure the player's AI set down brings its free unit (a refinery's miner) out at `due`."""
        self._w.production.bring(due, structure, player, x, y, team)

    def brought(self, player, frame):
        """The player's free units due by `frame`, made now (in the order brought)."""
        return self._w.production.brought(frame, player)

    def proto(self, template, player):
        """A thing of the template the world never placed, to read its figures off."""
        return self._w.proto(template, player)

    def engineer_entry(self, body, target):
        """Whether the target building lets the body in to capture it."""
        return self._w.engineer_entry(body, target)

    @property
    def _wallet(self):
        return self._w.wallet

    def held(self, player):
        """The player's money now (its wallet)."""
        return self._wallet.held(player)

    def charge(self, player, amount):
        """Take the amount off the player's wallet (a shortcut: the AI paying for what it places at once)."""
        return self._wallet.charge(player, amount)

    def instal(self, player, job, progress):
        """A yard job's instalment to `progress` taken if held; whether it was (simmoney.Money.instal)."""
        return self._wallet.instal(player, job, progress)

    def multiply_income(self, player, mult):
        """Scale the player's income (a shortcut: the AI personality's resource multiplier)."""
        return self._wallet.multiply_income(player, mult)

    def mined_since(self, player, frame):
        """What the player's collectors paid in from `frame` on (simmoney.Money.mined_since)."""
        return self._wallet.mined_since(player, frame)


def drive(world, plugin, frames):
    """`world` `frames` frames on (a frame at a time), `plugin.tick(frame)` after each (None: no plug-in); stops at an
    ending. Returns the plug-in."""
    target = world.frame_now() + frames
    while world.frame_now() < target and world.ending is None:
        world.advance(1)
        if plugin is not None:
            plugin.tick(world.frame_now())
    return plugin
