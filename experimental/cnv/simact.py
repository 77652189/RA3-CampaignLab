"""L6 script actions as a lookup table (ADR 0029 step 3, docs/engine/sim-layers.md): action name -> function.

The action files are grouped by the layer an action works on (simact_vision: L3 visibility, simact_player: L4
player systems, ...); each holds `ACTIONS = {name: fn}` with `fn(sim, name, a, script)`. A name has one function in
one file (tests/test_sim_layers.py). `act` runs the name's function; False back (a guarded action whose guard failed)
or no function: not taken, and the action is an unknown one (Sim.unknown, a gap), as the old chain's last else had it.
"""
import simact_ability
import simact_object
import simact_order
import simact_player
import simact_show
import simact_vision
import simact_world
from simscript import refined
from simworld import GAP_ACTION

GROUPS = (simact_vision, simact_player, simact_order, simact_object, simact_ability, simact_world, simact_show)


def table(groups=GROUPS):
    """The groups' ACTIONS in one dict; a name in two groups is an error (which one would run was the old chain's
    order: one owner keeps that question out)."""
    out = {}
    for g in groups:
        twice = out.keys() & g.ACTIONS.keys()
        if twice:
            raise ValueError(f'{g.__name__}: actions already in another group: {sorted(twice)}')
        out.update(g.ACTIONS)
    return out


ACTIONS = table()


def act(sim, name, a, script, unit=None):
    """Run the action `name` if a group has it; True where it was taken. Not taken (no group has it, or its guarded
    function declined): counted in sim.unknown and logged as a gap, False back. `unit`: the object a giver already
    picked, acted on as it is (named_buttons' `unit`; 11-19 same-name sweep S4: the player's power)."""
    fn = ACTIONS.get(name)
    if fn is not None and (fn(sim, name, a, script) if unit is None else fn(sim, name, a, script, unit=unit)) \
            is not False:
        return True
    sim.unknown[name] = sim.unknown.get(name, 0) + 1
    sim.gap(GAP_ACTION, refined(name, a), 'Sim.act 不认识：没效果')
    return False
