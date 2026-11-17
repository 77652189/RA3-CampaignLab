"""L6 script actions as a lookup table (ADR 0029 step 3, docs/engine/sim-layers.md): action name -> function.

The action files are grouped by the layer an action works on (simact_vision: L3 visibility, simact_player: L4
player systems, ...); each holds `ACTIONS = {name: fn}` with `fn(sim, name, a, script)`. A name has one function in
one file (tests/test_sim_layers.py). `act` runs the name's function; False back (a guarded action whose guard failed)
or no function: not taken, and Sim.act's chain of the actions not yet moved goes on as before.
"""
import simact_object
import simact_order
import simact_player
import simact_vision

GROUPS = (simact_vision, simact_player, simact_order, simact_object)


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


def act(sim, name, a, script):
    """Run the action `name` if a group has it; True where it was taken."""
    fn = ACTIONS.get(name)
    return fn is not None and fn(sim, name, a, script) is not False
