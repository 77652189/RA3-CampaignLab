"""L2 object status bits (ADR 0029, docs/engine/sim-layers.md): which bits the simulator acts on, moved out of sim.py
so the action files can read them without importing sim. sim re-exports both (`sim.ACTED_STATUS` still works)."""

# the object statuses the simulator acts on (tested with `in b.status` in sim.py and the simact_* files; IN_STASIS =
# IMMOBILE NO_ATTACK UNATTACKABLE in simmodifier.modify); tests/test_sim.py checks the list against the source
ACTED_STATUS = frozenset({'SOLD', 'GENERIC_TOGGLE_STATE', 'IMMOBILE', 'NO_ATTACK', 'UNATTACKABLE', 'NON_AUTOACQUIRABLE', 'IN_STASIS', 'UNDER_FROZEN', 'ATTACHED', 'SHROUD_REVEAL_TO_ALL',
                          'NO_COLLISIONS', 'UNDER_IRON_CURTAIN'})   # MetaImpact: XML collision exclusion / magnetic status gate (line C)
# bits only a woken skirmish AI's own target choice reads (d115 10: its micro-manager), no gap here: the unit's own
# take, a script's order, the player's are untouched (bench 11-13 engine_acts flow 旗&2: an idle enemy fires on it)
AI_ONLY_STATUS = frozenset({'SKIRMISH_AI_DO_NOT_ATTACK', 'SKIRMISH_AI_DO_NOT_TAKE'})   # DO_NOT_TAKE: an engineer still takes it (bench 11-13 engine_acts_u)
