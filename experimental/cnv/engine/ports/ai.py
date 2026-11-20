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

What the AI still reads on its host beyond these (simai.PEERS: the observation reads 13f-2b moves, the player
systems 13f-2c) is listed there."""


class Settings:
    """The mission's AI settings on one world (today a sim.Sim), read and written through."""
    __slots__ = ('_w',)

    def __init__(self, world):
        self._w = world

    @property
    def ai(self):
        """player -> the mission second the mission handed it to the skirmish AI."""
        return self._w.ai

    @property
    def ai_paused(self):
        return self._w.ai_paused

    @property
    def ai_switches(self):
        return self._w.ai_switches

    @property
    def ai_priorities(self):
        return self._w.ai_priorities

    @property
    def base_construction_disabled(self):
        return self._w.base_construction_disabled

    @property
    def border(self):
        return self._w.border

    def take_personality(self, player, personality):
        self._w.take_personality(player, personality)

    def add_team_lookup(self, look):
        self._w.add_team_lookup(look)


def drive(world, plugin, frames):
    """`world` `frames` frames on (a frame at a time), `plugin.tick(frame)` after each (None: no plug-in); stops at an
    ending. Returns the plug-in."""
    target = world.frame_now() + frames
    while world.frame_now() < target and world.ending is None:
        world.advance(1)
        if plugin is not None:
            plugin.tick(world.frame_now())
    return plugin
