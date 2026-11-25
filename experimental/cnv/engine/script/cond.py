"""L6 script conditions as a lookup table (ADR 0029 step 3, docs/engine/sim-layers.md): condition name -> function.

The condition files are grouped by the layer a condition reads (simcond_world: L0 flags, timers, counters, teams;
simcond_object: L2; simcond_vision: L3; simcond_player: L4; simcond_show: the presentation); each holds
`CONDITIONS = {name: fn}` with `fn(sim, name, a)`. A name has one function in one file (tests/test_sim_layers.py).
`cond` runs the name's function; None back (a guarded condition whose guard failed) or no function: an unknown
condition (Sim.unknown, a gap), false -- as the old chain's end had it.

The retail-campaign conditions came in batches, each with its bench (a function's `# retail batch N` comment):
1 round 207, benches/script/control/checks.py#engine_conds (the program read in work/re d115_script_semantics.md where it says 码, the rest
INFERRED from Generals until the bench); 2 round 210, benches/script/control/checks.py#engine_conds sight (d115_script_semantics.md 4-6);
4 round 238, checks/engine_sighted.py all (bench 11-15 CampSightedAll_mcp_1115_001541); 6 round 245,
checks/engine_enter.py all (bench 11-15 run_queue engine_area:all at bddb0af4, the build since renamed engine_enter).
"""
import engine.script.cond_object as simcond_object
import engine.script.cond_player as simcond_player
import engine.script.cond_show as simcond_show
import engine.script.cond_vision as simcond_vision
import engine.script.cond_world as simcond_world
from engine.world.handle import GAP_CONDITION

GROUPS = (simcond_world, simcond_object, simcond_vision, simcond_player, simcond_show)


def table(groups=GROUPS):
    """The groups' CONDITIONS in one dict; a name in two groups is an error."""
    out = {}
    for g in groups:
        twice = out.keys() & g.CONDITIONS.keys()
        if twice:
            raise ValueError(f'{g.__name__}: conditions already in another group: {sorted(twice)}')
        out.update(g.CONDITIONS)
    return out


CONDITIONS = table()


def cond(sim, name, a):
    """The condition `name`'s answer. Not taken (no group has it, or its guarded function declined): counted in
    sim.unknown and logged as a gap, false."""
    fn = CONDITIONS.get(name)
    got = fn(sim, name, a) if fn is not None else None
    if got is not None:
        return got
    sim.unknown[name] = sim.unknown.get(name, 0) + 1
    sim.gap(GAP_CONDITION, name, 'Sim.cond 不认识：当成不成立')
    return False
